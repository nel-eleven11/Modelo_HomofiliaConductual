"""Directed bonds, network metrics and independent snapshots."""

from datetime import datetime

import pytest

from homophily_sim.config import load_config
from homophily_sim.domain.agent import Origin, Sex, StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.network.builder import build_graph
from homophily_sim.network.metrics import compute_metrics
from homophily_sim.network.snapshots import capture_snapshot


def _agent(identifier: int, relationships: dict[int, float] | None = None) -> StudentAgent:
    return StudentAgent(
        id=identifier,
        age=18,
        sex=Sex.FEMALE if identifier % 2 == 0 else Sex.MALE,
        origin=Origin.GUATEMALA_DEPARTMENT,
        semester=1,
        interests={"music"},
        extraversion=5,
        relationships=relationships or {},
    )


def _interaction(receiver: int, sender: int, moment: datetime) -> InteractionRecord:
    return InteractionRecord(
        run_id="network-test",
        seed=42,
        semester=1,
        week=1,
        day=1,
        course_id="C1",
        section_id="S1",
        conversation_id="conv-1",
        topic_id="music",
        sender_id=sender,
        receiver_id=receiver,
        sender_text="Hola",
        receiver_interest=1,
        similarity=0.5,
        relationship_before=0.5,
        participation_probability=0.4,
        agreement=0.5,
        sentiment_valence=0.5,
        interaction_score=0.5,
        relationship_after=0.8,
        timestamp_simulation=moment,
    )


def test_graph_has_80_nodes_and_directed_weights() -> None:
    agents = [_agent(i) for i in range(80)]
    agents[0].relationships[1] = 0.8
    agents[1].relationships[0] = 0.2
    early = datetime(2000, 1, 1, 8)
    late = datetime(2000, 1, 1, 9)
    graph = build_graph(
        agents,
        [
            _interaction(0, 1, early),
            _interaction(0, 1, late),
            _interaction(1, 0, early),
        ],
    )
    assert graph.number_of_nodes() == 80
    assert graph.number_of_edges() == 2
    assert graph[0][1] == {
        "weight": 0.8,
        "interaction_count": 2,
        "last_interaction": late,
    }
    assert graph[1][0]["weight"] == 0.2
    assert graph[1][0]["interaction_count"] == 1
    assert 2 not in graph[0]


def test_metrics_keep_direction_and_explicit_projection() -> None:
    agents = [_agent(0, {1: 0.8}), _agent(1, {0: 0.2}), _agent(2)]
    graph = build_graph(agents)
    config = load_config("configs/base.yaml").model_copy(update={"population_size": 3})
    result = compute_metrics(graph, agents, config)
    assert result.density == pytest.approx(1 / 3)
    assert result.in_degree == {0: 1, 1: 1, 2: 0}
    assert result.out_strength == {0: 0.8, 1: 0.2, 2: 0.0}
    assert result.reciprocity == 1.0
    assert result.isolates == (2,)
    assert result.weak_components == ((0, 1), (2,))
    assert result.strong_components == ((0, 1), (2,))
    assert result.mean_clustering == 0.0
    assert result.community_sizes == (2, 1)
    assert result.relationship_weights == (0.2, 0.8)
    assert result.mean_edge_similarity is not None
    assert 0 <= result.mean_edge_similarity <= 1


def test_snapshot_is_detached_from_later_relationship_changes() -> None:
    agents = [_agent(0, {1: 0.7}), _agent(1)]
    first = capture_snapshot(agents, [], kind="semester_end", semester=1)
    agents[0].relationships[1] = 0.9
    agents[1].relationships[0] = 0.6
    second = capture_snapshot(agents, [], kind="year_end", semester=2)
    assert first.graph[0][1]["weight"] == 0.7
    assert not first.graph.has_edge(1, 0)
    assert second.graph[0][1]["weight"] == 0.9
    assert second.graph[1][0]["weight"] == 0.6
    with pytest.raises(ValueError):
        capture_snapshot(agents, [], kind="year_end", semester=3)
    with pytest.raises(ValueError):
        capture_snapshot(agents, [], kind="final", semester=9)
