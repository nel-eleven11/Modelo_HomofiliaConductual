"""Provenance recorded with every simulation run."""

import platform
import subprocess
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from homophily_sim.config import SimulationConfig


class RunMetadata(BaseModel):
    """Identifiers, software versions and data versions for one run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    seed: int
    scenario: str
    git_commit: str
    software_versions: dict[str, str]
    prompt_version: str
    topic_bank_version: str
    demographic_calibration_version: str
    model_name: str
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def chronological(self) -> Self:
        if self.end_time < self.start_time:
            raise ValueError("end_time must not precede start_time")
        return self


def current_git_commit() -> str:
    """Return the current revision, or a clear marker outside a Git checkout."""
    repository = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def software_versions() -> dict[str, str]:
    """Record versions used to create and read output tables."""
    versions = {"python": platform.python_version()}
    for package in (
        "homophily-sim", "numpy", "pandas", "pydantic", "pyarrow",
        "networkx", "matplotlib",
    ):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def make_run_metadata(
    config: SimulationConfig,
    *,
    run_id: str,
    seed: int,
    prompt_version: str,
    topic_bank_version: str,
    demographic_calibration_version: str,
    model_name: str,
    start_time: datetime,
    end_time: datetime,
) -> RunMetadata:
    """Build metadata from explicit run inputs and the local environment."""
    return RunMetadata(
        run_id=run_id,
        seed=seed,
        scenario=config.scenario,
        git_commit=current_git_commit(),
        software_versions=software_versions(),
        prompt_version=prompt_version,
        topic_bank_version=topic_bank_version,
        demographic_calibration_version=demographic_calibration_version,
        model_name=model_name,
        start_time=start_time,
        end_time=end_time,
    )
