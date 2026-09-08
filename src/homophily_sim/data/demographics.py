"""Explicit operational demographic profiles for synthetic sampling."""

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DemographicProfile(BaseModel):
    """Input probabilities; names do not imply empirical calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    age_probabilities: dict[int, float]
    female_probability: float = Field(ge=0, le=1)
    guatemala_department_probability: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def valid_age_distribution(self) -> Self:
        if not self.age_probabilities or any(age < 0 for age in self.age_probabilities):
            raise ValueError("age probabilities need nonnegative ages")
        if any(value < 0 for value in self.age_probabilities.values()):
            raise ValueError("age probabilities cannot be negative")
        if abs(sum(self.age_probabilities.values()) - 1) > 1e-9:
            raise ValueError("age probabilities must sum to 1")
        return self


def load_demographic_profile(path: str | Path, name: str) -> DemographicProfile:
    """Load one named versioned profile from YAML."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), dict):
        raise ValueError("demographic profile file must contain profiles")
    if name not in raw["profiles"]:
        raise ValueError(f"unknown demographic profile: {name}")
    return DemographicProfile.model_validate(
        {"name": name, "version": raw["version"], **raw["profiles"][name]}
    )
