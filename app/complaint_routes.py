import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.backends import OllamaBackend, TemplateBackend
from app.agents.service import run_domain_agent
from app.classification.schemas import ProcessRequest, ProcessResponse
from app.classification.service import classify_complaint, db_as_of_date, save_classification
from app.config import settings
from app.db import get_db
from app.laya_service import get_laya

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["complaints"])


def _agent_backend():
    if settings.agent_enabled:
        return OllamaBackend(
            model=settings.agent_model, host=settings.ollama_host, timeout=settings.agent_timeout_seconds
        )
    return TemplateBackend()


# Plain `def` so FastAPI runs the (blocking, CPU-bound) inference in its threadpool.
@router.post("/process", response_model=ProcessResponse)
def process_complaints(payload: ProcessRequest, db: Session = Depends(get_db)):
    """Classify complaints with Laya, store the result, then run the matching domain agent.

    A domain agent produces a draft reply (where one applies) and ranked action items. Agent
    failures never block the batch (requirement B5) - see app/agents/service.py.
    """
    as_of = payload.as_of_date or settings.as_of_date or db_as_of_date(db) or date.today()
    laya = get_laya()
    backend = _agent_backend()
    results = []
    try:
        for complaint in payload.complaints:
            complaint_id = complaint.complaint_id or f"CMP-{uuid.uuid4().hex[:10]}"
            result, raw = classify_complaint(complaint, complaint_id, as_of, laya)
            result.classification_id = save_classification(db, complaint, result, raw, as_of)
            # A database error in the agent step (e.g. the dashboard views are missing) rolls back
            # only this savepoint, so the classification above is kept. No AgentRun row survives to
            # record it, hence the log line (backend failures are recorded on the row instead).
            try:
                with db.begin_nested():
                    run_domain_agent(db, complaint, result, as_of, backend=backend)
            except Exception:
                logger.exception("Agent step failed for complaint %s", complaint_id)
            results.append(result)
        db.commit()
    except ValueError as e:
        # Laya raises ValueError for malformed questions, with a readable message.
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    return ProcessResponse(as_of_date=as_of, results=results)
