"""LangChain tools for the domain agent, triggered by one of two buttons on a complaint's case
view - "Get context" (produces action items) or "Generate draft" (produces a draft reply).

Every tool is scoped to one complaint via closures - the agent is never given ids to pass as
arguments, so a small local model can't get them wrong. The context-gathering tools (read_case,
get_account_complaints, get_case_profile, get_region_meter_picture) are shared by both buttons and
every domain, since none of them reference anything domain-specific. Which single output tool is
bound (create_action_brief or save_draft_reply) is what actually separates the two buttons - the
model structurally cannot produce the other kind of output, whatever the prompt says.

LangGraph's ToolNode runs every tool call through a ThreadPoolExecutor, even when there's only
one call to make (confirmed by reading langgraph.prebuilt.tool_node - it always goes through
`executor.map`, never inline on the calling thread). Every DB-touching tool built here therefore
takes the same `lock` (one per request, created by the caller) around its query/write, so two
tool calls sharing one SQLAlchemy Session are never actually concurrent - confirmed live against
a real Ollama model, which reliably reproduced "Session is already flushing" without this lock.
"""
import threading
from datetime import date

from langchain.tools import tool
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import ActionItem, Complaint, DraftResponse

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

_STOPWORDS = {"what", "does", "mean", "this", "that", "have", "with", "from", "your", "will", "about"}


def _keywords(text_: str) -> set[str]:
    return {w.strip("?\"'.,") for w in text_.lower().split() if len(w) > 3} - _STOPWORDS


def _pct(value: float | None) -> str:
    return f"{value * 100:.0f}%" if value is not None else "unknown"


def build_context_tools(
    db: Session, complaint: Complaint, as_of: date, lock: threading.Lock, customer_text: str | None = None
) -> list:
    """Read-only lookups every domain shares. No side effects. customer_text is what the customer
    said, from the intake template - None for complaints loaded from the CSV, which have no text."""

    @tool
    def read_case() -> str:
        """Read this complaint's own details: category, channel, priority, region, source
        system, status, and how long it has been open. Always useful - call this first."""
        # No `db` access at all - just the complaint's own attributes - so no lock needed.
        open_days = (as_of - complaint.date_opened).days
        parts = [
            f"Complaint {complaint.complaint_id}: {complaint.category}, via {complaint.channel}, "
            f"priority {complaint.priority} (target {complaint.sla_days} days), region {complaint.region}, "
            f"source system {complaint.source_system}, status {complaint.status}, "
            f"opened {complaint.date_opened}, {open_days} days open."
        ]
        if complaint.transferred_between_systems:
            parts.append("It has been transferred between systems.")
        if customer_text:
            parts.append(f"The customer said: {customer_text}")
        return " ".join(parts)

    @tool
    def get_account_complaints() -> str:
        """List this account's other complaints (category, status, resolution), to spot repeat
        issues or earlier context on the same account."""
        with lock:
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
        with lock:
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
        with lock:
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

    return [read_case, get_account_complaints, get_case_profile, get_region_meter_picture]


def _knowledge_base_tool():
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

    return search_knowledge_base


def build_context_tools_for(
    agent_id: str | None,
    db: Session,
    complaint: Complaint,
    as_of: date,
    lock: threading.Lock,
    customer_text: str | None = None,
) -> list:
    """Context tools for the given domain. general additionally gets search_knowledge_base -
    the one genuinely domain-specific real data source available (a static FAQ). Every other
    domain, and an unclassified complaint (agent_id is None), gets the shared set only."""
    tools = build_context_tools(db, complaint, as_of, lock, customer_text)
    if agent_id == "general":
        tools = [*tools, _knowledge_base_tool()]
    return tools


def build_action_item_tool(db: Session, complaint: Complaint, run_id: int, lock: threading.Lock):
    """The only tool bound to the "Get context" button. Every call records one action item;
    call it once per distinct action, in the order staff should tackle them."""

    @tool
    def create_action_brief(action_type: str, description: str, rationale: str) -> str:
        """Record one concrete next action for staff to take on this case.

        Args:
            action_type: a short machine-friendly label, e.g. correct_bill, book_meter_read,
                escalate_field, call_customer.
            description: what staff should do, in one sentence.
            rationale: why this action, in one short phrase.
        """
        with lock:
            # Ranked within this run: each click of "Get context" is a fresh list starting at 1.
            rank = db.query(ActionItem).filter_by(run_id=run_id).count() + 1
            db.add(ActionItem(
                complaint_id=complaint.complaint_id, run_id=run_id, action_type=action_type,
                description=description, rationale=rationale, rank=rank,
            ))
            db.flush()
        return "Action item recorded."

    return create_action_brief


def build_draft_tool(db: Session, complaint: Complaint, run_id: int, lock: threading.Lock):
    """The only tool bound to the "Generate draft" button. The draft is saved for staff to
    review, edit and send themselves - it is never sent automatically."""

    @tool
    def save_draft_reply(body: str) -> str:
        """Save a drafted reply to the customer for this complaint."""
        with lock:
            db.add(DraftResponse(complaint_id=complaint.complaint_id, run_id=run_id, body=body))
            db.flush()
        return "Draft saved for staff review."

    return save_draft_reply
