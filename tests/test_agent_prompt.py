from datetime import date

from app.agents.prompt import render_agent_prompt
from app.agents.schemas import AccountHistoryEntry, AgentContext, CaseProfile, RegionMeterPicture
from app.classification.schemas import ComplaintIn


def test_prompt_includes_the_complaint_fields():
    complaint = ComplaintIn(category="Billing - disputed amount", region="Barrowdale", channel="Phone",
                             priority="P3", text="I was billed twice")
    prompt = render_agent_prompt(complaint, AgentContext())
    assert "Billing - disputed amount" in prompt
    assert "Barrowdale" in prompt
    assert "I was billed twice" in prompt


def test_prompt_says_so_when_there_is_no_case_history():
    prompt = render_agent_prompt(ComplaintIn(text="x"), AgentContext())
    assert "No matching case history" in prompt
    assert "No earlier complaints" in prompt
    assert "No meter data" in prompt


def test_prompt_includes_the_case_profile_numbers():
    ctx = AgentContext(case_profile=CaseProfile(
        category="Billing - estimated read", region="Barrowdale", source_system="SYS-05",
        n=1281, avg_days=31.2, info_only_share=0.24, transfer_rate=0.33, reopen_rate=0.17,
        breach_rate=0.81, top_resolution="Bill corrected and re-issued",
    ))
    prompt = render_agent_prompt(ComplaintIn(text="x"), ctx)
    assert "1281" in prompt
    assert "24%" in prompt  # info_only_share as a percentage
    assert "Bill corrected and re-issued" in prompt


def test_prompt_flags_repeat_contact_in_account_history():
    ctx = AgentContext(account_history=[
        AccountHistoryEntry(complaint_id="NW-2", date_opened=date(2026, 6, 1), category="Other",
                             status="Closed", resolution_action="Information provided",
                             days_to_close=3, is_repeat=True),
    ])
    prompt = render_agent_prompt(ComplaintIn(text="x"), ctx)
    assert "[repeat contact]" in prompt


def test_prompt_includes_the_meter_picture():
    ctx = AgentContext(region_meter_picture=RegionMeterPicture(
        region="Barrowdale", month="2026-09", estimated_read_rate=0.62,
        smart_meter_penetration=0.0, billing_exceptions_per_1000=45.2, billing_metering_share=0.75,
    ))
    prompt = render_agent_prompt(ComplaintIn(text="x"), ctx)
    assert "62%" in prompt
    assert "45.2" in prompt
