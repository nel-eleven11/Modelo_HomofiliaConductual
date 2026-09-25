"""Independent network snapshots at academic boundaries."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import networkx as nx  # type: ignore[import-untyped]

from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.network.builder import build_graph

SnapshotKind = Literal["semester_end", "year_end", "final"]


@dataclass(frozen=True, slots=True)
class NetworkSnapshot:
    """A graph detached from subsequent changes to student relationships."""

    kind: SnapshotKind
    semester: int
    graph: nx.DiGraph


def capture_snapshot(
    agents: Sequence[StudentAgent],
    interactions: Sequence[InteractionRecord],
    *,
    kind: SnapshotKind,
    semester: int,
    total_semesters: int = 10,
) -> NetworkSnapshot:
    """Capture a semester, year or final graph from current student state."""
    if not 1 <= semester <= total_semesters:
        raise ValueError("semester is outside the configured range")
    if kind == "year_end" and semester % 2:
        raise ValueError("year_end requires an even semester")
    if kind == "final" and semester != total_semesters:
        raise ValueError("final requires the last semester")
    if any(record.semester > semester for record in interactions):
        raise ValueError("snapshot cannot contain future interactions")
    return NetworkSnapshot(kind, semester, build_graph(agents, interactions))
