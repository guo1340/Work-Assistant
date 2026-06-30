from fastapi import APIRouter

from app.core.config import get_settings
from app.db.connection import database_is_ready

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "database": "ready" if database_is_ready(settings.database_path) else "unavailable",
        "service": "devflow-engine",
    }
