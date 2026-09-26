"""Classification and agent reports: GET /reports/agent-results and, next, the classification summary."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()


class AgentResultRow(BaseModel):
    agent_id: str  # billing, metering, field_services, customer_support, general
    name: str
    classified: int  # current classifications in this agent's group
    fast_lane: int  # of those, in the quick (information-only) lane
    runs: int  # AI agent runs
    runs_failed: int
    drafts: int
    drafts_pending: int
    drafts_approved: int
    drafts_edited: int
    drafts_rejected: int
    drafts_sent: int


AGENT_SORTS = {name: name for name in AgentResultRow.model_fields}


@router.get("/agent-results", response_model=Page[AgentResultRow], summary="Classified cases, runs and drafts per AI agent")
def agent_results(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `classified:desc`. Names: {', '.join(AGENT_SORTS)}"),
    agent_id: list[str] | None = Query(None, description="Repeat the parameter for several values"),
    classified_min: int | None = Query(None, ge=0),
    runs_min: int | None = Query(None, ge=0),
    has_failed_runs: bool | None = Query(None, description="Only agents with at least one failed run (or none)"),
    drafts_pending_min: int | None = Query(None, ge=0, description="Drafts still waiting for staff"),
    db: Session = Depends(get_db),
):
    where = Where()
    where.any_of("agent_id", agent_id)
    where.compare("classified", ">=", classified_min)
    where.compare("runs", ">=", runs_min)
    if has_failed_runs is not None:
        where.raw("runs_failed > 0" if has_failed_runs else "runs_failed = 0")
    where.compare("drafts_pending", ">=", drafts_pending_min)

    order, applied = order_by(sort, AGENT_SORTS, "classified:desc", "agent_id")
    return fetch_page(
        db, columns="*", source="v_agent_results", where=where, order=order, applied_sort=applied, pagination=pagination
    )
