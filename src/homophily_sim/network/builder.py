"""Build the directed network from explicit relationship state."""

from collections.abc import Sequence
from datetime import datetime

import networkx as nx  # type: ignore[import-untyped]

from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.interaction import InteractionRecord


def build_graph(
    agents: Sequence[StudentAgent],
    interactions: Sequence[InteractionRecord] = (),
) -> nx.DiGraph:
    """Create one node per student and one edge per stored directed bond.

    An evaluation by receiver i of sender j belongs to edge i -> j.
    Absent relationships remain absent edges; their neutral prior is not a tie.
    """
    graph = nx.DiGraph()
    by_id = {agent.id: agent for agent in agents}
    if len(by_id) != len(agents):
        raise ValueError("student ids must be unique")
    for agent in agents:
        graph.add_node(
            agent.id,
            age=agent.age,
            sex=agent.sex.value,
            origin=agent.origin.value,
            interests=tuple(sorted(agent.interests)),
        )
    for agent in agents:
        for other_id, weight in agent.relationships.items():
            if other_id not in by_id or other_id == agent.id:
                raise ValueError("relationship must refer to another student in the cohort")
            graph.add_edge(
                agent.id,
                other_id,
                weight=weight,
                interaction_count=0,
                last_interaction=None,
            )
    for record in interactions:
        edge = (record.receiver_id, record.sender_id)
        if not graph.has_edge(*edge):
            raise ValueError("interaction has no corresponding directed relationship")
        attributes = graph.edges[edge]
        attributes["interaction_count"] += 1
        last: datetime | None = attributes["last_interaction"]
        if last is None or record.timestamp_simulation > last:
            attributes["last_interaction"] = record.timestamp_simulation
    return graph
