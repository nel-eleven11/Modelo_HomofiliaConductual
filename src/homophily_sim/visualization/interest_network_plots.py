"""Figures for interest mixing and filtered semester networks."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def plot_interest_heatmap(
    rows: Sequence[Mapping[str, Any]], categories: Sequence[str], destination: Path,
    *, title: str,
) -> Path:
    """Show weighted exposure, response, and conditional response rate."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    index = {category: position for position, category in enumerate(categories)}
    exposures = np.zeros((len(categories), len(categories)))
    responses = np.zeros_like(exposures)
    rates = np.full_like(exposures, np.nan)
    for row in rows:
        source = index[str(row["initiator_interest_category"])]
        target = index[str(row["exposed_interest_category"])]
        exposures[source, target] = float(row["weighted_exposure_count"])
        responses[source, target] = float(row["weighted_response_count"])
        rates[source, target] = float(row["response_rate_given_exposure"])
    figure = Figure(figsize=(20, 7), dpi=140)
    FigureCanvasAgg(figure)
    axes = figure.subplots(1, 3)
    for axis, values, label, maximum in zip(
        axes,
        (exposures, responses, rates),
        ("Exposiciones ponderadas", "Respuestas ponderadas", "Respuestas / exposición"),
        (None, None, 1.0),
        strict=True,
    ):
        image = axis.imshow(values, cmap="viridis", vmin=0, vmax=maximum)
        axis.set(title=label, xlabel="Interés del estudiante expuesto")
        axis.set_xticks(range(len(categories)), categories, rotation=90, fontsize=7)
        axis.set_yticks(range(len(categories)), categories, fontsize=7)
        figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axes[0].set_ylabel("Interés del iniciador")
    figure.suptitle(title)
    figure.tight_layout()
    figure.savefig(destination)
    return destination


def plot_strong_network(
    graph: nx.DiGraph, positions: Mapping[Any, Any], threshold: float,
    destination: Path, *, scenario: str, semester: int,
) -> Path:
    """Draw strong one-way ties and highlight reciprocal strong pairs."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    strong = {
        (source, target) for source, target, attrs in graph.edges(data=True)
        if float(attrs["weight"]) >= threshold
    }
    mutual = sorted({
        tuple(sorted((source, target)))
        for source, target in strong if (target, source) in strong
    })
    one_way = sorted((source, target) for source, target in strong
                     if (target, source) not in strong)
    figure = Figure(figsize=(9, 7), dpi=140)
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    nx.draw_networkx_nodes(graph, positions, ax=axis, node_size=38, node_color="#355c7d")
    if one_way:
        nx.draw_networkx_edges(graph, positions, edgelist=one_way, ax=axis,
                               arrows=False, width=0.65, alpha=0.27,
                               edge_color="#778899")
    if mutual:
        nx.draw_networkx_edges(graph, positions, edgelist=mutual, ax=axis,
                               arrows=False, width=1.25, alpha=0.75,
                               edge_color="#e66b37")
    axis.set_title(
        f"{scenario} · semestre {semester:02d} · R ≥ {threshold:.2f}\n"
        f"{len(strong)} vínculos dirigidos fuertes · {len(mutual)} pares recíprocos"
    )
    axis.set_axis_off()
    figure.tight_layout()
    figure.savefig(destination)
    return destination


def plot_strong_trajectories(
    rows: Sequence[Mapping[str, Any]], destination: Path,
) -> Path:
    """Compare semester means of strong directed and reciprocal densities."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure = Figure(figsize=(10, 5), dpi=150)
    FigureCanvasAgg(figure)
    axes = figure.subplots(1, 2)
    targets = (
        ("strong_directed_density", "Densidad de vínculos fuertes dirigidos"),
        ("mutual_strong_pair_density", "Densidad de pares fuertes recíprocos"),
    )
    for axis, (metric, label) in zip(axes, targets, strict=True):
        for scenario in sorted({str(row["scenario"]) for row in rows}):
            series = sorted(
                (row for row in rows
                 if row["scenario"] == scenario and row["metric"] == metric),
                key=lambda row: int(row["semester"]),
            )
            if series:
                axis.plot([int(row["semester"]) for row in series],
                          [float(row["mean"]) for row in series], marker="o",
                          markersize=3, label=scenario)
        axis.set(xlabel="Semestre", ylabel=label, xticks=range(1, 11))
        axis.grid(alpha=0.2)
    axes[1].legend(frameon=False, fontsize=8)
    figure.tight_layout()
    figure.savefig(destination)
    return destination
