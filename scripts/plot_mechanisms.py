"""Draw mechanism trajectories and selected saved network snapshots."""

import argparse
import csv
from pathlib import Path

import networkx as nx  # type: ignore[import-untyped]
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

SCENARIOS = (
    ("homophily_low", "h = 0.20", "#3579b0"),
    ("homophily_medium", "h = 0.50", "#dd7b24"),
    ("homophily_high", "h = 0.80", "#2b8c6e"),
)
TRAJECTORIES = (
    ("participation_rate", "Tasa de respuesta"),
    ("mean_responding_pair_similarity", "Similitud de quienes responden"),
    ("mean_responding_previous_relationship", "Vínculo previo de quienes responden"),
    ("repeated_unordered_response_rate", "Respuestas repetidas entre pares"),
    ("strengthened_evaluation_updates", "Evaluaciones que fortalecen vínculos"),
    ("weakened_evaluation_updates", "Evaluaciones que debilitan vínculos"),
    ("evaluation_activity_persistence_rate", "Persistencia de evaluaciones activas"),
    ("strong_relationship_persistence_rate", "Permanencia de vínculos fuertes"),
    ("between_community_response_rate", "Respuestas entre comunidades"),
)


def render_trajectories(summary_csv: Path, output: Path) -> list[Path]:
    """Render scenario means and available 95% intervals from saved aggregates."""
    with summary_csv.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    output.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for metric, label in TRAJECTORIES:
        figure = Figure(figsize=(8, 4.5), dpi=150)
        FigureCanvasAgg(figure)
        axes = figure.subplots()
        plotted = False
        for scenario, legend, color in SCENARIOS:
            series = sorted(
                (row for row in rows if row["scenario"] == scenario
                 and row["metric"] == metric and row["mean"]),
                key=lambda row: int(row["semester"]),
            )
            if not series:
                continue
            plotted = True
            semesters = [int(row["semester"]) for row in series]
            means = [float(row["mean"]) for row in series]
            axes.plot(semesters, means, marker="o", markersize=3,
                      linewidth=1.8, color=color, label=legend)
            bounded = [row for row in series if row["ci_low"] and row["ci_high"]]
            if bounded:
                axes.fill_between(
                    [int(row["semester"]) for row in bounded],
                    [float(row["ci_low"]) for row in bounded],
                    [float(row["ci_high"]) for row in bounded],
                    color=color, alpha=0.15,
                )
        axes.set(xlabel="Semestre", ylabel=label, xticks=list(range(1, 11)))
        axes.grid(alpha=0.2)
        if plotted:
            axes.legend(frameon=False)
        else:
            axes.text(0.5, 0.5, "Sin datos definidos", ha="center", va="center",
                      transform=axes.transAxes)
        axes.set_title(f"{label} por escenario")
        figure.tight_layout()
        destination = output / f"{metric}.png"
        figure.savefig(destination)
        created.append(destination)
    return created


def render_network_snapshots(
    experiment: Path, output: Path, *, seed: int = 1,
    semesters: tuple[int, ...] = (1, 5, 10), kind: str = "evaluation",
) -> list[Path]:
    """Render saved GraphML networks for selected scenarios and semesters."""
    if kind not in {"evaluation", "active_response"}:
        raise ValueError("kind must be evaluation or active_response")
    output.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for scenario, legend, _ in SCENARIOS:
        run_id = f"phase18-{scenario}-seed-{seed:03d}"
        for semester in semesters:
            source = (experiment / "runs" / run_id / "network_snapshots" /
                      kind / f"semester_{semester:02d}.graphml")
            if not source.exists():
                continue
            graph = nx.read_graphml(source)
            figure = Figure(figsize=(7, 6), dpi=150)
            FigureCanvasAgg(figure)
            axes = figure.subplots()
            positions = nx.spring_layout(graph, seed=seed, weight=None)
            colors = [int(graph.nodes[node]["community_id"]) for node in graph.nodes]
            nx.draw_networkx_nodes(
                graph, positions, ax=axes, node_color=colors, cmap="tab20", node_size=35
            )
            nx.draw_networkx_edges(
                graph, positions, ax=axes, arrows=False, width=0.45, alpha=0.10
            )
            axes.set_title(f"{legend} · semestre {semester} · {kind}")
            axes.set_axis_off()
            figure.tight_layout()
            destination = output / f"{scenario}_{kind}_semester_{semester:02d}.png"
            figure.savefig(destination)
            created.append(destination)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=Path("outputs/phase-18-scenarios"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--networks", action="store_true")
    parser.add_argument("--network-kind", choices=("evaluation", "active_response"),
                        default="evaluation")
    args = parser.parse_args()
    output = args.output or args.experiment / "mechanism_figures"
    render_trajectories(args.experiment / "scenario_summary.csv", output)
    if args.networks:
        render_network_snapshots(
            args.experiment, output, seed=args.seed, kind=args.network_kind
        )


if __name__ == "__main__":
    main()
