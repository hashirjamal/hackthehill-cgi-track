"""Classification and agent reports: GET /reports/agent-results and GET /reports/classifications/summary."""
from datetime import date
from typing import Any, Literal

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


# --- GET /reports/classifications/summary ------------------------------------------------------

GroupBy = Literal[
    "group_name", "subcategory", "priority", "base_priority", "base_priority_source", "lane", "routed_team",
    "group_source", "subcategory_source", "low_confidence", "likely_cause", "classifier_version", "laya_group", "emergency",
]
SUMMARY_METRICS = ["classifications", "share_of_total", "avg_group_confidence", "data_fallbacks", "group_match_rate"]


class SummaryPage(Page[dict[str, Any]]):
    group_by: list[str]  # every item has these columns plus the metrics


@router.get(
    "/classifications/summary",
    response_model=SummaryPage,
    summary="Classification results counted by group, lane, team, priority and so on",
)
def classification_summary(
    pagination: Pagination = Depends(),
    group_by: list[GroupBy] = Query(["group_name"], description="Repeat for several, e.g. group_by=group_name&group_by=lane"),
    sort: str | None = Query(
        None,
        description="Comma-separated `name:asc|desc`, by a group_by column or a metric. Default `classifications:desc`. "
        f"Metrics: {', '.join(SUMMARY_METRICS)}",
    ),
    current_only: bool = Query(True, description="Only each complaint's current classification, not its history"),
    group_name: list[str] | None = Query(None, description="Filters take repeated values"),
    subcategory: list[str] | None = Query(None),
    priority: list[str] | None = Query(None, description="Priority after flags"),
    base_priority: list[str] | None = Query(None),
    base_priority_source: list[str] | None = Query(None, description="data, laya or emergency"),
    lane: list[str] | None = Query(None, description="emergency, review, quick_lane, standard"),
    routed_team: list[str] | None = Query(None),
    group_source: list[str] | None = Query(None, description="laya, or data when Laya was unsure"),
    likely_cause: list[str] | None = Query(None),
    classifier_version: list[str] | None = Query(None),
    low_confidence: bool | None = None,
    emergency: bool | None = None,
    created_from: date | None = Query(None, description="Classified on or after this date"),
    created_to: date | None = Query(None, description="Classified on or before this date"),
    min_classifications: int | None = Query(None, ge=1, description="Hide groups smaller than this"),
    db: Session = Depends(get_db),
):
    columns = list(dict.fromkeys(group_by))
    inner = Where("i")
    if current_only:
        inner.raw("is_current")
    for column, values in (
        ("group_name", group_name), ("subcategory", subcategory), ("priority", priority),
        ("base_priority", base_priority), ("base_priority_source", base_priority_source), ("lane", lane),
        ("routed_team", routed_team), ("group_source", group_source), ("likely_cause", likely_cause),
        ("classifier_version", classifier_version),
    ):
        inner.any_of(column, values)
    inner.flag("low_confidence", low_confidence)
    inner.flag("emergency", emergency)
    inner.compare("created_at::date", ">=", created_from)
    inner.compare("created_at::date", "<=", created_to)
    outer = Where("o")
    outer.compare("classifications", ">=", min_classifications)

    group_sql = ", ".join(columns)
    source = f"""(
        SELECT {group_sql},
               count(*)::int AS classifications,
               round(count(*)::numeric / sum(count(*)) OVER (), 4)::float AS share_of_total,
               round(avg(group_confidence)::numeric, 3)::float AS avg_group_confidence,
               (count(*) FILTER (WHERE group_source = 'data'))::int AS data_fallbacks,
               round(avg(group_matches_data::int)::numeric, 3)::float AS group_match_rate
        FROM classifications {inner.sql}
        GROUP BY {group_sql}
    ) summary"""
    # Priorities sort P1 first, as the other reports do.
    allowed = {
        c: (f"CASE {c} WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END" if c in ("priority", "base_priority") else c)
        for c in columns
    } | {m: m for m in SUMMARY_METRICS}
    order, applied = order_by(sort, allowed, "classifications:desc", group_sql)
    page = fetch_page(
        db, columns="*", source=source, where=outer, order=order, applied_sort=applied,
        pagination=pagination, params=inner.params,
    )
    return {**page, "group_by": columns}
