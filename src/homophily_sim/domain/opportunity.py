"""One seeded opportunity to respond, recorded before message evaluation."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class ParticipationOpportunity(BaseModel):
    run_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    seed: int = Field(ge=0)
    semester: int = Field(ge=1)
    week: int = Field(ge=1)
    day: int = Field(ge=1)
    course_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    topic_id: str = Field(min_length=1)
    initiator_id: int = Field(ge=0)
    candidate_id: int = Field(ge=0)
    candidate_interest: float = Field(ge=0, le=1)
    similarity: float = Field(ge=0, le=1)
    relationship_before: float = Field(ge=0, le=1)
    participation_probability: float = Field(ge=0, le=1)
    participated: bool

    @model_validator(mode="after")
    def distinct_agents(self) -> Self:
        if self.initiator_id == self.candidate_id:
            raise ValueError("an initiator cannot be their own response candidate")
        return self
