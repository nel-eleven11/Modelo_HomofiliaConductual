"""Typed, versioned simulation parameters loaded from YAML."""

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SimulationConfig(BaseModel):
    """All operational parameters shared by the main homophily scenarios."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: str
    population_size: int = Field(gt=0)
    years: int = Field(gt=0)
    semesters: int = Field(gt=0)
    weeks_per_semester: int = Field(gt=0)
    days_per_week: int = Field(gt=0)
    courses_per_semester: int = Field(gt=0)
    sessions_per_course_per_week: int = Field(gt=0)
    sections_per_course: int = Field(gt=0)
    exposed_fraction: float = Field(ge=0, le=1)
    h: float = Field(ge=0, le=1)
    w_interest: float = Field(ge=0, le=1)
    w_age: float = Field(ge=0, le=1)
    w_sex: float = Field(ge=0, le=1)
    w_origin: float = Field(ge=0, le=1)
    beta_0: float
    beta_E: float
    beta_I: float
    beta_R: float
    lambda_R: float
    lambda_S: float
    alpha_relationship: float = Field(ge=0, le=1)
    gamma_section: float = Field(ge=0, le=1)
    w_agreement: float = Field(ge=0, le=1)
    w_sentiment: float = Field(ge=0, le=1)
    epsilon_start: float = Field(gt=0, le=1)
    initial_relationship: float = Field(ge=0, le=1)
    max_age_difference: int = Field(gt=0)
    demographic_profile: str = Field(min_length=1)
    interest_count_probabilities: dict[int, float]
    extraversion_mean: float = Field(ge=0, le=10)
    extraversion_std: float = Field(ge=0)
    utterance_max_words: int = Field(gt=0, le=100)

    @model_validator(mode="after")
    def validate_structure(self) -> Self:
        """Reject inconsistent weights and an impossible cohort layout."""
        if abs(self.w_interest + self.w_age + self.w_sex + self.w_origin - 1) > 1e-9:
            raise ValueError("similarity weights must sum to 1")
        if abs(self.w_agreement + self.w_sentiment - 1) > 1e-9:
            raise ValueError("evaluation weights must sum to 1")
        if self.sections_per_course > self.population_size:
            raise ValueError("sections_per_course cannot exceed population_size")
        if self.semesters != 2 * self.years:
            raise ValueError("semesters must equal twice years")
        if set(self.interest_count_probabilities) != set(range(1, 6)):
            raise ValueError("interest count probabilities must cover 1 through 5")
        if any(value < 0 for value in self.interest_count_probabilities.values()):
            raise ValueError("interest count probabilities cannot be negative")
        if abs(sum(self.interest_count_probabilities.values()) - 1) > 1e-9:
            raise ValueError("interest count probabilities must sum to 1")
        if self.sessions_per_course_per_week > self.days_per_week:
            raise ValueError("a course cannot meet more than once per day")
        return self


def load_config(path: str | Path) -> SimulationConfig:
    """Load a base file or a one-level scenario overlay beside it."""
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("configuration must be a YAML mapping")
    parent_name = raw.pop("extends", None)
    if parent_name is not None:
        if not isinstance(parent_name, str) or Path(parent_name).name != parent_name:
            raise ValueError("extends must name a YAML file in the same directory")
        parent = yaml.safe_load((config_path.parent / parent_name).read_text(encoding="utf-8"))
        if not isinstance(parent, dict) or "extends" in parent:
            raise ValueError("base configuration must be a mapping without extends")
        raw = {**parent, **raw}
    return SimulationConfig.model_validate(raw)
