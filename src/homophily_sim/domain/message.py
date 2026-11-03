"""One simulated message and its auditable expressed-tone draw."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class MessageRecord(BaseModel):
    run_id: str
    seed: int
    scenario: str
    semester: int
    week: int
    day: int
    course_id: str
    section_id: str
    conversation_id: str
    message_id: str
    role: Literal["initial", "response"]
    sender_id: int
    topic_id: str
    sender_topic_interest: float = Field(ge=0, le=1)
    sender_topic_orientation: float = Field(ge=-1, le=1)
    sentiment_negative_probability: float = Field(ge=0, le=1)
    sentiment_neutral_probability: float = Field(ge=0, le=1)
    sentiment_positive_probability: float = Field(ge=0, le=1)
    sampled_tone: Literal["negative", "neutral", "positive"]
    sampled_valence: float = Field(ge=0, le=1)
    sentiment_rule_version: str
    rng_stream: str
    message_text: str

    @model_validator(mode="after")
    def valid_tone(self) -> Self:
        total = (self.sentiment_negative_probability + self.sentiment_neutral_probability
                 + self.sentiment_positive_probability)
        if abs(total - 1) > 1e-9:
            raise ValueError("tone sampling probabilities must sum to one")
        expected = {"negative": 0.0, "neutral": 0.5, "positive": 1.0}[self.sampled_tone]
        if self.sampled_valence != expected:
            raise ValueError("sampled valence must match tone")
        return self
