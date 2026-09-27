"""Tests the shared context tools plus the two single-purpose output tools, against SQLite
tables shaped like the dashboard views' output columns (not the real Postgres view SQL) - the
queries here are plain SELECT ... WHERE ..., so only the column names matter, matching the
precedent already set elsewhere in this test suite for testing view-backed queries."""
from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.agents.tools import (
    build_action_item_tool,
    build_context_tools,
    build_context_tools_for,
    build_draft_tool,
)
from app.db import Base
from app.models import ActionItem, Complaint, DraftResponse

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


def test_read_case_describes_the_complaints_own_fields():
    for db in _db():
        tools = build_context_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "read_case").invoke({})
        assert "NW-1" in result and "Billing - disputed amount" in result
        assert "priority P3" in result and "target 20 days" in result
        assert "29 days open" in result  # 2026-09-01 to 2026-09-30


def test_read_case_notes_a_transfer():
    for db in _db():
        tools = build_context_tools(db, _complaint(transferred_between_systems=True), AS_OF)
        assert "transferred between systems" in _tool(tools, "read_case").invoke({})


def test_get_account_complaints_returns_a_message_when_there_is_no_history():
    for db in _db():
        tools = build_context_tools(db, _complaint(), AS_OF)
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
        tools = build_context_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "get_account_complaints").invoke({})
        assert "NW-0" in result and "Information provided" in result
        assert "NW-1" not in result  # the current complaint is excluded


def test_get_case_profile_returns_a_message_with_no_matching_history():
    for db in _db():
        tools = build_context_tools(db, _complaint(), AS_OF)
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
        tools = build_context_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "get_case_profile").invoke({})
        assert "100 similar closed cases" in result
        assert "Bill corrected and re-issued" in result


def test_get_region_meter_picture_returns_a_message_with_no_data():
    for db in _db():
        tools = build_context_tools(db, _complaint(), AS_OF)
        assert _tool(tools, "get_region_meter_picture").invoke({}) == "No meter data for this region and month."


def test_get_region_meter_picture_reports_the_current_month():
    for db in _db():
        db.execute(text("INSERT INTO v_region_meter_complaints VALUES ('Ashford', '2026-09', 0.2, 0.8, 5.0)"))
        tools = build_context_tools(db, _complaint(), AS_OF)
        result = _tool(tools, "get_region_meter_picture").invoke({})
        assert "20%" in result and "80%" in result


def test_context_tools_for_unclassified_or_non_general_domains_has_no_knowledge_base():
    for db in _db():
        for agent_id in (None, "billing", "metering", "field_services", "customer_support"):
            names = {t.name for t in build_context_tools_for(agent_id, db, _complaint(), AS_OF)}
            assert names == {"read_case", "get_account_complaints", "get_case_profile", "get_region_meter_picture"}


def test_context_tools_for_general_adds_the_knowledge_base():
    for db in _db():
        names = {t.name for t in build_context_tools_for("general", db, _complaint(), AS_OF)}
        assert "search_knowledge_base" in names


def test_search_knowledge_base_matches_a_known_question():
    for db in _db():
        tools = build_context_tools_for("general", db, _complaint(), AS_OF)
        answer = _tool(tools, "search_knowledge_base").invoke({"question": "How do I pay my bill this month?"})
        assert "online, phone, bank transfer" in answer


def test_search_knowledge_base_has_no_answer_for_an_unrelated_question():
    for db in _db():
        tools = build_context_tools_for("general", db, _complaint(), AS_OF)
        answer = _tool(tools, "search_knowledge_base").invoke({"question": "What is the weather like today?"})
        assert answer == "No approved answer for this question in the knowledge base. Hand the case to a person."


def test_create_action_brief_writes_an_action_item_with_increasing_rank():
    for db in _db():
        create_action_brief = build_action_item_tool(db, _complaint(), run_id=1)
        create_action_brief.invoke({"action_type": "correct_bill", "description": "Reissue the bill",
                                     "rationale": "Estimated read"})
        create_action_brief.invoke({"action_type": "call_customer", "description": "Call to confirm",
                                     "rationale": "Follow-up"})
        items = db.query(ActionItem).filter_by(complaint_id="NW-1").order_by(ActionItem.rank).all()
        assert [i.action_type for i in items] == ["correct_bill", "call_customer"]
        assert [i.rank for i in items] == [1, 2]
        assert all(i.run_id == 1 for i in items)


def test_save_draft_reply_writes_a_draft_response_row_linked_to_the_run():
    for db in _db():
        save_draft_reply = build_draft_tool(db, _complaint(), run_id=7)
        result = save_draft_reply.invoke({"body": "We're sorry for the delay."})
        assert result == "Draft saved for staff review."
        draft = db.query(DraftResponse).filter_by(complaint_id="NW-1").one()
        assert draft.body == "We're sorry for the delay."
        assert draft.run_id == 7
