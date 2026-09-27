from datetime import date

from fastapi.testclient import TestClient
from langchain.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.laya_service import get_laya
from app.main import app
from app.models import AgentRun, ChatMessage, ChatSession, Classification, Complaint, DraftResponse


class FakeLaya:
    def predict(self, state, questions, model=None):
        answers = {}
        if "emergency" in questions:
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


class ScriptedChatModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _client(monkeypatch):
    # FastAPI runs this (sync) route in a worker thread. Plain "sqlite://" defaults to
    # SingletonThreadPool, which hands that thread a *different*, empty in-memory database than
    # the one created below - StaticPool + check_same_thread=False shares the one connection
    # across threads (the pattern FastAPI's own testing docs use for this exact reason).
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    # The dashboard views app/agents/tools.py reads only exist on Postgres; here they are empty
    # stand-in tables shaped like the view output, following the precedent in tests/test_agent_tools.py.
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE v_case_profile (category TEXT, region TEXT, source_system TEXT, n INT, "
            "avg_days REAL, info_only_share REAL, transfer_rate REAL, reopen_rate REAL, "
            "breach_rate REAL, top_resolution TEXT)"
        ))
        conn.execute(text(
            "CREATE TABLE v_account_history (account_id TEXT, complaint_id TEXT, date_opened TEXT, "
            "category TEXT, status TEXT, resolution_action TEXT)"
        ))
        conn.execute(text(
            "CREATE TABLE v_region_meter_complaints (region TEXT, month TEXT, estimated_read_rate REAL, "
            "smart_meter_penetration REAL, billing_exceptions_per_1000 REAL)"
        ))

    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    # setitem is undone after each test, so the override never leaks into other test files.
    monkeypatch.setitem(app.dependency_overrides, get_db, override_get_db)
    monkeypatch.setattr("app.complaint_routes.get_laya", lambda: FakeLaya())
    monkeypatch.setattr("app.complaint_routes.settings.agent_enabled", False)
    return TestClient(app), TestSession


def _complaint(**overrides) -> Complaint:
    fields = dict(
        complaint_id="NW-1", account_id="ACC-1", date_opened=date(2026, 9, 1), status="Open",
        channel="Phone", category="Billing - disputed amount", priority="P3", region="Ashford",
        source_system="SYS-01", transferred_between_systems=False, sla_days=20, sla_breach=False,
        reopened=False,
    )
    fields.update(overrides)
    return Complaint(**fields)


def _current_classification(complaint_id: str, group_name: str) -> Classification:
    return Classification(
        complaint_id=complaint_id, classifier_version="test", is_current=True, as_of_date=date(2026, 9, 30),
        input={}, emergency=False, group_name=group_name, priority="P3", base_priority="P3",
        base_priority_source="data", routed_team="Billing team", lane="standard", flags=[], laya_output={},
    )


def test_process_complaints_classifies_without_running_any_agent(monkeypatch):
    client, TestSession = _client(monkeypatch)
    response = client.post("/complaints/process", json={
        "as_of_date": "2026-09-30",
        "complaints": [{"complaint_id": "NW-1", "category": "Other", "account_id": "ACC-1"}],
    })
    assert response.status_code == 200

    db = TestSession()
    assert db.query(Classification).filter_by(complaint_id="NW-1").count() == 1
    assert db.query(AgentRun).count() == 0  # nothing runs automatically any more
    db.close()


def test_chat_with_an_unknown_complaint_returns_404(monkeypatch):
    client, _ = _client(monkeypatch)
    response = client.post("/complaints/NW-999/chat", json={"message": "hello"})
    assert response.status_code == 404


def test_chat_uses_the_fallback_message_when_agent_is_disabled(monkeypatch):
    client, TestSession = _client(monkeypatch)  # agent_enabled=False, set in _client
    db = TestSession()
    db.add(_complaint())
    db.add(_current_classification("NW-1", "Billing"))
    db.commit()
    db.close()

    response = client.post("/complaints/NW-1/chat", json={"message": "Analyze this account."})
    assert response.status_code == 200
    body = response.json()
    assert "turned off" in body["reply"]
    assert body["draft_saved"] is False

    db = TestSession()
    session = db.query(ChatSession).filter_by(complaint_id="NW-1").one()
    messages = db.query(ChatMessage).filter_by(session_id=session.session_id).order_by(ChatMessage.message_id).all()
    assert [m.role for m in messages] == ["staff", "assistant"]
    assert messages[0].content == "Analyze this account."
    db.close()


def test_chat_runs_the_scripted_model_with_the_billing_tools_and_can_save_a_draft(monkeypatch):
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint())
    db.add(_current_classification("NW-1", "Billing"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "save_draft_reply", "args": {"body": "Sorry for the delay."}, "id": "1"}]),
        AIMessage(content="I've drafted a reply for you to review."),
    ])
    monkeypatch.setattr("app.complaint_routes._build_chat_model", lambda: fake)

    response = client.post("/complaints/NW-1/chat", json={"message": "Draft an apology for the delay."})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "I've drafted a reply for you to review."
    assert body["draft_saved"] is True

    db = TestSession()
    draft = db.query(DraftResponse).filter_by(complaint_id="NW-1").one()
    assert draft.body == "Sorry for the delay."
    db.close()


def test_chat_with_a_domain_that_has_no_tools_yet_still_works(monkeypatch):
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint(complaint_id="NW-2", category="Metering - no read taken"))
    db.add(_current_classification("NW-2", "Metering"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[AIMessage(content="No meter tools exist yet, but I can still chat.")])
    monkeypatch.setattr("app.complaint_routes._build_chat_model", lambda: fake)

    response = client.post("/complaints/NW-2/chat", json={"message": "What's up with this case?"})
    assert response.status_code == 200
    assert response.json()["reply"] == "No meter tools exist yet, but I can still chat."
