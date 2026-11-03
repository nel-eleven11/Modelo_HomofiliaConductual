"""Resumable single-scenario longitudinal experiment using Gemini."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.domain.opportunity import ParticipationOpportunity
from homophily_sim.domain.section import Section
from homophily_sim.experiments.runner import _metric_row, _write_csv, _write_json
from homophily_sim.experiments.scenarios import load_homophily_scenarios
from homophily_sim.io.mechanisms import export_mechanisms, mechanism_row
from homophily_sim.io.metadata import current_git_commit, make_run_metadata
from homophily_sim.io.results import save_run
from homophily_sim.llm.base import UtteranceRequest, UtteranceResult
from homophily_sim.llm.cache import SqliteUtteranceCache
from homophily_sim.llm.gemini import GeminiLanguageModelProvider
from homophily_sim.llm.prompts import PROMPT_VERSION
from homophily_sim.network.metrics import NetworkMetrics
from homophily_sim.nlp.sentiment import TransformersSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel, StudentMesaAgent

INPUT_USD_PER_MILLION = 0.30
OUTPUT_USD_PER_MILLION = 2.50
USAGE_KEYS = (
    "api_calls",
    "cache_hits",
    "prompt_tokens",
    "output_tokens",
    "total_tokens",
    "responses_with_usage",
)


def estimated_cost(usage: dict[str, int]) -> float:
    """Estimate standard text price, including non-candidate output tokens."""
    output = max(usage["output_tokens"], usage["total_tokens"] - usage["prompt_tokens"])
    return (
        usage["prompt_tokens"] * INPUT_USD_PER_MILLION + output * OUTPUT_USD_PER_MILLION
    ) / 1_000_000


class BudgetedProvider:
    """Stop new requests before the configured estimated token budget."""

    def __init__(
        self, provider: GeminiLanguageModelProvider, base: dict[str, int], limit: float
    ) -> None:
        self.provider = provider
        self.base = base
        self.limit = limit

    def usage(self) -> dict[str, int]:
        return {key: self.base[key] + getattr(self.provider, key) for key in USAGE_KEYS}

    def generate_utterance(self, request: UtteranceRequest) -> UtteranceResult:
        # Reserve for one unusually long reply. Cache hits remain available after the limit.
        if estimated_cost(self.usage()) + 0.01 >= self.limit:
            raise RuntimeError("Gemini estimated-cost limit reached; checkpoint is resumable")
        result = self.provider.generate_utterance(request)
        if self.provider.api_calls > self.provider.responses_with_usage:
            raise RuntimeError("Gemini did not report token usage; stopping to protect the budget")
        return result


def _encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class WeekCheckpoint:
    """Commit one completed week and its records in a single SQLite transaction."""

    def __init__(self, path: Path, fingerprint: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=60)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS interactions "
            "(seq INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS opportunities "
            "(seq INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
        )
        stored = self.get("fingerprint")
        if stored is None:
            self.put("fingerprint", fingerprint)
            self.put("completed_weeks", 0)
            self.put("usage", dict.fromkeys(USAGE_KEYS, 0))
            self.put("started_at", datetime.now(UTC).isoformat())
            self.connection.commit()
        elif stored != fingerprint:
            raise ValueError("checkpoint inputs differ from this experiment")

    def get(self, key: str) -> Any:
        row = self.connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: Any) -> None:
        self.connection.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, _encode(value)))

    def restore(self, model: HomophilyModel) -> None:
        weeks = int(self.get("completed_weeks"))
        if not weeks:
            return
        original_step = model._user_step
        model._user_step = lambda: None
        for _ in range(weeks):
            model.step()
        model._user_step = original_step
        state = self.get("state")
        by_id = {
            agent.id: agent
            for agent in (StudentAgent.model_validate(row) for row in state["students"])
        }
        for agent in model.agents:
            if isinstance(agent, StudentMesaAgent):
                agent.state = by_id[agent.state.id]
        model.current_semester = state["semester"]
        model.current_week = state["week"]
        model.sections_by_course = {
            course: tuple(Section.model_validate(row) for row in sections)
            for course, sections in state["sections"].items()
        }
        model.metric_history = []
        for semester, metrics in state["metrics"]:
            for name in ("in_degree", "out_degree", "in_strength", "out_strength"):
                metrics[name] = {int(key): value for key, value in metrics[name].items()}
            for name in ("isolates", "relationship_weights", "community_sizes"):
                metrics[name] = tuple(metrics[name])
            for name in ("weak_components", "strong_components", "communities"):
                metrics[name] = tuple(tuple(group) for group in metrics[name])
            model.metric_history.append((semester, NetworkMetrics(**metrics)))
        model.conversation_count = state["conversation_count"]
        model.interactions = [
            InteractionRecord.model_validate_json(row[0])
            for row in self.connection.execute("SELECT payload FROM interactions ORDER BY seq")
        ]
        model.opportunities = [
            ParticipationOpportunity.model_validate_json(row[0])
            for row in self.connection.execute("SELECT payload FROM opportunities ORDER BY seq")
        ]
        if weeks == model.config.semesters * model.config.weeks_per_semester:
            model.running = False

    def save_week(self, model: HomophilyModel, usage: dict[str, int]) -> None:
        interaction_count = self.count("interactions")
        opportunity_count = self.count("opportunities")
        with self.connection:
            self.connection.executemany(
                "INSERT INTO interactions VALUES (?,?)",
                (
                    (interaction_count + offset, record.model_dump_json())
                    for offset, record in enumerate(model.interactions[interaction_count:], 1)
                ),
            )
            self.connection.executemany(
                "INSERT INTO opportunities VALUES (?,?)",
                (
                    (opportunity_count + offset, item.model_dump_json())
                    for offset, item in enumerate(model.opportunities[opportunity_count:], 1)
                ),
            )
            self.put(
                "state",
                {
                    "students": [agent.model_dump(mode="json") for agent in model.students],
                    "semester": model.current_semester,
                    "week": model.current_week,
                    "sections": {
                        course: [section.model_dump(mode="json") for section in sections]
                        for course, sections in model.sections_by_course.items()
                    },
                    "metrics": [
                        (semester, asdict(metrics)) for semester, metrics in model.metric_history
                    ],
                    "conversation_count": model.conversation_count,
                },
            )
            self.put("usage", usage)
            self.put("completed_weeks", model.steps)

    def count(self, table: str) -> int:
        return int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def run_real_gemini(
    output_root: str | Path = "outputs/real-gemini-medium-seed-001",
    *,
    seed: int = 1,
    max_cost_usd: float = 10.0,
    max_weeks: int | None = None,
) -> Path:
    """Run or resume the medium-homophily cohort with a local spending guard."""
    if seed < 0 or max_cost_usd <= 0:
        raise ValueError("seed and budget must be valid")
    root = Path(__file__).resolve().parents[3]
    config = load_homophily_scenarios(root)["homophily_medium"]
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    run_id = f"gemini-{config.scenario}-seed-{seed:03d}"
    provider = GeminiLanguageModelProvider(
        cache=SqliteUtteranceCache(output / "llm_cache.sqlite3"),
        generation_seed=seed,
    )
    fingerprint = {
        "config": config.model_dump(mode="json"),
        "seed": seed,
        "run_id": run_id,
        "git_commit": current_git_commit(),
        "topic_bank_version": bank.topic_bank_version,
        "demographic_profile": profile.version,
        "model": provider.model_name,
        "prompt_version": PROMPT_VERSION,
        "sentiment_model": "cardiffnlp/twitter-xlm-roberta-base-sentiment",
        "temperature": provider.temperature,
        "max_output_tokens": provider.max_output_tokens,
    }
    checkpoint = WeekCheckpoint(output / "checkpoint.sqlite3", fingerprint)
    destination = output / "runs" / run_id
    if destination.exists():
        return destination
    base = checkpoint.get("usage")
    language = BudgetedProvider(provider, base, max_cost_usd)
    sentiment = TransformersSentimentAnalyzer()
    model = HomophilyModel(
        config,
        bank,
        profile,
        run_seed=seed,
        run_id=run_id,
        language_model=language,
        sentiment_analyzer=sentiment,
    )
    checkpoint.restore(model)
    target_weeks = config.semesters * config.weeks_per_semester
    if max_weeks is not None:
        target_weeks = min(target_weeks, max_weeks)
    try:
        while model.running and model.steps < target_weeks:
            model.step()
            checkpoint.save_week(model, language.usage())
            print(
                f"completed semester={model.current_semester} week={model.current_week} "
                f"weeks={model.steps}/{config.semesters * config.weeks_per_semester} "
                f"calls={language.usage()['api_calls']} "
                f"estimated_usd={estimated_cost(language.usage()):.4f}",
                flush=True,
            )
    except BaseException:
        with checkpoint.connection:
            checkpoint.put("usage", language.usage())
        raise
    if model.steps < config.semesters * config.weeks_per_semester:
        return output
    metadata = make_run_metadata(
        config,
        run_id=run_id,
        seed=seed,
        prompt_version=PROMPT_VERSION,
        topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name=provider.model_name,
        sentiment_model_name=sentiment.model_name,
        language_settings={
            "temperature": provider.temperature,
            "max_output_tokens": provider.max_output_tokens,
            "generation_seed": seed,
        },
        start_time=datetime.fromisoformat(checkpoint.get("started_at")),
        end_time=datetime.now(UTC),
    )
    destination = save_run(
        output / "runs",
        config=config,
        agents=model.students,
        interactions=model.interactions,
        opportunities=model.opportunities,
        metadata=metadata,
    )
    mechanisms = export_mechanisms(destination, bank)
    rows = [
        {
            **_metric_row(config.scenario, config.h, seed, semester, metrics),
            **mechanism_row(
                mechanisms.interaction[semester - 1], mechanisms.relationships[semester - 1]
            ),
        }
        for semester, metrics in model.metric_history
    ]
    _write_csv(destination / "run_metrics.csv", rows)
    _write_json(
        destination / "metrics_by_semester.json",
        [{"semester": semester, **asdict(metrics)} for semester, metrics in model.metric_history],
    )
    _write_json(
        destination / "experiment_run.json",
        {
            "run_id": run_id,
            "completed_semesters": config.semesters,
            "conversation_count": model.conversation_count,
            "interaction_count": len(model.interactions),
            "opportunity_count": len(model.opportunities),
            "gemini_usage": language.usage(),
            "estimated_cost_usd": estimated_cost(language.usage()),
            "price_usd_per_million_input_tokens": INPUT_USD_PER_MILLION,
            "price_usd_per_million_output_tokens": OUTPUT_USD_PER_MILLION,
        },
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="outputs/real-gemini-medium-seed-001")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-cost-usd", type=float, default=10.0)
    parser.add_argument("--max-weeks", type=int)
    args = parser.parse_args()
    print(
        run_real_gemini(
            args.output, seed=args.seed, max_cost_usd=args.max_cost_usd, max_weeks=args.max_weeks
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
