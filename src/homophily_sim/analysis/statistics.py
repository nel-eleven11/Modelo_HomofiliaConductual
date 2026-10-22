"""Descriptive summaries and paired t intervals for experimental runs."""

from collections import Counter
from collections.abc import Mapping, Sequence
from math import sqrt
from statistics import fmean, median, stdev
from typing import Any

from scipy.stats import t  # type: ignore[import-untyped]

METRICS = (
    "sex_assortativity",
    "origin_assortativity",
    "mean_edge_similarity",
    "modularity",
    "mean_relationship_weight",
    "community_count",
    "largest_community_size",
    "isolate_count",
    "reciprocity",
    "density",
)


def describe(values: Sequence[float | int | None]) -> dict[str, float | int | None]:
    """Report a 95% two-sided Student-t interval for available observations."""
    observed = [float(value) for value in values if value is not None]
    if not observed:
        return {"n": 0, "mean": None, "std": None, "median": None,
                "ci_low": None, "ci_high": None}
    mean = fmean(observed)
    if len(observed) == 1:
        return {"n": 1, "mean": mean, "std": None, "median": mean,
                "ci_low": None, "ci_high": None}
    std = stdev(observed)
    margin = float(t.ppf(0.975, len(observed) - 1)) * std / sqrt(len(observed))
    return {
        "n": len(observed), "mean": mean, "std": std, "median": median(observed),
        "ci_low": mean - margin, "ci_high": mean + margin,
    }


def aggregate_scenarios(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate each numeric network metric by scenario and semester."""
    groups: dict[tuple[str, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["scenario"]), int(row["semester"])), []).append(row)
    return [
        {"scenario": scenario, "semester": semester, "metric": metric,
         **describe([row[metric] for row in group])}
        for (scenario, semester), group in sorted(groups.items())
        for metric in METRICS
    ]


def paired_final_differences(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Compare final-semester metrics using only matching seeds."""
    if not rows:
        return []
    final_semester = max(int(row["semester"]) for row in rows)
    indexed = {
        (str(row["scenario"]), int(row["seed"])): row
        for row in rows if int(row["semester"]) == final_semester
    }
    pairs = (("homophily_medium", "homophily_low"),
             ("homophily_high", "homophily_medium"),
             ("homophily_high", "homophily_low"))
    results = []
    for higher, lower in pairs:
        upper_seeds = {seed for scenario, seed in indexed if scenario == higher}
        lower_seeds = {seed for scenario, seed in indexed if scenario == lower}
        if upper_seeds != lower_seeds:
            raise ValueError("scenario comparison requires identical seed sets")
        for metric in METRICS:
            differences = [
                float(indexed[higher, seed][metric]) - float(indexed[lower, seed][metric])
                for seed in sorted(upper_seeds)
                if indexed[higher, seed][metric] is not None
                and indexed[lower, seed][metric] is not None
            ]
            results.append(
                {"higher": higher, "lower": lower, "semester": final_semester,
                 "metric": metric, **describe(differences)}
            )
    return results


def community_size_distribution(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Count communities of each size across runs for each semester."""
    counts: Counter[tuple[str, int, int]] = Counter()
    for row in rows:
        for size in row["community_sizes"]:
            counts[str(row["scenario"]), int(row["semester"]), int(size)] += 1
    return [
        {"scenario": scenario, "semester": semester, "size": size, "communities": count}
        for (scenario, semester, size), count in sorted(counts.items())
    ]
