"""Small paired experiment exercises result persistence without API calls."""

import csv
import json
from pathlib import Path

from homophily_sim.analysis.statistics import METRICS, describe
from homophily_sim.experiments.runner import run_scenarios
from homophily_sim.io.results import load_run


def test_describe_uses_available_values_and_sample_uncertainty() -> None:
    result = describe([1.0, 2.0, 3.0, None])
    assert result["n"] == 3
    assert result["mean"] == 2.0
    assert result["std"] == 1.0
    assert result["median"] == 2.0
    assert result["ci_low"] < 2.0 < result["ci_high"]
    assert describe([None, None])["ci_low"] is None
    assert describe([1.0])["std"] is None


def test_six_short_runs_are_paired_and_resumable(tmp_path: Path) -> None:
    destination = run_scenarios(output_root=tmp_path / "experiment", seeds=(1, 2), smoke=True)
    summary = json.loads((destination / "experiment_summary.json").read_text())
    with (destination / "run_metrics.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    with (destination / "run_inventory.csv").open(newline="", encoding="utf-8") as source:
        inventory = list(csv.DictReader(source))

    assert summary["run_count"] == 6
    assert summary["semester_rows"] == 12
    assert len(rows) == 12
    assert len(inventory) == 6
    assert len(summary["scenario_summary"]) == 3 * 2 * len(METRICS)
    assert len(summary["paired_final_differences"]) == 3 * len(METRICS)
    assert {int(row["seed"]) for row in inventory} == {1, 2}
    assert all(
        {int(row["seed"]) for row in inventory if row["scenario"] == scenario} == {1, 2}
        for scenario in ("homophily_low", "homophily_medium", "homophily_high")
    )
    stored = load_run(destination / inventory[0]["run_directory"])
    assert stored.config.population_size == 20
    assert stored.metadata.seed == int(inventory[0]["seed"])
    assert stored.interactions
    assert run_scenarios(output_root=destination, seeds=(1, 2), smoke=True) == destination
