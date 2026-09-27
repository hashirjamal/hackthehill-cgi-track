"""Pydantic models for the two case-view buttons: "Get context" and "Generate draft"."""
from pydantic import BaseModel


class ActionItemOut(BaseModel):
    action_id: int
    action_type: str
    description: str
    rationale: str | None
    rank: int


class ContextResponse(BaseModel):
    run_id: int
    status: str  # "succeeded" or "failed"
    action_items: list[ActionItemOut]
    error: str | None = None


class DraftOut(BaseModel):
    run_id: int
    status: str  # "succeeded" or "failed"
    draft_id: int | None = None
    body: str | None = None
    error: str | None = None
