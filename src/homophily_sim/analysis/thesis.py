"""Validated, directed graph inputs for final thesis figures."""

from collections.abc import Mapping, Sequence
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]

SCENARIOS = ("homophily_low", "homophily_medium", "homophily_high")


def validate_scenario_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    """Require the same seeds and contiguous semesters for all three scenarios."""
    if not rows:
        raise ValueError("scenario results are empty")
    keys = [(str(row["scenario"]), int(row["seed"]), int(row["semester"])) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate scenario, seed and semester combination")
    scenarios = {key[0] for key in keys}
    seeds = {key[1] for key in keys}
    semesters = {key[2] for key in keys}
    expected = {
        (scenario, seed, semester)
        for scenario in SCENARIOS for seed in seeds for semester in semesters
    }
    if (
        scenarios != set(SCENARIOS)
        or semesters != set(range(1, max(semesters) + 1))
        or set(keys) != expected
    ):
        raise ValueError("scenario results require complete paired seeds and semesters")
    return len(seeds), len(semesters)


def build_semester_graph(
    interactions: pd.DataFrame, node_ids: Sequence[int], *, semester: int,
) -> nx.DiGraph:
    """Restore accumulated R_ij through a semester from chronological records."""
    if semester < 1:
        raise ValueError("semester must be positive")
    graph = nx.DiGraph()
    graph.add_nodes_from(int(node) for node in node_ids)
    for row in interactions.itertuples(index=False):
        if int(row.semester) > semester:
            continue
        observer = int(row.receiver_id)
        other = int(row.sender_id)
        if observer not in graph or other not in graph or observer == other:
            raise ValueError("interaction references an invalid student")
        weight = float(row.relationship_after)
        if not 0 <= weight <= 1:
            raise ValueError("relationship weight outside [0, 1]")
        graph.add_edge(observer, other, weight=weight)
    return graph


def select_strongest_edges(graph: nx.DiGraph, *, per_observer: int = 3) -> nx.DiGraph:
    """Return a display subgraph with each observer's strongest directed ties."""
    if per_observer < 1:
        raise ValueError("per_observer must be positive")
    selected = nx.DiGraph()
    selected.add_nodes_from(graph.nodes(data=True))
    for observer in graph.nodes:
        ranked = sorted(
            graph.out_edges(observer, data=True),
            key=lambda edge: (-float(edge[2]["weight"]), int(edge[1])),
        )
        selected.add_edges_from(ranked[:per_observer])
    return selected
