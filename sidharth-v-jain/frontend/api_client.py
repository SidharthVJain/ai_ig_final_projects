"""HTTP client used by Streamlit to communicate with FastAPI."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


def get_backend_url() -> str:
    """Return the backend URL from environment variables or Streamlit secrets."""
    backend_url = os.getenv("BACKEND_URL", "").strip()
    if not backend_url:
        try:
            import streamlit as st

            backend_url = str(st.secrets.get("BACKEND_URL", "")).strip()
        except Exception:
            # Local development may not have a Streamlit secrets file.
            backend_url = ""
    return (backend_url or "http://127.0.0.1:8000").rstrip("/")


def _get(path: str, params: dict[str, Any] | None = None, timeout: float = 30.0) -> Any:
    response = httpx.get(
        f"{get_backend_url()}{path}", params=params, timeout=timeout
    )
    response.raise_for_status()
    return response.json()


def get_health(timeout: float = 5.0) -> dict[str, Any]:
    """Call the FastAPI health endpoint."""
    return _get("/health", timeout=timeout)


def search_repositories(
    *, query: str, language: str | None, sort: str, limit: int
) -> dict[str, Any]:
    """Search repositories through the DevDigest backend."""
    return _get(
        "/api/v1/repositories/search",
        {"query": query, "language": language or None, "sort": sort, "limit": limit},
    )


def get_trending_repositories(
    *, language: str | None, period: str, limit: int
) -> dict[str, Any]:
    """Fetch popular repositories pushed within a recent time window."""
    return _get(
        "/api/v1/repositories/trending",
        {"language": language or None, "period": period, "limit": limit},
    )


def get_repository(owner: str, repo: str) -> dict[str, Any]:
    """Fetch repository metadata."""
    return _get(f"/api/v1/repositories/{owner}/{repo}")


def get_repository_activity(owner: str, repo: str, limit: int = 5) -> dict[str, Any]:
    """Fetch releases and recent commits for a repository."""
    return _get(
        f"/api/v1/repositories/{owner}/{repo}/activity", {"limit": limit}
    )


def list_research_documents() -> dict[str, Any]:
    """List PDFs currently indexed in the backend's persistent Chroma collection."""
    return _get("/api/v1/research/documents", timeout=20.0)


def upload_research_document(filename: str, content: bytes) -> dict[str, Any]:
    """Upload a PDF as multipart form data and wait for indexing to complete."""
    response = httpx.post(
        f"{get_backend_url()}/api/v1/research/documents/upload",
        files={"file": (filename, content, "application/pdf")},
        timeout=180.0,
    )
    response.raise_for_status()
    return response.json()


def ask_research_question(
    *, question: str, document_ids: list[str] | None = None, top_k: int = 5
) -> dict[str, Any]:
    """Ask a question against all or selected indexed research PDFs."""
    response = httpx.post(
        f"{get_backend_url()}/api/v1/research/ask",
        json={"question": question, "document_ids": document_ids or None, "top_k": top_k},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def generate_briefing(*, topic: str, repositories: list[str], research_notes: str = "", document_ids: list[str] | None = None) -> dict[str, Any]:
    """Generate a technical briefing through the CrewAI backend workflow."""
    response = httpx.post(
        f"{get_backend_url()}/api/v1/briefings/generate",
        json={"topic": topic, "repositories": repositories, "research_notes": research_notes, "document_ids": document_ids or []},
        timeout=300.0,
    )
    response.raise_for_status()
    return response.json()
