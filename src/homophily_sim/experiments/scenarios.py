"""Validated paired homophily scenarios sharing all other parameters."""

from pathlib import Path

from homophily_sim.config import SimulationConfig, load_config

SCENARIO_LEVELS = {
    "homophily_low": 0.20,
    "homophily_medium": 0.50,
    "homophily_high": 0.80,
}


def load_homophily_scenarios(root: Path, *, smoke: bool = False) -> dict[str, SimulationConfig]:
    """Load the three published overlays and reject other parameter changes."""
    configs = {
        name: load_config(root / "configs" / f"{name}.yaml")
        for name in SCENARIO_LEVELS
    }
    reference = configs["homophily_medium"].model_dump(exclude={"scenario", "h"})
    for name, config in configs.items():
        if config.scenario != name or config.h != SCENARIO_LEVELS[name]:
            raise ValueError(f"unexpected homophily scenario: {name}")
        if config.model_dump(exclude={"scenario", "h"}) != reference:
            raise ValueError("homophily scenarios differ outside h and scenario")
    if smoke:
        configs = {
            name: SimulationConfig.model_validate(
                {**config.model_dump(), "population_size": 20, "years": 1,
                 "semesters": 2, "weeks_per_semester": 1}
            )
            for name, config in configs.items()
        }
    return configs
