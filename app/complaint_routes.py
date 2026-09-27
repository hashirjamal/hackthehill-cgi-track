import threading
import uuid
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.config import AGENT_CONFIGS, GROUP_TO_AGENT_ID
from app.agents.runner import (
    AgentBackendError,
    GENERATE_DRAFT_INSTRUCTION,
    GET_CONTEXT_INSTRUCTION,
    run_agent_once,
)
from app.agents.schemas import ActionItemOut, ContextResponse, DraftOut
from app.agents import rules_engine
from app.agents.systems import NorthwindLookups, SystemsClient, build_system_tools
from app.agents.tools import build_action_item_tool, build_context_tools_for, build_draft_tool
from app.classification.schemas import ComplaintIn, IntakeRequest, IntakeResponse, ProcessRequest, ProcessResponse
from app.classification.keywords import KEYWORDS_VERSION, KeywordModel
from app.classification.service import CLASSIFIER_VERSION, classify_complaint, db_as_of_date, save_classification
from app.config import settings
from app.db import get_db
from app.laya_service import get_laya
from app.models import Account, ActionItem, AgentRun, Classification, Complaint, DraftResponse, Region

router = APIRouter(prefix="/complaints", tags=["complaints"])


# Plain `def` so FastAPI runs the (blocking, CPU-bound) inference in its threadpool.
@router.post("/process", response_model=ProcessResponse)
def process_complaints(payload: ProcessRequest, db: Session = Depends(get_db)):
    """Classify complaints with Laya and store the result. Nothing else runs automatically - the
    domain agent only runs when a staff member clicks "Get context" or "Generate draft" on a
    specific complaint (POST /complaints/{complaint_id}/context or /draft)."""
    as_of = payload.as_of_date or settings.as_of_date or db_as_of_date(db) or date.today()
    laya = get_laya()
    results = []
    try:
        for complaint in payload.complaints:
            complaint_id = complaint.complaint_id or f"CMP-{uuid.uuid4().hex[:10]}"
            result, raw = classify_complaint(complaint, complaint_id, as_of, laya)
            result.classification_id = save_classification(db, complaint, result, raw, as_of)
            results.append(result)
        db.commit()
    except ValueError as e:
        # Laya raises ValueError for malformed questions, with a readable message.
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    return ProcessResponse(as_of_date=as_of, results=results)


def _next_complaint_id(db: Session) -> str:
    """Continue Northwind's NW-nnnnnn numbering (the ids are all six digits, so the text max is the number max)."""
    last = db.execute(select(func.max(Complaint.complaint_id)).where(Complaint.complaint_id.like("NW-%"))).scalar()
    return f"NW-{int(last[3:]) + 1 if last else 100001}"


# Plain `def` for the same reason as process_complaints above.
@router.post("/intake", response_model=IntakeResponse)
def intake_complaint(
    payload: IntakeRequest,
    mode: Literal["ai", "rules"] = Query("ai", description="ai (Laya) or rules (keyword rules, no AI - less accurate)"),
    db: Session = Depends(get_db),
):
    """A brand-new complaint from one of the four intake systems. Laya classifies it straight away -
    group, urgency and flags from the text, not from Northwind's history - and the complaint is
    saved as an open case, so it is on the worklist, ranked, the moment this returns."""
    if db.get(Region, payload.region) is None:
        raise HTTPException(status_code=422, detail=f"unknown region {payload.region!r}")
    as_of = settings.as_of_date or db_as_of_date(db) or date.today()
    complaint_id = _next_complaint_id(db)
    complaint_in = ComplaintIn(
        complaint_id=complaint_id, text=payload.text, channel=payload.channel, region=payload.region,
        source_system=payload.source_system, transferred_between_systems=False, date_opened=as_of,
        account_id=payload.account_id,
    )
    if mode == "rules":
        model, version = KeywordModel(), KEYWORDS_VERSION
    else:
        model, version = get_laya(), CLASSIFIER_VERSION
    try:
        result, raw = classify_complaint(complaint_in, complaint_id, as_of, model, classifier_version=version)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # A new customer may not have an account row yet; the upstream team owns account ids, so trust it.
    if db.get(Account, payload.account_id) is None:
        db.add(Account(account_id=payload.account_id))
    # Emergencies and review-queue cases have no subcategory; "Other" keeps the category column valid.
    category = result.subcategory.name if result.subcategory else "Other"
    db.add(Complaint(
        complaint_id=complaint_id, account_id=payload.account_id, date_opened=as_of, status="Open",
        channel=payload.channel, category=category, priority=result.priority.level, region=payload.region,
        source_system=payload.source_system, transferred_between_systems=False,
        sla_days=result.priority.target_days, sla_breach=False, reopened=False,
    ))
    db.flush()
    result.classification_id = save_classification(db, complaint_in, result, raw, as_of)
    db.commit()
    return IntakeResponse(complaint_id=complaint_id, category=category, as_of_date=as_of, classification=result)


