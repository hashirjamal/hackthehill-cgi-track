from datetime import date

from app.agents.schemas import (
    AccountHistoryEntry,
    ActionItemOut,
    AgentContext,
    AgentDraftOutput,
    CaseProfile,
    RegionMeterPicture,
)


def test_agent_draft_output_defaults_to_no_reply_and_no_actions():
    out = AgentDraftOutput()
    assert out.draft_reply is None
    assert out.action_items == []


def test_action_item_rank_must_be_at_least_one():
    import pytest
    from pydantic import ValidationError

    ActionItemOut(action_type="correct_bill", description="Reissue the bill", rationale="Estimated read", rank=1)
    with pytest.raises(ValidationError):
        ActionItemOut(action_type="correct_bill", description="x", rationale="y", rank=0)


def test_agent_context_defaults_to_empty_history_and_no_profile():
    ctx = AgentContext()
    assert ctx.case_profile is None
    assert ctx.account_history == []
    assert ctx.region_meter_picture is None


def test_full_context_round_trips():
    ctx = AgentContext(
        case_profile=CaseProfile(
            category="Billing - estimated read", region="Barrowdale", source_system="SYS-05",
            n=1281, avg_days=31.2, info_only_share=0.24, transfer_rate=0.33, reopen_rate=0.17,
            breach_rate=0.81, top_resolution="Bill corrected and re-issued",
        ),
        account_history=[
            AccountHistoryEntry(complaint_id="NW-1", date_opened=date(2026, 1, 1), category="Other",
                                 status="Closed", resolution_action="Information provided",
                                 days_to_close=5, is_repeat=False),
        ],
        region_meter_picture=RegionMeterPicture(
            region="Barrowdale", month="2026-09", estimated_read_rate=0.62,
            smart_meter_penetration=0.0, billing_exceptions_per_1000=45.2, billing_metering_share=0.75,
        ),
    )
    assert ctx.case_profile.n == 1281
    assert ctx.account_history[0].is_repeat is False
    assert ctx.region_meter_picture.estimated_read_rate == 0.62
