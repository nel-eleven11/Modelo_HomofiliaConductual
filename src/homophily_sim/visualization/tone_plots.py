"""Plot semester tone indicators from saved aggregate rows."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import fmean
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_tone_trends(rows: Sequence[Mapping[str, Any]], output_dir: str | Path) -> Path:
    """Show unique-message tone shares and evaluated valence by scenario."""
    destination = Path(output_dir) / "tone_trends.png"
    metrics = (
        ("negative_message_rate", "Mensajes negativos"),
        ("neutral_message_rate", "Mensajes neutrales"),
        ("positive_message_rate", "Mensajes positivos"),
        ("mean_expressed_valence", "Valencia expresada por mensaje"),
        ("mean_evaluated_valence", "Valencia por evaluación"),
    )
    fig, axes = plt.subplots(3, 2, figsize=(12, 11), sharex=True)
    for axis, (metric, label) in zip(axes.flat, metrics, strict=False):
        grouped: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            value = row.get(metric)
            if value is not None:
                grouped[str(row["scenario"])][int(row["semester"])].append(float(value))
        for scenario, semesters in sorted(grouped.items()):
            axis.plot(sorted(semesters), [fmean(semesters[key]) for key in sorted(semesters)],
                      marker="o", label=scenario)
        axis.set_title(label)
        axis.set_ylim(0, 1)
        axis.set_xlabel("Semestre")
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right")
    fig.tight_layout()
    fig.savefig(destination, dpi=150)
    plt.close(fig)
    return destination
