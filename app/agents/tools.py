"""LangChain tools for the domain-agent chat.

Each tool is scoped to one open complaint via closures - the agent is never given ids to pass
as tool arguments, so a small local model can't get them wrong. Tools only read data or (for
save_draft_reply) record a suggestion for staff; nothing here ever acts on a real account.

The three read tools and save_draft_reply are genuinely domain-agnostic (none of them reference
anything specific to a category), so every domain shares them. General additionally gets
search_knowledge_base, since it's the only tool backed by real data that isn't already in
Postgres (a small, static, hand-written FAQ - not a fake mocked backend system).
"""
from datetime import date

from langchain.tools import tool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Complaint, DraftResponse

# From the team's own knowledge-base examples. Answer only from here; no good match means the
# agent should say so, never guess (the same rule the team wrote for a human front-desk agent).
KNOWLEDGE_BASE: dict[str, str] = {
    "How do I pay my bill?": "Payment methods: online, phone, bank transfer, or in person.",
    "How do I read my meter?": "Where the meter is and how to read it depends on the meter type; "
        "ask the customer for the meter type or check the account's meter records.",
    'What does "estimated bill" mean?': "The bill is based on an estimate rather than an actual "
        "reading. This happens when no reading was available. The customer can submit their own "
        "reading to get an accurate bill.",
    "How do I set up a payment plan?": "Eligibility and how to apply depend on the account's "
        "current balance and payment history; refer the customer to Collections for the exact terms.",
    "How do I move or close my account?": "Requires advance notice and a final meter reading; "
        "refer the customer to account services for the exact steps and notice period.",
    "What do I do in a power outage?": "Check for known outages in the area and call the emergency "
        "number if the outage is unexpected or looks dangerous.",
}


def _pct(value: float | None) -> str:
    return f"{value * 100:.0f}%" if value is not None else "unknown"


_STOPWORDS = {"what", "does", "mean", "this", "that", "have", "with", "from", "your", "will", "about"}


def _keywords(text: str) -> set[str]:
    return {w.strip("?\"'.,") for w in text.lower().split() if len(w) > 3} - _STOPWORDS


def build_shared_tools(db: Session, complaint: Complaint, as_of: date) -> list:
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
        billing, metering or estimated-read cases."""
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


def build_general_tools(db: Session, complaint: Complaint, as_of: date) -> list:
    @tool
    def search_knowledge_base(question: str) -> str:
        """Find the approved answer to a general information question, e.g. how to pay a bill,
        read a meter, or set up a payment plan. Only answers from the fixed list below - if
        nothing matches well, say so rather than guessing."""
        question_words = _keywords(question)
        best_answer, best_score = None, 0
        for kb_question, answer in KNOWLEDGE_BASE.items():
            score = len(_keywords(kb_question) & question_words)
            if score > best_score:
                best_answer, best_score = answer, score
        if best_score == 0:
            return "No approved answer for this question in the knowledge base. Hand the case to a person."
        return best_answer

    return build_shared_tools(db, complaint, as_of) + [search_knowledge_base]


TOOL_BUILDERS = {
    "billing": build_shared_tools,
    "metering": build_shared_tools,
    "field_services": build_shared_tools,
    "customer_support": build_shared_tools,
    "general": build_general_tools,
}


def build_tools(agent_id: str | None, db: Session, complaint: Complaint, as_of: date) -> list:
    """Tools for the given domain. An unrecognized agent_id gets an empty list (still usable
    as a plain chat, just without lookups)."""
    builder = TOOL_BUILDERS.get(agent_id) if agent_id else None
    return builder(db, complaint, as_of) if builder else []
