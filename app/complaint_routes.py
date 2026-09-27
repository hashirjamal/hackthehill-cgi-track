import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.chat import NO_LLM_REPLY, run_chat_turn
from app.agents.config import AGENT_CONFIGS, GROUP_TO_AGENT_ID
from app.agents.schemas import ChatRequest, ChatResponse
from app.agents.tools import build_tools
from app.classification.schemas import ProcessRequest, ProcessResponse
from app.classification.service import classify_complaint, db_as_of_date, save_classification
from app.config import settings
from app.db import get_db
from app.laya_service import get_laya
from app.models import ChatMessage, ChatSession, Classification, Complaint

router = APIRouter(prefix="/complaints", tags=["complaints"])


# Plain `def` so FastAPI runs the (blocking, CPU-bound) inference in its threadpool.
@router.post("/process", response_model=ProcessResponse)
def process_complaints(payload: ProcessRequest, db: Session = Depends(get_db)):
    """Classify complaints with Laya and store the result. Nothing else runs automatically -
    the domain agent only runs when a staff member opens a chat on a specific complaint
    (POST /complaints/{complaint_id}/chat)."""
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


def _build_chat_model() -> BaseChatModel | None:
    """None means N6's fallback: AI chat is off, callers get a fixed message instead."""
    if not settings.agent_enabled:
        return None
    return ChatOllama(
        model=settings.agent_model,
        base_url=settings.ollama_host,
        sync_client_kwargs={"timeout": settings.agent_timeout_seconds},
    )


@router.post("/{complaint_id}/chat", response_model=ChatResponse)
def chat_with_agent(complaint_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    """One turn of a staff <-> domain-agent chat about one complaint. The agent only runs when
    called here - triggered by a staff member opening this specific complaint, never automatically.
    """
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"complaint {complaint_id} not found")

    classification = db.execute(
        select(Classification).where(
            Classification.complaint_id == complaint_id, Classification.is_current.is_(True)
        )
    ).scalar_one_or_none()
    agent_id = GROUP_TO_AGENT_ID.get(classification.group_name) if classification and classification.group_name else None
    cfg = AGENT_CONFIGS.get(agent_id) if agent_id else None

    as_of = settings.as_of_date or db_as_of_date(db) or date.today()
    tools = build_tools(agent_id, db, complaint, as_of)

    session = ChatSession(staff_id=payload.staff_id, complaint_id=complaint_id)
    db.add(session)
    db.flush()
    db.add(ChatMessage(session_id=session.session_id, role="staff", content=payload.message))

    model = _build_chat_model()
    if model is None:
        reply, draft_saved = NO_LLM_REPLY, False
    else:
        history = [(turn.role, turn.content) for turn in payload.history]
        reply, draft_saved = run_chat_turn(model, cfg, tools, history, payload.message)

    db.add(ChatMessage(session_id=session.session_id, role="assistant", content=reply))
    db.commit()
    return ChatResponse(session_id=session.session_id, reply=reply, draft_saved=draft_saved)
