"""Pipeline tests with a fake Laya, so they run without the model download."""
from datetime import date

from app.classification.schemas import ComplaintIn
from app.classification.service import classify_complaint, render_state
from app.classification.taxonomy import TEXT_FLAG_QUESTIONS
from app.config import settings

AS_OF = date(2026, 9, 30)


class FakeLaya:
    """Returns canned answers shaped like Laya's. Unset text flags answer 0."""

    def __init__(self, *, emergency=0.0, group="Billing", group_p=0.9, urgency=0, flags=None, subcategory=None):
        self.emergency, self.group, self.group_p = emergency, group, group_p
        self.urgency, self.flags, self.subcategory = urgency, flags or {}, subcategory
        self.calls = []

    def predict(self, state, questions, model=None):
        self.calls.append(sorted(questions))
        if "emergency" in questions:
            return {"answers": {"emergency": {"noul": self.emergency}}}
        if "subcategory" in questions:
            names = list(questions["subcategory"]["criteria"])
            chosen = self.subcategory or names[0]
            probs = {n: (0.8 if n == chosen else 0.1) for n in names}
            return {"answers": {"subcategory": {"probabilities": probs}}}
        answers = {}
        if "group" in questions:
            names = list(questions["group"]["criteria"])
            rest = (1 - self.group_p) / (len(names) - 1)
            answers["group"] = {"probabilities": {n: (self.group_p if n == self.group else rest) for n in names}}
        if "urgency" in questions:
            answers["urgency"] = {
                "score": float(self.urgency),
                "probabilities": {str(i): (1.0 if i == self.urgency else 0.0) for i in range(3)},
            }
        for name in TEXT_FLAG_QUESTIONS:
            answers[name] = {"noul": self.flags.get(name, 0.0)}
        return {"answers": answers}


def run(fake, **fields):
    fields.setdefault("text", "text")
    complaint = ComplaintIn(**fields)
    result, _ = classify_complaint(complaint, "C1", AS_OF, fake, settings)
    return result


def test_emergency_skips_everything_else():
    fake = FakeLaya(emergency=0.9)
    result = run(fake)
    assert result.emergency and result.routing.team == "Emergency dispatch" and result.priority.level == "P1"
    assert result.group is None
    assert fake.calls == [["emergency"]]


def test_single_option_group_skips_stage_two():
    fake = FakeLaya(group="Metering")
    result = run(fake)
    assert result.subcategory.name == "Metering - no read taken" and result.subcategory.confidence is None
    assert ["subcategory"] not in fake.calls


def test_multi_option_group_runs_stage_two():
    fake = FakeLaya(group="Field services", subcategory="Water - pressure or quality")
    result = run(fake)
    assert result.subcategory.name == "Water - pressure or quality"
    assert result.routing.team == "Water operations"
    assert ["subcategory"] in fake.calls


def test_low_confidence_with_no_data_category_goes_to_review_and_skips_stage_two():
    fake = FakeLaya(group="Billing", group_p=0.5)
    result = run(fake)
    assert result.low_confidence
    assert (result.routing.team, result.routing.lane) == ("General review queue", "review")
    assert result.subcategory is None
    assert ["subcategory"] not in fake.calls


def test_low_confidence_falls_back_to_the_data_category():
    fake = FakeLaya(group="Customer support", group_p=0.4)  # Laya is unsure and picks the wrong group
    result = run(fake, text=None, category="Service - missed appointment")
    assert result.low_confidence
    assert (result.group.name, result.group.source, result.group.laya_name) == ("Field services", "data", "Customer support")
    assert (result.subcategory.name, result.subcategory.source) == ("Service - missed appointment", "data")
    assert (result.routing.team, result.routing.lane) == ("Field services", "standard")  # not the review queue
    assert ["subcategory"] not in fake.calls  # stage 2 is skipped
    assert result.group_matches_data is False  # Laya's own pick is what is compared
    assert result.subcategory_matches_data is None


def test_confident_laya_is_not_replaced_by_the_data_category():
    fake = FakeLaya(group="Field services", group_p=0.9, subcategory="Water - pressure or quality")
    result = run(fake, text=None, category="Service - missed appointment")
    assert not result.low_confidence
    assert (result.group.source, result.subcategory.source) == ("laya", "laya")
    assert result.routing.team == "Water operations"


def test_estimated_read_routes_to_metering_team():
    result = run(FakeLaya(group="Billing", subcategory="Billing - estimated read"))
    assert result.routing.team == "Metering team" and result.likely_cause is None


def test_legacy_region_tags_cause_and_routes_to_metering():
    result = run(FakeLaya(group="Billing", subcategory="Billing - disputed amount"), region="Barrowdale")
    assert result.likely_cause is None  # disputed amount is not an estimated-read complaint

    result = run(FakeLaya(group="Billing", subcategory="Billing - estimated read"), region="Barrowdale")
    assert result.likely_cause == "estimated_reading" and result.routing.team == "Metering team"


