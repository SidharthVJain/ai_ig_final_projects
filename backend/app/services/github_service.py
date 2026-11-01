"""Asynchronous client for the public GitHub REST API."""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx

from backend.app.core.config import get_settings


class GitHubAPIError(Exception):
    """An upstream GitHub API error with useful rate-limit context."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        rate_limit_remaining: str | None = None,
        rate_limit_reset: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset = rate_limit_reset
        self.retry_after = retry_after


class GitHubService:
    """Thin async wrapper around GitHub repository/search endpoints."""

    API_VERSION = "2026-03-10"

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.token = token if token is not None else settings.github_token
        self.base_url = (base_url or settings.github_api_base_url).rstrip("/")
        self.timeout = timeout or settings.github_timeout_seconds
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
            "User-Agent": "DevDigest/0.2.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.get(path, params=params)
                if response.is_error:
                    try:
                        payload = response.json()
                    except ValueError:
                        payload = {}
                    message = payload.get("message", "GitHub API request failed")
                    raise GitHubAPIError(
                        str(message),
                        status_code=response.status_code,
                        rate_limit_remaining=response.headers.get("x-ratelimit-remaining"),
                        rate_limit_reset=response.headers.get("x-ratelimit-reset"),
                        retry_after=response.headers.get("retry-after"),
                    )
                return response.json()
        except GitHubAPIError:
            raise
        except httpx.TimeoutException as exc:
            raise GitHubAPIError("GitHub API request timed out", status_code=504) from exc
        except httpx.RequestError as exc:
            raise GitHubAPIError(
                "Could not connect to GitHub. Check the backend's network connection.",
                status_code=502,
            ) from exc

    @staticmethod
    def _repo_qualifiers(query: str, language: str | None = None) -> str:
        parts = [query.strip(), "is:public", "fork:false"]
        if language and language.strip():
            parts.append(f"language:{language.strip()}")
        return " ".join(part for part in parts if part)

    async def search_repositories(
        self,
        *,
        query: str,
        language: str | None = None,
        sort: Literal["stars", "updated"] = "stars",
        order: Literal["asc", "desc"] = "desc",
        limit: int = 10,
    ) -> dict[str, Any]:
        github_query = self._repo_qualifiers(query, language)
        payload = await self._get(
            "/search/repositories",
            params={"q": github_query, "sort": sort, "order": order, "per_page": limit},
        )
        return {
            "query": github_query,
            "total_count": payload.get("total_count", 0),
            "incomplete_results": payload.get("incomplete_results", False),
            "sort": sort,
            "order": order,
            "items": payload.get("items", []),
        }

    async def get_trending_repositories(
        self,
        *,
        language: str | None = None,
        period: Literal["day", "week", "month"] = "week",
        limit: int = 10,
    ) -> dict[str, Any]:
        days = {"day": 1, "week": 7, "month": 30}[period]
        pushed_since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        query = f"pushed:>={pushed_since} is:public fork:false"
        if language and language.strip():
            query += f" language:{language.strip()}"
        payload = await self._get(
            "/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
        )
        return {
            "period": period,
            "pushed_since": pushed_since,
            "total_count": payload.get("total_count", 0),
            "items": payload.get("items", []),
        }

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        return await self._get(f"/repos/{owner}/{repo}")

    async def get_releases(self, owner: str, repo: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self._get(
            f"/repos/{owner}/{repo}/releases", params={"per_page": limit, "page": 1}
        )

    async def get_commits(self, owner: str, repo: str, limit: int = 10) -> list[dict[str, Any]]:
        raw_commits = await self._get(
            f"/repos/{owner}/{repo}/commits", params={"per_page": limit, "page": 1}
        )
        commit_items = []
        for item in raw_commits:
            commit_data = item.get("commit") or {}
            author = commit_data.get("author") or {}
            committer = commit_data.get("committer") or {}
            commit_items.append(
                {
                    "sha": item.get("sha", ""),
                    "html_url": item.get("html_url"),
                    "message": commit_data.get("message", ""),
                    "author_name": author.get("name"),
                    "author_date": author.get("date"),
                    "committer_name": committer.get("name"),
                    "committed_at": committer.get("date"),
                }
            )
        return commit_items

    async def get_repository_activity(
        self, owner: str, repo: str, limit: int = 5
    ) -> dict[str, Any]:
        import asyncio

        releases, commits = await asyncio.gather(
            self.get_releases(owner, repo, limit),
            self.get_commits(owner, repo, limit),
        )
        return {
            "full_name": f"{owner}/{repo}",
            "releases": releases,
            "commits": commits,
        }
