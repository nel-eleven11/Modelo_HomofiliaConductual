"""Network visualization utilities for the behavioral homophily MVP."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx


def visualizar_red(
    grafo: nx.Graph,
    ruta_salida: str | Path = "outputs/network_final.png",
) -> Path:
    """Generate and save a PNG visualization of the final interaction network."""
    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 7))
    posiciones = nx.spring_layout(grafo, seed=42)
    etiquetas = {
        nodo: datos.get("nombre", str(nodo))
        for nodo, datos in grafo.nodes(data=True)
    }
    pesos = [datos.get("peso", 1) for _, _, datos in grafo.edges(data=True)]
    grosores = [1 + peso * 0.8 for peso in pesos]

    nx.draw_networkx_nodes(
        grafo,
        posiciones,
        node_color="#4C78A8",
        node_size=900,
        edgecolors="#1F2937",
        linewidths=1,
    )
    nx.draw_networkx_edges(
        grafo,
        posiciones,
        width=grosores,
        edge_color="#8A8F98",
        alpha=0.75,
    )
    nx.draw_networkx_labels(
        grafo,
        posiciones,
        labels=etiquetas,
        font_size=9,
        font_color="#111827",
    )

    plt.title("Red final de interacciones estudiantiles")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close()

    return ruta
