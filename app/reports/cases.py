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


# --- GET /reports/cases/{complaint_id} ---------------------------------------------------------


class CaseContext(BaseModel):
    case: CaseRow
    classification: dict[str, Any] | None  # the current classification, without the raw Laya output
    region_meter: list[dict[str, Any]]  # the region's last six months, newest first
    profile: dict[str, Any] | None  # closed cases of the same category, region and source system
    category_profile: dict[str, Any] | None  # closed cases of the same category, all regions
    resolution_mix: list[dict[str, Any]]  # how closed cases of this category ended, most common first
    account_complaints_total: int
    account_history: list[dict[str, Any]]  # oldest first, up to history_limit
    drafts: list[dict[str, Any]]
    action_items: list[dict[str, Any]]
    # Northwind systems the agent checked, for the latest "Get context" and "Generate draft" runs, by run_id.
    systems_checked: dict[int, list[dict[str, Any]]] = {}
    run_modes: dict[int, str] = {}  # "ai" or "rules" (no AI), by run_id


def _rows(db: Session, sql: str, **params) -> list[dict[str, Any]]:
    return [_plain(dict(r)) for r in db.execute(text(sql), params).mappings().all()]


def _plain(row: dict[str, Any]) -> dict[str, Any]:
    """Decimals to floats, so the JSON has numbers and not strings."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}


@router.get(
    "/cases/{complaint_id}",
    response_model=CaseContext,
    summary="Everything known about one complaint: case, classification, meter data, history, drafts",
)
def case_context(
    complaint_id: str,
    history_limit: int = Query(20, ge=1, le=50, description="How many of the account's complaints to include"),
    db: Session = Depends(get_db),
):
    case = db.execute(text(f"SELECT * FROM {CASES_SOURCE} WHERE complaint_id = :id"), {"id": complaint_id}).mappings().first()
    if case is None:
        raise HTTPException(status_code=404, detail=f"complaint {complaint_id!r} not found")
    case = _plain(dict(case))
    category, region, source_system = case["category"], case["region"], case["source_system"]

    classification = _rows(
        db,
        """SELECT id AS classification_id, classifier_version, created_at, as_of_date, emergency, emergency_probability,
                  group_name, group_confidence, group_source, laya_group, subcategory, subcategory_confidence,
                  subcategory_source, low_confidence, group_matches_data, subcategory_matches_data, priority,
                  base_priority, base_priority_source, urgency_score, routed_team, lane, likely_cause, flags
           FROM classifications WHERE complaint_id = :id AND is_current""",
        id=complaint_id,
    )
    region_meter = _rows(
        db,
        """SELECT m.month, m.estimated_read_rate, m.smart_meter_penetration, m.billing_exceptions_raised,
                  round(m.billing_exceptions_raised * 1000.0 / m.accounts, 2) AS billing_exceptions_per_1000
           FROM meter_reads m WHERE m.region = :region AND m.month <= to_char(CAST(:as_of AS date), 'YYYY-MM')
           ORDER BY m.month DESC LIMIT 6""",
        region=region, as_of=case["as_of_date"],
    )
    profile = _rows(
        db,
        "SELECT * FROM v_case_profile WHERE category = :c AND region = :r AND source_system = :s",
        c=category, r=region, s=source_system,
    )
    category_profile = _rows(
        db,
        """SELECT count(*) AS n, round(avg(days_to_close), 1) AS avg_days,
                  round(avg(resolvable_by_information_only::int), 3) AS info_only_share,
                  round(avg(transferred_between_systems::int), 3) AS transfer_rate,
                  round(avg(reopened::int), 3) AS reopen_rate, round(avg(sla_breach::int), 3) AS breach_rate,
                  round(avg(bill_correction_value), 2) AS avg_bill_correction
           FROM complaints WHERE status <> 'Open' AND category = :c""",
        c=category,
    )
    resolution_mix = _rows(
        db,
        """SELECT resolution_action, count(*) AS cases,
                  round(count(*)::numeric / sum(count(*)) OVER (), 3) AS share
           FROM complaints WHERE status <> 'Open' AND category = :c
           GROUP BY resolution_action ORDER BY cases DESC, resolution_action""",
        c=category,
    )
    total = db.execute(text("SELECT count(*) FROM complaints WHERE account_id = :a"), {"a": case["account_id"]}).scalar_one()
    history = _rows(
        db,
        """SELECT complaint_id, date_opened, status, category, region, priority, resolution_action, days_to_close,
                  reopened, complaint_seq, is_repeat, days_since_previous
           FROM v_account_history WHERE account_id = :a ORDER BY complaint_seq LIMIT :n""",
        a=case["account_id"], n=history_limit,
    )
    drafts = _rows(
        db,
        """SELECT draft_id, run_id, status, body, final_body, reviewed_by, reviewed_at, created_at
           FROM draft_responses WHERE complaint_id = :id ORDER BY created_at DESC, draft_id DESC LIMIT 5""",
        id=complaint_id,
    )
    actions = _rows(
        db,
        """SELECT action_id, run_id, action_type, description, rationale, rank, status, assigned_team, due_date
           FROM action_items WHERE complaint_id = :id ORDER BY run_id DESC NULLS LAST, rank, action_id""",
        id=complaint_id,
    )
    run_ids = {r["run_id"] for r in (actions[:1] + drafts[:1]) if r.get("run_id") is not None}
    runs = _rows(db, "SELECT run_id, context FROM agent_runs WHERE run_id = ANY(:ids)", ids=list(run_ids)) if run_ids else []
    systems_checked = {r["run_id"]: (r["context"] or {}).get("systems_checked", []) for r in runs}
    run_modes = {r["run_id"]: (r["context"] or {}).get("mode", "ai") for r in runs}
    return {
        "systems_checked": systems_checked,
        "run_modes": run_modes,
        "case": case,
        "classification": classification[0] if classification else None,
        "region_meter": region_meter,
        "profile": profile[0] if profile else None,
        "category_profile": category_profile[0] if category_profile and category_profile[0]["n"] else None,
        "resolution_mix": resolution_mix,
        "account_complaints_total": total,
        "account_history": history,
        "drafts": drafts,
        "action_items": actions,
    }
