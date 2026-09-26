"""GET /reports/worklist: the open backlog for contact-centre staff, most urgent first."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()


class WorklistRow(BaseModel):
    complaint_id: str
    account_id: str
    date_opened: date
    channel: str
    category: str
    priority: str  # Northwind's priority
    region: str
    source_system: str
    sla_days: int
    days_open: int
    days_overdue: int  # negative while still inside the target
    breached_live: bool
    domain: str  # the AI agent that handles it
    classification_id: int | None  # None until the case has been classified
    group_name: str | None
    subcategory: str | None
    classified_priority: str  # after flags; Northwind's priority if not classified yet
    base_priority: str | None
    base_priority_source: str | None
    routed_team: str | None
    lane: str | None  # emergency, review, quick_lane or standard
    likely_cause: str | None
    low_confidence: bool | None
    flags: list[dict] | None
    region_estimated_read_rate: float | None
    draft_id: int | None
    draft_status: str | None
    open_actions: int
    next_action: str | None


PRIORITY_RANK = "CASE {c} WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END"
SORTS = {
    "classified_priority": PRIORITY_RANK.format(c="classified_priority"),
    "priority": PRIORITY_RANK.format(c="priority"),
    "days_overdue": "days_overdue",
    "days_open": "days_open",
    "date_opened": "date_opened",
    "sla_days": "sla_days",
    "complaint_id": "complaint_id",
    "region": "region",
    "category": "category",
    "domain": "domain",
    "routed_team": "routed_team",
    "lane": "lane",
    "open_actions": "open_actions",
    "region_estimated_read_rate": "region_estimated_read_rate",
}


@router.get("/worklist", response_model=Page[WorklistRow], summary="Ranked worklist of open complaints")
def worklist(
    pagination: Pagination = Depends(),
    sort: str | None = Query(
        None,
        description="Comma-separated `name:asc|desc`. Default `classified_priority,days_overdue:desc` "
        f"(P1 first, then most overdue). Names: {', '.join(SORTS)}",
    ),
    q: str | None = Query(None, description="Complaint or account id starts with this"),
    region: list[str] | None = Query(None, description="Repeat the parameter for several values"),
    category: list[str] | None = Query(None),
    domain: list[str] | None = Query(None, description="billing, metering, field_services, customer_support, general"),
    priority: list[str] | None = Query(None, description="Northwind's priority, P1 to P3"),
    classified_priority: list[str] | None = Query(None, description="Priority after the classifier's flags"),
    group_name: list[str] | None = Query(None, description="Classifier group"),
    routed_team: list[str] | None = Query(None),
    lane: list[str] | None = Query(None, description="emergency, review, quick_lane, standard"),
    source_system: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    likely_cause: list[str] | None = Query(None, description="e.g. estimated_reading"),
    breached: bool | None = Query(None, description="Past its SLA target as of the as_of_date"),
    classified: bool | None = Query(None, description="Has a current classification"),
    low_confidence: bool | None = Query(None),
    days_overdue_min: int | None = Query(None, description="Use 0 for cases already past target"),
    days_overdue_max: int | None = None,
    days_open_min: int | None = None,
    days_open_max: int | None = None,
    opened_from: date | None = None,
    opened_to: date | None = None,
    db: Session = Depends(get_db),
):
    where = Where()
    where.prefix(["complaint_id", "account_id"], q)
    for column, values in (
        ("region", region), ("category", category), ("domain", domain), ("priority", priority),
        ("classified_priority", classified_priority), ("group_name", group_name), ("routed_team", routed_team),
        ("lane", lane), ("source_system", source_system), ("channel", channel), ("likely_cause", likely_cause),
    ):
        where.any_of(column, values)
    where.flag("breached_live", breached)
    where.is_set("classification_id", classified)
    where.flag("low_confidence", low_confidence)
    where.compare("days_overdue", ">=", days_overdue_min)
    where.compare("days_overdue", "<=", days_overdue_max)
    where.compare("days_open", ">=", days_open_min)
    where.compare("days_open", "<=", days_open_max)
    where.compare("date_opened", ">=", opened_from)
    where.compare("date_opened", "<=", opened_to)

    order, applied = order_by(sort, SORTS, "classified_priority,days_overdue:desc", "complaint_id")
    return fetch_page(
        db, columns="*", source="v_worklist", where=where, order=order, applied_sort=applied, pagination=pagination
    )
