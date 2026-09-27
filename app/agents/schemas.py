"""Pydantic models for the staff <-> domain-agent chat endpoint."""
from typing import Literal

from pydantic import BaseModel, Field


class ChatTurnIn(BaseModel):
    role: Literal["staff", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurnIn] = Field(default_factory=list)
    staff_id: int = 1  # no staff auth yet; defaults to the seeded placeholder demo staff row


class ChatResponse(BaseModel):
    session_id: int
    reply: str
    draft_saved: bool
