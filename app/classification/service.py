"""Two-stage Laya classification of a complaint.

Order: emergency screen, then stage 1 (group, urgency, text flags), then stage 2 (subcategory,
only for groups with several options), then the data flags and the priority rules.
Laya runs every step on every complaint. It reads a description of the complaint's fields, and the
text too when there is any. The category already in the data is not used to skip a step; it is only
compared with Laya's answer afterwards. The one exception is priority: Northwind's own priority is the
starting point when the complaint has one, and Laya's urgency score is used only when it does not.
When Laya's top group probability is under the threshold, the category in the data is used instead, and only
a complaint with no data category goes to the review queue.
"""
from datetime import date
from typing import Any

from sqlalchemy import text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.classification import rules
from app.classification.schemas import (
    ClassificationResult,
    ComplaintIn,
    FlagOut,
    GroupOut,
    PriorityOut,
    RoutingOut,
    SubcategoryOut,
)
from app.classification.taxonomy import (
    CATEGORY_TO_GROUP,
    EMERGENCY_QUESTION,
    GROUPS,
    TARGET_DAYS_TO_PRIORITY,
    TEXT_FLAG_QUESTIONS,
    stage1_questions,
    stage2_question,
)
from app.config import Settings, settings
from app.models import Classification

CLASSIFIER_VERSION = "laya-two-stage-v4"


def render_state(complaint: ComplaintIn) -> str:
    """Describe the complaint for Laya. Ids and dates are left out, so similar complaints share answers."""
    parts = ["Customer complaint."]
    if complaint.category:
        parts.append(f"Category: {complaint.category}.")
    if complaint.channel:
        parts.append(f"Channel: {complaint.channel}.")
    if complaint.priority:
        target = f", target {complaint.sla_days} days" if complaint.sla_days else ""
        parts.append(f"Priority: {complaint.priority}{target}.")
    if complaint.region:
        parts.append(f"Region: {complaint.region}.")
    if complaint.source_system:
        parts.append(f"Source system: {complaint.source_system}.")
    if complaint.transferred_between_systems is not None:
        parts.append(f"Transferred between systems: {'yes' if complaint.transferred_between_systems else 'no'}.")
    if complaint.text:
        parts.append(f"Customer said: {complaint.text}")
    return " ".join(parts)


