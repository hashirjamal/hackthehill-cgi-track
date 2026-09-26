"""Root-cause reports: GET /reports/root-cause (region x month) and, next, the open-backlog clusters."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.backlog import MONTH
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()


class RootCauseRow(BaseModel):
    month: str  # YYYY-MM
    region: str
    accounts: int
    estimated_read_rate: float  # share of bills based on an estimated reading
    smart_meter_penetration: float
    billing_exceptions_raised: int
    billing_exceptions_per_1000: float
    complaints: int  # all complaints opened in the region that month
    billing_metering_complaints: int
    billing_metering_per_1000: float  # per 1,000 accounts
    billing_metering_share: float | None  # of the region's complaints that month


ROOT_SORTS = {name: name for name in RootCauseRow.model_fields}


@router.get(
    "/root-cause",
    response_model=Page[RootCauseRow],
    summary="Estimated reads against billing and metering complaints, by region and month",
)
def root_cause(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `month,region`. Names: {', '.join(ROOT_SORTS)}"),
    region: list[str] | None = Query(None, description="Repeat the parameter for several values"),
    month_from: str | None = Query(None, pattern=MONTH, description="YYYY-MM"),
    month_to: str | None = Query(None, pattern=MONTH, description="YYYY-MM"),
    estimated_read_rate_min: float | None = Query(None, ge=0, le=1, description="e.g. 0.4 for the high-estimate region-months"),
    estimated_read_rate_max: float | None = Query(None, ge=0, le=1),
    smart_meter_penetration_min: float | None = Query(None, ge=0, le=1),
    smart_meter_penetration_max: float | None = Query(None, ge=0, le=1),
    billing_metering_per_1000_min: float | None = Query(None, ge=0),
    complaints_min: int | None = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    where = Where()
    where.any_of("region", region)
    where.compare("month", ">=", month_from)
    where.compare("month", "<=", month_to)
    where.compare("estimated_read_rate", ">=", estimated_read_rate_min)
    where.compare("estimated_read_rate", "<=", estimated_read_rate_max)
    where.compare("smart_meter_penetration", ">=", smart_meter_penetration_min)
    where.compare("smart_meter_penetration", "<=", smart_meter_penetration_max)
    where.compare("billing_metering_per_1000", ">=", billing_metering_per_1000_min)
    where.compare("complaints", ">=", complaints_min)

    order, applied = order_by(sort, ROOT_SORTS, "month,region", "month, region")
    return fetch_page(
        db, columns="*", source="v_region_meter_complaints", where=where, order=order,
        applied_sort=applied, pagination=pagination,
    )


# --- GET /reports/root-cause/clusters -----------------------------------------------------------

ESTIMATION_PRONE_RATE = 0.4  # region-months with at least this share of estimated reads
ESTIMATION_CATEGORIES = ("Billing - estimated read", "Metering - no read taken")


class ClusterRow(BaseModel):
    region: str
    category: str
    open_cases: int
    breached_cases: int
    avg_days_open: float
    share_of_region_backlog: float
    region_estimated_read_rate: float | None  # as of the as_of_date month
    region_smart_meter_penetration: float | None
    region_billing_exceptions_per_1000: float | None
    estimation_prone: bool  # the region's estimated-read rate is 40% or more
    estimation_driven: bool  # estimation prone, and an estimated-read or no-read complaint


CLUSTER_SORTS = {name: name for name in ClusterRow.model_fields}


@router.get(
    "/root-cause/clusters",
    response_model=Page[ClusterRow],
    summary="Open complaints by region and category, next to the region's meter picture",
)
def root_cause_clusters(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `open_cases:desc`. Names: {', '.join(CLUSTER_SORTS)}"),
    region: list[str] | None = Query(None, description="Repeat the parameter for several values"),
    category: list[str] | None = Query(None),
    estimation_prone: bool | None = Query(None, description="Only regions with 40%+ estimated reads (or only the others)"),
    estimation_driven: bool | None = Query(None, description="Only clusters likely caused by estimated readings"),
    min_open_cases: int | None = Query(None, ge=1),
    min_breached_cases: int | None = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    inner = Where("i")
    inner.raw("v.status = 'Open'")
    inner.any_of("v.region", region)
    outer = Where("o")
    outer.any_of("category", category)  # after the share is worked out, so it stays a share of the whole region
    outer.flag("estimation_prone", estimation_prone)
    outer.flag("estimation_driven", estimation_driven)
    outer.compare("open_cases", ">=", min_open_cases)
    outer.compare("breached_cases", ">=", min_breached_cases)

    cats = ", ".join(f"'{c}'" for c in ESTIMATION_CATEGORIES)
    source = f"""(
        SELECT g.*,
               (COALESCE(g.region_estimated_read_rate, 0) >= {ESTIMATION_PRONE_RATE}) AS estimation_prone,
               (COALESCE(g.region_estimated_read_rate, 0) >= {ESTIMATION_PRONE_RATE} AND g.category IN ({cats})) AS estimation_driven
        FROM (
            SELECT v.region, v.category,
                   count(*)::int AS open_cases,
                   (count(*) FILTER (WHERE v.breached_live))::int AS breached_cases,
                   round(avg(v.days_open), 1)::float AS avg_days_open,
                   round(count(*)::numeric / sum(count(*)) OVER (PARTITION BY v.region), 4)::float AS share_of_region_backlog,
                   max(m.estimated_read_rate)::float AS region_estimated_read_rate,
                   max(m.smart_meter_penetration)::float AS region_smart_meter_penetration,
                   round(max(m.billing_exceptions_raised) * 1000.0 / max(m.accounts), 2)::float AS region_billing_exceptions_per_1000
            FROM v_case_sla v
            LEFT JOIN meter_reads m ON m.region = v.region AND m.month = to_char(v.as_of_date, 'YYYY-MM')
            {inner.sql}
            GROUP BY v.region, v.category
        ) g
    ) clusters"""
    order, applied = order_by(sort, CLUSTER_SORTS, "open_cases:desc", "region, category")
    return fetch_page(
        db, columns="*", source=source, where=outer, order=order, applied_sort=applied,
        pagination=pagination, params=inner.params,
    )
