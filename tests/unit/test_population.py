"""Reproducibility and cohort bounds."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from homophily_sim.config import load_config
from homophily_sim.data.demographics import DemographicProfile, load_demographic_profile
from homophily_sim.data.population import generate_population
from homophily_sim.data.topics import load_topics

ROOT = Path(__file__).resolve().parents[2]


def test_population_is_reproducible_and_bounded() -> None:
    config = load_config(ROOT / "configs/base.yaml")
    bank = load_topics(ROOT / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        ROOT / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )
    first = generate_population(config, bank, profile, seed=42)
    again = generate_population(config, bank, profile, seed=42)
    assert [agent.model_dump() for agent in first] == [agent.model_dump() for agent in again]
    assert len(first) == 80
    assert len({agent.id for agent in first}) == 80
    assert all(1 <= len(agent.interests) <= 5 and 0 <= agent.extraversion <= 10 for agent in first)
    assert all(len(agent.topic_orientations) == len(bank.topics) for agent in first)

    different = generate_population(config, bank, profile, seed=43)
    assert [agent.model_dump() for agent in different] != [agent.model_dump() for agent in first]


def test_invalid_demographic_probabilities_are_rejected() -> None:
    profile = load_demographic_profile(ROOT / "data/demographics/profiles_v1.yaml", "custom")
    with pytest.raises(ValidationError, match="sum to 1"):
        DemographicProfile.model_validate({**profile.model_dump(), "age_probabilities": {18: 0.7}})
    with pytest.raises(ValidationError):
        DemographicProfile.model_validate({**profile.model_dump(), "female_probability": 1.2})
