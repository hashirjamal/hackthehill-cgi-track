"""LangChain tools for the domain-agent chat.

Each tool is scoped to one open complaint via closures - the agent is never given ids to pass
as tool arguments, so a small local model can't get them wrong. Tools only read data or (for
save_draft_reply) record a suggestion for staff; nothing here ever acts on a real account.
"""
from datetime import date

from langchain.tools import tool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Complaint, DraftResponse


def _pct(value: float | None) -> str:
    return f"{value * 100:.0f}%" if value is not None else "unknown"


def build_billing_tools(db: Session, complaint: Complaint, as_of: date) -> list:
    @tool
    def get_account_complaints() -> str:
        """List this account's other complaints (category, status, resolution), to spot repeat
        issues or earlier context on the same account."""
        rows = db.execute(
            text(
                "SELECT complaint_id, date_opened, category, status, resolution_action "
                "FROM v_account_history WHERE account_id = :account_id AND complaint_id != :current "
                "ORDER BY date_opened DESC LIMIT 20"
            ),
            {"account_id": complaint.account_id, "current": complaint.complaint_id},
        ).mappings().all()
        if not rows:
            return "No other complaints found for this account."
        return "\n".join(
            f"- {r['complaint_id']} ({r['date_opened']}): {r['category']}, {r['status']}, "
            f"resolution: {r['resolution_action'] or 'none yet'}"
            for r in rows
        )

    @tool
    def get_case_profile() -> str:
        """Look up how similar closed cases (same category, region and source system as this
        complaint) were usually handled: how many, average days to close, information-only
        share, transfer/reopen/breach rates, and the most common resolution."""
        row = db.execute(
            text(
                "SELECT n, avg_days, info_only_share, transfer_rate, reopen_rate, breach_rate, "
                "top_resolution FROM v_case_profile "
                "WHERE category = :category AND region = :region AND source_system = :source_system"
            ),
            {
                "category": complaint.category,
                "region": complaint.region,
                "source_system": complaint.source_system,
            },
        ).mappings().first()
        if not row:
            return "No matching case history for this category, region and system."
        return (
            f"Of {row['n']} similar closed cases: average {row['avg_days']} days to close, "
            f"{_pct(row['info_only_share'])} needed only information, {_pct(row['transfer_rate'])} "
            f"were transferred, {_pct(row['reopen_rate'])} were reopened, {_pct(row['breach_rate'])} "
            f"breached the SLA. Most common resolution: {row['top_resolution'] or 'no single common resolution'}."
        )

    @tool
    def get_region_meter_picture() -> str:
        """Look up this complaint's region's meter picture for the current month: estimated-read
        rate, smart-meter penetration, billing exceptions per 1,000 accounts. Most useful for
        billing or estimated-read cases."""
        row = db.execute(
            text(
                "SELECT month, estimated_read_rate, smart_meter_penetration, "
                "billing_exceptions_per_1000 FROM v_region_meter_complaints "
                "WHERE region = :region AND month = :month"
            ),
            {"region": complaint.region, "month": as_of.strftime("%Y-%m")},
        ).mappings().first()
        if not row:
            return "No meter data for this region and month."
        exceptions = row["billing_exceptions_per_1000"]
        return (
            f"{row['month']}: {_pct(row['estimated_read_rate'])} of bills are estimated reads, "
            f"{_pct(row['smart_meter_penetration'])} smart-meter penetration, "
            f"{exceptions if exceptions is not None else '?'} billing exceptions per 1,000 accounts."
        )

    @tool
    def save_draft_reply(body: str) -> str:
        """Save a drafted reply to the customer for this complaint. Only call this when staff
        explicitly ask for a draft. The draft is saved for staff review and is never sent
        automatically."""
        db.add(DraftResponse(complaint_id=complaint.complaint_id, body=body))
        db.flush()
        return "Draft saved for staff review."

    return [get_account_complaints, get_case_profile, get_region_meter_picture, save_draft_reply]


TOOL_BUILDERS = {"billing": build_billing_tools}


def build_tools(agent_id: str | None, db: Session, complaint: Complaint, as_of: date) -> list:
    """Tools for the given domain. Domains with no tool set yet get an empty list (still usable
    as a plain chat, just without lookups)."""
    builder = TOOL_BUILDERS.get(agent_id) if agent_id else None
    return builder(db, complaint, as_of) if builder else []
