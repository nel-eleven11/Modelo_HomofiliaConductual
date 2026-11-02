"""Small paired experiment exercises result persistence without API calls."""

import csv
import json
from pathlib import Path

import networkx as nx  # type: ignore[import-untyped]
from scripts.plot_mechanisms import render_network_snapshots, render_trajectories

from homophily_sim.analysis.mechanisms import summarize_saved_run
from homophily_sim.analysis.statistics import METRICS, describe
from homophily_sim.data.topics import load_topics
from homophily_sim.experiments.rebuild_mechanisms import rebuild_experiment
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
    assert stored.opportunities
    assert all(
        item.relationship_before == next(
            record.relationship_before for record in stored.interactions
            if record.conversation_id == item.conversation_id
            and record.receiver_id == item.candidate_id
            and record.sender_id == item.initiator_id
        )
        for item in stored.opportunities
    )
    run_path = destination / inventory[0]["run_directory"]
    rebuilt = summarize_saved_run(
        run_path, load_topics(Path(__file__).resolve().parents[2] / "data/topics/topics_v1.yaml")
    )
    assert len(rebuilt.interaction) == 2
    assert len(rebuilt.graphs) == 2
    for row, evolution in zip(rebuilt.interaction, rebuilt.relationships, strict=True):
        assert row["exposure_count"] >= row["response_count"]
        assert row["directed_evaluation_count"] == (
            row["exposure_count"] + row["response_count"]
        )
        assert 0 <= row["participation_rate"] <= 1
        assert 0 <= row["unique_active_student_count"] <= 20
        assert sum(evolution[key] for key in (
            "strengthened_evaluation_updates", "weakened_evaluation_updates",
            "unchanged_evaluation_updates",
        )) == row["directed_evaluation_count"]
    assert any(row["exposure_count"] > row["response_count"] for row in rebuilt.interaction)
    graph = nx.read_graphml(
        run_path / "network_snapshots/evaluation/semester_01.graphml"
    )
    assert graph.number_of_nodes() == 20
    historical_metrics = json.loads(
        (run_path / "metrics_by_semester.json").read_text(encoding="utf-8")
    )
    assert nx.density(graph) == historical_metrics[0]["density"]
    assert (run_path / "network_snapshots/active_response/final.graphml").exists()
    original_summary = (destination / "scenario_summary.csv").read_bytes()
    assert rebuild_experiment(destination) == destination
    assert (destination / "scenario_summary.csv").read_bytes() == original_summary
    figures = render_trajectories(
        destination / "scenario_summary.csv", tmp_path / "figures"
    )
    assert figures and all(path.is_file() for path in figures)
    networks = render_network_snapshots(
        destination, tmp_path / "figures", semesters=(1,)
    )
    assert len(networks) == 3
    assert run_scenarios(output_root=destination, seeds=(1, 2), smoke=True) == destination