def classify_complaint(
    complaint: ComplaintIn,
    complaint_id: str,
    as_of: date,
    laya: Any,
    cfg: Settings = settings,
) -> tuple[ClassificationResult, dict]:
    """Classify one complaint. Returns the result and Laya's raw answers (kept for the audit trail)."""
    state = render_state(complaint)
    raw: dict[str, Any] = {"state": state}

    raw["emergency"] = laya.predict(state, {"emergency": EMERGENCY_QUESTION})["answers"]
    emergency_p = raw["emergency"]["emergency"]["noul"]
    if emergency_p >= cfg.emergency_threshold:
        team, lane = rules.emergency_route()
        return ClassificationResult(
            complaint_id=complaint_id,
            classifier_version=CLASSIFIER_VERSION,
            emergency=True,
            emergency_probability=emergency_p,
            priority=PriorityOut(
                level="P1", target_days=5, base_level="P1", base_source="emergency", urgency_score=None,
                raised_by=["emergency"],
            ),
            routing=RoutingOut(team=team, lane=lane),
            data_category=complaint.category,
        ), raw

    # Northwind's priority (or the SLA target that goes with it) is the starting point when there is one.
    data_priority = complaint.priority or TARGET_DAYS_TO_PRIORITY.get(complaint.sla_days)
    raw["stage1"] = laya.predict(state, stage1_questions(need_urgency=data_priority is None))["answers"]
    s1 = raw["stage1"]

    group_probs = s1["group"]["probabilities"]
    group_name = max(group_probs, key=group_probs.get)
    group_conf = group_probs[group_name]
    low_confidence = group_conf < cfg.group_confidence_threshold

    urgency_score = None
    if data_priority:
        base_level, base_source = rules.PRIORITY_TO_LEVEL[data_priority], "data"
    else:
        urgency_probs = s1["urgency"]["probabilities"]
        base_level, base_source = int(max(urgency_probs, key=urgency_probs.get)), "laya"
        urgency_score = s1["urgency"]["score"]
    text_probs = {name: s1[name]["noul"] for name in TEXT_FLAG_QUESTIONS}

    # Low confidence: fall back to the category already in the data. With no data category there is
    # nothing to fall back to, so the case goes to the review queue. Either way stage 2 is skipped.
    subcategory: SubcategoryOut | None = None
    used_group, group_source = group_name, "laya"
    needs_review = False
    if low_confidence:
        if complaint.category:
            used_group, group_source = CATEGORY_TO_GROUP[complaint.category], "data"
            subcategory = SubcategoryOut(name=complaint.category, source="data", confidence=None)
        else:
            needs_review = True
    else:
        options = GROUPS[group_name]["subcategories"]
        if len(options) == 1:
            subcategory = SubcategoryOut(name=options[0], source="laya", confidence=None)
        else:
            raw["stage2"] = laya.predict(state, {"subcategory": stage2_question(group_name)})["answers"]
            probs = raw["stage2"]["subcategory"]["probabilities"]
            name = max(probs, key=probs.get)
            subcategory = SubcategoryOut(name=name, source="laya", confidence=probs[name])

    hits = rules.text_flag_hits(text_probs, cfg.flag_threshold)
    for hit in (
        rules.legacy_region_hit(complaint.region, subcategory.name if subcategory else None),
        rules.regulator_referral_hit(complaint.channel),
    ):
        if hit:
            hits.append(hit)

    # Deadline risk is measured against Northwind's existing target, or the target of the
    # priority reached so far when the case has none.
    open_days = rules.days_open(complaint.date_opened, as_of)
    target = complaint.sla_days or rules.combine_priority(base_level, hits).target_days
    deadline = rules.deadline_risk_hit(open_days, target)
    if deadline:
        hits.append(deadline)

    decision = rules.combine_priority(base_level, hits)
    team, lane = rules.route(subcategory.name if subcategory else "Other", hits=hits, low_confidence=needs_review)
    legacy = any(h.effect == "route_metering" for h in hits)

    data_category = complaint.category
    return ClassificationResult(
        complaint_id=complaint_id,
        classifier_version=CLASSIFIER_VERSION,
        emergency=False,
        emergency_probability=emergency_p,
        group=GroupOut(
            name=used_group,
            source=group_source,
            laya_name=group_name,
            confidence=group_conf,
            probabilities=group_probs,
        ),
        subcategory=subcategory,
        low_confidence=low_confidence,
        priority=PriorityOut(
            level=decision.priority,
            target_days=decision.target_days,
            base_level=rules.LEVEL_TO_PRIORITY[decision.base_level],
            base_source=base_source,
            urgency_score=urgency_score,
            raised_by=decision.driving_flags,
        ),
        routing=RoutingOut(team=team, lane=lane),
        flags=[
            FlagOut(name=h.name, source=h.source, effect=h.effect, probability=h.probability, reason=h.reason)
            for h in hits
        ],
        text_flag_probabilities=text_probs,
        likely_cause="estimated_reading" if legacy else None,
        data_category=data_category,
        # Compared on Laya's own answers, so a data fallback does not count as a match.
        group_matches_data=(group_name == CATEGORY_TO_GROUP[data_category]) if data_category else None,
        subcategory_matches_data=(
            (subcategory.name == data_category) if data_category and subcategory and subcategory.source == "laya" else None
        ),
    ), raw


def db_as_of_date(db: Session) -> date | None:
    """The as_of_date row in app_settings (db/schema.sql), or None when the table or row is not there."""
    try:
        value = db.execute(text("SELECT value FROM app_settings WHERE key = 'as_of_date'")).scalar()
    except DBAPIError:
        db.rollback()  # a failed query aborts the transaction on Postgres
        return None
    return date.fromisoformat(value) if value else None


def save_classification(
    db: Session, complaint: ComplaintIn, result: ClassificationResult, raw: dict, as_of: date
) -> int:
    """Store the result as the complaint's current classification. Earlier ones are kept as history."""
    db.execute(
        update(Classification)
        .where(Classification.complaint_id == result.complaint_id, Classification.is_current.is_(True))
        .values(is_current=False)
    )
    row = Classification(
        complaint_id=result.complaint_id,
        classifier_version=result.classifier_version,
        as_of_date=as_of,
        input=complaint.model_dump(mode="json"),
        emergency=result.emergency,
        emergency_probability=result.emergency_probability,
        group_name=result.group.name if result.group else None,
        group_confidence=result.group.confidence if result.group else None,
        group_source=result.group.source if result.group else None,
        laya_group=result.group.laya_name if result.group else None,
        subcategory=result.subcategory.name if result.subcategory else None,
        subcategory_confidence=result.subcategory.confidence if result.subcategory else None,
        subcategory_source=result.subcategory.source if result.subcategory else None,
        low_confidence=result.low_confidence,
        group_matches_data=result.group_matches_data,
        subcategory_matches_data=result.subcategory_matches_data,
        priority=result.priority.level,
        base_priority=result.priority.base_level,
        base_priority_source=result.priority.base_source,
        urgency_score=result.priority.urgency_score,
        routed_team=result.routing.team,
        lane=result.routing.lane,
        likely_cause=result.likely_cause,
        flags=[f.model_dump() for f in result.flags],
        laya_output=raw,
    )
    db.add(row)
    db.flush()
    return row.id
