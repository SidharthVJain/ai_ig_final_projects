"""Pydantic response models for service health checks."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = Field(description="Name of the service")
    version: str = Field(description="Application version")
    environment: str = Field(description="Current application environment")
    timestamp: datetime = Field(description="UTC time when the health check ran")
