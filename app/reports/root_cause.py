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
