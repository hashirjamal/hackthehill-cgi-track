from datetime import date

from app.classification import rules
from app.classification.rules import FlagHit


def hit(name, effect, level=None):
    return FlagHit(name, "text", effect, level)


def test_no_flags_keeps_base_level():
    d = rules.combine_priority(0, [])
    assert (d.priority, d.target_days, d.driving_flags) == ("P3", 20, [])


def test_at_least_floor_raises_but_never_lowers():
    assert rules.combine_priority(0, [hit("disconnection", "at_least", 1)]).priority == "P2"
    # A P1 case stays P1 when a flag only asks for P2.
    assert rules.combine_priority(2, [hit("disconnection", "at_least", 1)]).priority == "P1"


def test_vulnerable_goes_to_p1():
    assert rules.combine_priority(0, [hit("vulnerable", "at_least", 2)]).priority == "P1"


def test_raise_one_level_and_cap_at_p1():
    assert rules.combine_priority(0, [hit("repeat_contact", "raise_one")]).priority == "P2"
    assert rules.combine_priority(1, [hit("repeat_contact", "raise_one")]).priority == "P1"
    assert rules.combine_priority(2, [hit("repeat_contact", "raise_one")]).priority == "P1"


def test_several_flags_use_the_highest_required():
    hits = [hit("disconnection", "at_least", 1), hit("repeat_contact", "raise_one")]
    d = rules.combine_priority(0, hits)
    assert d.priority == "P2"
    assert sorted(d.driving_flags) == ["disconnection", "repeat_contact"]

    hits = [hit("disconnection", "at_least", 1), hit("vulnerable", "at_least", 2)]
    d = rules.combine_priority(0, hits)
    assert (d.priority, d.driving_flags) == ("P1", ["vulnerable"])


def test_quick_lane_flag_does_not_change_priority():
    assert rules.combine_priority(0, [hit("info_only", "quick_lane")]).priority == "P3"


def test_text_flags_fire_at_threshold():
    hits = rules.text_flag_hits({"disconnection": 0.5, "vulnerable": 0.49, "info_only": 0.9}, 0.5)
    assert {h.name for h in hits} == {"disconnection", "info_only"}


def test_legacy_region_needs_region_and_subcategory():
    assert rules.legacy_region_hit("Barrowdale", "Billing - estimated read")
    assert rules.legacy_region_hit("dunmoor", "Metering - no read taken")
    assert rules.legacy_region_hit("Ashford", "Billing - estimated read") is None
    assert rules.legacy_region_hit("Barrowdale", "Billing - disputed amount") is None
    assert rules.legacy_region_hit(None, "Billing - estimated read") is None


def test_regulator_referral():
    assert rules.regulator_referral_hit("Regulator referral").level == 1
    assert rules.regulator_referral_hit("Phone") is None


def test_deadline_risk_is_over_75_percent_of_target():
    assert rules.deadline_risk_hit(15, 20) is None  # exactly 75%
    assert rules.deadline_risk_hit(16, 20)
    assert rules.deadline_risk_hit(None, 20) is None
    assert rules.days_open(date(2026, 9, 2), date(2026, 9, 30)) == 28


def test_routing():
    hits = []
    assert rules.route("Billing - disputed amount", hits=hits, low_confidence=False) == ("Billing team", "standard")
    assert rules.route("Payment - plan or arrears", hits=hits, low_confidence=False) == ("Collections", "standard")
    # Low confidence always goes to a person.
    assert rules.route("Billing - disputed amount", hits=hits, low_confidence=True) == ("General review queue", "review")

    legacy = [FlagHit("legacy_region", "data", "route_metering")]
    assert rules.route("Billing - disputed amount", hits=legacy, low_confidence=False)[0] == "Metering team"

    quick = [hit("info_only", "quick_lane")]
    assert rules.route("Billing - disputed amount", hits=quick, low_confidence=False) == ("Billing team", "quick_lane")
