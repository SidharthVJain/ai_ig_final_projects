"""FastAPI application entry point for DevDigest."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.briefings import router as briefings_router
from backend.app.api.routes.repositories import router as repositories_router
from backend.app.api.routes.research import router as research_router
from backend.app.core.config import get_settings
from backend.app.services.github_service import GitHubAPIError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for DevDigest: open-source intelligence, research-paper Q&A, "
        "and AI-generated technical briefings."
    ),
)

app.include_router(health_router)
app.include_router(repositories_router)
app.include_router(research_router)
app.include_router(briefings_router)


@app.exception_handler(GitHubAPIError)
async def github_api_error_handler(_request: Request, exc: GitHubAPIError) -> JSONResponse:
    """Translate GitHub upstream errors into safe, actionable API responses."""
    if exc.status_code == 404:
        status_code = 404
    elif exc.status_code in (403, 429):
        status_code = 503
    elif exc.status_code == 504:
        status_code = 504
    else:
        status_code = 502

    detail: dict[str, str | None] = {
        "message": exc.message,
        "upstream": "GitHub",
        "upstream_status": str(exc.status_code),
        "rate_limit_remaining": exc.rate_limit_remaining,
        "rate_limit_reset": exc.rate_limit_reset,
        "retry_after": exc.retry_after,
    }
    headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


@app.get("/", tags=["Root"], summary="API welcome message")
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to DevDigest API",
        "docs": "/docs",
        "health": "/health",
        "repositories": "/api/v1/repositories/trending",
        "research": "/api/v1/research/documents",
        "briefings": "/api/v1/briefings/generate",
    }
