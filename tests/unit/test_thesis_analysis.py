"""Small checks for the reproducible thesis artifact inputs."""

import pandas as pd
import pytest

from homophily_sim.analysis.thesis import (
    build_semester_graph,
    select_strongest_edges,
    validate_scenario_rows,
)


def test_validate_scenario_rows_requires_paired_complete_runs() -> None:
    rows = [
        {"scenario": scenario, "seed": seed, "semester": semester}
        for scenario in ("homophily_low", "homophily_medium", "homophily_high")
        for seed in (1, 2)
        for semester in (1, 2)
    ]
    assert validate_scenario_rows(rows) == (2, 2)
    with pytest.raises(ValueError, match="paired"):
        validate_scenario_rows(rows[:-1])
    with pytest.raises(ValueError, match="duplicate"):
        validate_scenario_rows([*rows, rows[0]])


def test_graph_uses_latest_directed_receiver_relationship() -> None:
    interactions = pd.DataFrame(
        [
            {"semester": 1, "receiver_id": 0, "sender_id": 1,
             "relationship_after": 0.6},
            {"semester": 1, "receiver_id": 0, "sender_id": 1,
             "relationship_after": 0.8},
            {"semester": 2, "receiver_id": 1, "sender_id": 0,
             "relationship_after": 0.4},
        ]
    )
    first = build_semester_graph(interactions, [0, 1, 2], semester=1)
    assert first.number_of_nodes() == 3
    assert first[0][1]["weight"] == 0.8
    assert not first.has_edge(1, 0)
    second = build_semester_graph(interactions, [0, 1, 2], semester=2)
    assert second[0][1]["weight"] == 0.8
    assert second[1][0]["weight"] == 0.4


def test_strongest_edges_are_selected_per_observer() -> None:
    interactions = pd.DataFrame(
        [
            {"semester": 1, "receiver_id": 0, "sender_id": 1,
             "relationship_after": 0.2},
            {"semester": 1, "receiver_id": 0, "sender_id": 2,
             "relationship_after": 0.9},
            {"semester": 1, "receiver_id": 1, "sender_id": 0,
             "relationship_after": 0.7},
        ]
    )
    graph = build_semester_graph(interactions, [0, 1, 2], semester=1)
    selected = select_strongest_edges(graph, per_observer=1)
    assert set(selected.edges) == {(0, 2), (1, 0)}
    assert set(selected.nodes) == {0, 1, 2}
