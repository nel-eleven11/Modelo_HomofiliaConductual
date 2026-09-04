"""Conversation topic metadata."""

from enum import StrEnum

from pydantic import BaseModel, Field


class PolarizationLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Topic(BaseModel):
    topic_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    subcategory: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    polarization_level: PolarizationLevel
