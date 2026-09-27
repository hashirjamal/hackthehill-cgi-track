from datetime import date

from fastapi.testclient import TestClient
from langchain.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.classification.taxonomy import TEXT_FLAG_QUESTIONS
from app.laya_service import get_laya
from app.main import app
from app.models import Account, ActionItem, AgentRun, Classification, Complaint, DraftResponse, Region


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
        for name in TEXT_FLAG_QUESTIONS:
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
    # Point the Northwind systems at a closed port, so tests never reach servers running locally.
    for name in ("helix_url", "aurora_url", "casetrack_url", "callcentre_url", "connect_url"):
        monkeypatch.setattr(f"app.config.settings.{name}", "http://127.0.0.1:9")
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
    assert db.query(AgentRun).count() == 0  # nothing runs until a button is clicked
    db.close()


def test_get_context_with_an_unknown_complaint_returns_404(monkeypatch):
    client, _ = _client(monkeypatch)
    assert client.post("/complaints/NW-999/context").status_code == 404


def test_generate_draft_with_an_unknown_complaint_returns_404(monkeypatch):
    client, _ = _client(monkeypatch)
    assert client.post("/complaints/NW-999/draft").status_code == 404


def test_get_context_with_ai_disabled_uses_the_no_ai_rules(monkeypatch):
    client, TestSession = _client(monkeypatch)  # agent_enabled=False, set in _client
    db = TestSession()
    db.add(_complaint(category="Service - missed appointment"))
    db.add(_current_classification("NW-1", "Field services"))
    db.commit()
    db.close()

    body = client.post("/complaints/NW-1/context").json()
    assert (body["status"], body["mode"]) == ("succeeded", "rules")
    assert "turned off" in body["error"]
    assert body["action_items"][0]["action_type"] == "rebook_and_compensate"
    # The systems are unreachable in tests: that is traced, and the rules carry on regardless.
    assert body["systems_checked"][0]["summary"] == "Helix CIS did not respond."

    db = TestSession()
    run = db.query(AgentRun).filter_by(complaint_id="NW-1").one()
    assert (run.status, run.model, run.context["mode"]) == ("succeeded", "rules (no AI)", "rules")
    db.close()


def test_rules_mode_never_calls_the_model_even_when_ai_is_on(monkeypatch):
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint())
    db.commit()
    db.close()

    def no_model():
        raise AssertionError("rules mode must not build a model")

    monkeypatch.setattr("app.complaint_routes._build_agent_model", no_model)
    body = client.post("/complaints/NW-1/draft?mode=rules").json()
    assert (body["status"], body["mode"], body["error"]) == ("succeeded", "rules", None)
    assert body["body"].startswith("Dear Customer,")  # Helix unreachable, so no name
    assert "[Your name], Northwind Energy & Water" in body["body"]


def test_get_context_runs_the_scripted_model_and_returns_the_action_items(monkeypatch):
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint())
    db.add(_current_classification("NW-1", "Billing"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "create_action_brief",
            "args": {"action_type": "correct_bill", "description": "Reissue the bill", "rationale": "Estimated read"},
            "id": "1",
        }]),
        AIMessage(content="Done."),
    ])
    monkeypatch.setattr("app.complaint_routes._build_agent_model", lambda: fake)

    response = client.post("/complaints/NW-1/context")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert len(body["action_items"]) == 1
    assert body["action_items"][0]["action_type"] == "correct_bill"

    db = TestSession()
    assert db.query(ActionItem).filter_by(complaint_id="NW-1").count() == 1
    assert db.query(DraftResponse).count() == 0  # the context tool set has no drafting tool at all
    db.close()


def test_generate_draft_runs_the_scripted_model_and_returns_the_draft(monkeypatch):
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint())
    db.add(_current_classification("NW-1", "Billing"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "save_draft_reply", "args": {"body": "Sorry for the delay."}, "id": "1",
        }]),
        AIMessage(content="Done."),
    ])
    monkeypatch.setattr("app.complaint_routes._build_agent_model", lambda: fake)

    response = client.post("/complaints/NW-1/draft")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["body"] == "Sorry for the delay."

    db = TestSession()
    assert db.query(DraftResponse).filter_by(complaint_id="NW-1").count() == 1
    assert db.query(ActionItem).count() == 0  # the draft tool set has no action-item tool at all
    db.close()


def test_get_context_for_an_unclassified_complaint_still_works(monkeypatch):
    # No current Classification row at all - agent_id resolves to None, AgentRun falls back to
    # the "general" ai_agents row, and the case still gets the shared context tools.
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint(complaint_id="NW-2", category="Other"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "create_action_brief",
            "args": {"action_type": "review", "description": "Review the case", "rationale": "Not yet classified"},
            "id": "1",
        }]),
        AIMessage(content="Done."),
    ])
    monkeypatch.setattr("app.complaint_routes._build_agent_model", lambda: fake)

    response = client.post("/complaints/NW-2/context")
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"

    db = TestSession()
    run = db.query(AgentRun).filter_by(complaint_id="NW-2").one()
    assert run.agent_id == "general"
    db.close()


