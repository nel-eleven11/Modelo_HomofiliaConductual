"""One-at-a-time local sensitivity across the three homophily scenarios."""

import argparse
import gc
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from homophily_sim.analysis.statistics import METRICS, describe
from homophily_sim.config import SimulationConfig
from homophily_sim.data.demographics import DemographicProfile, load_demographic_profile
from homophily_sim.data.topics import TopicBank, load_topics
from homophily_sim.experiments.runner import _frozen_files, _metric_row, _write_csv, _write_json
from homophily_sim.experiments.scenarios import load_homophily_scenarios
from homophily_sim.io.metadata import current_git_commit, make_run_metadata
from homophily_sim.io.results import save_run
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel

SENSITIVITY_LEVELS: dict[str, tuple[float, float, float]] = {
    "alpha_relationship": (0.10, 0.20, 0.40),
    "w_interest": (0.50, 0.70, 0.80),
    "beta_I": (1.00, 1.40, 1.80),
    "beta_E": (0.40, 0.80, 1.20),
    "beta_R": (0.30, 0.60, 0.90),
    "w_agreement": (0.60, 0.75, 0.90),
    "gamma_section": (0.25, 0.50, 0.75),
}


@dataclass(frozen=True)
class Variant:
    """A single parameter perturbation relative to one h-specific baseline."""

    parameter: str
    level: str
    value: float | None
    config: SimulationConfig

    @property
    def key(self) -> str:
        return "baseline" if self.parameter == "baseline" else f"{self.parameter}_{self.level}"


def build_variants(
    base: SimulationConfig, *, parameters: Sequence[str] = tuple(SENSITIVITY_LEVELS),
) -> list[Variant]:
    """Vary one free parameter, preserving required weight normalizations."""
    if len(set(parameters)) != len(parameters) or any(
        parameter not in SENSITIVITY_LEVELS for parameter in parameters
    ):
        raise ValueError("parameters must be unique supported sensitivity names")
    variants = [Variant("baseline", "base", None, base)]
    for parameter in parameters:
        low, baseline, high = SENSITIVITY_LEVELS[parameter]
        if abs(float(getattr(base, parameter)) - baseline) > 1e-9:
            raise ValueError(f"baseline differs from the planned {parameter} value")
        for level, value in (("low", low), ("high", high)):
            data = base.model_dump()
            data[parameter] = value
            if parameter == "w_interest":
                other_total = base.w_age + base.w_sex + base.w_origin
                for name in ("w_age", "w_sex", "w_origin"):
                    data[name] = (1 - value) * float(getattr(base, name)) / other_total
            if parameter == "w_agreement":
                data["w_sentiment"] = 1 - value
            data["scenario"] = f"{base.scenario}_{parameter}_{level}"
            variants.append(
                Variant(parameter, level, value, SimulationConfig.model_validate(data))
            )
    return variants


def _group_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[float, str, str, float | None, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["h"], row["parameter"], row["level"], row["value"], row["semester"])
        groups.setdefault(key, []).append(row)
    return [
        {"h": h, "parameter": parameter, "level": level, "value": value,
         "semester": semester, "metric": metric,
         **describe([row[metric] for row in group])}
        for (h, parameter, level, value, semester), group in sorted(
            groups.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][4])
        )
        for metric in METRICS
    ]


def _paired_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {
        (row["h"], row["seed"], row["semester"], row["variant"]): row
        for row in rows
    }
    groups: dict[tuple[float, str, str, float, int, str], list[float]] = {}
    for row in rows:
        if row["variant"] == "baseline":
            continue
        baseline = indexed[row["h"], row["seed"], row["semester"], "baseline"]
        for metric in METRICS:
            changed, original = row[metric], baseline[metric]
            if changed is None or original is None:
                continue
            key = (row["h"], row["parameter"], row["level"], row["value"],
                   row["semester"], metric)
            groups.setdefault(key, []).append(float(changed) - float(original))
    return [
        {"h": h, "parameter": parameter, "level": level, "value": value,
         "semester": semester, "metric": metric, **describe(values)}
        for (h, parameter, level, value, semester, metric), values in sorted(groups.items())
    ]


