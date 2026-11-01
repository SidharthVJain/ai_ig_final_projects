"""API endpoint for multi-agent technical briefings."""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import get_github_service, get_rag_service
from backend.app.schemas.briefing import BriefingRequest, BriefingResponse
from backend.app.services.briefing_service import BriefingService, BriefingServiceError
from backend.app.services.github_service import GitHubService
from backend.app.services.rag_service import RAGService, RAGServiceError

router = APIRouter(prefix="/api/v1/briefings", tags=["AI Briefings"])

# Keep the model input compact enough for Groq's 8K TPM free-tier limit.
MAX_SOURCE_CONTEXT_CHARS = 7_500
MAX_RESEARCH_NOTES_CHARS = 4_000


def _compact(value: Any, max_chars: int) -> str:
    """Convert an upstream value to short, single-line text."""
    text = " ".join(str(value or "").split())
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text or "Not provided"


def _format_repository_context(
    full_name: str, details: dict[str, Any], activity: dict[str, Any]
) -> str:
    """Retain decision-useful GitHub fields and discard bulky API response fields."""
    lines = [
        f"REPOSITORY: {full_name}",
        f"Description: {_compact(details.get('description'), 240)}",
        f"Language: {_compact(details.get('language'), 60)}",
        (
            f"Stars: {details.get('stargazers_count', 'unknown')} | "
            f"Forks: {details.get('forks_count', 'unknown')} | "
            f"Updated: {details.get('updated_at', 'unknown')}"
        ),
        f"URL: {details.get('html_url') or f'https://github.com/{full_name}'}",
        "Recent releases:",
    ]

    releases = activity.get("releases") or []
    if releases:
        for release in releases[:2]:
            if not isinstance(release, dict):
                continue
            tag = _compact(release.get("tag_name"), 60)
            name = _compact(release.get("name"), 100)
            published = _compact(release.get("published_at"), 32)
            body = _compact(release.get("body"), 260)
            url = _compact(release.get("html_url"), 180)
            lines.append(f"- {tag} | {name} | {published} | {body} | {url}")
    else:
        lines.append("- No releases found.")

    lines.append("Recent commits:")
    commits = activity.get("commits") or []
    if commits:
        for commit in commits[:3]:
            if not isinstance(commit, dict):
                continue
            raw_message = str(commit.get("message") or "").splitlines()[0]
            message = _compact(raw_message, 150)
            date = _compact(commit.get("committed_at") or commit.get("author_date"), 32)
            url = _compact(commit.get("html_url"), 180)
            lines.append(f"- {date} | {message} | {url}")
    else:
        lines.append("- No recent commits found.")

    return "\n".join(lines)


def get_briefing_service() -> BriefingService:
    return BriefingService()


BriefingDep = Annotated[BriefingService, Depends(get_briefing_service)]
GitHubDep = Annotated[GitHubService, Depends(get_github_service)]
RAGDep = Annotated[RAGService, Depends(get_rag_service)]


@router.post("/generate", response_model=BriefingResponse)
async def generate_briefing(
    payload: BriefingRequest, service: BriefingDep, github: GitHubDep, rag: RAGDep
):
    """Gather compact source context and execute the sequential CrewAI workflow."""

    async def repository_context(full_name: str) -> str:
        owner, repo = full_name.split("/", maxsplit=1)
        details, activity = await asyncio.gather(
            github.get_repository(owner, repo),
            # Fetch only a few entries; the formatter below keeps selected fields only.
            github.get_repository_activity(owner, repo, limit=3),
        )
        return _format_repository_context(full_name, details, activity)

    try:
        contexts = await asyncio.gather(
            *(repository_context(name) for name in payload.repositories)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not gather GitHub context: {exc}"
        ) from exc

    source_parts = list(contexts)
    if payload.document_ids:
        try:
            paper_context = await asyncio.to_thread(
                rag.retrieve_context,
                question=payload.topic,
                document_ids=payload.document_ids,
                top_k=3,
            )
            if paper_context:
                # The retriever returns ~1K-character chunks; cap the combined paper excerpt.
                source_parts.append(
                    "RESEARCH PAPER EXCERPTS:\n" + paper_context[:3_200]
                )
        except RAGServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    source_context = "\n\n---\n\n".join(source_parts)
    source_context = source_context[:MAX_SOURCE_CONTEXT_CHARS]
    research_notes = (payload.research_notes or "")[:MAX_RESEARCH_NOTES_CHARS]

    try:
        # CrewAI kickoff is synchronous; run it off the event loop.
        return await asyncio.to_thread(
            service.generate,
            topic=payload.topic,
            source_context=source_context,
            research_notes=research_notes,
        )
    except BriefingServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
