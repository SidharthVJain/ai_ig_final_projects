"""Validated request/response models for GitHub repository data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class GitHubModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RepositoryOwner(GitHubModel):
    login: str
    avatar_url: HttpUrl | None = None
    html_url: HttpUrl | None = None


class LicenseSummary(GitHubModel):
    key: str | None = None
    name: str | None = None
    spdx_id: str | None = None


class RepositorySummary(GitHubModel):
    id: int
    name: str
    full_name: str
    description: str | None = None
    html_url: HttpUrl
    owner: RepositoryOwner | None = None
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    watchers_count: int = 0
    topics: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    pushed_at: datetime | None = None
    visibility: str | None = None
    default_branch: str | None = None


class RepositoryDetail(RepositorySummary):
    license: LicenseSummary | None = None
    size: int | None = None
    subscribers_count: int | None = None


class RepositorySearchResponse(GitHubModel):
    query: str
    total_count: int
    incomplete_results: bool = False
    sort: Literal["stars", "updated"]
    order: Literal["asc", "desc"]
    items: list[RepositorySummary]


class TrendingRepositoriesResponse(GitHubModel):
    period: Literal["day", "week", "month"]
    pushed_since: str
    total_count: int
    items: list[RepositorySummary]


class ReleaseSummary(GitHubModel):
    id: int
    tag_name: str
    name: str | None = None
    body: str | None = None
    html_url: HttpUrl
    draft: bool = False
    prerelease: bool = False
    created_at: datetime | None = None
    published_at: datetime | None = None
    target_commitish: str | None = None


class CommitSummary(GitHubModel):
    sha: str
    html_url: HttpUrl
    message: str
    author_name: str | None = None
    author_date: datetime | None = None
    committer_name: str | None = None
    committed_at: datetime | None = None


class RepositoryActivityResponse(GitHubModel):
    full_name: str
    releases: list[ReleaseSummary]
    commits: list[CommitSummary]
