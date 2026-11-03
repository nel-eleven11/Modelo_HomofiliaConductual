"""Interest mixing and strong-tie measurements from saved experiment events."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from itertools import product
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from homophily_sim.data.topics import TopicBank
from homophily_sim.domain.opportunity import ParticipationOpportunity


def interest_mixing(
    interests_by_student: Mapping[int, set[str]],
    opportunities: Iterable[ParticipationOpportunity],
    bank: TopicBank,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Count exposures and replies by interest category and exact overlap.

    Each opportunity contributes a total weight of one across all category
    cells, even when either student has several interests. The matrix is
    directed from initiator to exposed student; its rate conditions on an
    actual exposure, not on all possible student pairs.
    """
    category_for = {
        term: category
        for category, subcategories in bank.taxonomy.items()
        for term in (category, *subcategories)
    }
    categories_by_student: dict[int, tuple[str, ...]] = {}
    for student_id, interests in interests_by_student.items():
        unknown = interests - category_for.keys()
        if unknown:
            raise ValueError(f"unknown interest labels: {sorted(unknown)}")
        categories_by_student[student_id] = tuple(sorted({category_for[i] for i in interests}))
    cells: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    overlap = {False: [0, 0], True: [0, 0]}
    for opportunity in opportunities:
        initiator = opportunity.initiator_id
        candidate = opportunity.candidate_id
        shared = bool(interests_by_student[initiator] & interests_by_student[candidate])
        overlap[shared][0] += 1
        overlap[shared][1] += int(opportunity.participated)
        source_categories = categories_by_student[initiator]
        target_categories = categories_by_student[candidate]
        contribution = 1 / (len(source_categories) * len(target_categories))
        for source, target in product(source_categories, target_categories):
            cell = cells[source, target]
            cell[0] += contribution
            cell[1] += contribution * int(opportunity.participated)
    matrix = [
        {
            "initiator_interest_category": source,
            "exposed_interest_category": target,
            "weighted_exposure_count": values[0],
            "weighted_response_count": values[1],
            "response_rate_given_exposure": values[1] / values[0],
        }
        for (source, target), values in sorted(cells.items())
    ]
    comparison = [
        {
            "shared_exact_interest": shared,
            "exposure_count": overlap[shared][0],
            "response_count": overlap[shared][1],
            "response_rate_given_exposure": (
                overlap[shared][1] / overlap[shared][0] if overlap[shared][0] else None
            ),
        }
        for shared in (False, True)
    ]
    return matrix, comparison


def strong_tie_metrics(
    graph: nx.DiGraph, threshold: float, previous: set[tuple[int, int]]
) -> tuple[dict[str, float | int | None], set[tuple[int, int]]]:
    """Summarize observed directed and mutually strong ties at one snapshot."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    strong = {
        (source, target)
        for source, target, attrs in graph.edges(data=True)
        if float(attrs["weight"]) >= threshold
    }
    reciprocal = {
        frozenset((source, target))
        for source, target in strong
        if (target, source) in strong
    }
    nodes = graph.number_of_nodes()
    directed_possible = nodes * (nodes - 1)
    undirected_possible = directed_possible / 2
    return {
        "observed_evaluation_edge_count": graph.number_of_edges(),
        "strong_directed_edge_count": len(strong),
        "strong_directed_density": len(strong) / directed_possible if directed_possible else 0.0,
        "strong_share_of_observed_edges": (
            len(strong) / graph.number_of_edges() if graph.number_of_edges() else None
        ),
        "mutual_strong_pair_count": len(reciprocal),
        "mutual_strong_pair_density": (
            len(reciprocal) / undirected_possible if undirected_possible else 0.0
        ),
        "new_strong_directed_edge_count": len(strong - previous),
        "lost_strong_directed_edge_count": len(previous - strong),
        "strong_directed_persistence_rate": (
            len(strong & previous) / len(previous) if previous else None
        ),
    }, strong
