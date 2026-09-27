from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.laya_service import get_laya
from app.main import app
from app.models import ActionItem, AgentRun, Classification, DraftResponse


class FakeLaya:
    def predict(self, state, questions, model=None):
        answers = {}
        if "emergency" in questions:
            # Complaint text mentioning a gas leak screens as an emergency; nothing else does.
            return {"answers": {"emergency": {"noul": 0.95 if "gas leak" in state else 0.0}}}
        if "subcategory" in questions:
            names = list(questions["subcategory"]["criteria"])
            return {"answers": {"subcategory": {"probabilities": {n: 1.0 / len(names) for n in names}}}}
        if "group" in questions:
            names = list(questions["group"]["criteria"])
            probs = {n: (0.9 if n == "Customer support" else 0.1 / (len(names) - 1)) for n in names}
            answers["group"] = {"probabilities": probs}
        if "urgency" in questions:
            answers["urgency"] = {"score": 0.0, "probabilities": {"0": 1.0, "1": 0.0, "2": 0.0}}
        for name in ("disconnection", "vulnerable", "escalation_threat", "repeat_contact", "high_bill", "info_only"):
            answers[name] = {"noul": 0.0}
        return {"answers": answers}


def _client(monkeypatch, with_views=True):
    # FastAPI runs this (sync) route in a worker thread. Plain "sqlite://" defaults to
    # SingletonThreadPool, which hands that thread a *different*, empty in-memory database than
    # the one created below - StaticPool + check_same_thread=False shares the one connection
    # across threads (the pattern FastAPI's own testing docs use for this exact reason).
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    # The dashboard views build_context reads (db/views.sql) only exist on Postgres; here they are
    # empty stand-in tables shaped like the view output, following the precedent set in
    # tests/test_agent_context.py and tests/test_agent_service.py. with_views=False leaves them out,
    # like a fresh local SQLite database.
    if with_views:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE v_case_profile (category TEXT, region TEXT, source_system TEXT, n INT, "
                "avg_days REAL, info_only_share REAL, transfer_rate REAL, reopen_rate REAL, "
                "breach_rate REAL, top_resolution TEXT)"
            ))
            conn.execute(text(
                "CREATE TABLE v_account_history (account_id TEXT, complaint_id TEXT, date_opened TEXT, "
                "category TEXT, status TEXT, resolution_action TEXT, days_to_close INT, is_repeat INT)"
            ))
            conn.execute(text(
                "CREATE TABLE v_region_meter_complaints (region TEXT, month TEXT, estimated_read_rate REAL, "
                "smart_meter_penetration REAL, billing_exceptions_per_1000 REAL, billing_metering_share REAL)"
            ))

    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.complaint_routes.get_laya", lambda: FakeLaya())
    monkeypatch.setattr("app.complaint_routes.settings.agent_enabled", False)
    return TestClient(app), TestSession


def test_process_complaint_creates_an_agent_run_and_a_draft(monkeypatch):
    client, TestSession = _client(monkeypatch)
    # Seed a v_case_profile row with info_only_share >= 0.5, so TemplateBackend.draft() actually
    # produces a draft_reply (not just an action item) - matching what the test's name promises.
    seed_db = TestSession()
    seed_db.execute(text(
        "INSERT INTO v_case_profile VALUES ('Service - poor communication', 'Ashford', 'SYS-01', "
        "100, 10.0, 0.6, 0.1, 0.05, 0.2, 'Information provided')"
    ))
    seed_db.commit()
    seed_db.close()

    response = client.post("/complaints/process", json={
        "as_of_date": "2026-09-30",
        "complaints": [{"complaint_id": "NW-1", "category": "Service - poor communication",
                         "region": "Ashford", "source_system": "SYS-01", "account_id": "ACC-1"}],
    })
    assert response.status_code == 200

    db = TestSession()
    run = db.query(AgentRun).filter_by(complaint_id="NW-1").one()
    assert run.status == "succeeded"
    assert run.model == "template"
    drafts = db.query(DraftResponse).filter_by(complaint_id="NW-1").all()
    assert len(drafts) == 1 and drafts[0].body
    assert db.query(ActionItem).filter_by(complaint_id="NW-1").count() == 1
    db.close()


