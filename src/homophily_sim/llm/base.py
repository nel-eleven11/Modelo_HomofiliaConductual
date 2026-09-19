"""Minimal language-provider contract shared by mocks and future API clients."""

from typing import Literal, Protocol

from pydantic import BaseModel, Field


class UtteranceRequest(BaseModel):
    """Only conversational context needed to write one short Spanish message."""

    agent_id: int = Field(ge=0)
    topic_id: str = Field(min_length=1)
    topic_prompt: str = Field(min_length=1)
    orientation: float = Field(ge=-1, le=1)
    relevant_interests: tuple[str, ...]
    extraversion: float = Field(ge=0, le=10)
    previous_message: str | None = None
    max_words: int = Field(gt=0)
    language: Literal["es"] = "es"


class UtteranceResult(BaseModel):
    """One generated message without any social-model decisions."""

    text: str = Field(min_length=1)


class LanguageModelProvider(Protocol):
    def generate_utterance(self, request: UtteranceRequest) -> UtteranceResult:
        """Generate wording without calculating relationships or probabilities."""
        ...
