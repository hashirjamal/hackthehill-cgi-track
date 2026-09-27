"""Builds an AgentContext by reading the dashboard SQL views (db/views.sql).

Queries name the view's output columns, not Postgres-only SQL, so the queries themselves are
portable and testable against a plain SQLite table shaped like the view (see tests/test_agent_context.py).
"""
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.schemas import AccountHistoryEntry, AgentContext, CaseProfile, RegionMeterPicture
from app.classification.schemas import ComplaintIn


def case_profile(db: Session, category: str, region: str, source_system: str) -> CaseProfile | None:
    row = db.execute(
        text(
            "SELECT category, region, source_system, n, avg_days, info_only_share, transfer_rate, "
            "reopen_rate, breach_rate, top_resolution FROM v_case_profile "
            "WHERE category = :category AND region = :region AND source_system = :source_system"
        ),
        {"category": category, "region": region, "source_system": source_system},
    ).mappings().first()
    return CaseProfile(**row) if row else None


def account_history(db: Session, account_id: str, limit: int = 10) -> list[AccountHistoryEntry]:
    rows = db.execute(
        text(
            "SELECT complaint_id, date_opened, category, status, resolution_action, days_to_close, is_repeat "
            "FROM v_account_history WHERE account_id = :account_id "
            "ORDER BY date_opened DESC LIMIT :limit"
        ),
        {"account_id": account_id, "limit": limit},
    ).mappings().all()
    return [AccountHistoryEntry(**{**r, "is_repeat": bool(r["is_repeat"])}) for r in rows]


def region_meter_picture(db: Session, region: str, month: str) -> RegionMeterPicture | None:
    row = db.execute(
        text(
            "SELECT region, month, estimated_read_rate, smart_meter_penetration, "
            "billing_exceptions_per_1000, billing_metering_share FROM v_region_meter_complaints "
            "WHERE region = :region AND month = :month"
        ),
        {"region": region, "month": month},
    ).mappings().first()
    return RegionMeterPicture(**row) if row else None


def build_context(db: Session, complaint: ComplaintIn, as_of: date) -> AgentContext:
    """Look up whatever the complaint gives us enough fields for; skip the rest silently."""
    profile = None
    if complaint.category and complaint.region and complaint.source_system:
        profile = case_profile(db, complaint.category, complaint.region, complaint.source_system)

    history: list[AccountHistoryEntry] = []
    if complaint.account_id:
        history = account_history(db, complaint.account_id)

    meter = None
    if complaint.region:
        meter = region_meter_picture(db, complaint.region, as_of.strftime("%Y-%m"))

    return AgentContext(case_profile=profile, account_history=history, region_meter_picture=meter)