def _build_agent_model() -> BaseChatModel | None:
    """None means N6's fallback: AI assistance is off, callers get a failed run instead of an LLM call."""
    if not settings.agent_enabled:
        return None
    return ChatOllama(
        model=settings.agent_model,
        base_url=settings.ollama_host,
        # Thinking off: left to its default, gemma4 writes hundreds of hidden reasoning tokens before
        # every tool call, which LangChain throws away. Measured: 291s per "Get context" with it, 21s without.
        reasoning=False,
        keep_alive="30m",  # stay loaded between clicks instead of reloading after Ollama's 5-minute default
        sync_client_kwargs={"timeout": settings.agent_timeout_seconds},
    )


def _resolve_complaint_and_agent(db: Session, complaint_id: str) -> tuple[Complaint, str | None, str | None]:
    """The complaint, its domain agent id (None when unclassified) and the customer's text (None
    unless it came in through /intake - the text is kept in the classification's input)."""
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"complaint {complaint_id} not found")
    classification = db.execute(
        select(Classification).where(
            Classification.complaint_id == complaint_id, Classification.is_current.is_(True)
        )
    ).scalar_one_or_none()
    agent_id = (
        GROUP_TO_AGENT_ID.get(classification.group_name) if classification and classification.group_name else None
    )
    customer_text = (classification.input or {}).get("text") if classification else None
    return complaint, agent_id, customer_text


RULES_MODEL = "rules (no AI)"  # agent_runs.model for runs built by app/agents/rules_engine.py


def _ai_run(db, complaint, agent_id, customer_text, as_of, run, model, trace, kind) -> str | None:
    """Run the local LLM. Returns None on success, or why it didn't produce anything."""
    # One lock per call, shared by every tool bound to it - LangGraph's ToolNode dispatches every
    # tool call (even a single one) through a thread pool, and one SQLAlchemy Session is not
    # safe for concurrent use across threads (confirmed live: reproduced "Session is already
    # flushing" without this).
    lock = threading.Lock()
    system_tools = build_system_tools(complaint, SystemsClient(trace))
    output_tool = (build_action_item_tool if kind == "context" else build_draft_tool)(db, complaint, run.run_id, lock)
    tools = [*build_context_tools_for(agent_id, db, complaint, as_of, lock, customer_text, system_tools), output_tool]
    cfg = AGENT_CONFIGS.get(agent_id) if agent_id else None
    try:
        run_agent_once(model, cfg, tools, GET_CONTEXT_INSTRUCTION if kind == "context" else GENERATE_DRAFT_INSTRUCTION)
    except AgentBackendError as e:
        return str(e)
    # The model can finish the loop without ever calling its output tool - e.g. it just answers in
    # plain text instead. "No exception" is not the same as "did what was asked".
    output = ActionItem if kind == "context" else DraftResponse
    if not db.query(output).filter_by(run_id=run.run_id).count():
        return "The AI did not record any action items." if kind == "context" else "The AI did not save a draft."
    return None


