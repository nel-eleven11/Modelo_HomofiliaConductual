"""Run the cohort with offline mocks and render the Phase 11 report."""

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.population import generate_population
from homophily_sim.data.topics import load_topics
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.io.metadata import make_run_metadata
from homophily_sim.io.results import save_run
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.network.metrics import NetworkMetrics, compute_metrics
from homophily_sim.network.snapshots import NetworkSnapshot, capture_snapshot
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.calendar import generate_academic_calendar
from homophily_sim.simulation.conversation import simulate_week
from homophily_sim.simulation.enrollment import enroll_semester
from homophily_sim.visualization.metric_plots import (
    plot_metric_trends,
    plot_relationship_distribution,
)
from homophily_sim.visualization.network_plots import network_layout, plot_network


def _smoke_config(config: SimulationConfig) -> SimulationConfig:
    """Keep the same rules in a small, valid two-semester pilot."""
    return SimulationConfig.model_validate(
        {
            **config.model_dump(),
            "population_size": 20,
            "years": 1,
            "semesters": 2,
            "weeks_per_semester": 1,
        }
    )


def run_mock_mvp(
    *,
    config_path: str | Path,
    topic_path: str | Path,
    demographic_path: str | Path,
    output_root: str | Path,
    run_id: str,
    seed: int,
    smoke: bool = False,
) -> Path:
    """Simulate, persist and render one seeded run without external services."""
    started = datetime.now(UTC)
    config = load_config(config_path)
    if smoke:
        config = _smoke_config(config)
    bank = load_topics(topic_path)
    profile = load_demographic_profile(demographic_path, config.demographic_profile)
    students = generate_population(config, bank, profile, seed)
    calendar = generate_academic_calendar(config, seed)
    language_model = MockLanguageModelProvider()
    sentiment_analyzer = MockSentimentAnalyzer()
    interactions: list[InteractionRecord] = []
    snapshots: list[NetworkSnapshot] = []
    series: list[tuple[int, NetworkMetrics]] = []

    for schedule in calendar:
        sections = enroll_semester(students, schedule, config, seed)
        for week in range(1, config.weeks_per_semester + 1):
            events = simulate_week(
                students,
                schedule,
                sections,
                bank,
                config,
                seed,
                week,
                run_id,
                language_model,
                sentiment_analyzer,
            )
            interactions.extend(record for event in events for record in event.records)
        snapshot = capture_snapshot(
            students,
            interactions,
            kind="semester_end",
            semester=schedule.semester,
            total_semesters=config.semesters,
        )
        snapshots.append(snapshot)
        series.append((schedule.semester, compute_metrics(snapshot.graph, students, config)))

    final = capture_snapshot(
        students,
        interactions,
        kind="final",
        semester=config.semesters,
        total_semesters=config.semesters,
    )
    metadata = make_run_metadata(
        config,
        run_id=run_id,
        seed=seed,
        prompt_version="mock-v1",
        topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name="mock",
        start_time=started,
        end_time=datetime.now(UTC),
    )
    destination = save_run(
        output_root,
        config=config,
        agents=students,
        interactions=interactions,
        metadata=metadata,
    )
    (destination / "metrics_by_semester.json").write_text(
        json.dumps(
            [{"semester": semester, **asdict(metrics)} for semester, metrics in series],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    positions = network_layout(final.graph, seed)
    plot_network(snapshots[0], destination / "network_semester_01.png", positions=positions)
    plot_network(
        snapshots[-1],
        destination / f"network_semester_{config.semesters:02d}.png",
        positions=positions,
    )
    plot_network(final, destination / "network_final.png", positions=positions)
    plot_metric_trends(series, destination)
    plot_relationship_distribution(series[-1][1], destination / "relationship_distribution.png")
    return destination


def main() -> None:
    """CLI entry point for the full mock MVP or a two-semester pilot."""
    root = Path.cwd()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "configs/homophily_medium.yaml")
    parser.add_argument("--topics", type=Path, default=root / "data/topics/topics_v1.yaml")
    parser.add_argument(
        "--demographics", type=Path, default=root / "data/demographics/profiles_v1.yaml"
    )
    parser.add_argument("--output", type=Path, default=root / "outputs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-id", type=str)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    run_id = args.run_id or f"mock-{datetime.now(UTC):%Y%m%dT%H%M%S%f}-{args.seed}"
    destination = run_mock_mvp(
        config_path=args.config,
        topic_path=args.topics,
        demographic_path=args.demographics,
        output_root=args.output,
        run_id=run_id,
        seed=args.seed,
        smoke=args.smoke,
    )
    print(destination)


if __name__ == "__main__":
    main()
