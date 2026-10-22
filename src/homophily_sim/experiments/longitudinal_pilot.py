"""Reproducible ten-semester pilot with frozen inputs and saved snapshots."""

import argparse
import json
import resource
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.io.metadata import current_git_commit, make_run_metadata
from homophily_sim.io.results import save_run
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel
from homophily_sim.visualization.metric_plots import (
    plot_metric_trends,
    plot_relationship_distribution,
)
from homophily_sim.visualization.network_plots import plot_network


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _frozen_files(root: Path) -> dict[str, str]:
    """Hash every input resource and the active mock language definition."""
    paths = (
        "configs/base.yaml",
        "configs/homophily_medium.yaml",
        "data/topics/topics_v1.yaml",
        "data/demographics/profiles_v1.yaml",
        "src/homophily_sim/llm/mock.py",
        "src/homophily_sim/llm/prompts.py",
        "src/homophily_sim/nlp/mock.py",
    )
    return {name: sha256((root / name).read_bytes()).hexdigest() for name in paths}


def _state_fingerprints(model: HomophilyModel) -> dict[str, str]:
    """Hash outcomes independent of a run's identifier and wall-clock time."""
    agents_hash = sha256()
    for agent in model.students:
        agents_hash.update(
            json.dumps(agent.model_dump(mode="json"), sort_keys=True).encode("utf-8") + b"\n"
        )
    interactions_hash = sha256()
    prefix = f"{model.run_id}:"
    for record in model.interactions:
        row = record.model_dump(mode="json")
        if not row["conversation_id"].startswith(prefix):
            raise ValueError("conversation ID does not belong to the run")
        row.pop("run_id")
        row["conversation_id"] = row["conversation_id"][len(prefix):]
        interactions_hash.update(json.dumps(row, sort_keys=True).encode("utf-8") + b"\n")
    snapshots_hash = sha256()
    for snapshot in [*model.snapshots, *model.year_snapshots, model.final_snapshot]:
        if snapshot is None:
            raise ValueError("longitudinal run has no final snapshot")
        snapshots_hash.update(f"{snapshot.kind}:{snapshot.semester}\n".encode())
        for source, target, weight in sorted(
            (int(source), int(target), float(data["weight"]))
            for source, target, data in snapshot.graph.edges(data=True)
        ):
            snapshots_hash.update(f"{source},{target},{weight:.17g}\n".encode())
    return {
        "agents_sha256": agents_hash.hexdigest(),
        "interactions_sha256": interactions_hash.hexdigest(),
        "snapshots_sha256": snapshots_hash.hexdigest(),
    }


def _save_snapshots(model: HomophilyModel, destination: Path) -> list[dict[str, Any]]:
    directory = destination / "snapshots"
    directory.mkdir()
    index: list[dict[str, Any]] = []
    snapshots = [*model.snapshots, *model.year_snapshots, model.final_snapshot]
    for snapshot in snapshots:
        if snapshot is None:
            raise ValueError("longitudinal run has no final snapshot")
        filename = f"{snapshot.kind}_semester_{snapshot.semester:02d}.parquet"
        edges = [
            {"observer_id": int(source), "other_id": int(target), "weight": float(data["weight"])}
            for source, target, data in sorted(snapshot.graph.edges(data=True))
        ]
        pd.DataFrame(edges, columns=["observer_id", "other_id", "weight"]).to_parquet(
            directory / filename, index=False
        )
        index.append(
            {"kind": snapshot.kind, "semester": snapshot.semester,
             "nodes": snapshot.graph.number_of_nodes(), "edges": len(edges),
             "file": f"snapshots/{filename}"}
        )
    _write_json(destination / "snapshot_index.json", index)
    return index


