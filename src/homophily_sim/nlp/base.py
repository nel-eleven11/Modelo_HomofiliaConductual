"""Contract and validated three-class sentiment result."""

from typing import Protocol, Self

from pydantic import BaseModel, Field, model_validator


class SentimentResult(BaseModel):
    """Normalized negative, neutral and positive class probabilities."""

    p_negative: float = Field(ge=0, le=1)
    p_neutral: float = Field(ge=0, le=1)
    p_positive: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def probabilities_sum_to_one(self) -> Self:
        if abs(self.p_negative + self.p_neutral + self.p_positive - 1) > 1e-6:
            raise ValueError("sentiment probabilities must sum to 1")
        return self


class SentimentAnalyzer(Protocol):
    def analyze(self, text: str) -> SentimentResult:
        """Analyze text independently of its language generator."""
        ...
