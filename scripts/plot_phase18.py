"""Render presentation figures from the saved Phase 18 aggregate CSV."""

import argparse
import csv
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def render(source: Path, output: Path) -> None:
    with source.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("scenario summary is empty")
    scenarios = (
        ("homophily_low", "h = 0.20", "#3579b0"),
        ("homophily_medium", "h = 0.50", "#dd7b24"),
        ("homophily_high", "h = 0.80", "#2b8c6e"),
    )
    figures = (
        ("density", "Densidad", "density_by_scenario.png"),
        ("mean_relationship_weight", "Peso medio de vínculos", "relationship_by_scenario.png"),
        ("mean_edge_similarity", "Similitud media de aristas", "similarity_by_scenario.png"),
    )
    output.mkdir(parents=True, exist_ok=True)
    for metric, label, filename in figures:
        figure = Figure(figsize=(8, 4.5), dpi=150)
        FigureCanvasAgg(figure)
        axes = figure.subplots()
        for scenario, legend, color in scenarios:
            series = sorted(
                (row for row in rows if row["scenario"] == scenario and row["metric"] == metric),
                key=lambda row: int(row["semester"]),
            )
            if not series or any(not row["ci_low"] or not row["ci_high"] for row in series):
                raise ValueError(
                    f"missing aggregate or confidence interval for {scenario}/{metric}"
                )
            semesters = [int(row["semester"]) for row in series]
            means = [float(row["mean"]) for row in series]
            low = [float(row["ci_low"]) for row in series]
            high = [float(row["ci_high"]) for row in series]
            axes.plot(semesters, means, marker="o", markersize=3, linewidth=1.8,
                      color=color, label=legend)
            axes.fill_between(semesters, low, high, color=color, alpha=0.15)
        axes.set(xlabel="Semestre", ylabel=label, xticks=list(range(1, 11)))
        axes.grid(alpha=0.2)
        axes.legend(frameon=False)
        axes.set_title(f"{label} por escenario · media e IC 95 %")
        figure.tight_layout()
        figure.savefig(output / filename)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment", type=Path, default=Path("outputs/phase-18-scenarios")
    )
    args = parser.parse_args()
    render(args.experiment / "scenario_summary.csv", args.experiment)


if __name__ == "__main__":
    main()