def _run_button(db: Session, complaint_id: str, kind: str, mode: str | None) -> AgentRun:
    """One click of "Get context" (kind="context") or "Generate draft" (kind="draft").

    mode "ai" runs the local LLM; mode "rules" runs app/agents/rules_engine.py - the same systems and
    database, no AI at all. With AI off (AGENT_ENABLED=false) or when an AI run produces nothing,
    the rules run instead, so staff always get a result. run.context records which mode was used."""
    complaint, agent_id, customer_text = _resolve_complaint_and_agent(db, complaint_id)
    as_of = settings.as_of_date or db_as_of_date(db) or date.today()
    model = _build_agent_model() if mode != "rules" else None
    run = AgentRun(
        complaint_id=complaint_id,
        # ai_agents.agent_id has no "unclassified" row - general is the sensible default for a case
        # with no current classification yet.
        agent_id=agent_id or "general",
        status="running",
        model=settings.agent_model if model is not None else RULES_MODEL,
    )
    db.add(run)
    db.flush()

    trace: list[dict] = []  # every Northwind system call, for "Systems checked"
    note = None
    if model is not None:
        failure = _ai_run(db, complaint, agent_id, customer_text, as_of, run, model, trace, kind)
        if failure is None:
            used = "ai"
        else:
            used, note = "rules", f"The AI didn't finish ({failure}), so the no-AI rules were used instead."
            for output in (ActionItem, DraftResponse):  # drop anything half-written by the failed AI run
                db.query(output).filter_by(run_id=run.run_id).delete()
            trace.clear()
            run.model = RULES_MODEL
    else:
        used = "rules"
        if mode != "rules":
            note = "AI assistance is turned off, so the no-AI rules were used."

    if used == "rules":
        look = NorthwindLookups(complaint, SystemsClient(trace))
        (rules_engine.run_context if kind == "context" else rules_engine.run_draft)(db, complaint, look, run.run_id)
    run.status, run.error = "succeeded", note
    run.finished_at = datetime.now(timezone.utc)
    run.context = {"systems_checked": trace, "mode": used}
    db.commit()
    return run


@router.post("/{complaint_id}/context", response_model=ContextResponse)
def get_context(
    complaint_id: str,
    mode: Literal["ai", "rules"] | None = Query(None, description="ai (local LLM) or rules (no AI). Default: ai when enabled"),
    db: Session = Depends(get_db),
):
    """"Get context" button on a case: checks Northwind's systems and records action items for
    staff - never a draft. Nothing runs until this is called."""
    run = _run_button(db, complaint_id, "context", mode)
    items = db.query(ActionItem).filter_by(run_id=run.run_id).order_by(ActionItem.rank).all()
    return ContextResponse(
        run_id=run.run_id,
        status=run.status,
        error=run.error,
        mode=run.context["mode"],
        action_items=[
            ActionItemOut(
                action_id=i.action_id, action_type=i.action_type, description=i.description,
                rationale=i.rationale, rank=i.rank,
            )
            for i in items
        ],
        systems_checked=run.context["systems_checked"],
    )


@router.post("/{complaint_id}/draft", response_model=DraftOut)
def generate_draft(
    complaint_id: str,
    mode: Literal["ai", "rules"] | None = Query(None, description="ai (local LLM) or rules (no AI). Default: ai when enabled"),
    db: Session = Depends(get_db),
):
    """"Generate draft" button on a case: checks Northwind's systems and saves one drafted reply,
    for staff to copy, edit, approve and send themselves. Nothing is sent automatically."""
    run = _run_button(db, complaint_id, "draft", mode)
    draft = db.query(DraftResponse).filter_by(run_id=run.run_id).order_by(DraftResponse.draft_id.desc()).first()
    return DraftOut(
        run_id=run.run_id,
        status=run.status,
        error=run.error,
        mode=run.context["mode"],
        draft_id=draft.draft_id if draft else None,
        body=draft.body if draft else None,
        systems_checked=run.context["systems_checked"],
    )
