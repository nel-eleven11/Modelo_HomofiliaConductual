"""Internal verification and controlled logic checks for Phase 20."""

import argparse
import csv
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from statistics import fmean
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from homophily_sim.analysis.statistics import describe
from homophily_sim.analysis.thesis import SCENARIOS, validate_scenario_rows
from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.domain.agent import Origin, Sex, StudentAgent
from homophily_sim.io.metadata import make_run_metadata
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.conversation import start_weights
from homophily_sim.simulation.model import HomophilyModel
from homophily_sim.social.participation import participation_probability
from homophily_sim.social.relationships import update_relationship
from homophily_sim.social.similarity import interest_jaccard

CONTROL_CASES = (
    "baseline", "h_zero", "h_high", "shared_interests", "disjoint_interests",
    "neutral_relationship", "extraversion_zero", "extraversion_high",
)
BOUNDED_COLUMNS = (
    "similarity", "relationship_before", "participation_probability",
    "agreement", "sentiment_valence", "interaction_score", "relationship_after",
)


def logical_probes(base: SimulationConfig) -> list[dict[str, Any]]:
    """Check directions while fixing all other inputs to the social equations."""
    h0 = base.model_copy(update={"h": 0.0})
    h1 = base.model_copy(update={"h": 1.0})

    def probability(config: SimulationConfig, ext: float, relation: float,
                    similarity: float) -> float:
        return participation_probability(ext, 0.5, relation, similarity, config)

    zero_similarity_gap = probability(h0, 5, 0.5, 1) - probability(h0, 5, 0.5, 0)
    high_similarity_gap = probability(h1, 5, 0.5, 1) - probability(h1, 5, 0.5, 0)
    zero_relationship_gap = probability(h0, 5, 1, 0.5) - probability(h0, 5, 0, 0.5)
    high_relationship_gap = probability(h1, 5, 1, 0.5) - probability(h1, 5, 0, 0.5)
    interest_only = h1.model_copy(update={"beta_I": 0.0})
    same = interest_jaccard({"technology"}, {"technology"})
    distinct = interest_jaccard({"technology"}, {"music"})
    interest_gap = probability(interest_only, 5, 0.5, same) - probability(
        interest_only, 5, 0.5, distinct
    )
    neutral_shift = max(
        abs(update_relationship(0.5, score, 0) - 0.5) for score in (0, 1)
    )
    extraversion_gap = probability(base, 10, 0.5, 0.5) - probability(base, 0, 0.5, 0.5)
    students = (
        StudentAgent(id=0, age=18, sex=Sex.FEMALE, origin=Origin.REST_OF_COUNTRY,
                     semester=1, interests={"technology"}, extraversion=0),
        StudentAgent(id=1, age=18, sex=Sex.FEMALE, origin=Origin.REST_OF_COUNTRY,
                     semester=1, interests={"technology"}, extraversion=10),
    )
    minimum_start_weight = min(start_weights(students, base.epsilon_start))
    specifications = (
        ("h_zero_ignores_similarity", zero_similarity_gap, "zero", zero_similarity_gap == 0),
        ("h_high_increases_similarity_effect", high_similarity_gap - zero_similarity_gap,
         "positive", high_similarity_gap > zero_similarity_gap),
        ("h_high_increases_relationship_effect", high_relationship_gap - zero_relationship_gap,
         "positive", high_relationship_gap > zero_relationship_gap),
        ("same_vs_disjoint_interests", interest_gap, "positive", interest_gap > 0),
        ("relationship_fixed_neutral", neutral_shift, "zero", neutral_shift == 0),
        ("extreme_extraversion_participation", extraversion_gap, "positive",
         extraversion_gap > 0),
        ("zero_extraversion_can_initiate", minimum_start_weight, "positive",
         minimum_start_weight > 0),
    )
    return [
        {"case": name, "observed_difference": difference, "expected": expected,
         "passed": passed} for name, difference, expected, passed in specifications
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def audit_saved_runs(source: Path) -> dict[str, Any]:
    """Check every Phase 18 run's directed updates and saved final weights."""
    rows = _read_csv(source / "run_metrics.csv")
    if validate_scenario_rows(rows) != (30, 10):
        raise ValueError("expected 30 paired seeds and 10 semesters")
    inventory = _read_csv(source / "run_inventory.csv")
    if len(inventory) != 90:
        raise ValueError("expected 90 complete run inventories")
    plan = json.loads((source / "experiment_plan.json").read_text(encoding="utf-8"))
    if plan["smoke"] or plan["model_name"] != "mock" or plan["seeds"] != list(range(1, 31)):
        raise ValueError("saved experiment is not the expected offline full design")
    interactions_total = 0
    asymmetric_runs = 0
    max_update_error = 0.0
    for item in inventory:
        directory = source / item["run_directory"]
        config = SimulationConfig.model_validate_json(
            (directory / "config.json").read_text(encoding="utf-8")
        )
        if config.population_size != 80 or config.semesters != 10 or config.h != float(item["h"]):
            raise ValueError(f"unexpected configuration: {directory}")
        agents = pd.read_parquet(directory / "agents.parquet", columns=["id"])
        if len(agents) != 80 or len(set(agents["id"])) != 80:
            raise ValueError(f"invalid cohort: {directory}")
        interactions = pd.read_parquet(
            directory / "interactions.parquet",
            columns=["receiver_id", "sender_id", "semester", *BOUNDED_COLUMNS],
        )
        if interactions.empty or len(interactions) != int(item["interaction_count"]):
            raise ValueError(f"interaction count mismatch: {directory}")
        if not interactions["semester"].between(1, 10).all():
            raise ValueError(f"semester outside horizon: {directory}")
        if (interactions["receiver_id"] == interactions["sender_id"]).any():
            raise ValueError(f"self interaction: {directory}")
        for column in BOUNDED_COLUMNS:
            values = interactions[column].to_numpy(dtype=float)
            if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
                raise ValueError(f"invalid {column}: {directory}")
        expected = (
            (1 - config.alpha_relationship) * interactions["relationship_before"]
            + config.alpha_relationship * interactions["interaction_score"]
        )
        error = float(np.max(np.abs(interactions["relationship_after"] - expected)))
        max_update_error = max(max_update_error, error)
        if error > 1e-12:
            raise ValueError(f"relationship update mismatch: {directory}")
        last = interactions.drop_duplicates(["receiver_id", "sender_id"], keep="last")
        saved = pd.read_parquet(directory / "relationships.parquet")
        merged = last.merge(
            saved, left_on=["receiver_id", "sender_id"],
            right_on=["observer_id", "other_id"], validate="one_to_one",
        )
        if len(merged) != len(last) or len(merged) != len(saved) or not np.allclose(
            merged["relationship_after"], merged["weight"], atol=1e-12, rtol=0
        ):
            raise ValueError(f"saved directed graph differs from interactions: {directory}")
        reverse = saved.merge(
            saved, left_on=["observer_id", "other_id"],
            right_on=["other_id", "observer_id"], suffixes=("_forward", "_reverse"),
        )
        asymmetric_runs += int(
            (np.abs(reverse["weight_forward"] - reverse["weight_reverse"]) > 1e-12).any()
        )
        interactions_total += len(interactions)
    if asymmetric_runs != 90:
        raise ValueError("directed relationships unexpectedly symmetric")
    for row in rows:
        for key in ("density", "reciprocity", "mean_relationship_weight",
                    "mean_edge_similarity"):
            if not 0 <= float(row[key]) <= 1:
                raise ValueError(f"invalid network metric {key}")
    return {
        "status": "passed", "runs": 90, "semesters": 900,
        "interactions": interactions_total, "asymmetric_runs": asymmetric_runs,
        "max_relationship_update_error": max_update_error,
        "mock_provider_only": True,
    }


def _controlled_config(base: SimulationConfig, case: str) -> SimulationConfig:
    values = {
        **base.model_dump(), "scenario": f"validation_{case}",
        "population_size": 20, "years": 1, "semesters": 2, "weeks_per_semester": 1,
    }
    if case == "h_zero":
        values["h"] = 0.0
    elif case in ("h_high", "shared_interests", "disjoint_interests"):
        values["h"] = 1.0
    if case in ("shared_interests", "disjoint_interests"):
        values["beta_I"] = 0.0
    elif case == "neutral_relationship":
        values["alpha_relationship"] = 0.0
    elif case in ("extraversion_zero", "extraversion_high"):
        values["extraversion_mean"] = 0.0 if case == "extraversion_zero" else 10.0
        values["extraversion_std"] = 0.0
    return SimulationConfig.model_validate(values)


def controlled_runs(root: Path, destination: Path, seeds: Sequence[int]) -> list[dict[str, Any]]:
    """Run one full academic week per controlled condition with matched seeds."""
    if not seeds or len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise ValueError("controlled seeds must be unique nonnegative integers")
    base = load_config(root / "configs/base.yaml")
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", base.demographic_profile
    )
    if len(bank.interest_terms) < 20:
        raise ValueError("disjoint-interest probe requires 20 taxonomy terms")
    terms = sorted(bank.interest_terms)
    run_root = destination / "runs"
    run_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for case in CONTROL_CASES:
        config = _controlled_config(base, case)
        for seed in seeds:
            run_id = f"phase20-{case}-seed-{seed:03d}"
            start = datetime.now(UTC)
            model = HomophilyModel(
                config, bank, profile, run_seed=seed, run_id=run_id,
                language_model=MockLanguageModelProvider(),
                sentiment_analyzer=MockSentimentAnalyzer(),
            )
            if case == "shared_interests":
                for student in model.students:
                    student.interests = {terms[0]}
            elif case == "disjoint_interests":
                for student, term in zip(model.students, terms[:20], strict=True):
                    student.interests = {term}
            model.step()
            exposures = [
                record for event in model.last_events
                for record in event.records[:len(event.exposed_ids)]
            ]
            if not exposures or len(model.snapshots) != 1:
                raise RuntimeError(f"controlled run did not finish one week: {run_id}")
            probabilities = [record.participation_probability for record in exposures]
            if any(value is None for value in probabilities):
                raise RuntimeError(f"missing participation probability: {run_id}")
            participants = sum(len(event.participant_ids) for event in model.last_events)
            row = {
                "case": case, "seed": seed, "run_id": run_id,
                "h": config.h, "beta_I": config.beta_I,
                "alpha_relationship": config.alpha_relationship,
                "conversations": len(model.last_events),
                "exposures": len(exposures), "participants": participants,
                "participation_rate": participants / len(exposures),
                "mean_exposure_probability": fmean(
                    value for value in probabilities if value is not None
                ),
                "mean_exposure_similarity": fmean(record.similarity for record in exposures),
                "max_relationship_shift": max(
                    abs(record.relationship_after - 0.5) for record in model.interactions
                ),
                "density": model.metric_history[0][1].density,
            }
            directory = run_root / run_id
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "config.json").write_text(config.model_dump_json(indent=2) + "\n")
            metadata = make_run_metadata(
                config, run_id=run_id, seed=seed, prompt_version="mock-v1",
                topic_bank_version=bank.topic_bank_version,
                demographic_calibration_version=profile.version,
                model_name="mock", sentiment_model_name="mock",
                start_time=start, end_time=datetime.now(UTC),
            )
            (directory / "run_metadata.json").write_text(metadata.model_dump_json(indent=2) + "\n")
            (directory / "result.json").write_text(json.dumps(row, indent=2) + "\n")
            rows.append(row)
    return rows


