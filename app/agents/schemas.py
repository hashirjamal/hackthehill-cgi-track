"""Pydantic models for the two case-view buttons: "Get context" and "Generate draft"."""
from pydantic import BaseModel


class ActionItemOut(BaseModel):
    action_id: int
    action_type: str
    description: str
    rationale: str | None
    rank: int


class SystemCall(BaseModel):
    """One request the agent made to a Northwind system, for the "Systems checked" trace."""

    system: str  # helix, aurora, casetrack, callcentre, connect
    system_name: str
    request: str
    raw: str | None  # the system's raw response (None when it failed or had no record)
    summary: str | None  # what the agent was told


class ContextResponse(BaseModel):
    run_id: int
    status: str  # "succeeded" or "failed"
    action_items: list[ActionItemOut]
    error: str | None = None
    systems_checked: list[SystemCall] = []


class DraftOut(BaseModel):
    run_id: int
    status: str  # "succeeded" or "failed"
    draft_id: int | None = None
    body: str | None = None
    error: str | None = None
    systems_checked: list[SystemCall] = []
