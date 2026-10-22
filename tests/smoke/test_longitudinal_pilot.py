"""A short cohort proves longitudinal snapshot persistence and replay."""

import json
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.experiments.longitudinal_pilot import run_longitudinal_pilot
from homophily_sim.io.results import load_run


def test_longitudinal_pilot_saves_boundaries_and_replays(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    base = load_config(root / "configs/homophily_medium.yaml")
    small = SimulationConfig.model_validate(
        {**base.model_dump(), "population_size": 20, "years": 1,
         "semesters": 2, "weeks_per_semester": 1}
    )
    destination = run_longitudinal_pilot(
        output_root=tmp_path, run_id="longitudinal-smoke", seed=42, config=small
    )
    summary = json.loads((destination / "longitudinal_summary.json").read_text())
    index = json.loads((destination / "snapshot_index.json").read_text())
    stored = load_run(destination)

    assert summary["reproducible"] is True
    assert summary["completed_semesters"] == 2
    assert summary["completed_years"] == 1
    assert summary["snapshot_count"] == 4
    assert summary["fingerprints"] == summary["replay_fingerprints"]
    assert [(item["kind"], item["semester"]) for item in index] == [
        ("semester_end", 1), ("semester_end", 2), ("year_end", 2), ("final", 2)
    ]
    assert all(item["nodes"] == 20 for item in index)
    assert len(pd.read_parquet(destination / index[-1]["file"])) == index[-1]["edges"]
    assert len(stored.agents) == 20
    assert len(stored.interactions) == summary["interaction_count"]
    assert stored.metadata.prompt_version == "mock-v1"
