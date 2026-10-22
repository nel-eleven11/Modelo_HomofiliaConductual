"""Full-cohort, one-semester pilot and a separate small Gemini probe."""

import argparse
import csv
import json
import resource
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any

from homophily_sim.config import load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.io.metadata import make_run_metadata
from homophily_sim.io.results import load_run, save_run
from homophily_sim.llm.base import UtteranceRequest
from homophily_sim.llm.cache import SqliteUtteranceCache
from homophily_sim.llm.gemini import GeminiLanguageModelProvider
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.llm.prompts import PROMPT_VERSION
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel
from homophily_sim.visualization.metric_plots import plot_relationship_distribution
from homophily_sim.visualization.network_plots import plot_network


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _peak_rss_mb() -> float:
    """Peak resident set size on Linux, including imported libraries."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _report(summary: dict[str, Any]) -> str:
    network = summary["network"]
    probe = summary.get("gemini_probe")
    lines = [
        "# Piloto 2 — cohorte completa, un semestre",
        "",
        f"Ejecución: `{summary['run_id']}`; semilla {summary['seed']}; "
        f"homofilia {summary['h']:.2f}.",
        f"{summary['population_size']} agentes; {summary['completed_semesters']} semestre; "
        f"{summary['completed_weeks']} semanas.",
        "",
        "| Indicador | Resultado |",
        "| --- | ---: |",
        f"| Tiempo de simulación | {summary['simulation_seconds']:.2f} s |",
        f"| Memoria máxima residente del proceso | {summary['peak_rss_mb']:.1f} MiB |",
        f"| Conversaciones | {summary['conversation_count']} |",
        f"| Exposiciones | {summary['exposure_count']} |",
        f"| Respuestas | {summary['participant_count']} |",
        f"| Tasa de participación | {summary['participation_rate']:.2%} |",
        f"| Interacciones dirigidas | {summary['interaction_count']} |",
        f"| Aristas dirigidas | {summary['directed_edges']} |",
        f"| Densidad | {network['density']:.4f} |",
        f"| Reciprocidad | {network['reciprocity']:.4f} |",
        f"| Aislados | {len(network['isolates'])} |",
        f"| Modularidad | {network['modularity']:.4f} |",
        f"| Similitud media de aristas | {network['mean_edge_similarity']:.4f} |",
        f"| Peso medio de vínculos | {summary['mean_relationship_weight']:.4f} |",
        "",
        "La simulación usó lenguaje y sentimiento simulados: 0 llamadas API. "
        "La configuración conserva el horizonte de 10 semestres, pero esta corrida "
        "se detuvo al finalizar el primero. La memoria indicada es el pico RSS del "
        "proceso en Linux, no la memoria exclusiva del modelo.",
    ]
    if probe is not None:
        tokens = probe["tokens"]
        total = "no disponible" if tokens["total"] is None else str(tokens["total"])
        lines.extend(
            [
                "",
                "## Muestra de Gemini separada",
                "",
                f"Modelo `{probe['model']}`; {probe['selected_requests']} mensajes distintos; "
                f"{probe['api_requests']} solicitudes API; {probe['cache_hits']} aciertos "
                f"de caché ({probe['cache_hit_rate']:.1%}); {probe['elapsed_seconds']:.2f} s.",
                f"Tokens totales informados por API: {total}.",
                "Esta muestra usa agentes y temas de la corrida guardada. Sus textos "
                "no alteraron las interacciones ni las métricas de red.",
            ]
        )
    lines.extend(
        [
            "",
            "Los datos completos están en los Parquet, `pilot_2_summary.json`, "
            "`weekly_metrics.csv`, `network_metrics.json` y `network_semester_01.png`.",
            "Es un modelo exploratorio sintético; no predice amistades reales.",
            "",
        ]
    )
    return "\n".join(lines)


def _save_report(destination: Path, summary: dict[str, Any]) -> None:
    _write_json(destination / "pilot_2_summary.json", summary)
    (destination / "pilot_2_report.md").write_text(_report(summary), encoding="utf-8")


def run_pilot_2(
    *, output_root: str | Path = "outputs", run_id: str = "pilot-2-medium-seed-42",
    seed: int = 42,
) -> Path:
    """Simulate the configured 80 students for all 20 weeks of semester one."""
    root = Path(__file__).resolve().parents[3]
    config = load_config(root / "configs/homophily_medium.yaml")
    if config.population_size != 80 or config.weeks_per_semester != 20:
        raise ValueError("pilot 2 requires 80 agents and 20 weeks per semester")
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )
    started = datetime.now(UTC)
    start_clock = perf_counter()
    model = HomophilyModel(
        config, bank, profile, run_seed=seed, run_id=run_id,
        language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    weekly_rows: list[dict[str, int | float]] = []
    exposure_count = participant_count = 0
    for week in range(1, config.weeks_per_semester + 1):
        model.step()
        events = model.last_events
        exposures = sum(len(event.exposed_ids) for event in events)
        participants = sum(len(event.participant_ids) for event in events)
        exposure_count += exposures
        participant_count += participants
        weekly_rows.append(
            {
                "semester": 1, "week": week, "conversations": len(events),
                "exposures": exposures, "participants": participants,
                "interactions": sum(len(event.records) for event in events),
                "cumulative_interactions": len(model.interactions),
                "participation_rate": participants / exposures,
            }
        )
    simulation_seconds = perf_counter() - start_clock
    peak_rss_mb = _peak_rss_mb()
    if len(model.snapshots) != 1 or len(model.metric_history) != 1:
        raise RuntimeError("pilot 2 must end with exactly one semester snapshot")
    if model.conversation_count != config.weeks_per_semester * 36:
        raise RuntimeError("unexpected conversation count for the full cohort")
    if len(model.interactions) != exposure_count + participant_count:
        raise RuntimeError("interaction records differ from exposure and response counts")
    students = model.students
    if len(students) != 80:
        raise RuntimeError("pilot 2 lost students")
    metadata = make_run_metadata(
        config, run_id=run_id, seed=seed, prompt_version="mock-v1",
        topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name="mock", sentiment_model_name="mock",
        start_time=started, end_time=datetime.now(UTC),
    )
    destination = save_run(
        output_root, config=config, agents=students,
        interactions=model.interactions, metadata=metadata,
    )
    with (destination / "weekly_metrics.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(weekly_rows[0]))
        writer.writeheader()
        writer.writerows(weekly_rows)
    metrics = asdict(model.metric_history[0][1])
    _write_json(destination / "network_metrics.json", {"semester": 1, **metrics})
    snapshot = model.snapshots[0]
    plot_network(snapshot, destination / "network_semester_01.png", layout_seed=seed)
    plot_relationship_distribution(
        model.metric_history[0][1], destination / "relationship_distribution.png"
    )
    weights = metrics["relationship_weights"]
    summary = {
        "run_id": run_id, "seed": seed, "scenario": config.scenario, "h": config.h,
        "population_size": len(students), "configured_semesters": config.semesters,
        "completed_semesters": 1, "completed_weeks": config.weeks_per_semester,
        "simulation_seconds": simulation_seconds, "peak_rss_mb": peak_rss_mb,
        "conversation_count": model.conversation_count,
        "exposure_count": exposure_count, "participant_count": participant_count,
        "participation_rate": participant_count / exposure_count,
        "interaction_count": len(model.interactions),
        "directed_edges": snapshot.graph.number_of_edges(),
        "mean_relationship_weight": fmean(weights) if weights else None,
        "network": metrics, "api_requests": 0, "cache_hits": 0,
        "token_usage": None, "language_model": "mock", "sentiment_model": "mock",
    }
    _save_report(destination, summary)
    return destination


def probe_gemini(destination: str | Path, *, count: int = 5) -> dict[str, Any]:
    """Generate a small independent text sample from saved pilot agents."""
    if count < 1:
        raise ValueError("count must be positive")
    directory = Path(destination)
    stored = load_run(directory)
    root = Path(__file__).resolve().parents[3]
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    selected = stored.agents[:count]
    if len(selected) != count:
        raise ValueError("count exceeds saved cohort size")
    provider = GeminiLanguageModelProvider(
        cache=SqliteUtteranceCache(directory / "gemini_probe_cache.sqlite3"),
        generation_seed=stored.metadata.seed,
    )
    requests = []
    for index, student in enumerate(selected):
        topic = bank.topics[index % len(bank.topics)]
        requests.append(
            UtteranceRequest(
                agent_id=student.id, topic_id=topic.topic_id, topic_prompt=topic.prompt,
                orientation=student.topic_orientations[topic.topic_id],
                relevant_interests=tuple(sorted(student.interests & (
                    {topic.category, topic.subcategory}
                    | set(bank.related_categories[topic.category])
                ))),
                extraversion=student.extraversion,
                max_words=stored.config.utterance_max_words,
            )
        )
    start_clock = perf_counter()
    messages = [provider.generate_utterance(request) for request in requests]
    for request in requests:
        provider.generate_utterance(request)
    elapsed = perf_counter() - start_clock
    attempts = provider.api_calls + provider.cache_hits
    probe = {
        "model": provider.model_name, "prompt_version": PROMPT_VERSION,
        "selected_requests": count, "api_requests": provider.api_calls,
        "cache_hits": provider.cache_hits,
        "cache_hit_rate": provider.cache_hits / attempts,
        "elapsed_seconds": elapsed, "peak_rss_mb": _peak_rss_mb(),
        "tokens": {
            "prompt": provider.prompt_tokens if provider.responses_with_usage else None,
            "output": provider.output_tokens if provider.responses_with_usage else None,
            "total": provider.total_tokens if provider.responses_with_usage else None,
            "responses_with_usage": provider.responses_with_usage,
        },
        "samples": [
            {"agent_id": request.agent_id, "topic_id": request.topic_id,
             "orientation": request.orientation, "text": result.text}
            for request, result in zip(requests, messages, strict=True)
        ],
    }
    _write_json(directory / "gemini_probe.json", probe)
    summary_path = directory / "pilot_2_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["gemini_probe"] = probe
    _save_report(directory, summary)
    return probe


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--run-id", default="pilot-2-medium-seed-42")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--probe-gemini", type=Path,
                        help="Probe Gemini using an existing saved pilot directory")
    parser.add_argument("--gemini-count", type=int, default=5)
    args = parser.parse_args()
    if args.probe_gemini is not None:
        probe_gemini(args.probe_gemini, count=args.gemini_count)
        print(args.probe_gemini)
    else:
        print(run_pilot_2(output_root=args.output, run_id=args.run_id, seed=args.seed))


if __name__ == "__main__":
    main()
