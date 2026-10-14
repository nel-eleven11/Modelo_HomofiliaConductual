"""First small simulation pilot with saved diagnostics for presentation."""

import argparse
import csv
import json
from collections.abc import Sequence
from math import ceil
from pathlib import Path
from statistics import fmean, median
from typing import Any

from homophily_sim.experiments.mock_mvp import run_mock_mvp
from homophily_sim.io.results import load_run
from homophily_sim.llm.base import LanguageModelProvider
from homophily_sim.llm.gemini import GeminiLanguageModelProvider
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.base import SentimentAnalyzer
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.nlp.sentiment import TransformersSentimentAnalyzer
from homophily_sim.simulation.conversation import ConversationEvent


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    """Summarize a nonempty observed distribution without statistical extrapolation."""
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "mean": fmean(ordered),
        "median": median(ordered),
        "p90": ordered[ceil(0.9 * len(ordered)) - 1],
        "max": ordered[-1],
    }


def _network_rows(metrics: list[dict[str, Any]]) -> list[dict[str, int | float | None]]:
    rows: list[dict[str, int | float | None]] = []
    for item in metrics:
        weights = item["relationship_weights"]
        rows.append(
            {
                "semester": int(item["semester"]),
                "directed_edges": len(weights),
                "density": float(item["density"]),
                "isolates": len(item["isolates"]),
                "reciprocity": item["reciprocity"],
                "modularity": float(item["modularity"]),
                "mean_edge_similarity": item["mean_edge_similarity"],
                "mean_relationship": fmean(weights) if weights else None,
            }
        )
    return rows


