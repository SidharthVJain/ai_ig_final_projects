"""GitHub repository discovery and activity endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_github_service
from backend.app.schemas.github import (
    CommitSummary,
    ReleaseSummary,
    RepositoryActivityResponse,
    RepositoryDetail,
    RepositorySearchResponse,
    TrendingRepositoriesResponse,
)
from backend.app.services.github_service import GitHubService

router = APIRouter(prefix="/api/v1/repositories", tags=["Repositories"])
ServiceDep = Annotated[GitHubService, Depends(get_github_service)]


@router.get("/trending", response_model=TrendingRepositoriesResponse)
async def trending_repositories(
    service: ServiceDep,
    language: str | None = Query(default=None, max_length=40),
    period: Literal["day", "week", "month"] = "week",
    limit: int = Query(default=10, ge=1, le=30),
) -> TrendingRepositoriesResponse:
    """Return popular repositories pushed within the requested time window."""
    return await service.get_trending_repositories(
        language=language, period=period, limit=limit
    )


@router.get("/search", response_model=RepositorySearchResponse)
async def search_repositories(
    service: ServiceDep,
    query: str = Query(min_length=1, max_length=200),
    language: str | None = Query(default=None, max_length=40),
    sort: Literal["stars", "updated"] = "stars",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=10, ge=1, le=30),
) -> RepositorySearchResponse:
    """Search public repositories by keywords and optional language."""
    return await service.search_repositories(
        query=query, language=language, sort=sort, order=order, limit=limit
    )


@router.get("/{owner}/{repo}", response_model=RepositoryDetail)
async def repository_details(
    owner: str,
    repo: str,
    service: ServiceDep,
) -> RepositoryDetail:
    """Return metadata for one public GitHub repository."""
    return await service.get_repository(owner, repo)


@router.get("/{owner}/{repo}/releases", response_model=list[ReleaseSummary])
async def repository_releases(
    owner: str,
    repo: str,
    service: ServiceDep,
    limit: int = Query(default=10, ge=1, le=30),
) -> list[ReleaseSummary]:
    """Return the latest published releases for a repository."""
    return await service.get_releases(owner, repo, limit)


@router.get("/{owner}/{repo}/commits", response_model=list[CommitSummary])
async def repository_commits(
    owner: str,
    repo: str,
    service: ServiceDep,
    limit: int = Query(default=10, ge=1, le=30),
) -> list[CommitSummary]:
    """Return recent commits for the repository's default branch."""
    return await service.get_commits(owner, repo, limit)


@router.get("/{owner}/{repo}/activity", response_model=RepositoryActivityResponse)
async def repository_activity(
    owner: str,
    repo: str,
    service: ServiceDep,
    limit: int = Query(default=5, ge=1, le=20),
) -> RepositoryActivityResponse:
    """Return the latest releases and commits in one request."""
    return await service.get_repository_activity(owner, repo, limit)