def test_a_batch_with_no_case_history_still_returns_200(monkeypatch):
    # No matching v_case_profile/v_account_history/v_region_meter_complaints rows exist in this
    # empty test DB at all - confirms the agent step degrades gracefully end-to-end (Review Focus).
    client, _ = _client(monkeypatch)
    response = client.post("/complaints/process", json={
        "as_of_date": "2026-09-30",
        "complaints": [{"complaint_id": "NW-2", "category": "Other", "account_id": "ACC-2"}],
    })
    assert response.status_code == 200


def test_a_batch_of_several_complaints_creates_an_agent_run_for_each(monkeypatch):
    client, TestSession = _client(monkeypatch)
    response = client.post("/complaints/process", json={
        "as_of_date": "2026-09-30",
        "complaints": [
            {"complaint_id": "NW-3", "category": "Other", "account_id": "ACC-3"},
            {"complaint_id": "NW-4", "category": "Metering - no read taken", "account_id": "ACC-4"},
        ],
    })
    assert response.status_code == 200

    db = TestSession()
    runs = db.query(AgentRun).filter(AgentRun.complaint_id.in_(["NW-3", "NW-4"])).all()
    assert {r.complaint_id for r in runs} == {"NW-3", "NW-4"}
    assert all(r.status == "succeeded" for r in runs)
    db.close()


def test_a_database_error_in_the_agent_step_keeps_the_batch_classifications(monkeypatch, caplog):
    # Without the dashboard views (a fresh local SQLite DB has none), build_context fails with a
    # database error. That must roll back only the agent step, not the batch's classifications.
    client, TestSession = _client(monkeypatch, with_views=False)
    response = client.post("/complaints/process", json={
        "as_of_date": "2026-09-30",
        "complaints": [
            {"complaint_id": "NW-5", "category": "Other", "account_id": "ACC-5"},
            {"complaint_id": "NW-6", "category": "Other", "account_id": "ACC-6"},
        ],
    })
    assert response.status_code == 200

    db = TestSession()
    assert {c.complaint_id for c in db.query(Classification).all()} == {"NW-5", "NW-6"}
    assert db.query(AgentRun).count() == 0  # the savepoint rolled back the half-written run
    db.close()
    assert "Agent step failed for complaint NW-5" in caplog.text


class FailingBackend:
    model_name = "fake-failure"

    def draft(self, cfg, complaint, context):
        from app.agents.backends import AgentBackendError
        raise AgentBackendError("the model is not running")


def test_a_mixed_batch_with_a_failing_agent_and_an_emergency_still_returns_200(monkeypatch):
    client, TestSession = _client(monkeypatch)
    monkeypatch.setattr("app.complaint_routes._agent_backend", lambda: FailingBackend())
    response = client.post("/complaints/process", json={
        "as_of_date": "2026-09-30",
        "complaints": [
            {"complaint_id": "NW-7", "category": "Billing - disputed amount", "account_id": "ACC-7"},
            {"complaint_id": "NW-8", "text": "I can smell a gas leak outside my house", "account_id": "ACC-8"},
        ],
    })
    assert response.status_code == 200
    by_id = {r["complaint_id"]: r for r in response.json()["results"]}
    assert by_id["NW-8"]["emergency"] is True

    db = TestSession()
    failed = db.query(AgentRun).filter_by(complaint_id="NW-7").one()
    assert failed.status == "failed"
    assert "not running" in failed.error
    assert db.query(AgentRun).filter_by(complaint_id="NW-8").count() == 0
    assert db.query(AgentRun).count() == 1
    db.close()
