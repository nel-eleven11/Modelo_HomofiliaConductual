"""Run paired 30-seed homophily scenarios and save complete comparisons."""

import argparse
import csv
import gc
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

from homophily_sim.analysis.statistics import (
    METRICS,
    aggregate_scenarios,
    community_size_distribution,
    paired_final_differences,
)
from homophily_sim.config import SimulationConfig
from homophily_sim.data.demographics import DemographicProfile, load_demographic_profile
from homophily_sim.data.topics import TopicBank, load_topics
from homophily_sim.experiments.scenarios import load_homophily_scenarios
from homophily_sim.io.metadata import current_git_commit, make_run_metadata
from homophily_sim.io.results import save_run
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.network.metrics import NetworkMetrics
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot export empty table")
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value
                             for key, value in row.items()})


def _frozen_files(root: Path) -> dict[str, str]:
    names = (
        "configs/base.yaml", "configs/homophily_low.yaml",
        "configs/homophily_medium.yaml", "configs/homophily_high.yaml",
        "data/topics/topics_v1.yaml", "data/demographics/profiles_v1.yaml",
        "src/homophily_sim/llm/mock.py", "src/homophily_sim/llm/prompts.py",
        "src/homophily_sim/nlp/mock.py",
    )
    source_names = tuple(
        path.relative_to(root).as_posix()
        for path in sorted((root / "src/homophily_sim").rglob("*.py"))
    )
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in (*names, *source_names)
    }


def _metric_row(
    scenario: str, h: float, seed: int, semester: int, metrics: NetworkMetrics,
) -> dict[str, Any]:
    sizes = list(metrics.community_sizes)
    weights = metrics.relationship_weights
    return {
        "scenario": scenario, "h": h, "seed": seed, "semester": semester,
        "sex_assortativity": metrics.sex_assortativity,
        "origin_assortativity": metrics.origin_assortativity,
        "mean_edge_similarity": metrics.mean_edge_similarity,
        "modularity": metrics.modularity,
        "mean_relationship_weight": fmean(weights) if weights else None,
        "community_count": len(sizes),
        "largest_community_size": max(sizes) if sizes else 0,
        "community_sizes": sizes,
        "isolate_count": len(metrics.isolates),
        "reciprocity": metrics.reciprocity,
        "density": metrics.density,
    }


