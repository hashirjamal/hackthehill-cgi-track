"""Pydantic models for the domain agent scaffold: agent output and the context it's given."""
from datetime import date

from pydantic import BaseModel, Field


class ActionItemOut(BaseModel):
    action_type: str = Field(
        description="A short machine-friendly label, e.g. correct_bill, book_meter_read, escalate_field, call_customer"
    )
    description: str = Field(description="What staff should do, in one sentence")
    rationale: str = Field(description="Why this action, in one short phrase")
    rank: int = Field(ge=1, description="Suggested order within the case, starting at 1")


class AgentDraftOutput(BaseModel):
    """What a domain agent produces for one complaint."""

    draft_reply: str | None = Field(default=None, description="A reply to send the customer, or null if none is needed")
    action_items: list[ActionItemOut] = Field(default_factory=list)


class CaseProfile(BaseModel):
    """Historic pattern for this case type, from v_case_profile."""

    category: str
    region: str
    source_system: str
    n: int
    avg_days: float | None
    info_only_share: float | None
    transfer_rate: float | None
    reopen_rate: float | None
    breach_rate: float | None
    top_resolution: str | None


class AccountHistoryEntry(BaseModel):
    """One earlier complaint on the account, from v_account_history."""

    complaint_id: str
    date_opened: date
    category: str
    status: str
    resolution_action: str | None
    days_to_close: int | None
    is_repeat: bool


class RegionMeterPicture(BaseModel):
    """The region's meter picture for one month, from v_region_meter_complaints."""

    region: str
    month: str
    estimated_read_rate: float
    smart_meter_penetration: float
    billing_exceptions_per_1000: float | None
    billing_metering_share: float | None


class AgentContext(BaseModel):
    """Everything a domain agent is given about a case, beyond the complaint itself."""

    case_profile: CaseProfile | None = None
    account_history: list[AccountHistoryEntry] = Field(default_factory=list)
    region_meter_picture: RegionMeterPicture | None = None