def _report(summary: dict[str, Any], rows: list[dict[str, int | float | None]]) -> str:
    probability = summary["participation_probability"]
    relationship = summary["relationship_after"]
    lines = [
        "# Piloto 1 — homofilia media",
        "",
        f"Ejecución: `{summary['run_id']}` · semilla: {summary['seed']} · h: {summary['h']}",
        f"{summary['population_size']} agentes · {summary['simulated_weeks']} semanas simuladas "
        f"(una por semestre) · {summary['conversation_count']} conversaciones.",
        "",
        "## Participación y vínculos",
        "",
        f"- Exposiciones: {summary['exposure_count']}; respuestas: {summary['participant_count']} "
        f"({summary['participation_rate']:.1%}).",
        f"- P: media {probability['mean']:.3f}, mediana {probability['median']:.3f}, "
        f"rango [{probability['min']:.3f}, {probability['max']:.3f}], "
        f"p90 {probability['p90']:.3f}.",
        f"- R después de cada interacción: media {relationship['mean']:.3f}, "
        f"rango [{relationship['min']:.3f}, {relationship['max']:.3f}].",
        f"- Vínculos finales saturados (≤0.01 o ≥0.99): "
        f"{summary['saturated_final_relationships']}.",
        "",
        "## Red por semestre",
        "",
        "| Semestre | Aristas dirigidas | Densidad | Aislados | R media |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        weight = row["mean_relationship"]
        mean_weight = "n/a" if weight is None else f"{weight:.3f}"
        lines.append(
            f"| {row['semester']} | {row['directed_edges']} | {row['density']:.3f} "
            f"| {row['isolates']} | {mean_weight} |"
        )
    lines.extend(
        [
            "",
            "## Ejecución y alcance",
            "",
            f"- Generaciones de texto: {summary['generated_utterances']}; "
            f"llamadas API LLM: {summary['llm_api_calls']}; "
            f"aciertos de caché LLM: {summary['llm_cache_hits']}.",
            f"- Costo API LLM: {summary['llm_cost_usd']} USD "
            "(0 con lenguaje simulado; desconocido con Gemini).",
            f"- Comprobaciones de consistencia: {sum(summary['checks'].values())} de "
            f"{len(summary['checks'])} correctas; errores detectados: {len(summary['errors'])}.",
            "- Es un modelo exploratorio con agentes sintéticos; estas cifras no "
            "predicen amistades reales.",
            "",
            "Los archivos `pilot_1_summary.json`, `pilot_1_network_metrics.csv`, "
            "`pilot_1_conversations.csv`, `metrics_by_semester.json`, las tablas Parquet "
            "y los PNG guardan "
            "los datos completos de esta ejecución.",
            "",
        ]
    )
    return "\n".join(lines)


def run_pilot_1(
    *,
    output_root: str | Path = "outputs",
    run_id: str = "pilot-1-medium-seed-42",
    seed: int = 42,
    language_model: LanguageModelProvider | None = None,
    sentiment_analyzer: SentimentAnalyzer | None = None,
) -> Path:
    """Run 20 students for two simulated weeks and save auditable outcomes."""
    root = Path(__file__).resolve().parents[3]
    provider = language_model or MockLanguageModelProvider()
    analyzer = sentiment_analyzer or TransformersSentimentAnalyzer()
    events: list[ConversationEvent] = []
    destination = run_mock_mvp(
        config_path=root / "configs/homophily_medium.yaml",
        topic_path=root / "data/topics/topics_v1.yaml",
        demographic_path=root / "data/demographics/profiles_v1.yaml",
        output_root=output_root,
        run_id=run_id,
        seed=seed,
        smoke=True,
        language_model=provider,
        sentiment_analyzer=analyzer,
        event_observer=events.extend,
    )
    stored = load_run(destination)
    metrics = json.loads((destination / "metrics_by_semester.json").read_text(encoding="utf-8"))
    network_rows = _network_rows(metrics)
    exposure_records = [
        record for event in events for record in event.records[: len(event.exposed_ids)]
    ]
    probabilities = [record.participation_probability for record in exposure_records]
    if not probabilities or any(value is None for value in probabilities):
        raise RuntimeError("pilot has no recorded exposure probabilities")
    observed_probabilities = [float(value) for value in probabilities if value is not None]
    participant_count = sum(len(event.participant_ids) for event in events)
    gemini = provider if isinstance(provider, GeminiLanguageModelProvider) else None
    checks = {
        "unique_conversations": len(events) == len({event.conversation_id for event in events}),
        "expected_conversations": len(events) == 72,
        "participants_exposed": all(
            set(event.participant_ids) <= set(event.exposed_ids) for event in events
        ),
        "event_records_match": all(
            len(event.records) == len(event.exposed_ids) + len(event.participant_ids)
            and all(record.conversation_id == event.conversation_id for record in event.records)
            for event in events
        ),
        "message_directions_match": all(
            tuple(record.sender_id for record in event.records[: len(event.exposed_ids)])
            == (event.initiator_id,) * len(event.exposed_ids)
            and tuple(record.receiver_id for record in event.records[: len(event.exposed_ids)])
            == event.exposed_ids
            and tuple(record.sender_id for record in event.records[len(event.exposed_ids) :])
            == event.participant_ids
            and all(
                record.receiver_id == event.initiator_id
                for record in event.records[len(event.exposed_ids) :]
            )
            for event in events
        ),
        "timestamps_ordered": all(
            all(
                previous.timestamp_simulation <= following.timestamp_simulation
                for previous, following in zip(event.records, event.records[1:], strict=False)
            )
            for event in events
        ),
        "interaction_count_match": len(stored.interactions)
        == len(exposure_records) + participant_count,
        "probabilities_bounded": all(0 <= value <= 1 for value in observed_probabilities),
        "relationships_bounded": all(
            0 <= record.relationship_before <= 1 and 0 <= record.relationship_after <= 1
            for record in stored.interactions
        ),
        "network_has_edges": all(int(row["directed_edges"] or 0) > 0 for row in network_rows),
        "participation_not_zero": participant_count > 0,
        "participation_not_universal": participant_count < len(exposure_records),
        "network_not_complete": all(
            int(row["directed_edges"] or 0)
            < stored.config.population_size * (stored.config.population_size - 1)
            for row in network_rows
        ),
    }
    final_weights = [float(weight) for weight in stored.relationships["weight"]]
    checks["relationships_not_saturated"] = all(
        0.01 < weight < 0.99 for weight in final_weights
    )
    summary: dict[str, Any] = {
        "run_id": run_id,
        "scenario": stored.config.scenario,
        "h": stored.config.h,
        "seed": seed,
        "population_size": stored.config.population_size,
        "simulated_weeks": stored.config.semesters * stored.config.weeks_per_semester,
        "language_model": stored.metadata.model_name,
        "sentiment_model": stored.metadata.sentiment_model_name,
        "conversation_count": len(events),
        "exposure_count": len(exposure_records),
        "participant_count": participant_count,
        "participation_rate": participant_count / len(exposure_records),
        "interaction_count": len(stored.interactions),
        "participation_probability": _distribution(observed_probabilities),
        "relationship_before": _distribution(
            [record.relationship_before for record in stored.interactions]
        ),
        "relationship_after": _distribution(
            [record.relationship_after for record in stored.interactions]
        ),
        "final_relationships": _distribution(final_weights),
        "saturated_final_relationships": sum(
            weight <= 0.01 or weight >= 0.99 for weight in final_weights
        ),
        "generated_utterances": len(events) + participant_count,
        "llm_api_calls": gemini.api_calls if gemini is not None else 0,
        "llm_cache_hits": gemini.cache_hits if gemini is not None else 0,
        "llm_cost_usd": None if gemini is not None else 0,
        "network_by_semester": network_rows,
        "checks": checks,
        "errors": [name for name, passed in checks.items() if not passed],
    }
    (destination / "pilot_1_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (destination / "pilot_1_network_metrics.csv").open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.DictWriter(output, fieldnames=list(network_rows[0]))
        writer.writeheader()
        writer.writerows(network_rows)
    with (destination / "pilot_1_conversations.csv").open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "conversation_id", "semester", "week", "course_id", "section_id",
                "initiator_id", "topic_id", "exposed_ids", "participant_ids",
                "participation_probabilities",
            ],
        )
        writer.writeheader()
        for event in events:
            first = event.records[0]
            writer.writerow(
                {
                    "conversation_id": event.conversation_id,
                    "semester": first.semester,
                    "week": first.week,
                    "course_id": first.course_id,
                    "section_id": first.section_id,
                    "initiator_id": event.initiator_id,
                    "topic_id": event.topic_id,
                    "exposed_ids": json.dumps(event.exposed_ids),
                    "participant_ids": json.dumps(event.participant_ids),
                    "participation_probabilities": json.dumps(
                        [record.participation_probability
                         for record in event.records[: len(event.exposed_ids)]]
                    ),
                }
            )
    (destination / "pilot_1_report.md").write_text(
        _report(summary, network_rows), encoding="utf-8"
    )
    return destination


def main() -> None:
    """Run the offline pilot by default, with optional Gemini or mock sentiment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--run-id", default="pilot-1-medium-seed-42")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gemini", action="store_true")
    parser.add_argument("--mock-sentiment", action="store_true")
    args = parser.parse_args()
    destination = run_pilot_1(
        output_root=args.output,
        run_id=args.run_id,
        seed=args.seed,
        language_model=GeminiLanguageModelProvider(generation_seed=args.seed)
        if args.gemini
        else None,
        sentiment_analyzer=MockSentimentAnalyzer() if args.mock_sentiment else None,
    )
    print(destination)


if __name__ == "__main__":
    main()
