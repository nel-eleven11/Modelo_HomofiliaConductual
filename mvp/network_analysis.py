"""Network construction and metrics for the behavioral homophily MVP."""

from __future__ import annotations

import csv
from pathlib import Path

import networkx as nx

from agent import StudentAgent


def construir_red_interacciones(
    agentes: list[StudentAgent],
    registros_interaccion: list[dict[str, object]],
) -> nx.Graph:
    """Build a weighted social graph from successful interaction records."""
    grafo = nx.Graph()

    for agente in agentes:
        grafo.add_node(
            agente.id,
            nombre=agente.nombre,
            edad=agente.edad,
            genero=agente.genero,
            carrera=agente.carrera,
            semestre=agente.semestre,
        )

    for registro in registros_interaccion:
        if not registro["interaccion"]:
            continue

        agente_1 = int(registro["agente_1"])
        agente_2 = int(registro["agente_2"])

        if grafo.has_edge(agente_1, agente_2):
            grafo[agente_1][agente_2]["peso"] += 1
        else:
            grafo.add_edge(agente_1, agente_2, peso=1)

    return grafo


def calcular_metricas_red(grafo: nx.Graph) -> dict[str, int | float]:
    """Calculate basic metrics for the interaction network."""
    numero_nodos = grafo.number_of_nodes()
    numero_aristas = grafo.number_of_edges()
    numero_interacciones = sum(
        datos.get("peso", 1) for _, _, datos in grafo.edges(data=True)
    )
    grados = dict(grafo.degree())
    grado_promedio = sum(grados.values()) / numero_nodos if numero_nodos else 0.0
    componentes_conectados = nx.number_connected_components(grafo) if numero_nodos else 0

    return {
        "numero_agentes": numero_nodos,
        "numero_interacciones": numero_interacciones,
        "numero_conexiones": numero_aristas,
        "numero_nodos": numero_nodos,
        "numero_aristas": numero_aristas,
        "grado_promedio": round(grado_promedio, 3),
        "densidad": round(nx.density(grafo), 3),
        "componentes_conectados": componentes_conectados,
    }


def exportar_metricas_red(
    metricas: dict[str, int | float],
    ruta_salida: str | Path = "outputs/network_metrics.csv",
) -> Path:
    """Export the main network metrics to a CSV file."""
    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    columnas = [
        "numero_agentes",
        "numero_interacciones",
        "numero_conexiones",
        "densidad",
        "grado_promedio",
        "componentes_conectados",
    ]

    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerow({columna: metricas[columna] for columna in columnas})

    return ruta