def controlled_contrasts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare matched seeds and record directions without a significance claim."""
    indexed = {(row["case"], row["seed"]): row for row in rows}
    seeds = sorted({row["seed"] for row in rows})
    specifications = (
        ("h_high_vs_zero", "h_high", "h_zero", "mean_exposure_probability"),
        ("shared_vs_disjoint_similarity", "shared_interests", "disjoint_interests",
         "mean_exposure_similarity"),
        ("shared_vs_disjoint_participation", "shared_interests", "disjoint_interests",
         "mean_exposure_probability"),
        ("extreme_extraversion", "extraversion_high", "extraversion_zero",
         "mean_exposure_probability"),
    )
    results = []
    for name, higher, lower, metric in specifications:
        differences = [indexed[higher, seed][metric] - indexed[lower, seed][metric]
                       for seed in seeds]
        summary = describe(differences)
        results.append({
            "contrast": name, "metric": metric, "higher": higher, "lower": lower,
            **summary, "positive_seeds": sum(value > 0 for value in differences),
            "passed": bool(summary["mean"] > 0),
        })
    neutral = [indexed["neutral_relationship", seed]["max_relationship_shift"]
               for seed in seeds]
    results.append({
        "contrast": "neutral_relationship_fixed", "metric": "max_relationship_shift",
        "higher": "neutral_relationship", "lower": "neutral_prior", **describe(neutral),
        "positive_seeds": sum(value > 0 for value in neutral),
        "passed": all(value == 0 for value in neutral),
    })
    return results


def seed_stability(source: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Summarize within-scenario variation and paired signs over 30 seeds."""
    rows = _read_csv(source / "run_metrics.csv")
    if validate_scenario_rows(rows) != (30, 10):
        raise ValueError("stability requires 30 paired full runs")
    indexed = {(row["scenario"], int(row["seed"]), int(row["semester"])): row
               for row in rows}
    metrics = ("density", "mean_relationship_weight", "mean_edge_similarity",
               "modularity")
    summaries = []
    for scenario in SCENARIOS:
        for semester in (1, 10):
            for metric in metrics:
                values = [float(indexed[scenario, seed, semester][metric])
                          for seed in range(1, 31)]
                summaries.append({
                    "scenario": scenario, "semester": semester, "metric": metric,
                    **describe(values), "minimum": min(values), "maximum": max(values),
                })
    paired = []
    for semester, metric in ((1, "density"), (10, "density"),
                             (10, "mean_relationship_weight"),
                             (10, "mean_edge_similarity")):
        differences = [
            float(indexed["homophily_high", seed, semester][metric])
            - float(indexed["homophily_low", seed, semester][metric])
            for seed in range(1, 31)
        ]
        paired.append({
            "semester": semester, "metric": metric, **describe(differences),
            "positive_seeds": sum(value > 0 for value in differences),
            "negative_seeds": sum(value < 0 for value in differences),
            "zero_seeds": sum(value == 0 for value in differences),
        })
    return summaries, paired