def _run_variant(
    *, variant: Variant, seed: int, bank: TopicBank, profile: DemographicProfile,
    run_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = variant.config
    h_label = {0.2: "low", 0.5: "medium", 0.8: "high"}[config.h]
    run_id = f"phase19-{h_label}-{variant.key}-seed-{seed:03d}"
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
        len(model.students) != config.population_size
        or len(model.snapshots) != config.semesters
        or len(model.year_snapshots) != config.years
        or model.final_snapshot is None
    ):
        raise RuntimeError(f"incomplete sensitivity run: {run_id}")
    rows = []
    for semester, metrics in model.metric_history:
        row = _metric_row(config.scenario, config.h, seed, semester, metrics)
        row.update(
            {"parameter": variant.parameter, "level": variant.level,
             "value": variant.value, "variant": variant.key}
        )
        rows.append(row)
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
        "h": config.h, "parameter": variant.parameter, "level": variant.level,
        "value": variant.value, "variant": variant.key, "seed": seed,
        "run_id": run_id, "completed_semesters": len(model.snapshots),
        "conversation_count": model.conversation_count,
        "interaction_count": len(model.interactions),
        "simulation_seconds": seconds, "run_directory": f"runs/{run_id}",
    }
    _write_json(destination / "sensitivity_run.json", {"inventory": inventory, "rows": rows})
    return rows, inventory


def run_sensitivity(
    *, output_root: str | Path = "outputs/phase-19-sensitivity",
    seeds: Sequence[int] = tuple(range(1, 6)),
    parameters: Sequence[str] = tuple(SENSITIVITY_LEVELS),
    smoke: bool = False,
) -> Path:
    """Run or resume paired one-at-a-time variations for every h level."""
    if not seeds or len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise ValueError("seeds must be distinct nonnegative integers")
    root = Path(__file__).resolve().parents[3]
    configs = load_homophily_scenarios(root, smoke=smoke)
    conditions = {
        name: build_variants(config, parameters=parameters)
        for name, config in configs.items()
    }
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
        "seeds": list(seeds), "parameters": list(parameters), "smoke": smoke,
        "git_commit": current_git_commit(),
        "conditions": {
            name: {variant.key: variant.config.model_dump(mode="json")
                   for variant in variants}
            for name, variants in conditions.items()
        },
        "files_sha256": _frozen_files(root),
        "topic_bank_version": bank.topic_bank_version,
        "demographic_calibration_version": profile.version,
        "model_name": "mock", "prompt_version": "mock-v1",
        "sentiment_model_name": "mock",
    }
    plan_path = destination / "sensitivity_plan.json"
    if plan_path.exists():
        stored = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["git_commit"] = stored["git_commit"]
        if stored != plan:
            raise ValueError("sensitivity inputs differ from the frozen plan")
    else:
        if any(run_root.iterdir()):
            raise ValueError("run directory exists without a frozen plan")
        _write_json(plan_path, plan)
    rows: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    total = len(seeds) * sum(len(variants) for variants in conditions.values())
    completed = 0
    for seed in seeds:
        for variants in conditions.values():
            for variant in variants:
                h_label = {0.2: "low", 0.5: "medium", 0.8: "high"}[variant.config.h]
                run_id = f"phase19-{h_label}-{variant.key}-seed-{seed:03d}"
                run_dir = run_root / run_id
                if run_dir.exists():
                    cached = json.loads(
                        (run_dir / "sensitivity_run.json").read_text(encoding="utf-8")
                    )
                    if (
                        cached["inventory"]["seed"] != seed
                        or cached["inventory"]["variant"] != variant.key
                    ):
                        raise ValueError("saved sensitivity run does not match the plan")
                    current_rows, current_inventory = cached["rows"], cached["inventory"]
                else:
                    current_rows, current_inventory = _run_variant(
                        variant=variant, seed=seed, bank=bank, profile=profile,
                        run_root=run_root,
                    )
                rows.extend(current_rows)
                inventory.append(current_inventory)
                completed += 1
                print(f"{completed}/{total} h={variant.config.h:.2f} "
                      f"{variant.key} seed={seed}", flush=True)
                gc.collect()
                if _frozen_files(root) != plan["files_sha256"]:
                    raise RuntimeError("sensitivity inputs changed during execution")
    expected = total * configs["homophily_medium"].semesters
    if len(rows) != expected:
        raise RuntimeError("sensitivity results have missing semester rows")
    summary = _group_summaries(rows)
    deltas = _paired_deltas(rows)
    _write_csv(destination / "run_inventory.csv", inventory)
    _write_csv(destination / "run_metrics.csv", rows)
    _write_csv(destination / "sensitivity_summary.csv", summary)
    _write_csv(destination / "paired_deltas.csv", deltas)
    _write_json(
        destination / "sensitivity_summary.json",
        {"run_count": len(inventory), "semester_rows": len(rows),
         "seeds": list(seeds), "parameters": list(parameters),
         "summary": summary, "paired_deltas": deltas},
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/phase-19-sensitivity"))
    parser.add_argument("--seed-count", type=int, default=5)
    args = parser.parse_args()
    if args.seed_count < 1:
        parser.error("--seed-count must be positive")
    print(run_sensitivity(output_root=args.output, seeds=tuple(range(1, args.seed_count + 1))))


if __name__ == "__main__":
    main()
