"""Deterministic, headless drawings of directed network snapshots."""

from collections.abc import Mapping
from pathlib import Path

import networkx as nx  # type: ignore[import-untyped]
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from homophily_sim.network.snapshots import NetworkSnapshot


def network_layout(graph: nx.DiGraph, seed: int) -> dict[int, tuple[float, float]]:
    """Place all students using a seeded layout of the final undirected graph."""
    positions = nx.spring_layout(graph.to_undirected(), seed=seed)
    return {int(node): (float(point[0]), float(point[1])) for node, point in positions.items()}


def plot_network(
    snapshot: NetworkSnapshot,
    destination: str | Path,
    *,
    positions: Mapping[int, tuple[float, float]] | None = None,
    layout_seed: int = 42,
) -> Path:
    """Draw all directed ties and color nodes by synthetic sex category."""
    graph = snapshot.graph
    layout = dict(positions) if positions is not None else network_layout(graph, layout_seed)
    if set(layout) != set(graph.nodes):
        raise ValueError("layout must contain exactly the snapshot's students")
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure = Figure(figsize=(9, 7), dpi=150)
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    axes.set_facecolor("#f8fafc")
    if graph.number_of_edges():
        nx.draw_networkx_edges(
            graph,
            layout,
            ax=axes,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=7,
            node_size=100,
            width=0.6,
            alpha=min(0.13, max(0.025, 25 / graph.number_of_edges())),
            edge_color="#334155",
            connectionstyle="arc3,rad=0.08",
        )
    palette = {
        "FEMALE": ("Mujer", "#d65a75"),
        "MALE": ("Hombre", "#397da5"),
    }
    for category, (label, color) in palette.items():
        members = [node for node in graph if graph.nodes[node].get("sex") == category]
        if members:
            nx.draw_networkx_nodes(
                graph,
                layout,
                nodelist=members,
                node_size=95,
                node_color=color,
                linewidths=0.4,
                edgecolors="#ffffff",
                ax=axes,
                label=label,
            )
    axes.legend(title="Sexo sintético", loc="upper right", frameon=False)
    axes.set_title(f"Red dirigida · semestre {snapshot.semester:02d} · {snapshot.kind}")
    axes.set_axis_off()
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    return output
