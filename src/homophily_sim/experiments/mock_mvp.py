"""Run the cohort with mock or Gemini language and render its report."""

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.io.metadata import make_run_metadata
from homophily_sim.io.results import save_run
from homophily_sim.llm.base import LanguageModelProvider
from homophily_sim.llm.gemini import GeminiLanguageModelProvider
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.llm.prompts import PROMPT_VERSION
from homophily_sim.nlp.base import SentimentAnalyzer
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.nlp.sentiment import TransformersSentimentAnalyzer
from homophily_sim.simulation.conversation import ConversationEvent
from homophily_sim.simulation.model import HomophilyModel
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
    language_model: LanguageModelProvider | None = None,
    sentiment_analyzer: SentimentAnalyzer | None = None,
    event_observer: Callable[[list[ConversationEvent]], None] | None = None,
) -> Path:
    """Simulate, persist and render one run with injectable language and sentiment."""
    started = datetime.now(UTC)
    config = load_config(config_path)
    if smoke:
        config = _smoke_config(config)
    bank = load_topics(topic_path)
    profile = load_demographic_profile(demographic_path, config.demographic_profile)
    provider = language_model or MockLanguageModelProvider()
    sentiment = sentiment_analyzer or MockSentimentAnalyzer()
    model = HomophilyModel(
        config,
        bank,
        profile,
        run_seed=seed,
        run_id=run_id,
        language_model=provider,
        sentiment_analyzer=sentiment,
    )
    if event_observer is None:
        model.run_to_completion()
    else:
        while model.running:
            model.step()
            event_observer(model.last_events)
    final = model.final_snapshot
    if final is None:
        raise RuntimeError("completed Mesa run has no final snapshot")
    students = model.students
    series = model.metric_history
    gemini = provider if isinstance(provider, GeminiLanguageModelProvider) else None
    metadata = make_run_metadata(
        config,
        run_id=run_id,
        seed=seed,
        prompt_version=PROMPT_VERSION if gemini is not None else "mock-v1",
        topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name=gemini.model_name if gemini is not None else "mock",
        sentiment_model_name=(
            sentiment.model_name if isinstance(sentiment, TransformersSentimentAnalyzer) else "mock"
        ),
        language_settings={
            "temperature": gemini.temperature,
            "max_output_tokens": gemini.max_output_tokens,
            "generation_seed": gemini.generation_seed,
            "timeout_ms": gemini.timeout_ms,
            "retry_attempts": gemini.retry_attempts,
        }
        if gemini is not None
        else {},
        start_time=started,
        end_time=datetime.now(UTC),
    )
    destination = save_run(
        output_root,
        config=config,
        agents=students,
        interactions=model.interactions,
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
    plot_network(model.snapshots[0], destination / "network_semester_01.png", positions=positions)
    plot_network(
        model.snapshots[-1],
        destination / f"network_semester_{config.semesters:02d}.png",
        positions=positions,
    )
    plot_network(final, destination / "network_final.png", positions=positions)
    plot_metric_trends(series, destination)
    plot_relationship_distribution(series[-1][1], destination / "relationship_distribution.png")
    return destination


def main() -> None:
    """CLI entry point for a full run or a short two-semester pilot."""
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
    parser.add_argument("--gemini", action="store_true", help="Use Gemini for language generation")
    parser.add_argument(
        "--sentiment", action="store_true", help="Use a local multilingual sentiment classifier"
    )
    args = parser.parse_args()
    provider = GeminiLanguageModelProvider(generation_seed=args.seed) if args.gemini else None
    prefix = "gemini" if provider is not None else "mock"
    run_id = args.run_id or f"{prefix}-{datetime.now(UTC):%Y%m%dT%H%M%S%f}-{args.seed}"
    destination = run_mock_mvp(
        config_path=args.config,
        topic_path=args.topics,
        demographic_path=args.demographics,
        output_root=args.output,
        run_id=run_id,
        seed=args.seed,
        smoke=args.smoke,
        language_model=provider,
        sentiment_analyzer=TransformersSentimentAnalyzer() if args.sentiment else None,
    )
    print(destination)


if __name__ == "__main__":
    main()
