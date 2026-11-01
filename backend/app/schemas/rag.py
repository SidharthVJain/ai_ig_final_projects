"""Pydantic request and response models for the research assistant."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    sha256: str
    page_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    total_count: int
    items: list[DocumentSummary]


class DocumentUploadResponse(BaseModel):
    status: Literal["indexed"]
    document: DocumentSummary
    message: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[str] | None = Field(default=None, max_length=50)
    top_k: int | None = Field(default=None, ge=1, le=10)


class SourceReference(BaseModel):
    citation_id: str
    document_id: str
    filename: str
    page_number: int = Field(ge=1)
    excerpt: str


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    retrieved_count: int = Field(ge=0)
    sources: list[SourceReference]
