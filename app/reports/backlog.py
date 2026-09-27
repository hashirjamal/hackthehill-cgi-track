"""Backlog reports: GET /reports/backlog-flow (per month) and GET /reports/backlog-breakdown (open cases, grouped)."""
from typing import Any, Literal

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


# --- GET /reports/backlog-breakdown ------------------------------------------------------------

GROUP_COLUMNS = ["region", "category", "domain", "priority", "age_band", "breached_live", "channel", "source_system"]
GroupBy = Literal["region", "category", "domain", "priority", "age_band", "breached_live", "channel", "source_system"]
AGE_BAND_RANK = "CASE age_band WHEN '0-5' THEN 1 WHEN '6-10' THEN 2 WHEN '11-20' THEN 3 WHEN '21-40' THEN 4 ELSE 5 END"
METRICS = ["open_cases", "breached_cases", "at_risk_cases", "total_days_overdue", "avg_days_open", "share_of_backlog"]


class BreakdownPage(Page[dict[str, Any]]):
    group_by: list[str]  # the columns each row is grouped on; every item has these plus the metrics


@router.get(
    "/backlog-breakdown",
    response_model=BreakdownPage,
    summary="The open backlog grouped by any of region, category, domain, priority, age band ...",
)
def backlog_breakdown(
    pagination: Pagination = Depends(),
    group_by: list[GroupBy] = Query(["region"], description="Repeat for several, e.g. group_by=region&group_by=category"),
    sort: str | None = Query(
        None,
        description="Comma-separated `name:asc|desc`, by a group_by column or a metric. Default `open_cases:desc`. "
        f"Metrics: {', '.join(METRICS)}",
    ),
    region: list[str] | None = Query(None, description="Filters take repeated values, like the other reports"),
    category: list[str] | None = Query(None),
    domain: list[str] | None = Query(None),
    priority: list[str] | None = Query(None),
    age_band: list[str] | None = Query(None, description="0-5, 6-10, 11-20, 21-40, 41+"),
    channel: list[str] | None = Query(None),
    source_system: list[str] | None = Query(None),
    breached: bool | None = Query(None, description="Past its SLA target as of the as_of_date"),
    min_open_cases: int | None = Query(None, ge=1, description="Hide groups smaller than this"),
    db: Session = Depends(get_db),
):
    columns = list(dict.fromkeys(group_by))
    inner = Where("i")
    inner.raw("status = 'Open'")
    for column, values in (
        ("region", region), ("category", category), ("domain", domain), ("priority", priority),
        ("age_band", age_band), ("channel", channel), ("source_system", source_system),
    ):
        inner.any_of(column, values)
    inner.flag("breached_live", breached)
    outer = Where("o")
    outer.compare("open_cases", ">=", min_open_cases)

    group_sql = ", ".join(columns)
    source = f"""(
        SELECT {group_sql},
               count(*)::int AS open_cases,
               (count(*) FILTER (WHERE breached_live))::int AS breached_cases,
               (count(*) FILTER (WHERE NOT breached_live AND days_open > 0.75 * sla_days))::int AS at_risk_cases,
               COALESCE(sum(days_overdue) FILTER (WHERE breached_live), 0)::int AS total_days_overdue,
               round(avg(days_open), 1)::float AS avg_days_open,
               round(count(*)::numeric / sum(count(*)) OVER (), 4)::float AS share_of_backlog
        FROM v_case_sla {inner.sql}
        GROUP BY {group_sql}
    ) breakdown"""
    allowed = {c: (AGE_BAND_RANK if c == "age_band" else c) for c in columns} | {m: m for m in METRICS}
    order, applied = order_by(sort, allowed, "open_cases:desc", group_sql)
    page = fetch_page(
        db, columns="*", source=source, where=outer, order=order, applied_sort=applied,
        pagination=pagination, params=inner.params,
    )
    return {**page, "group_by": columns}
