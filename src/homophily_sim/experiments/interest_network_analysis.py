"""Rebuild interest heatmaps and strong-tie trajectories from saved runs."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]

from homophily_sim.analysis.interest_network import interest_mixing, strong_tie_metrics
from homophily_sim.analysis.statistics import describe
from homophily_sim.config import SimulationConfig
from homophily_sim.data.topics import TopicBank
from homophily_sim.domain.opportunity import ParticipationOpportunity
from homophily_sim.io.mechanisms import read_csv, write_csv
from homophily_sim.visualization.interest_network_plots import (
    plot_interest_heatmap,
    plot_strong_network,
    plot_strong_trajectories,
)

STRONG_METRICS = (
    "strong_directed_edge_count",
    "strong_directed_density",
    "strong_share_of_observed_edges",
    "mutual_strong_pair_count",
    "mutual_strong_pair_density",
    "new_strong_directed_edge_count",
    "lost_strong_directed_edge_count",
    "strong_directed_persistence_rate",
)
SCENARIO_PAIRS = (
    ("homophily_medium", "homophily_low"),
    ("homophily_high", "homophily_medium"),
    ("homophily_high", "homophily_low"),
)


def _run_data(run_dir: Path) -> tuple[dict[int, set[str]], list[ParticipationOpportunity]]:
    agents = pd.read_parquet(run_dir / "agents.parquet", columns=["id", "interests"])
    interests = {
        int(row.id): set(json.loads(row.interests)) for row in agents.itertuples(index=False)
    }
    opportunities = pd.read_parquet(run_dir / "participation_attempts.parquet")
    return interests, [
        ParticipationOpportunity.model_validate(row)
        for row in opportunities.to_dict("records")
    ]


def _scenario_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["scenario"], row["semester"]].append(row)
    return [
        {"scenario": scenario, "semester": semester, "metric": metric,
         **describe([row[metric] for row in group])}
        for (scenario, semester), group in sorted(groups.items())
        for metric in STRONG_METRICS
    ]


def _overlap_summaries(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, bool], list[float | None]] = defaultdict(list)
    by_run: dict[tuple[str, int, str], dict[bool, float | None]] = defaultdict(dict)
    for row in rows:
        shared = bool(row["shared_exact_interest"])
        rate = row["response_rate_given_exposure"]
        groups[row["scenario"], shared].append(rate)
        by_run[row["scenario"], row["seed"], row["run_id"]][shared] = rate
    summary = [
        {"scenario": scenario, "shared_exact_interest": shared,
         "metric": "response_rate_given_exposure", **describe(values)}
        for (scenario, shared), values in sorted(groups.items())
    ]
    effects = [
        {"scenario": scenario, "seed": seed, "run_id": run_id,
         "shared_interest_response_rate_gap": (
             rates[True] - rates[False]
             if rates.get(True) is not None and rates.get(False) is not None else None
         )}
        for (scenario, seed, run_id), rates in sorted(by_run.items())
    ]
    effect_groups: dict[str, list[float | None]] = defaultdict(list)
    for row in effects:
        effect_groups[row["scenario"]].append(row["shared_interest_response_rate_gap"])
    effect_summary = [
        {"scenario": scenario, "metric": "shared_interest_response_rate_gap",
         **describe(values)}
        for scenario, values in sorted(effect_groups.items())
    ]
    return summary, effects, effect_summary


def _paired_final(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    final = max(row["semester"] for row in rows)
    indexed = {
        (row["scenario"], row["seed"]): row
        for row in rows if row["semester"] == final
    }
    comparisons = []
    for higher, lower in SCENARIO_PAIRS:
        seeds = {seed for scenario, seed in indexed if scenario == higher}
        if seeds != {seed for scenario, seed in indexed if scenario == lower}:
            raise ValueError("paired comparison requires identical seeds across scenarios")
        for metric in STRONG_METRICS:
            differences = [
                indexed[higher, seed][metric] - indexed[lower, seed][metric]
                for seed in sorted(seeds)
                if indexed[higher, seed][metric] is not None
                and indexed[lower, seed][metric] is not None
            ]
            comparisons.append({
                "higher": higher, "lower": lower, "semester": final,
                "metric": metric, **describe(differences),
            })
    return comparisons


def analyze_experiment(
    experiment: Path, *, output: Path | None = None, image_seed: int | None = None,
) -> Path:
    """Produce one heatmap per run and ten network images per selected scenario."""
    experiment = Path(experiment)
    destination = output or experiment / "interest_network_analysis"
    inventory = read_csv(experiment / "run_inventory.csv")
    if not inventory:
        raise ValueError("run_inventory.csv contains no saved runs")
    available: dict[str, set[int]] = defaultdict(set)
    for item in inventory:
        available[item["scenario"]].add(int(item["seed"]))
    common_seeds = set.intersection(*available.values())
    if not common_seeds:
        raise ValueError("network images require a seed shared by all scenarios")
    selected_seed = image_seed if image_seed is not None else min(common_seeds)
    if selected_seed not in common_seeds:
        raise ValueError("the requested image seed is not present in every scenario")
    destination.mkdir(parents=True, exist_ok=True)
    matrix_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    strong_rows: list[dict[str, Any]] = []
    snapshots: dict[tuple[str, int], list[nx.DiGraph]] = {}
    thresholds: set[float] = set()
    for item in inventory:
        scenario = item["scenario"]
        seed = int(item["seed"])
        run_id = item["run_id"]
        run_dir = experiment / item["run_directory"]
        config = SimulationConfig.model_validate_json(
            (run_dir / "config.json").read_text(encoding="utf-8")
        )
        bank = TopicBank.model_validate_json(
            (run_dir / "topic_bank.json").read_text(encoding="utf-8")
        )
        interests, opportunities = _run_data(run_dir)
        matrix, comparison = interest_mixing(interests, opportunities, bank)
        identity = {"scenario": scenario, "h": config.h, "seed": seed, "run_id": run_id}
        matrix_rows.extend({**identity, **row} for row in matrix)
        overlap_rows.extend({**identity, **row} for row in comparison)
        plot_interest_heatmap(
            matrix, tuple(sorted(bank.taxonomy)),
            destination / "heatmaps" / f"{run_id}.png",
            title=f"Intereses y respuestas · {scenario} · semilla {seed}",
        )
        previous: set[tuple[int, int]] = set()
        selected = []
        for semester in range(1, config.semesters + 1):
            snapshot = (run_dir / "network_snapshots" / "evaluation" /
                        f"semester_{semester:02d}.graphml")
            graph = nx.read_graphml(snapshot)
            metrics, previous = strong_tie_metrics(
                graph, config.strong_relationship_threshold, previous
            )
            strong_rows.append({
                **identity, "semester": semester,
                "strong_relationship_threshold": config.strong_relationship_threshold,
                **metrics,
            })
            if seed == selected_seed:
                selected.append(graph)
        if selected:
            snapshots[scenario, seed] = selected
        thresholds.add(config.strong_relationship_threshold)
    for scenario in sorted(available):
        graphs = snapshots[scenario, selected_seed]
        final = graphs[-1]
        threshold = next(row["strong_relationship_threshold"] for row in strong_rows
                         if row["scenario"] == scenario and row["seed"] == selected_seed)
        final_strong = nx.Graph()
        final_strong.add_nodes_from(final.nodes)
        final_strong.add_edges_from(
            (a, b) for a, b, data in final.edges(data=True)
            if float(data["weight"]) >= threshold
        )
        positions = nx.spring_layout(final_strong, seed=selected_seed, weight=None)
        for semester, graph in enumerate(graphs, start=1):
            plot_strong_network(
                graph, positions, threshold,
                destination / "networks" / scenario / f"semester_{semester:02d}.png",
                scenario=scenario, semester=semester,
            )
    summary = _scenario_summary(strong_rows)
    overlap_summary, overlap_effects, overlap_effect_summary = _overlap_summaries(
        overlap_rows
    )
    write_csv(destination / "interest_matrix.csv", matrix_rows)
    write_csv(destination / "interest_overlap.csv", overlap_rows)
    write_csv(destination / "interest_overlap_scenario_summary.csv", overlap_summary)
    write_csv(destination / "interest_overlap_effect_by_run.csv", overlap_effects)
    write_csv(destination / "interest_overlap_effect_scenario_summary.csv",
              overlap_effect_summary)
    write_csv(destination / "strong_ties_by_semester.csv", strong_rows)
    write_csv(destination / "strong_ties_scenario_summary.csv", summary)
    write_csv(destination / "strong_ties_paired_final_differences.csv", _paired_final(strong_rows))
    plot_strong_trajectories(summary, destination / "strong_ties_trajectory.png")
    (destination / "analysis_manifest.json").write_text(
        json.dumps({
            "source_experiment": str(experiment), "run_count": len(inventory),
            "image_seed": selected_seed, "network_image_count": sum(
                len(graphs) for (scenario, seed), graphs in snapshots.items()
                if seed == selected_seed
            ),
            "heatmap_count": len(inventory),
            "strong_relationship_thresholds": sorted(thresholds),
            "interest_overlap_definition": "at least one identical interest label",
            "matrix_weighting": "each exposure contributes total weight one across category cells",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path,
                        help="experiment directory containing run_inventory.csv")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--image-seed", type=int)
    args = parser.parse_args()
    print(analyze_experiment(args.experiment, output=args.output, image_seed=args.image_seed))


if __name__ == "__main__":
    main()
