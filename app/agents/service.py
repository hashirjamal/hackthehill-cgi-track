"""Orchestrates one domain agent run: build context, call the backend, persist the result.

Per requirement B5, a backend failure must never stop the batch: it is caught here and recorded on
the AgentRun row (status='failed', error=<message>), and no DraftResponse/ActionItem rows are written.
"""
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.agents.backends import AgentBackend, AgentBackendError
from app.agents.config import AGENT_CONFIGS, GROUP_TO_AGENT_ID
from app.agents.context import build_context
from app.classification.schemas import ClassificationResult, ComplaintIn
from app.models import ActionItem, AgentRun, DraftResponse


def run_domain_agent(
    db: Session, complaint: ComplaintIn, result: ClassificationResult, as_of: date, backend: AgentBackend
) -> AgentRun | None:
    """Returns the AgentRun row, or None when the complaint is an emergency (agents don't run at all)."""
    if result.emergency:
        return None

    agent_id = GROUP_TO_AGENT_ID[result.group.name]
    cfg = AGENT_CONFIGS[agent_id]

    run = AgentRun(
        complaint_id=result.complaint_id,
        agent_id=agent_id,
        classification_id=result.classification_id,
        status="running",
        model=backend.model_name,
    )
    db.add(run)
    db.flush()

    context = build_context(db, complaint, as_of)
    run.context = context.model_dump(mode="json")

    try:
        draft = backend.draft(cfg, complaint, context)
    except AgentBackendError as e:
        run.status = "failed"
        run.error = str(e)
        run.finished_at = datetime.now(timezone.utc)
        return run

    run.status = "succeeded"
    run.finished_at = datetime.now(timezone.utc)
    if draft.draft_reply is not None:
        db.add(DraftResponse(complaint_id=result.complaint_id, run_id=run.run_id, body=draft.draft_reply))
    for item in draft.action_items:
        db.add(ActionItem(
            complaint_id=result.complaint_id,
            run_id=run.run_id,
            action_type=item.action_type,
            description=item.description,
            rationale=item.rationale,
            rank=item.rank,
        ))
    return run
