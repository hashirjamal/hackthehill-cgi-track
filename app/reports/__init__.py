from fastapi import APIRouter

from app.reports import accounts, backlog, cases, classification, root_cause, worklist

router = APIRouter(prefix="/reports", tags=["reports"])
router.include_router(worklist.router)
router.include_router(backlog.router)
router.include_router(root_cause.router)
router.include_router(accounts.router)
router.include_router(cases.router)
router.include_router(classification.router)
