"""Tests the shared chat tools against SQLite tables shaped like the dashboard views' output
columns (not the real Postgres view SQL) - the queries in app/agents/tools.py are plain
SELECT ... WHERE ..., so only the column names matter here, matching the precedent already set
elsewhere in this test suite for testing view-backed queries."""
from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.agents.tools import build_general_tools, build_shared_tools, build_tools
from app.db import Base
from app.models import Complaint, DraftResponse

AS_OF = date(2026, 9, 30)


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.execute(text(
            "CREATE TABLE v_case_profile (category TEXT, region TEXT, source_system TEXT, n INT, "
            "avg_days REAL, info_only_share REAL, transfer_rate REAL, reopen_rate REAL, breach_rate REAL, "
            "top_resolution TEXT)"
        ))
        db.execute(text(
            "CREATE TABLE v_account_history (account_id TEXT, complaint_id TEXT, date_opened TEXT, "
            "category TEXT, status TEXT, resolution_action TEXT)"
        ))
        db.execute(text(
            "CREATE TABLE v_region_meter_complaints (region TEXT, month TEXT, estimated_read_rate REAL, "
            "smart_meter_penetration REAL, billing_exceptions_per_1000 REAL)"
        ))
        yield db


def _complaint(**overrides) -> Complaint:
    fields = dict(
        complaint_id="NW-1", account_id="ACC-1", date_opened=date(2026, 9, 1), status="Open",
        channel="Phone", category="Billing - disputed amount", priority="P3", region="Ashford",
        source_system="SYS-01", transferred_between_systems=False, sla_days=20, sla_breach=False,
        reopened=False,
    )
    fields.update(overrides)
    return Complaint(**fields)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_get_account_complaints_returns_a_message_when_there_is_no_history():
    for db in _db():
        tools = build_shared_tools(db, _complaint(), AS_OF)
        assert _tool(tools, "get_account_complaints").invoke({}) == "No other complaints found for this account."


def test_get_account_complaints_lists_other_complaints_excluding_the_current_one():
    for db in _db():
        db.execute(text(
            "INSERT INTO v_account_history VALUES "
            "('ACC-1', 'NW-1', '2026-09-01', 'Billing - disputed amount', 'Open', NULL)"
        ))
        db.execute(text(
            "INSERT INTO v_account_history VALUES "
            "('ACC-1', 'NW-0', '2026-01-01', 'Other', 'Closed', 'Information provided')"
        ))
        tools = build_shared_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "get_account_complaints").invoke({})
        assert "NW-0" in result and "Information provided" in result
        assert "NW-1" not in result  # the current complaint is excluded


def test_get_case_profile_returns_a_message_with_no_matching_history():
    for db in _db():
        tools = build_shared_tools(db, _complaint(), AS_OF)
        assert (
            _tool(tools, "get_case_profile").invoke({})
            == "No matching case history for this category, region and system."
        )


def test_get_case_profile_reports_the_matching_row():
    for db in _db():
        db.execute(text(
            "INSERT INTO v_case_profile VALUES ('Billing - disputed amount', 'Ashford', 'SYS-01', 100, "
            "12.5, 0.3, 0.1, 0.05, 0.2, 'Bill corrected and re-issued')"
        ))
        tools = build_shared_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "get_case_profile").invoke({})
        assert "100 similar closed cases" in result
        assert "Bill corrected and re-issued" in result


def test_get_region_meter_picture_returns_a_message_with_no_data():
    for db in _db():
        tools = build_shared_tools(db, _complaint(), AS_OF)
        assert _tool(tools, "get_region_meter_picture").invoke({}) == "No meter data for this region and month."


def test_get_region_meter_picture_reports_the_current_month():
    for db in _db():
        db.execute(text("INSERT INTO v_region_meter_complaints VALUES ('Ashford', '2026-09', 0.2, 0.8, 5.0)"))
        tools = build_shared_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "get_region_meter_picture").invoke({})
        assert "20%" in result and "80%" in result


def test_save_draft_reply_writes_a_draft_response_row():
    for db in _db():
        tools = build_shared_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "save_draft_reply").invoke({"body": "We're sorry for the delay."})
        assert result == "Draft saved for staff review."
        draft = db.query(DraftResponse).filter_by(complaint_id="NW-1").one()
        assert draft.body == "We're sorry for the delay."


def test_build_tools_returns_nothing_for_no_domain_or_an_unrecognized_one():
    for db in _db():
        assert build_tools(None, db, _complaint(), AS_OF) == []
        assert build_tools("not-a-real-agent-id", db, _complaint(), AS_OF) == []


def test_every_real_domain_has_at_least_the_four_shared_tools():
    for db in _db():
        for agent_id in ("billing", "metering", "field_services", "customer_support", "general"):
            names = {t.name for t in build_tools(agent_id, db, _complaint(), AS_OF)}
            assert {"get_account_complaints", "get_case_profile", "get_region_meter_picture", "save_draft_reply"} <= names


def test_only_general_gets_the_knowledge_base_tool():
    for db in _db():
        assert "search_knowledge_base" not in {t.name for t in build_shared_tools(db, _complaint(), AS_OF)}
        assert "search_knowledge_base" in {t.name for t in build_general_tools(db, _complaint(), AS_OF)}


def test_search_knowledge_base_matches_a_known_question():
    for db in _db():
        tools = build_general_tools(db, _complaint(), AS_OF)
        answer = _tool(tools, "search_knowledge_base").invoke({"question": "How do I pay my bill this month?"})
        assert "online, phone, bank transfer" in answer


def test_search_knowledge_base_has_no_answer_for_an_unrelated_question():
    for db in _db():
        tools = build_general_tools(db, _complaint(), AS_OF)
        answer = _tool(tools, "search_knowledge_base").invoke({"question": "What is the weather like today?"})
        assert answer == "No approved answer for this question in the knowledge base. Hand the case to a person."
