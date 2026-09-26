"""Backlog reports: GET /reports/backlog-flow (per month) and, next, the open backlog breakdown."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()

MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


class FlowRow(BaseModel):
    month: str  # YYYY-MM
    opened: int
    closed: int  # by the month the complaint was closed
    net_change: int  # opened minus closed
    backlog_end_of_month: int  # open complaints at the end of the month, within the filters
    avg_days_to_close: float | None  # of complaints closed that month
    breach_rate_closed: float | None  # share of those closed that month past their SLA


FLOW_SORTS = {name: name for name in FlowRow.model_fields}


@router.get("/backlog-flow", response_model=Page[FlowRow], summary="Opened against closed per month, with the running backlog")
def backlog_flow(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `month`. Names: {', '.join(FLOW_SORTS)}"),
    region: list[str] | None = Query(None, description="Repeat the parameter for several values"),
    category: list[str] | None = Query(None),
    domain: list[str] | None = Query(None, description="billing, metering, field_services, customer_support, general"),
    priority: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    source_system: list[str] | None = Query(None),
    month_from: str | None = Query(None, pattern=MONTH, description="YYYY-MM. Only limits which months are shown"),
    month_to: str | None = Query(None, pattern=MONTH, description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    # Dimension filters go inside, so they change the counts. Month filters go outside, after the
    # running backlog is worked out, so a shortened range still starts from the right backlog.
    inner = Where("i")
    for column, values in (
        ("c.region", region), ("c.category", category), ("cat.agent_id", domain), ("c.priority", priority),
        ("c.channel", channel), ("c.source_system", source_system),
    ):
        inner.any_of(column, values)
    outer = Where("o")
    outer.compare("month", ">=", month_from)
    outer.compare("month", "<=", month_to)

    source = f"""(
        WITH f AS (
            SELECT c.* FROM complaints c JOIN categories cat USING (category) {inner.sql}
        ), opened AS (
            SELECT to_char(date_opened, 'YYYY-MM') AS month, count(*) AS n FROM f GROUP BY 1
        ), closed AS (
            SELECT to_char(date_closed, 'YYYY-MM') AS month, count(*) AS n,
                   avg(days_to_close) AS avg_days, avg(sla_breach::int) AS breach_rate
            FROM f WHERE date_closed IS NOT NULL GROUP BY 1
        ), months AS (
            SELECT month,
                   COALESCE(o.n, 0)::int AS opened,
                   COALESCE(c.n, 0)::int AS closed,
                   (COALESCE(o.n, 0) - COALESCE(c.n, 0))::int AS net_change,
                   round(c.avg_days, 1)::float AS avg_days_to_close,
                   round(c.breach_rate, 3)::float AS breach_rate_closed
            FROM opened o FULL JOIN closed c USING (month)
        )
        SELECT month, opened, closed, net_change,
               (sum(net_change) OVER (ORDER BY month))::int AS backlog_end_of_month,
               avg_days_to_close, breach_rate_closed
        FROM months
    ) flow"""
    order, applied = order_by(sort, FLOW_SORTS, "month", "month")
    return fetch_page(
        db, columns="*", source=source, where=outer, order=order, applied_sort=applied,
        pagination=pagination, params=inner.params,
    )
