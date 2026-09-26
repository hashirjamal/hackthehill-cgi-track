from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.laya_service import get_router

router = APIRouter(prefix="/laya", tags=["laya"])

SAMPLE_STATE = "Hi, we were billed twice for March. Please refund the duplicate charge or we'll cancel our subscription."
SAMPLE_QUESTIONS = {
    "department": {
        "type": "choice",
        "instructions": "Which department handles this?",
        "criteria": {"billing": "invoices, refunds", "technical": "bugs, outages"},
    },
    "churn_risk": {
        "type": "noul",
        "instructions": "Does the user threaten to leave?",
    },
}


class PredictIn(BaseModel):
    # State can be plain text, or a dict/list (e.g. an email or JSON record).
    state: str | dict[str, Any] | list[Any]
    # {name: {"type": "choice"|"score"|"noul", "instructions": str, "criteria": ...}}
    questions: dict[str, dict[str, Any]]
    # Optional: "english", "multilingual" or "typed-decisions". Omit to auto-route.
    model: str | None = None


# Plain `def` so FastAPI runs the (blocking, CPU-bound) inference in its threadpool.
@router.post("/predict")
def predict(payload: PredictIn):
    try:
        return get_router().predict(payload.state, payload.questions, model=payload.model)
    except ValueError as e:
        # Laya raises ValueError for malformed questions, with a readable message.
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/test")
def test():
    """Run a canned support-ticket example to check Laya works end to end."""
    return {
        "request": {"state": SAMPLE_STATE, "questions": SAMPLE_QUESTIONS},
        "response": get_router().predict(SAMPLE_STATE, SAMPLE_QUESTIONS),
    }
