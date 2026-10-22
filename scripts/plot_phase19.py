"""Render local sensitivity effects from saved paired differences."""

import argparse
import csv
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

PARAMETERS = (
    "alpha_relationship", "w_interest", "beta_I", "beta_E", "beta_R",
    "w_agreement", "gamma_section",
)


def render(source: Path, output: Path) -> None:
    with source.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("paired sensitivity table is empty")
    with (source.parent / "fixed_similarity_paired_deltas.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        fixed_rows = list(csv.DictReader(stream))
    figures = (
        (
            "mean_relationship_weight", 10, "Cambio en peso medio de vínculos",
            "sensitivity_relationship.png", rows,
        ),
        ("density", 1, "Cambio en densidad", "sensitivity_density_early.png", rows),
        (
            "fixed_similarity", 1, "Cambio en similitud media con pesos base",
            "sensitivity_similarity_early.png", fixed_rows,
        ),
    )
    output.mkdir(parents=True, exist_ok=True)
    for metric, semester, label, filename, table in figures:
        figure = Figure(figsize=(13, 5), dpi=150)
        FigureCanvasAgg(figure)
        axes = figure.subplots(1, 3, sharey=True)
        for ax, h in zip(axes, (0.2, 0.5, 0.8), strict=True):
            for level, offset, color, marker in (
                ("low", -0.12, "#3579b0", "o"),
                ("high", 0.12, "#dd7b24", "s"),
            ):
                selected = {
                    row["parameter"]: row
                    for row in table
                    if float(row["h"]) == h
                    and int(row["semester"]) == semester
                    and (metric == "fixed_similarity" or row["metric"] == metric)
                    and row["level"] == level
                }
                if set(selected) != set(PARAMETERS):
                    raise ValueError(f"missing sensitivity results for h={h}, {metric}")
                values = [float(selected[name]["mean"]) for name in PARAMETERS]
                lower = [values[i] - float(selected[name]["ci_low"])
                         for i, name in enumerate(PARAMETERS)]
                upper = [float(selected[name]["ci_high"]) - values[i]
                         for i, name in enumerate(PARAMETERS)]
                positions = [index + offset for index in range(len(PARAMETERS))]
                ax.errorbar(positions, values, yerr=[lower, upper], fmt=marker,
                            color=color, capsize=2, markersize=5, label=level)
            ax.axhline(0, color="#777777", linewidth=0.8)
            ax.set_title(f"h = {h:.2f}")
            ax.set_xticks(range(len(PARAMETERS)), PARAMETERS, rotation=55, ha="right")
            ax.grid(axis="y", alpha=0.2)
        axes[0].set_ylabel(label)
        axes[-1].legend(title="Valor", frameon=False)
        figure.suptitle(
            f"Sensibilidad local · semestre {semester} · "
            "diferencia frente a la base · media e IC 95 %"
        )
        figure.tight_layout(rect=(0, 0, 1, 0.94))
        figure.savefig(output / filename)
        figure.savefig(output / filename.replace(".png", ".pdf"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=Path("outputs/phase-19-sensitivity"))
    args = parser.parse_args()
    render(args.experiment / "paired_deltas.csv", args.experiment)


if __name__ == "__main__":
    main()
