"""Recalculate mechanism exports and aggregates from saved run files only."""

import argparse
import json
from pathlib import Path
from typing import Any

from homophily_sim.analysis.statistics import (
    aggregate_scenarios,
    community_size_distribution,
    paired_final_differences,
)
from homophily_sim.data.topics import TopicBank, load_topics
from homophily_sim.experiments.runner import _report, _write_csv, _write_json
from homophily_sim.experiments.sensitivity import _group_summaries, _paired_deltas
from homophily_sim.io.mechanisms import export_mechanisms, mechanism_row, read_csv, write_csv

TABLES = (
    "interaction_summary.csv", "relationship_evolution.csv",
    "topic_summary.csv", "student_activity.csv",
)


def rebuild_experiment(destination: Path) -> Path:
    """Derive every new output from persisted Parquet and original metric rows."""
    root = Path(__file__).resolve().parents[3]
    fallback_bank = load_topics(root / "data/topics/topics_v1.yaml")
    sensitivity = (destination / "sensitivity_plan.json").exists()
    manifest = "sensitivity_run.json" if sensitivity else "experiment_run.json"
    run_dirs = sorted((destination / "runs").iterdir())
    if not run_dirs:
        raise ValueError("no saved runs found")
    rows: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    all_tables: dict[str, list[dict[str, str]]] = {name: [] for name in TABLES}
    for run_dir in run_dirs:
        if not run_dir.is_dir():
            continue
        manifest_path = run_dir / manifest
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        bank_path = run_dir / "topic_bank.json"
        bank = (TopicBank.model_validate_json(bank_path.read_text(encoding="utf-8"))
                if bank_path.exists() else fallback_bank)
        tables = export_mechanisms(run_dir, bank)
        enriched = [
            {**row, **mechanism_row(
                tables.interaction[int(row["semester"]) - 1],
                tables.relationships[int(row["semester"]) - 1],
            )}
            for row in saved["rows"]
        ]
        saved["rows"] = enriched
        _write_json(manifest_path, saved)
        rows.extend(enriched)
        inventory.append(saved["inventory"])
        for name in TABLES:
            all_tables[name].extend(read_csv(run_dir / name))
    _write_csv(destination / "run_inventory.csv", inventory)
    _write_csv(destination / "run_metrics.csv", rows)
    for name in TABLES:
        write_csv(destination / name, all_tables[name])
    if sensitivity:
        summary = _group_summaries(rows)
        paired = _paired_deltas(rows)
        _write_csv(destination / "sensitivity_summary.csv", summary)
        _write_csv(destination / "paired_deltas.csv", paired)
        old = json.loads((destination / "sensitivity_summary.json").read_text(encoding="utf-8"))
        old.update({"summary": summary, "paired_deltas": paired})
        _write_json(destination / "sensitivity_summary.json", old)
    else:
        summary = aggregate_scenarios(rows)
        paired = paired_final_differences(rows)
        sizes = community_size_distribution(rows)
        _write_csv(destination / "scenario_summary.csv", summary)
        _write_csv(destination / "paired_final_differences.csv", paired)
        _write_csv(destination / "community_size_distribution.csv", sizes)
        old = json.loads((destination / "experiment_summary.json").read_text(encoding="utf-8"))
        old.update({"scenario_summary": summary, "paired_final_differences": paired,
                    "community_size_distribution": sizes})
        _write_json(destination / "experiment_summary.json", old)
        (destination / "report.md").write_text(
            _report(old["seeds"], summary, paired, max(int(row["semester"]) for row in rows)),
            encoding="utf-8",
        )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    print(rebuild_experiment(args.experiment))


if __name__ == "__main__":
    main()
