"""Persist derived mechanism tables and scalar GraphML snapshots."""

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from homophily_sim.analysis.mechanisms import MechanismTables, summarize_saved_run
from homophily_sim.data.topics import TopicBank

MECHANISM_METRICS = (
    "conversation_count",
    "participation_rate",
    "unique_initiator_count",
    "unique_responder_count",
    "unique_active_student_count",
    "directed_evaluation_count",
    "exposure_count",
    "response_count",
    "mean_exposed_pair_similarity",
    "mean_responding_pair_similarity",
    "mean_exposed_previous_relationship",
    "mean_responding_previous_relationship",
    "repeated_unordered_exposure_rate",
    "repeated_unordered_response_rate",
    "top_10_percent_exposure_pair_share",
    "top_10_percent_response_pair_share",
    "mean_agreement",
    "median_agreement",
    "std_agreement",
    "mean_sentiment_valence",
    "median_sentiment_valence",
    "std_sentiment_valence",
    "mean_interaction_score",
    "gini_active_responses",
    "top_10_percent_student_response_share",
    "evaluation_activity_persistence_rate",
    "response_activity_persistence_rate",
    "strong_relationship_persistence_rate",
    "between_community_evaluation_rate",
    "between_community_response_rate",
    "strengthened_evaluation_updates",
    "weakened_evaluation_updates",
    "unchanged_evaluation_updates",
    "mean_relationship_delta",
    "mean_absolute_relationship_delta",
    "observed_evaluation_relationship_count",
    "strong_relationship_count",
    "new_evaluation_relationship_count",
    "mean_observed_relationship_weight",
    "active_response_edge_count",
    "active_response_density",
)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write a deterministic CSV; an empty table is represented by an empty file."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def export_mechanisms(path: Path, bank: TopicBank) -> MechanismTables:
    """Rebuild every derived artifact from saved Parquet files."""
    if not (path / "participation_attempts.parquet").exists():
        raise ValueError("participation_attempts.parquet is required for mechanism exports")
    bank_path = path / "topic_bank.json"
    if bank_path.exists():
        if bank_path.read_text(encoding="utf-8") != bank.model_dump_json(indent=2) + "\n":
            raise ValueError("saved topic bank differs from requested bank")
    else:
        bank_path.write_text(bank.model_dump_json(indent=2) + "\n", encoding="utf-8")
    tables = summarize_saved_run(path, bank)
    for name, rows in (
        ("interaction_summary.csv", tables.interaction),
        ("relationship_evolution.csv", tables.relationships),
        ("topic_summary.csv", tables.topics),
        ("student_activity.csv", tables.students),
    ):
        write_csv(path / name, rows)
    snapshot_root = path / "network_snapshots"
    for kind in ("evaluation", "active_response"):
        (snapshot_root / kind).mkdir(parents=True, exist_ok=True)
    for semester, (evaluation, response) in enumerate(tables.graphs, start=1):
        filename = f"semester_{semester:02d}.graphml"
        nx.write_graphml(evaluation, snapshot_root / "evaluation" / filename)
        nx.write_graphml(response, snapshot_root / "active_response" / filename)
    if tables.graphs:
        evaluation, response = tables.graphs[-1]
        nx.write_graphml(evaluation, snapshot_root / "evaluation" / "final.graphml")
        nx.write_graphml(response, snapshot_root / "active_response" / "final.graphml")
    return tables


def mechanism_row(
    interaction: Mapping[str, Any], relationships: Mapping[str, Any]
) -> dict[str, Any]:
    """Select the named scalar metrics for scenario and sensitivity tables."""
    return {
        key: interaction[key] if key in interaction else relationships[key]
        for key in MECHANISM_METRICS
    }
