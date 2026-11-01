"""Request and response models for AI-generated technical briefings."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BriefingRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=240)
    repositories: list[str] = Field(default_factory=list, max_length=5)
    research_notes: str = Field(default="", max_length=4000)
    document_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("repositories")
    @classmethod
    def validate_repositories(cls, values: list[str]) -> list[str]:
        import re

        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        invalid = [value for value in cleaned if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value)]
        if invalid:
            raise ValueError("Repositories must use owner/repository format.")
        return cleaned


class BriefingResponse(BaseModel):
    briefing_id: str
    topic: str
    status: Literal["completed"] = "completed"
    briefing: str
    model: str
    agents: list[str]
    tools_available: list[str]
    generated_at: datetime
