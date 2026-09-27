import threading
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.config import AGENT_CONFIGS, GROUP_TO_AGENT_ID, AgentConfig
from app.agents.runner import (
    AgentBackendError,
    GENERATE_DRAFT_INSTRUCTION,
    GET_CONTEXT_INSTRUCTION,
    run_agent_once,
)
from app.agents.schemas import ActionItemOut, ContextResponse, DraftOut
from app.agents.tools import build_action_item_tool, build_context_tools_for, build_draft_tool
from app.classification.schemas import ComplaintIn, IntakeRequest, IntakeResponse, ProcessRequest, ProcessResponse
from app.classification.service import classify_complaint, db_as_of_date, save_classification
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
def intake_complaint(payload: IntakeRequest, db: Session = Depends(get_db)):
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
    try:
        result, raw = classify_complaint(complaint_in, complaint_id, as_of, get_laya())
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


def _start_run(db: Session, complaint_id: str, agent_id: str | None, model: BaseChatModel | None) -> AgentRun:
    # ai_agents.agent_id has no "unclassified" row - general is the sensible default for a case
    # with no current classification yet (it already handles low-confidence cases, per taxonomy).
    run = AgentRun(
        complaint_id=complaint_id,
        agent_id=agent_id or "general",
        status="running",
        model=settings.agent_model if model is not None else "disabled",
    )
    db.add(run)
    db.flush()
    return run


def _run_and_finish(
    run: AgentRun, model: BaseChatModel | None, cfg: AgentConfig | None, tools: list, instruction: str
) -> None:
    if model is None:
        run.status, run.error = "failed", "AI assistance is turned off (AGENT_ENABLED=false)."
    else:
        try:
            run_agent_once(model, cfg, tools, instruction)
            run.status = "succeeded"
        except AgentBackendError as e:
            run.status, run.error = "failed", str(e)
    run.finished_at = datetime.now(timezone.utc)


@router.post("/{complaint_id}/context", response_model=ContextResponse)
def get_context(complaint_id: str, db: Session = Depends(get_db)):
    """"Get context" button on a case: runs the domain agent's read-only tools and asks it to
    record action items for staff - never a draft. Nothing runs until this is called."""
    complaint, agent_id, customer_text = _resolve_complaint_and_agent(db, complaint_id)
    cfg = AGENT_CONFIGS.get(agent_id) if agent_id else None
    as_of = settings.as_of_date or db_as_of_date(db) or date.today()

    model = _build_agent_model()
    run = _start_run(db, complaint_id, agent_id, model)
    # One lock per call, shared by every tool bound to it - LangGraph's ToolNode dispatches every
    # tool call (even a single one) through a thread pool, and one SQLAlchemy Session is not
    # safe for concurrent use across threads (confirmed live: reproduced "Session is already
    # flushing" without this).
    lock = threading.Lock()
    tools = [
        *build_context_tools_for(agent_id, db, complaint, as_of, lock, customer_text),
        build_action_item_tool(db, complaint, run.run_id, lock),
    ]
    _run_and_finish(run, model, cfg, tools, GET_CONTEXT_INSTRUCTION)

    items = db.query(ActionItem).filter_by(run_id=run.run_id).order_by(ActionItem.rank).all()
    if run.status == "succeeded" and not items:
        # The model can finish the loop without ever calling create_action_brief - e.g. it just
        # answers in plain text instead. "No exception" is not the same as "did what was asked".
        run.status, run.error = "failed", "The agent did not record any action items."
    db.commit()
    return ContextResponse(
        run_id=run.run_id,
        status=run.status,
        error=run.error,
        action_items=[
            ActionItemOut(
                action_id=i.action_id, action_type=i.action_type, description=i.description,
                rationale=i.rationale, rank=i.rank,
            )
            for i in items
        ],
    )


@router.post("/{complaint_id}/draft", response_model=DraftOut)
def generate_draft(complaint_id: str, db: Session = Depends(get_db)):
    """"Generate draft" button on a case: runs the domain agent's read-only tools and asks it to
    save one drafted reply, for staff to copy, edit, approve and send themselves. Nothing is sent
    automatically."""
    complaint, agent_id, customer_text = _resolve_complaint_and_agent(db, complaint_id)
    cfg = AGENT_CONFIGS.get(agent_id) if agent_id else None
    as_of = settings.as_of_date or db_as_of_date(db) or date.today()

    model = _build_agent_model()
    run = _start_run(db, complaint_id, agent_id, model)
    lock = threading.Lock()  # see get_context() above for why this is needed
    tools = [
        *build_context_tools_for(agent_id, db, complaint, as_of, lock, customer_text),
        build_draft_tool(db, complaint, run.run_id, lock),
    ]
    _run_and_finish(run, model, cfg, tools, GENERATE_DRAFT_INSTRUCTION)

    draft = db.query(DraftResponse).filter_by(run_id=run.run_id).order_by(DraftResponse.draft_id.desc()).first()
    if run.status == "succeeded" and draft is None:
        # Same reasoning as get_context() above: the model can finish without ever calling
        # save_draft_reply, and that must not be reported as success.
        run.status, run.error = "failed", "The agent did not save a draft."
    db.commit()
    return DraftOut(
        run_id=run.run_id,
        status=run.status,
        error=run.error,
        draft_id=draft.draft_id if draft else None,
        body=draft.body if draft else None,
    )
