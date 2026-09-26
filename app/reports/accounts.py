"""GET /reports/account-history: every complaint per account, in order, with repeat information."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.reports.query import Page, Pagination, Where, fetch_page, order_by

router = APIRouter()


class AccountHistoryRow(BaseModel):
    account_id: str
    complaint_id: str
    date_opened: date
    date_closed: date | None
    status: str
    category: str
    region: str
    channel: str
    priority: str
    resolution_action: str | None
    days_to_close: int | None
    reopened: bool
    transferred_between_systems: bool
    complaint_seq: int  # 1 for the account's first complaint
    complaints_on_account: int
    days_since_previous: int | None
    is_repeat: bool  # not the account's first complaint


HISTORY_SORTS = {name: name for name in AccountHistoryRow.model_fields}


@router.get(
    "/account-history",
    response_model=Page[AccountHistoryRow],
    summary="Complaints per account, with repeat information",
)
def account_history(
    pagination: Pagination = Depends(),
    sort: str | None = Query(None, description=f"Comma-separated `name:asc|desc`. Default `account_id,complaint_seq`. Names: {', '.join(HISTORY_SORTS)}"),
    account_id: list[str] | None = Query(None, description="Exact account ids. Repeat the parameter for several"),
    q: str | None = Query(None, description="Account or complaint id starts with this"),
    status: list[str] | None = Query(None, description="Open, Closed, Closed - reopened"),
    category: list[str] | None = Query(None),
    region: list[str] | None = Query(None),
    channel: list[str] | None = Query(None),
    priority: list[str] | None = Query(None),
    resolution_action: list[str] | None = Query(None),
    is_repeat: bool | None = Query(None, description="true: only repeat complaints, false: only first complaints"),
    repeat_accounts_only: bool | None = Query(None, description="true: only accounts with more than one complaint"),
    complaints_on_account_min: int | None = Query(None, ge=1),
    reopened: bool | None = None,
    transferred: bool | None = Query(None, description="Was transferred between systems"),
    opened_from: date | None = None,
    opened_to: date | None = None,
    days_since_previous_max: int | None = Query(None, ge=0, description="Repeat complaints raised within this many days"),
    db: Session = Depends(get_db),
):
    where = Where()
    where.prefix(["account_id", "complaint_id"], q)
    for column, values in (
        ("account_id", account_id), ("status", status), ("category", category), ("region", region),
        ("channel", channel), ("priority", priority), ("resolution_action", resolution_action),
    ):
        where.any_of(column, values)
    where.flag("is_repeat", is_repeat)
    if repeat_accounts_only:
        where.compare("complaints_on_account", ">=", 2)
    where.compare("complaints_on_account", ">=", complaints_on_account_min)
    where.flag("reopened", reopened)
    where.flag("transferred_between_systems", transferred)
    where.compare("date_opened", ">=", opened_from)
    where.compare("date_opened", "<=", opened_to)
    where.compare("days_since_previous", "<=", days_since_previous_max)

    order, applied = order_by(sort, HISTORY_SORTS, "account_id,complaint_seq", "complaint_id")
    return fetch_page(
        db, columns="*", source="v_account_history", where=where, order=order,
        applied_sort=applied, pagination=pagination,
    )
