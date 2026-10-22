"""Build thesis tables and figures from the saved Phase 18/19 experiments."""

import argparse
import csv
import json
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import networkx as nx  # type: ignore[import-untyped]
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from plot_phase19 import render as render_sensitivity

from homophily_sim.analysis.thesis import (
    SCENARIOS,
    build_semester_graph,
    select_strongest_edges,
    validate_scenario_rows,
)

SCENARIO_STYLE = {
    "homophily_low": ("h = 0.20", "#3579b0"),
    "homophily_medium": ("h = 0.50", "#dd7b24"),
    "homophily_high": ("h = 0.80", "#2b8c6e"),
}
METRIC_LABELS = {
    "sex_assortativity": "Asortatividad por sexo",
    "origin_assortativity": "Asortatividad por procedencia",
    "mean_edge_similarity": "Similitud media de aristas",
    "modularity": "Modularidad",
    "mean_relationship_weight": "Peso medio de vínculos",
    "community_count": "Número de comunidades",
    "largest_community_size": "Comunidad más grande",
    "isolate_count": "Agentes aislados",
    "reciprocity": "Reciprocidad",
    "density": "Densidad",
}


def _save(figure: Figure, destination: Path) -> None:
    figure.tight_layout()
    figure.savefig(destination.with_suffix(".png"), dpi=180)
    figure.savefig(destination.with_suffix(".pdf"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path.name}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _metric_series(
    rows: list[dict[str, str]], scenario: str, metric: str,
) -> list[dict[str, str]]:
    selected = sorted(
        (row for row in rows if row["scenario"] == scenario and row["metric"] == metric),
        key=lambda row: int(row["semester"]),
    )
    if len(selected) != 10 or any(row["n"] != "30" for row in selected):
        raise ValueError(f"incomplete 30-seed trajectory: {scenario}/{metric}")
    return selected


def _draw_metric(ax: object, rows: list[dict[str, str]], metric: str) -> None:
    for scenario in SCENARIOS:
        legend, color = SCENARIO_STYLE[scenario]
        series = _metric_series(rows, scenario, metric)
        x = [int(row["semester"]) for row in series]
        mean = [float(row["mean"]) for row in series]
        low = [float(row["ci_low"]) for row in series]
        high = [float(row["ci_high"]) for row in series]
        ax.plot(x, mean, marker="o", markersize=2.8, color=color, label=legend)
        ax.fill_between(x, low, high, color=color, alpha=0.14)
    ax.set(xlabel="Semestre", ylabel=METRIC_LABELS[metric], xticks=range(1, 11))
    ax.grid(alpha=0.2)


def _trajectory_figures(rows: list[dict[str, str]], destination: Path) -> None:
    figures = {
        "assortativity": ("sex_assortativity", "origin_assortativity"),
        "modularity": ("modularity",),
        "density": ("density",),
        "relationship_weight": ("mean_relationship_weight",),
        "communities": ("community_count", "largest_community_size"),
        "edge_similarity": ("mean_edge_similarity",),
    }
    for name, metrics in figures.items():
        figure = Figure(figsize=(11 if len(metrics) == 2 else 7, 4.5), dpi=180)
        FigureCanvasAgg(figure)
        axes = figure.subplots(1, len(metrics), squeeze=False)[0]
        for ax, metric in zip(axes, metrics, strict=True):
            _draw_metric(ax, rows, metric)
            ax.set_title(METRIC_LABELS[metric])
        axes[-1].legend(frameon=False, fontsize=8)
        _save(figure, destination / name)


def _table_artifacts(
    scenario_root: Path, sensitivity_root: Path, probe_path: Path, destination: Path,
) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    run_rows = _read_csv(scenario_root / "run_metrics.csv")
    seeds, semesters = validate_scenario_rows(run_rows)
    if (seeds, semesters) != (30, 10):
        raise ValueError("Phase 21 requires the completed 30-seed, 10-semester experiment")
    plan = json.loads((scenario_root / "experiment_plan.json").read_text(encoding="utf-8"))
    if plan["smoke"] or plan["seeds"] != list(range(1, 31)):
        raise ValueError("scenario plan is not the expected full paired experiment")
    configs = plan["configs"]
    base = configs["homophily_medium"]
    if set(configs) != set(SCENARIOS):
        raise ValueError("missing scenario configuration")
    for scenario in SCENARIOS:
        differing = {key for key in base if configs[scenario][key] != base[key]}
        if differing - {"h", "scenario"}:
            raise ValueError(f"unexpected scenario parameter changes: {scenario}")
    sensitivity_plan = json.loads(
        (sensitivity_root / "sensitivity_plan.json").read_text(encoding="utf-8")
    )
    if sensitivity_plan["smoke"] or sensitivity_plan["seeds"] != list(range(1, 6)):
        raise ValueError("sensitivity plan is not the expected full paired experiment")
    for scenario in SCENARIOS:
        if sensitivity_plan["conditions"][scenario]["baseline"] != configs[scenario]:
            raise ValueError(f"sensitivity baseline differs from Phase 18: {scenario}")
    _write_csv(
        destination / "configuration_base.csv",
        [{"parameter": key, "value": json.dumps(value, ensure_ascii=False)}
         for key, value in base.items()],
    )
    _write_csv(
        destination / "scenario_parameters.csv",
        [{key: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
          for key, value in configs[scenario].items()} for scenario in SCENARIOS],
    )
    summary = _read_csv(scenario_root / "scenario_summary.csv")
    final = {
        (row["metric"], row["scenario"]): row for row in summary
        if int(row["semester"]) == 10
    }
    _write_csv(
        destination / "final_metrics.csv",
        [
            {
                "metric": metric, "label": label, "semester": 10,
                **{
                    f"{scenario}_{field}": final[metric, scenario][field]
                    for scenario in SCENARIOS for field in ("n", "mean", "ci_low", "ci_high")
                },
            }
            for metric, label in METRIC_LABELS.items()
        ],
    )
    sensitivity = _read_csv(sensitivity_root / "paired_deltas.csv")
    fixed = _read_csv(sensitivity_root / "fixed_similarity_paired_deltas.csv")
    targets = (("density", 1), ("modularity", 1), ("community_count", 1),
               ("mean_relationship_weight", 10))
    selected = [
        {"h": row["h"], "parameter": row["parameter"], "level": row["level"],
         "value": row["value"], "semester": int(row["semester"]),
         "metric": row["metric"], "n": row["n"], "mean_delta": row["mean"],
         "ci_low": row["ci_low"], "ci_high": row["ci_high"]}
        for row in sensitivity
        if (row["metric"], int(row["semester"])) in targets
    ]
    selected.extend(
        {"h": row["h"], "parameter": row["parameter"], "level": row["level"],
         "value": row["value"], "semester": int(row["semester"]),
         "metric": "fixed_mean_edge_similarity", "n": row["n"],
         "mean_delta": row["mean"], "ci_low": row["ci_low"], "ci_high": row["ci_high"]}
        for row in fixed if int(row["semester"]) in (1, 10)
    )
    if len(selected) != 3 * 14 * 6 or any(row["n"] != "5" for row in selected):
        raise ValueError("incomplete five-seed sensitivity comparison")
    _write_csv(destination / "sensitivity.csv", selected)
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    usage: list[dict[str, object]] = [
        {"source": "Phase 18: 90 full mock runs", "model": "mock", "requests": 0,
         "prompt_tokens": 0, "output_tokens": 0, "cost_usd": "0",
         "cost_status": "No API calls"},
        {"source": "Pilot 2: independent Gemini sample", "model": probe["model"],
         "requests": probe["api_requests"], "prompt_tokens": probe["tokens"]["prompt"],
         "output_tokens": probe["tokens"]["output"], "cost_usd": "",
         "cost_status": "Not recorded; no billed amount inferred"},
    ]
    _write_csv(destination / "llm_usage.csv", usage)
    _write_csv(
        destination / "validation_status.csv",
        [{"phase": 20, "status": "pending", "note": "Internal validation deferred by user"}],
    )
    return summary, usage


def _read_network_run(root: Path, scenario: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    directory = root / "runs" / f"phase18-{scenario}-seed-001"
    agents = pd.read_parquet(directory / "agents.parquet", columns=["id", "sex"])
    interactions = pd.read_parquet(
        directory / "interactions.parquet",
        columns=["semester", "receiver_id", "sender_id", "relationship_after"],
    )
    relationships = pd.read_parquet(directory / "relationships.parquet")
    return agents, interactions, relationships


def _draw_network(ax: object, graph: nx.DiGraph, positions: dict[int, object]) -> None:
    shown = select_strongest_edges(graph, per_observer=3)
    nx.draw_networkx_edges(
        shown, positions, ax=ax, arrows=True, arrowsize=6, node_size=48,
        width=0.55, alpha=0.20, edge_color="#425466",
    )
    for sex, color in (("FEMALE", "#d65a75"), ("MALE", "#397da5")):
        members = [node for node, data in graph.nodes(data=True) if data["sex"] == sex]
        nx.draw_networkx_nodes(
            graph, positions, nodelist=members, ax=ax, node_color=color,
            node_size=34, linewidths=0.2, edgecolors="white",
        )
    ax.set_axis_off()


def _network_figures(root: Path, destination: Path) -> None:
    graphs: dict[tuple[str, int], nx.DiGraph] = {}
    for scenario in SCENARIOS:
        agents, interactions, relationships = _read_network_run(root, scenario)
        ids = [int(value) for value in agents["id"]]
        for semester in ((1, 5, 10) if scenario == "homophily_medium" else (10,)):
            graph = build_semester_graph(interactions, ids, semester=semester)
            nx.set_node_attributes(
                graph, dict(zip(ids, agents["sex"], strict=True)), "sex"
            )
            graphs[scenario, semester] = graph
        final = graphs[scenario, 10]
        actual = {(int(row.observer_id), int(row.other_id)): float(row.weight)
                  for row in relationships.itertuples(index=False)}
        restored = {(int(i), int(j)): float(data["weight"])
                    for i, j, data in final.edges(data=True)}
        if actual != restored:
            raise ValueError(f"reconstructed final network differs from {scenario} saved state")
    anchor = select_strongest_edges(graphs["homophily_medium", 10])
    positions = nx.spring_layout(anchor.to_undirected(), seed=42)
    for filename, keys in (
        ("network_evolution", [("homophily_medium", semester) for semester in (1, 5, 10)]),
        ("network_final_scenarios", [(scenario, 10) for scenario in SCENARIOS]),
    ):
        figure = Figure(figsize=(14, 5), dpi=180)
        FigureCanvasAgg(figure)
        axes = figure.subplots(1, 3)
        for ax, key in zip(axes, keys, strict=True):
            graph = graphs[key]
            _draw_network(ax, graph, positions)
            ax.set_title(
                f"{SCENARIO_STYLE[key[0]][0]} · semestre {key[1]}\n"
                f"Red completa: {graph.number_of_edges():,} aristas · "
                f"densidad {nx.density(graph):.4f}"
            )
        figure.suptitle("Muestra visual: hasta 3 vínculos dirigidos más fuertes por agente")
        figure.legend(
            handles=[Patch(color="#d65a75", label="Mujer"),
                     Patch(color="#397da5", label="Hombre")],
            loc="lower center", ncol=2, frameon=False,
        )
        _save(figure, destination / filename)


def _relationship_distribution(root: Path, destination: Path) -> None:
    figure = Figure(figsize=(8, 4.5), dpi=180)
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    table: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        weights: list[float] = []
        for seed in range(1, 31):
            path = root / "runs" / f"phase18-{scenario}-seed-{seed:03d}" / "relationships.parquet"
            weights.extend(pd.read_parquet(path, columns=["weight"])["weight"].tolist())
        legend, color = SCENARIO_STYLE[scenario]
        counts, boundaries = np.histogram(weights, bins=40, range=(0, 1))
        table.extend(
            {"scenario": scenario, "bin_low": float(boundaries[index]),
             "bin_high": float(boundaries[index + 1]),
             "edge_count": int(count), "fraction": float(count / len(weights))}
            for index, count in enumerate(counts)
        )
        ax.hist(
            weights, bins=40, range=(0, 1), density=True, histtype="step",
            linewidth=1.8, color=color, label=f"{legend} (n={len(weights):,})",
        )
    ax.set(xlabel="Peso dirigido Rᵢⱼ al semestre 10", ylabel="Densidad de aristas")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=0.2)
    _save(figure, destination / "relationship_distribution")
    _write_csv(destination / "relationship_weight_bins.csv", table)


def _llm_figure(usage: list[dict[str, object]], destination: Path) -> None:
    figure = Figure(figsize=(8, 4.5), dpi=180)
    FigureCanvasAgg(figure)
    axes = figure.subplots(1, 2)
    axes[0].bar(["90 corridas mock", "Muestra Gemini"],
                [int(row["requests"]) for row in usage], color=["#3579b0", "#dd7b24"])
    axes[0].set_ylabel("Solicitudes lógicas al SDK")
    sample = usage[1]
    axes[1].bar(["Entrada", "Salida"],
                [int(sample["prompt_tokens"]), int(sample["output_tokens"])],
                color=["#3579b0", "#dd7b24"])
    axes[1].set_ylabel("Tokens informados: muestra Gemini")
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
    _save(figure, destination / "llm_usage")


def generate(scenario_root: Path, sensitivity_root: Path, probe: Path, output: Path) -> Path:
    """Create checked thesis tables, vector/raster figures, and a source manifest."""
    output.mkdir(parents=True, exist_ok=True)
    summary, usage = _table_artifacts(scenario_root, sensitivity_root, probe, output)
    _trajectory_figures(summary, output)
    _network_figures(scenario_root, output)
    _relationship_distribution(scenario_root, output)
    _llm_figure(usage, output)
    render_sensitivity(sensitivity_root / "paired_deltas.csv", output)
    sources = [
        scenario_root / "experiment_plan.json", scenario_root / "run_metrics.csv",
        scenario_root / "scenario_summary.csv", sensitivity_root / "sensitivity_plan.json",
        sensitivity_root / "paired_deltas.csv",
        sensitivity_root / "fixed_similarity_paired_deltas.csv", probe,
        Path(__file__), Path(__file__).with_name("plot_phase19.py"),
        Path(__file__).resolve().parents[1] / "src/homophily_sim/analysis/thesis.py",
    ]
    sources.extend(
        scenario_root / "runs" / f"phase18-{scenario}-seed-{seed:03d}" /
        "relationships.parquet"
        for scenario in SCENARIOS for seed in range(1, 31)
    )
    sources.extend(
        scenario_root / "runs" / f"phase18-{scenario}-seed-001" / name
        for scenario in SCENARIOS for name in ("agents.parquet", "interactions.parquet")
    )
    repository = Path(__file__).resolve().parents[1]

    def source_name(path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(repository).as_posix()
        except ValueError:
            return str(resolved)

    manifest = {
        "phase": 21, "scenario_replicates_per_h": 30,
        "sensitivity_replicates_per_condition": 5,
        "representative_network_seed": 1, "display_edges_per_observer": 3,
        "network_metrics_use_all_edges": True,
        "validation_phase_20": "pending per user instruction",
        "llm_cost": "Gemini sample billed amount not recorded; full mock experiment used no API",
        "sources_sha256": {
            source_name(path): sha256(path.read_bytes()).hexdigest() for path in sources
        },
        "artifacts": sorted(path.name for path in output.iterdir() if path.is_file()),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    archive = output.with_suffix(".zip")
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(output.iterdir()):
            if path.is_file():
                bundle.write(path, path.name)
        report = Path(__file__).resolve().parents[1] / "docs/experiments/phase_21_thesis.md"
        if report.exists():
            bundle.write(report, "phase_21_thesis.md")
    with ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("thesis archive failed integrity check")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=Path, default=Path("outputs/phase-18-scenarios"))
    parser.add_argument("--sensitivity", type=Path, default=Path("outputs/phase-19-sensitivity"))
    parser.add_argument(
        "--probe", type=Path,
        default=Path("outputs/pilot-2-medium-seed-42-final/gemini_probe.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/phase-21-thesis"))
    args = parser.parse_args()
    print(generate(args.scenarios, args.sensitivity, args.probe, args.output))


if __name__ == "__main__":
    main()
