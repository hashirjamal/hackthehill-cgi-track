from fastapi import APIRouter

from app.reports import worklist

router = APIRouter(prefix="/reports", tags=["reports"])
router.include_router(worklist.router)
