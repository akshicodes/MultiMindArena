from fastapi import APIRouter

from .session import router as session_router
from .analytics import router as analytics_router
from .topics import router as topics_router

router = APIRouter()
router.include_router(session_router)
router.include_router(analytics_router)
router.include_router(topics_router)
