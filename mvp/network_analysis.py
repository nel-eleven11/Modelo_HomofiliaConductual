"""Network construction and metrics for the behavioral homophily MVP."""

from __future__ import annotations

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
    grados = dict(grafo.degree())
    grado_promedio = sum(grados.values()) / numero_nodos if numero_nodos else 0.0
    componentes_conectados = nx.number_connected_components(grafo) if numero_nodos else 0

    return {
        "numero_nodos": numero_nodos,
        "numero_aristas": numero_aristas,
        "grado_promedio": round(grado_promedio, 3),
        "densidad": round(nx.density(grafo), 3),
        "componentes_conectados": componentes_conectados,
    }
