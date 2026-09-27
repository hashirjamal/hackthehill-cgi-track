from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.agents.schemas import ActionItemOut, AgentDraftOutput
from app.agents.service import run_domain_agent
from app.classification.schemas import (
    ClassificationResult, ComplaintIn, GroupOut, PriorityOut, RoutingOut,
)
from app.db import Base
from app.models import ActionItem, AgentRun, DraftResponse

AS_OF = date(2026, 9, 30)


def _db():
    """Real SQLite via Base.metadata.create_all, plus the dashboard views build_context reads.

    The views (db/views.sql) only exist on Postgres; here they are stand-in tables shaped like the
    view output, following the precedent set in tests/test_agent_context.py.
    """
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.execute(text(
        "CREATE TABLE v_case_profile (category TEXT, region TEXT, source_system TEXT, n INT, "
        "avg_days REAL, info_only_share REAL, transfer_rate REAL, reopen_rate REAL, breach_rate REAL, "
        "top_resolution TEXT)"
    ))
    db.execute(text(
        "CREATE TABLE v_account_history (account_id TEXT, complaint_id TEXT, date_opened TEXT, "
        "category TEXT, status TEXT, resolution_action TEXT, days_to_close INT, is_repeat INT)"
    ))
    db.execute(text(
        "CREATE TABLE v_region_meter_complaints (region TEXT, month TEXT, estimated_read_rate REAL, "
        "smart_meter_penetration REAL, billing_exceptions_per_1000 REAL, billing_metering_share REAL)"
    ))
    return db


def _classification(*, emergency=False, group="Billing") -> ClassificationResult:
    return ClassificationResult(
        complaint_id="NW-1",
        classifier_version="test",
        emergency=emergency,
        emergency_probability=0.0,
        group=None if emergency else GroupOut(name=group, source="laya", laya_name=group, confidence=0.9,
                                               probabilities={group: 0.9}),
        priority=PriorityOut(level="P1" if emergency else "P3", target_days=5 if emergency else 20,
                              base_level="P1" if emergency else "P3",
                              base_source="emergency" if emergency else "laya", urgency_score=None, raised_by=[]),
        routing=RoutingOut(team="Emergency dispatch" if emergency else "Billing team",
                            lane="emergency" if emergency else "standard"),
    )


class SucceedingBackend:
    model_name = "fake-success"

    def draft(self, cfg, complaint, context):
        return AgentDraftOutput(
            draft_reply="Thanks for reaching out.",
            action_items=[ActionItemOut(action_type="correct_bill", description="Reissue the bill",
                                         rationale="x", rank=1)],
        )


class NoReplyBackend:
    model_name = "fake-no-reply"

    def draft(self, cfg, complaint, context):
        return AgentDraftOutput(draft_reply=None, action_items=[])


class FailingBackend:
    model_name = "fake-failure"

    def draft(self, cfg, complaint, context):
        from app.agents.backends import AgentBackendError
        raise AgentBackendError("the model is not running")


def test_successful_run_persists_draft_and_action_items():
    db = _db()
    complaint = ComplaintIn(complaint_id="NW-1", category="Billing - disputed amount", account_id="ACC-1")
    result = _classification()
    run = run_domain_agent(db, complaint, result, AS_OF, backend=SucceedingBackend())
    db.commit()
    assert run.status == "succeeded"
    assert run.finished_at is not None
    assert db.query(DraftResponse).filter_by(complaint_id="NW-1").count() == 1
    assert db.query(ActionItem).filter_by(complaint_id="NW-1").count() == 1


def test_no_reply_needed_skips_the_draft_response_row():
    db = _db()
    complaint = ComplaintIn(complaint_id="NW-1", category="Billing - disputed amount", account_id="ACC-1")
    run = run_domain_agent(db, complaint, _classification(), AS_OF, backend=NoReplyBackend())
    db.commit()
    assert run.status == "succeeded"
    assert db.query(DraftResponse).filter_by(complaint_id="NW-1").count() == 0


def test_a_failing_backend_marks_the_run_failed_and_does_not_raise():
    db = _db()
    complaint = ComplaintIn(complaint_id="NW-1", category="Billing - disputed amount", account_id="ACC-1")
    run = run_domain_agent(db, complaint, _classification(), AS_OF, backend=FailingBackend())
    db.commit()
    assert run.status == "failed"
    assert "not running" in run.error
    assert run.finished_at is not None
    assert db.query(DraftResponse).filter_by(complaint_id="NW-1").count() == 0


def test_emergency_complaints_skip_the_agent_entirely():
    db = _db()
    complaint = ComplaintIn(complaint_id="NW-1", category="Supply - interruption", account_id="ACC-1")
    run = run_domain_agent(db, complaint, _classification(emergency=True), AS_OF, backend=FailingBackend())
    db.commit()
    assert run is None
    assert db.query(AgentRun).count() == 0


def test_a_complaint_not_yet_in_the_complaints_table_still_gets_an_agent_run():
    # The endpoint also classifies new complaints that are not in `complaints` yet (like
    # `classifications`, the agent tables have no FK on complaint_id). SQLite ignores FKs unless
    # asked, so turn enforcement on to match Postgres; ai_agents does need the referenced row.
    db = _db()
    db.execute(text("PRAGMA foreign_keys=ON"))
    db.execute(text("INSERT INTO ai_agents (agent_id, name, active) VALUES ('billing', 'Billing', 1)"))
    complaint = ComplaintIn(complaint_id="NW-1", category="Billing - disputed amount", account_id="ACC-1")
    run = run_domain_agent(db, complaint, _classification(), AS_OF, backend=SucceedingBackend())
    db.commit()
    assert run.status == "succeeded"
    assert db.query(DraftResponse).filter_by(complaint_id="NW-1").count() == 1
    assert db.query(ActionItem).filter_by(complaint_id="NW-1").count() == 1