def test_flags_raise_priority_and_info_only_uses_quick_lane():
    result = run(FakeLaya(urgency=0, flags={"vulnerable": 0.8, "info_only": 0.7}))
    assert result.priority.level == "P1" and result.priority.base_level == "P3"
    assert result.priority.raised_by == ["vulnerable"]
    assert result.routing.lane == "quick_lane"


def test_regulator_referral_raises_to_p2():
    result = run(FakeLaya(urgency=0), channel="Regulator referral")
    assert result.priority.level == "P2" and result.priority.raised_by == ["regulator_referral"]


def test_deadline_risk_uses_existing_target():
    # Opened 28 days before AS_OF, 20-day target: over 75%, so one level up.
    result = run(FakeLaya(urgency=0), date_opened=date(2026, 9, 2), sla_days=20)
    assert result.priority.level == "P2" and result.priority.raised_by == ["deadline_risk"]

    result = run(FakeLaya(urgency=0), date_opened=date(2026, 9, 28), sla_days=20)
    assert result.priority.level == "P3"


def test_new_complaint_without_dates_has_no_deadline_flag():
    assert run(FakeLaya(urgency=1)).priority.level == "P2"


# Laya runs every step, even when the data already has the category and the priority.


def test_laya_runs_every_step_even_when_the_data_has_category_and_priority():
    fake = FakeLaya(group="Billing", subcategory="Payment - plan or arrears", urgency=1)
    result = run(fake, text=None, category="Payment - plan or arrears", priority="P3")
    assert fake.calls[0] == ["emergency"]
    assert "group" in fake.calls[1] and set(TEXT_FLAG_QUESTIONS) <= set(fake.calls[1])
    assert ["subcategory"] in fake.calls  # stage 2 runs for a multi-option group
    assert result.subcategory.name == "Payment - plan or arrears"


def test_data_priority_is_the_starting_point_and_flags_raise_it():
    fake = FakeLaya(urgency=2, flags={"disconnection": 0.9})
    result = run(fake, text=None, category="Other", priority="P3")
    assert "urgency" not in fake.calls[1]  # Laya is not asked for it
    assert (result.priority.base_level, result.priority.base_source) == ("P3", "data")
    assert result.priority.level == "P2" and result.priority.raised_by == ["disconnection"]  # flag raises it

    # Flags never lower it.
    result = run(FakeLaya(flags={"disconnection": 0.9}), text=None, category="Other", priority="P1")
    assert result.priority.level == "P1"


def test_sla_target_gives_the_priority_when_priority_is_missing():
    result = run(FakeLaya(urgency=2), text=None, category="Other", sla_days=10)
    assert (result.priority.base_level, result.priority.base_source) == ("P2", "data")


def test_laya_urgency_is_used_only_when_the_data_has_no_priority():
    result = run(FakeLaya(urgency=2), text=None, category="Other")
    assert (result.priority.base_level, result.priority.base_source) == ("P1", "laya")
    assert result.priority.urgency_score == 2.0


def test_data_category_is_compared_with_laya_not_used_instead_of_it():
    result = run(FakeLaya(group="Billing", subcategory="Billing - disputed amount"), text=None,
                 category="Billing - disputed amount")
    assert result.group_matches_data and result.subcategory_matches_data

    result = run(FakeLaya(group="Field services", subcategory="Water - pressure or quality"), text=None,
                 category="Billing - disputed amount")
    assert result.group_matches_data is False and result.subcategory_matches_data is False
    assert result.routing.team == "Water operations"  # Laya's answer routes the case

    result = run(FakeLaya(), text="something")
    assert result.data_category is None and result.group_matches_data is None


def test_state_describes_the_record_without_ids_or_dates():
    c = ComplaintIn(complaint_id="NW-1", account_id="ACC-1", date_opened=date(2026, 9, 2), category="Other",
                    channel="Phone", priority="P3", sla_days=20, region="Ashford", source_system="SYS-05",
                    transferred_between_systems=True)
    state = render_state(c)
    assert "Category: Other" in state and "Priority: P3, target 20 days" in state
    assert "Transferred between systems: yes" in state and "Source system: SYS-05" in state
    assert "NW-1" not in state and "ACC-1" not in state and "2026" not in state


def test_text_is_added_to_the_state_when_there_is_some():
    assert "Customer said: my bill is wrong" in render_state(ComplaintIn(text="my bill is wrong"))


def test_needs_text_or_category():
    import pytest

    with pytest.raises(ValueError):
        ComplaintIn(priority="P3")
    with pytest.raises(ValueError):
        ComplaintIn(category="Not a category")


def test_cache_answers_repeat_states_once(monkeypatch):
    from app import laya_service

    calls = []

    class Router:
        def predict(self, state, questions):
            calls.append(state)
            return {"answers": {}}

    monkeypatch.setattr(laya_service, "get_router", lambda: Router())
    cached = laya_service.CachedLaya()
    q = {"q": {"type": "noul", "instructions": "x"}}
    cached.predict("a", q)
    cached.predict("a", q)
    cached.predict("b", q)
    assert calls == ["a", "b"]
