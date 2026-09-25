"""Directed network measurements and explicitly undirected projections."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum, isfinite

import networkx as nx  # type: ignore[import-untyped]

from homophily_sim.config import SimulationConfig
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.social.similarity import agent_similarity


@dataclass(frozen=True, slots=True)
class NetworkMetrics:
    """Measurements of one directed graph at a simulation instant."""

    density: float
    in_degree: dict[int, int]
    out_degree: dict[int, int]
    in_strength: dict[int, float]
    out_strength: dict[int, float]
    reciprocity: float | None
    isolates: tuple[int, ...]
    weak_components: tuple[tuple[int, ...], ...]
    strong_components: tuple[tuple[int, ...], ...]
    mean_clustering: float
    communities: tuple[tuple[int, ...], ...]
    modularity: float
    sex_assortativity: float | None
    origin_assortativity: float | None
    mean_edge_similarity: float | None
    relationship_weights: tuple[float, ...]
    community_sizes: tuple[int, ...]


def _ordered_groups(groups: Sequence[set[int] | frozenset[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(sorted((tuple(sorted(group)) for group in groups), key=lambda g: (-len(g), g)))


def _assortativity(graph: nx.DiGraph, attribute: str) -> float | None:
    if graph.number_of_edges() == 0:
        return None
    endpoint_values = {
        graph.nodes[node][attribute] for source, target in graph.edges for node in (source, target)
    }
    if len(endpoint_values) < 2:
        return None
    value = float(nx.attribute_assortativity_coefficient(graph, attribute))
    return value if isfinite(value) else None


def compute_metrics(
    graph: nx.DiGraph,
    agents: Sequence[StudentAgent],
    config: SimulationConfig,
) -> NetworkMetrics:
    """Measure direction where supported; project only for clustering/community.

    The undirected projection has an edge if either direction exists. Its
    clustering, communities and modularity are unweighted so reciprocal edge
    weights do not require an arbitrary merge rule. Undefined quantities are
    returned as None (reciprocity and similarity without edges, or assortativity
    without variation).
    """
    by_id = {agent.id: agent for agent in agents}
    if len(by_id) != len(agents) or set(by_id) != set(graph.nodes):
        raise ValueError("graph nodes must match unique agents")
    projection = nx.Graph()
    projection.add_nodes_from(graph.nodes)
    projection.add_edges_from(graph.edges)
    if projection.number_of_edges():
        raw_communities = list(nx.community.greedy_modularity_communities(projection, weight=None))
        modularity = float(nx.community.modularity(projection, raw_communities, weight=None))
    else:
        raw_communities = [{node} for node in projection.nodes]
        modularity = 0.0
    communities = _ordered_groups(raw_communities)
    weights = tuple(sorted(float(data["weight"]) for _, _, data in graph.edges(data=True)))
    similarities = [
        agent_similarity(by_id[source], by_id[target], config) for source, target in graph.edges
    ]
    reciprocity = nx.reciprocity(graph) if graph.number_of_edges() else None
    return NetworkMetrics(
        density=float(nx.density(graph)),
        in_degree={node: int(degree) for node, degree in graph.in_degree()},
        out_degree={node: int(degree) for node, degree in graph.out_degree()},
        in_strength={node: float(degree) for node, degree in graph.in_degree(weight="weight")},
        out_strength={node: float(degree) for node, degree in graph.out_degree(weight="weight")},
        reciprocity=float(reciprocity) if reciprocity is not None else None,
        isolates=tuple(sorted(nx.isolates(graph))),
        weak_components=_ordered_groups(list(nx.weakly_connected_components(graph))),
        strong_components=_ordered_groups(list(nx.strongly_connected_components(graph))),
        mean_clustering=float(nx.average_clustering(projection)) if projection else 0.0,
        communities=communities,
        modularity=modularity,
        sex_assortativity=_assortativity(graph, "sex"),
        origin_assortativity=_assortativity(graph, "origin"),
        mean_edge_similarity=fsum(similarities) / len(similarities) if similarities else None,
        relationship_weights=weights,
        community_sizes=tuple(len(community) for community in communities),
    )