def _one_run(
    *, config: SimulationConfig, bank: TopicBank, profile: DemographicProfile, run_root: Path,
    scenario: str, seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_id = f"phase18-{scenario}-seed-{seed:03d}"
    started = datetime.now(UTC)
    clock = perf_counter()
    model = HomophilyModel(
        config, bank, profile, run_seed=seed, run_id=run_id,
        language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    model.run_to_completion()
    seconds = perf_counter() - clock
    if (
        len(model.snapshots) != config.semesters
        or len(model.year_snapshots) != config.years
        or model.final_snapshot is None
        or len(model.students) != config.population_size
    ):
        raise RuntimeError(f"incomplete scenario run: {run_id}")
    rows = [
        _metric_row(scenario, config.h, seed, semester, metrics)
        for semester, metrics in model.metric_history
    ]
    metadata = make_run_metadata(
        config, run_id=run_id, seed=seed, prompt_version="mock-v1",
        topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name="mock", sentiment_model_name="mock",
        start_time=started, end_time=datetime.now(UTC),
    )
    destination = save_run(
        run_root, config=config, agents=model.students,
        interactions=model.interactions, metadata=metadata,
    )
    _write_json(
        destination / "metrics_by_semester.json",
        [{"semester": semester, **asdict(metrics)}
         for semester, metrics in model.metric_history],
    )
    inventory = {
        "scenario": scenario, "h": config.h, "seed": seed, "run_id": run_id,
        "completed_semesters": len(model.snapshots),
        "conversation_count": model.conversation_count,
        "interaction_count": len(model.interactions),
        "simulation_seconds": seconds,
        "run_directory": f"runs/{run_id}",
    }
    _write_json(destination / "experiment_run.json", {"inventory": inventory, "rows": rows})
    return rows, inventory


def _report(
    seeds: Sequence[int], summary: Sequence[Mapping[str, Any]],
    paired: Sequence[Mapping[str, Any]], final_semester: int,
) -> str:
    final = {(str(row["scenario"]), str(row["metric"])): row
             for row in summary if row["semester"] == final_semester}
    lines = [
        "# Fase 18 — escenarios de homofilia pareados",
        "",
        f"{len(seeds)} semillas compartidas por tres escenarios; "
        f"{3 * len(seeds)} corridas de {final_semester} semestres.",
        "Lenguaje y sentimiento simulados. Los demás parámetros son idénticos.",
        "",
        f"## Métricas al final del semestre {final_semester}",
        "",
        "| Métrica | h=0.20 | h=0.50 | h=0.80 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in METRICS:
        cells = []
        for scenario in ("homophily_low", "homophily_medium", "homophily_high"):
            item = final[scenario, metric]
            mean = item["mean"]
            cells.append("n/d" if mean is None else f"{mean:.4f}")
        lines.append(f"| {metric} | {' | '.join(cells)} |")
    lines.extend(
        [
            "",
            "Los intervalos de confianza del 95 %, desviaciones estándar y medianas "
            "están en `scenario_summary.csv`. Las diferencias finales entre "
            "escenarios, calculadas por semilla pareada, están en "
            "`paired_final_differences.csv`. Se usan intervalos t descriptivos.",
            f"Se calcularon {len(paired)} resúmenes de diferencias pareadas.",
            "La distribución de tamaños de comunidades está en "
            "`community_size_distribution.csv`.",
            "",
            "La red sintética puede alcanzar densidad cercana a uno al final; "
            "por eso también se reportan pesos de vínculos y similitud de aristas. "
            "Estos resultados exploratorios no predicen relaciones reales.",
            "",
        ]
    )
    return "\n".join(lines)


def run_scenarios(
    *, output_root: str | Path = "outputs/phase-18-scenarios",
    seeds: Sequence[int] = tuple(range(1, 31)), smoke: bool = False,
) -> Path:
    """Execute or resume paired seeds, persisting every run and aggregate."""
    if not seeds or len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise ValueError("seeds must be a nonempty list of distinct nonnegative integers")
    root = Path(__file__).resolve().parents[3]
    configs = load_homophily_scenarios(root, smoke=smoke)
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml",
        configs["homophily_medium"].demographic_profile,
    )
    destination = Path(output_root)
    destination.mkdir(parents=True, exist_ok=True)
    run_root = destination / "runs"
    run_root.mkdir(exist_ok=True)
    plan = {
        "seeds": list(seeds), "smoke": smoke, "git_commit": current_git_commit(),
        "configs": {name: config.model_dump(mode="json") for name, config in configs.items()},
        "files_sha256": _frozen_files(root),
        "topic_bank_version": bank.topic_bank_version,
        "demographic_calibration_version": profile.version,
        "model_name": "mock", "prompt_version": "mock-v1",
        "sentiment_model_name": "mock",
    }
    plan_path = destination / "experiment_plan.json"
    if plan_path.exists():
        stored_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["git_commit"] = stored_plan["git_commit"]
        if stored_plan != plan:
            raise ValueError("experiment inputs differ from the frozen plan")
    else:
        if any(run_root.iterdir()):
            raise ValueError("run directory exists without its frozen plan")
        _write_json(plan_path, plan)
    rows: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    total = len(seeds) * len(configs)
    completed = 0
    for seed in seeds:
        for scenario, config in configs.items():
            run_id = f"phase18-{scenario}-seed-{seed:03d}"
            run_dir = run_root / run_id
            if run_dir.exists():
                cached = json.loads((run_dir / "experiment_run.json").read_text(encoding="utf-8"))
                if (
                    cached["inventory"]["seed"] != seed
                    or cached["inventory"]["scenario"] != scenario
                ):
                    raise ValueError("saved run identifiers do not match the experiment plan")
                current_rows, current_inventory = cached["rows"], cached["inventory"]
            else:
                current_rows, current_inventory = _one_run(
                    config=config, bank=bank, profile=profile, run_root=run_root,
                    scenario=scenario, seed=seed,
                )
            rows.extend(current_rows)
            inventory.append(current_inventory)
            completed += 1
            print(f"{completed}/{total} {scenario} seed={seed}", flush=True)
            gc.collect()
            if _frozen_files(root) != plan["files_sha256"]:
                raise RuntimeError("experiment inputs changed during execution")
    expected = len(seeds) * len(configs) * configs["homophily_medium"].semesters
    if len(rows) != expected:
        raise RuntimeError("scenario results have missing semester rows")
    summary = aggregate_scenarios(rows)
    paired = paired_final_differences(rows)
    sizes = community_size_distribution(rows)
    _write_csv(destination / "run_inventory.csv", inventory)
    _write_csv(destination / "run_metrics.csv", rows)
    _write_csv(destination / "scenario_summary.csv", summary)
    _write_csv(destination / "paired_final_differences.csv", paired)
    _write_csv(destination / "community_size_distribution.csv", sizes)
    _write_json(
        destination / "experiment_summary.json",
        {"seeds": list(seeds), "run_count": len(inventory), "semester_rows": len(rows),
         "scenario_summary": summary, "paired_final_differences": paired,
         "community_size_distribution": sizes},
    )
    (destination / "report.md").write_text(
        _report(seeds, summary, paired, configs["homophily_medium"].semesters),
        encoding="utf-8",
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/phase-18-scenarios"))
    parser.add_argument("--seed-count", type=int, default=30)
    args = parser.parse_args()
    if args.seed_count < 1:
        parser.error("--seed-count must be positive")
    print(run_scenarios(output_root=args.output, seeds=tuple(range(1, args.seed_count + 1))))


if __name__ == "__main__":
    main()
