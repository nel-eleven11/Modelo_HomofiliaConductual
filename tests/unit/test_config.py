"""Configuration loading and invariants."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from homophily_sim.config import SimulationConfig, load_config

CONFIGS = Path(__file__).resolve().parents[2] / "configs"


def test_scenarios_change_only_h_and_name() -> None:
    base = load_config(CONFIGS / "base.yaml")
    for name, h in (("low", 0.2), ("medium", 0.5), ("high", 0.8)):
        scenario = load_config(CONFIGS / f"homophily_{name}.yaml")
        assert scenario.h == h
        assert scenario.model_dump(exclude={"h", "scenario"}) == base.model_dump(
            exclude={"h", "scenario"}
        )


def test_invalid_weights_and_sections_rejected() -> None:
    config = load_config(CONFIGS / "base.yaml").model_dump()
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate({**config, "w_interest": 0.8})
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate({**config, "sections_per_course": 81})