def run_validation(
    *, source: Path = Path("outputs/phase-18-scenarios"),
    destination: Path = Path("outputs/phase-20-validation"),
    seeds: Sequence[int] = tuple(range(1, 11)),
) -> Path:
    """Execute all four local evidence steps and save presentation tables."""
    root = Path(__file__).resolve().parents[3]
    destination.mkdir(parents=True, exist_ok=True)
    probes = logical_probes(load_config(root / "configs/base.yaml"))
    audit = audit_saved_runs(source)
    runs = controlled_runs(root, destination, seeds)
    contrasts = controlled_contrasts(runs)
    stability, paired = seed_stability(source)
    _write_csv(destination / "logical_probes.csv", probes)
    _write_csv(destination / "controlled_runs.csv", runs)
    _write_csv(destination / "controlled_contrasts.csv", contrasts)
    _write_csv(destination / "seed_stability.csv", stability)
    _write_csv(destination / "paired_seed_signs.csv", paired)
    sources = [source / "experiment_plan.json", source / "run_metrics.csv",
               source / "run_inventory.csv", root / "configs/base.yaml",
               root / "data/topics/topics_v1.yaml",
               root / "data/demographics/profiles_v1.yaml", Path(__file__)]
    result = {
        "phase": 20, "status": "completed",
        "verification": audit,
        "logical_probes": {"count": len(probes),
                           "passed": sum(row["passed"] for row in probes)},
        "controlled": {"seeds": list(seeds), "runs": len(runs),
                       "contrasts_passed": sum(row["passed"] for row in contrasts),
                       "contrasts_total": len(contrasts)},
        "stability": {"scenarios": len(SCENARIOS), "paired_seeds": 30,
                      "rows": len(stability), "paired_comparisons": len(paired)},
        "literature": "See docs/experiments/phase_20_validation.md",
        "source_sha256": {
            path.resolve().relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sources
        },
    }
    if any(not row["passed"] for row in probes + contrasts):
        result["status"] = "completed_with_failed_logic_checks"
    (destination / "validation_summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    archive = destination.parent / "phase-20-validation-summary.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(destination.iterdir()):
            if path.is_file():
                bundle.write(path, path.name)
        report = root / "docs/experiments/phase_20_validation.md"
        if report.exists():
            bundle.write(report, report.name)
    with ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("validation summary archive failed integrity check")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/phase-18-scenarios"))
    parser.add_argument("--output", type=Path, default=Path("outputs/phase-20-validation"))
    parser.add_argument("--seeds", type=int, default=10,
                        help="Number of matched controlled seeds, starting at 1")
    args = parser.parse_args()
    if args.seeds < 2:
        raise ValueError("at least two controlled seeds are required")
    print(run_validation(source=args.source, destination=args.output,
                         seeds=tuple(range(1, args.seeds + 1))))


if __name__ == "__main__":
    main()
