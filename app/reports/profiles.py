"""GET /reports/case-profiles: how closed cases of each type ended. The patterns the AI agents work from."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()


class CaseProfileRow(BaseModel):
    category: str
    region: str
    source_system: str
    n: int  # closed cases behind the figures below
    avg_days: float
    info_only_share: float
    transfer_rate: float
    reopen_rate: float
    breach_rate: float
    top_resolution: str  # the most common resolution action
    avg_bill_correction: float | None


PROFILE_SORTS = {name: name for name in CaseProfileRow.model_fields}


@router.get("/case-profiles", response_model=Page[CaseProfileRow], summary="Historic outcomes per category, region and source system")
def case_profiles(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `category,region,source_system`. Names: {', '.join(PROFILE_SORTS)}"),
    category: list[str] | None = Query(None, description="Repeat the parameter for several values"),
    region: list[str] | None = Query(None),
    source_system: list[str] | None = Query(None),
    top_resolution: list[str] | None = Query(None),
    n_min: int | None = Query(None, ge=1, description="Only profiles with at least this many closed cases"),
    avg_days_min: float | None = Query(None, ge=0),
    avg_days_max: float | None = Query(None, ge=0),
    info_only_share_min: float | None = Query(None, ge=0, le=1),
    transfer_rate_min: float | None = Query(None, ge=0, le=1),
    reopen_rate_min: float | None = Query(None, ge=0, le=1),
    breach_rate_min: float | None = Query(None, ge=0, le=1),
    db: Session = Depends(get_db),
):
    where = Where()
    for column, values in (
        ("category", category), ("region", region), ("source_system", source_system), ("top_resolution", top_resolution),
    ):
        where.any_of(column, values)
    where.compare("n", ">=", n_min)
    where.compare("avg_days", ">=", avg_days_min)
    where.compare("avg_days", "<=", avg_days_max)
    where.compare("info_only_share", ">=", info_only_share_min)
    where.compare("transfer_rate", ">=", transfer_rate_min)
    where.compare("reopen_rate", ">=", reopen_rate_min)
    where.compare("breach_rate", ">=", breach_rate_min)

    order, applied = order_by(sort, PROFILE_SORTS, "category,region,source_system", "category, region, source_system")
    return fetch_page(
        db, columns="*", source="v_case_profile", where=where, order=order, applied_sort=applied, pagination=pagination
    )
