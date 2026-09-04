"""Tabular record of one directed evaluation of a message."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator


class InteractionRecord(BaseModel):
    run_id: str = Field(min_length=1)
    seed: int
    semester: int = Field(ge=1, le=10)
    week: int = Field(ge=1, le=20)
    day: int = Field(ge=1, le=5)
    course_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    topic_id: str = Field(min_length=1)
    sender_id: int = Field(ge=0)
    receiver_id: int = Field(ge=0)
    sender_text: str
    receiver_interest: float = Field(ge=0, le=1)
    similarity: float = Field(ge=0, le=1)
    relationship_before: float = Field(ge=0, le=1)
    participation_probability: float | None = Field(default=None, ge=0, le=1)
    agreement: float = Field(ge=0, le=1)
    sentiment_valence: float = Field(ge=0, le=1)
    interaction_score: float = Field(ge=0, le=1)
    relationship_after: float = Field(ge=0, le=1)
    timestamp_simulation: datetime

    @model_validator(mode="after")
    def distinct_agents(self) -> Self:
        if self.sender_id == self.receiver_id:
            raise ValueError("a message cannot be evaluated by its sender")
        return self
