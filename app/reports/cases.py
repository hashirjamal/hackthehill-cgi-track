"""Case reports: GET /reports/cases (search all complaints) and GET /reports/cases/{complaint_id} (full context)."""
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()

PRIORITY_RANK = "CASE {c} WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END"
AGE_BAND_RANK = "CASE age_band WHEN '0-5' THEN 1 WHEN '6-10' THEN 2 WHEN '11-20' THEN 3 WHEN '21-40' THEN 4 ELSE 5 END"

# Every complaint, open or closed, with live SLA status and its current classification (if any).
CASES_SOURCE = """(
    SELECT v.*, cl.id AS classification_id, cl.group_name, cl.subcategory,
           COALESCE(cl.priority, v.priority) AS classified_priority, cl.routed_team, cl.lane
    FROM v_case_sla v
    LEFT JOIN classifications cl ON cl.complaint_id = v.complaint_id AND cl.is_current
) cases"""


class CaseRow(BaseModel):
    complaint_id: str
    account_id: str
    date_opened: date
    date_closed: date | None
    status: str
    channel: str
    category: str
    priority: str
    region: str
    source_system: str
    transferred_between_systems: bool
    sla_days: int
    days_to_close: int | None
    reopened: bool
    resolution_action: str | None
    resolvable_by_information_only: bool | None
    bill_correction_value: float | None
    domain: str
    days_open: int  # for closed cases, the days it took to close
    days_overdue: int  # negative while inside the target
    breached_live: bool
    age_band: str
    classification_id: int | None
    group_name: str | None
    subcategory: str | None
    classified_priority: str
    routed_team: str | None
    lane: str | None


CASE_SORTS = {
    "date_opened": "date_opened", "date_closed": "date_closed", "complaint_id": "complaint_id", "account_id": "account_id",
    "days_open": "days_open", "days_overdue": "days_overdue", "days_to_close": "days_to_close", "sla_days": "sla_days",
    "status": "status", "region": "region", "category": "category", "domain": "domain", "channel": "channel",
    "priority": PRIORITY_RANK.format(c="priority"), "classified_priority": PRIORITY_RANK.format(c="classified_priority"),
    "age_band": AGE_BAND_RANK, "bill_correction_value": "bill_correction_value", "routed_team": "routed_team",
}


@router.get("/cases", response_model=Page[CaseRow], summary="Search every complaint, open or closed")
def cases(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `date_opened:desc`. Names: {', '.join(CASE_SORTS)}"),
    q: str | None = Query(None, description="Complaint or account id starts with this"),
    status: list[str] | None = Query(None, description="Open, Closed, Closed - reopened. Repeat for several"),
    region: list[str] | None = Query(None),
    category: list[str] | None = Query(None),
    domain: list[str] | None = Query(None),
    priority: list[str] | None = Query(None),
    classified_priority: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    source_system: list[str] | None = Query(None),
    age_band: list[str] | None = Query(None, description="0-5, 6-10, 11-20, 21-40, 41+"),
    resolution_action: list[str] | None = Query(None),
    group_name: list[str] | None = Query(None),
    routed_team: list[str] | None = Query(None),
    lane: list[str] | None = Query(None),
    breached: bool | None = Query(None, description="Past its SLA target (for closed cases, took longer than the target)"),
    transferred: bool | None = Query(None, description="Was transferred between systems"),
    reopened: bool | None = None,
    info_only: bool | None = Query(None, description="Resolvable by information only. Only known for closed cases, so open cases match neither true nor false"),
    classified: bool | None = Query(None, description="Has a current classification"),
    days_open_min: int | None = None,
    days_open_max: int | None = None,
    days_overdue_min: int | None = None,
    opened_from: date | None = None,
    opened_to: date | None = None,
    closed_from: date | None = None,
    closed_to: date | None = None,
    bill_correction_min: float | None = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    where = Where()
    where.prefix(["complaint_id", "account_id"], q)
    for column, values in (
        ("status", status), ("region", region), ("category", category), ("domain", domain), ("priority", priority),
        ("classified_priority", classified_priority), ("channel", channel), ("source_system", source_system),
        ("age_band", age_band), ("resolution_action", resolution_action), ("group_name", group_name),
        ("routed_team", routed_team), ("lane", lane),
    ):
        where.any_of(column, values)
    where.flag("breached_live", breached)
    where.flag("transferred_between_systems", transferred)
    where.flag("reopened", reopened)
    where.flag("resolvable_by_information_only", info_only, strict=True)
    where.is_set("classification_id", classified)
    where.compare("days_open", ">=", days_open_min)
    where.compare("days_open", "<=", days_open_max)
    where.compare("days_overdue", ">=", days_overdue_min)
    where.compare("date_opened", ">=", opened_from)
    where.compare("date_opened", "<=", opened_to)
    where.compare("date_closed", ">=", closed_from)
    where.compare("date_closed", "<=", closed_to)
    where.compare("bill_correction_value", ">=", bill_correction_min)

    order, applied = order_by(sort, CASE_SORTS, "date_opened:desc", "complaint_id")
    return fetch_page(
        db, columns="*", source=CASES_SOURCE, where=where, order=order, applied_sort=applied, pagination=pagination
    )
