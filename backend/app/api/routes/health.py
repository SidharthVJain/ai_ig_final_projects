"""Health-check route."""

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Check API health")
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
    )
