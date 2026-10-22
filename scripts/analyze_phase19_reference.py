"""Compare edge similarity with one fixed baseline metric across all variants."""

import argparse
import csv
import json
from pathlib import Path
from statistics import fmean
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from homophily_sim.analysis.statistics import describe
from homophily_sim.config import load_config
from homophily_sim.social.similarity import age_similarity, interest_jaccard


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _pair_similarities(agents: pd.DataFrame, base_config: Any) -> dict[tuple[int, int], float]:
    states = {
        int(row.id): (int(row.age), str(row.sex), str(row.origin), set(json.loads(row.interests)))
        for row in agents.itertuples(index=False)
    }
    return {
        (left, right): (
            base_config.w_interest * interest_jaccard(states[left][3], states[right][3])
            + base_config.w_age * age_similarity(
                states[left][0], states[right][0], base_config.max_age_difference
            )
            + base_config.w_sex * float(states[left][1] == states[right][1])
            + base_config.w_origin * float(states[left][2] == states[right][2])
        )
        for left in states
        for right in states
        if left != right
    }


def analyze(experiment: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    base = load_config(root / "configs/homophily_medium.yaml")
    with (experiment / "run_inventory.csv").open(encoding="utf-8", newline="") as stream:
        inventory = list(csv.DictReader(stream))
    if not inventory:
        raise ValueError("sensitivity inventory is empty")
    rows: list[dict[str, Any]] = []
    for item in inventory:
        directory = experiment / item["run_directory"]
        agents = pd.read_parquet(
            directory / "agents.parquet", columns=["id", "age", "sex", "origin", "interests"]
        )
        similarity = _pair_similarities(agents, base)
        interactions = pd.read_parquet(
            directory / "interactions.parquet",
            columns=["semester", "receiver_id", "sender_id"],
        )
        edges: set[tuple[int, int]] = set()
        for semester, group in interactions.groupby("semester", sort=True):
            edges.update(
                (int(receiver), int(sender))
                for receiver, sender in group[["receiver_id", "sender_id"]].itertuples(
                    index=False, name=None
                )
            )
            rows.append(
                {
                    "h": float(item["h"]), "parameter": item["parameter"],
                    "level": item["level"], "value": item["value"],
                    "variant": item["variant"], "seed": int(item["seed"]),
                    "semester": int(semester), "edge_count": len(edges),
                    "fixed_mean_edge_similarity": fmean(similarity[edge] for edge in edges),
                }
            )
    groups: dict[tuple[float, str, str, str, int], list[float]] = {}
    indexed = {(r["h"], r["seed"], r["semester"], r["variant"]): r for r in rows}
    deltas: dict[tuple[float, str, str, str, int], list[float]] = {}
    for row in rows:
        key = (row["h"], row["parameter"], row["level"], row["value"], row["semester"])
        groups.setdefault(key, []).append(row["fixed_mean_edge_similarity"])
        if row["variant"] != "baseline":
            reference = indexed[row["h"], row["seed"], row["semester"], "baseline"]
            deltas.setdefault(key, []).append(
                row["fixed_mean_edge_similarity"] - reference["fixed_mean_edge_similarity"]
            )
    summary = [
        {"h": h, "parameter": parameter, "level": level, "value": value,
         "semester": semester, **describe(values)}
        for (h, parameter, level, value, semester), values in sorted(groups.items())
    ]
    paired = [
        {"h": h, "parameter": parameter, "level": level, "value": value,
         "semester": semester, **describe(values)}
        for (h, parameter, level, value, semester), values in sorted(deltas.items())
    ]
    _write_csv(experiment / "fixed_similarity_by_run.csv", rows)
    _write_csv(experiment / "fixed_similarity_summary.csv", summary)
    _write_csv(experiment / "fixed_similarity_paired_deltas.csv", paired)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=Path("outputs/phase-19-sensitivity"))
    args = parser.parse_args()
    analyze(args.experiment)


if __name__ == "__main__":
    main()