def run_longitudinal_pilot(
    *, output_root: str | Path = "outputs", run_id: str = "pilot-3-longitudinal-seed-42",
    seed: int = 42, config: SimulationConfig | None = None,
) -> Path:
    """Complete a seeded cohort, persist all boundaries, then replay it."""
    root = Path(__file__).resolve().parents[3]
    selected = config or load_config(root / "configs/homophily_medium.yaml")
    if selected.h != 0.5:
        raise ValueError("phase 17 pilot requires h = 0.50")
    frozen = _frozen_files(root)
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", selected.demographic_profile
    )
    started = datetime.now(UTC)
    start_clock = perf_counter()
    model = HomophilyModel(
        selected, bank, profile, run_seed=seed, run_id=run_id,
        language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    model.run_to_completion()
    run_seconds = perf_counter() - start_clock
    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    if (
        len(model.students) != selected.population_size
        or len(model.snapshots) != selected.semesters
        or len(model.year_snapshots) != selected.years
        or len(model.metric_history) != selected.semesters
        or model.final_snapshot is None
        or model.current_semester != selected.semesters
        or model.current_week != selected.weeks_per_semester
    ):
        raise RuntimeError("longitudinal run did not complete all expected boundaries")
    if _frozen_files(root) != frozen:
        raise RuntimeError("pilot inputs changed during the simulation")
    fingerprints = _state_fingerprints(model)
    metadata = make_run_metadata(
        selected, run_id=run_id, seed=seed, prompt_version="mock-v1",
        topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name="mock", sentiment_model_name="mock",
        start_time=started, end_time=datetime.now(UTC),
    )
    destination = save_run(
        output_root, config=selected, agents=model.students,
        interactions=model.interactions, metadata=metadata,
    )
    series = model.metric_history
    _write_json(
        destination / "metrics_by_semester.json",
        [{"semester": semester, **asdict(metrics)} for semester, metrics in series],
    )
    snapshot_index = _save_snapshots(model, destination)
    plot_network(model.final_snapshot, destination / "network_final.png", layout_seed=seed)
    plot_metric_trends(series, destination)
    plot_relationship_distribution(series[-1][1], destination / "relationship_distribution.png")

    replay_start = perf_counter()
    replay = HomophilyModel(
        selected, bank, profile, run_seed=seed, run_id=f"{run_id}-replay",
        language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    replay.run_to_completion()
    replay_seconds = perf_counter() - replay_start
    if _frozen_files(root) != frozen:
        raise RuntimeError("pilot inputs changed during the replay")
    replay_fingerprints = _state_fingerprints(replay)
    reproducible = replay_fingerprints == fingerprints
    summary = {
        "run_id": run_id, "seed": seed, "scenario": selected.scenario, "h": selected.h,
        "population_size": selected.population_size,
        "completed_semesters": len(model.snapshots),
        "completed_years": len(model.year_snapshots),
        "completed_weeks": selected.semesters * selected.weeks_per_semester,
        "conversation_count": model.conversation_count,
        "interaction_count": len(model.interactions),
        "simulation_seconds": run_seconds, "replay_seconds": replay_seconds,
        "peak_rss_mb_before_replay": peak_rss_mb,
        "snapshot_count": len(snapshot_index),
        "final_directed_edges": model.final_snapshot.graph.number_of_edges(),
        "final_density": series[-1][1].density,
        "reproducible": reproducible,
        "fingerprints": fingerprints,
        "replay_fingerprints": replay_fingerprints,
        "frozen_inputs": {
            "git_commit": current_git_commit(),
            "files_sha256": frozen,
            "prompt_version": "mock-v1",
            "topic_bank_version": bank.topic_bank_version,
            "demographic_calibration_version": profile.version,
            "model_name": "mock",
            "sentiment_model_name": "mock",
        },
    }
    _write_json(destination / "longitudinal_summary.json", summary)
    _write_json(destination / "frozen_inputs.json", summary["frozen_inputs"])
    if not reproducible:
        raise RuntimeError("same-seed replay produced different state fingerprints")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--run-id", default="pilot-3-longitudinal-seed-42")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(run_longitudinal_pilot(output_root=args.output, run_id=args.run_id, seed=args.seed))


if __name__ == "__main__":
    main()