def test_get_context_falls_back_to_rules_when_the_model_never_calls_create_action_brief(monkeypatch):
    # Finishing without an exception is not the same as doing what was asked - a model that just
    # answers in plain text gets replaced by the no-AI rules, and the note says so.
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint(category="Service - poor communication"))
    db.add(_current_classification("NW-1", "Customer support"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[AIMessage(content="I looked into it but have no recommendation.")])
    monkeypatch.setattr("app.complaint_routes._build_agent_model", lambda: fake)

    body = client.post("/complaints/NW-1/context").json()
    assert (body["status"], body["mode"]) == ("succeeded", "rules")
    assert "did not record any action items" in body["error"]
    assert [a["action_type"] for a in body["action_items"]] == ["named_handler"]


def test_generate_draft_falls_back_to_rules_when_the_model_never_calls_save_draft_reply(monkeypatch):
    client, TestSession = _client(monkeypatch)
    db = TestSession()
    db.add(_complaint())
    db.add(_current_classification("NW-1", "Billing"))
    db.commit()
    db.close()

    fake = ScriptedChatModel(responses=[AIMessage(content="I'm not sure what to say here.")])
    monkeypatch.setattr("app.complaint_routes._build_agent_model", lambda: fake)

    body = client.post("/complaints/NW-1/draft").json()
    assert (body["status"], body["mode"]) == ("succeeded", "rules")
    assert "did not save a draft" in body["error"]
    assert body["body"].startswith("Dear Customer,")



def _intake(**overrides) -> dict:
    body = dict(
        account_id="ACC-1", text="My bill doubled this month and nobody will explain why.",
        channel="Phone", region="Ashford", source_system="SYS-05",
    )
    body.update(overrides)
    return body


def _seed_region(TestSession, region="Ashford"):
    db = TestSession()
    db.add(Region(region=region))
    db.commit()
    db.close()


def test_intake_saves_a_new_open_complaint_classified_by_laya(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    db = TestSession()
    db.add(_complaint(complaint_id="NW-124205"))
    db.commit()
    db.close()

    response = client.post("/complaints/intake", json=_intake())
    assert response.status_code == 200
    body = response.json()
    assert body["complaint_id"] == "NW-124206"  # continues Northwind's numbering
    # No Northwind priority on a new complaint, so urgency comes from Laya, not the history.
    assert body["classification"]["priority"]["base_source"] == "laya"
    assert body["category"] == "Service - poor communication"  # FakeLaya picks Customer support

    db = TestSession()
    complaint = db.get(Complaint, "NW-124206")
    assert complaint.status == "Open"
    assert complaint.category == "Service - poor communication"
    assert complaint.priority == body["classification"]["priority"]["level"]
    assert complaint.sla_days == body["classification"]["priority"]["target_days"]
    current = db.query(Classification).filter_by(complaint_id="NW-124206", is_current=True).one()
    assert current.input["text"] == "My bill doubled this month and nobody will explain why."  # the text is kept
    db.close()


def test_intake_numbers_the_first_complaint_when_there_are_none(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    assert client.post("/complaints/intake", json=_intake()).json()["complaint_id"] == "NW-100001"


def test_intake_creates_the_account_when_it_is_new(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    assert client.post("/complaints/intake", json=_intake(account_id="ACC-NEW")).status_code == 200
    db = TestSession()
    assert db.get(Account, "ACC-NEW") is not None
    db.close()


def test_intake_rejects_an_unknown_region_and_saves_nothing(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    response = client.post("/complaints/intake", json=_intake(region="Atlantis"))
    assert response.status_code == 422
    assert "Atlantis" in response.json()["detail"]
    db = TestSession()
    assert db.query(Complaint).count() == 0 and db.query(Classification).count() == 0
    db.close()


def test_intake_rejects_blank_text(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    assert client.post("/complaints/intake", json=_intake(text="   ")).status_code == 422


def test_intake_rejects_a_system_that_is_not_an_intake_system(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    assert client.post("/complaints/intake", json=_intake(source_system="SYS-06")).status_code == 422


def test_get_context_gives_the_agent_the_customers_text_from_intake(monkeypatch):
    client, TestSession = _client(monkeypatch)
    _seed_region(TestSession)
    complaint_id = client.post("/complaints/intake", json=_intake()).json()["complaint_id"]

    captured = {}

    def fake_run(model, cfg, tools, instruction):
        captured["case"] = next(t for t in tools if t.name == "read_case").invoke({})
        next(t for t in tools if t.name == "create_action_brief").invoke(
            {"action_type": "review", "description": "Review the bill", "rationale": "Bill doubled"}
        )

    monkeypatch.setattr("app.complaint_routes._build_agent_model", lambda: object())
    monkeypatch.setattr("app.complaint_routes.run_agent_once", fake_run)
    assert client.post(f"/complaints/{complaint_id}/context").json()["status"] == "succeeded"
    assert "The customer said: My bill doubled this month" in captured["case"]
