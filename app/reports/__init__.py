from fastapi import APIRouter

from app.reports import backlog, root_cause, worklist

router = APIRouter(prefix="/reports", tags=["reports"])
router.include_router(worklist.router)
router.include_router(backlog.router)
router.include_router(root_cause.router)
