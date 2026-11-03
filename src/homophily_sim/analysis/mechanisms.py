"""Rebuild interaction mechanisms from saved opportunities and evaluations."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from statistics import fmean, median, stdev
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from homophily_sim.data.topics import TopicBank
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.domain.message import MessageRecord
from homophily_sim.domain.opportunity import ParticipationOpportunity
from homophily_sim.io.results import StoredRun, load_run


@dataclass(frozen=True)
class MechanismTables:
    """Semester tables and reconstructed network snapshots for one saved run."""

    interaction: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    topics: list[dict[str, Any]]
    students: list[dict[str, Any]]
    graphs: list[tuple[nx.DiGraph, nx.DiGraph]]
    tones: list[dict[str, Any]] | None = None
    tone_by_interest: list[dict[str, Any]] | None = None


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (
        position - lower
    )


def _top_share(counts: Counter[tuple[int, int]]) -> float | None:
    if not counts:
        return None
    top = ceil(len(counts) / 10)
    return sum(sorted(counts.values(), reverse=True)[:top]) / sum(counts.values())


def _gini(values: list[int]) -> float | None:
    total = sum(values)
    if not values or total == 0:
        return None
    ordered = sorted(values)
    return sum((2 * index - len(values) - 1) * value
               for index, value in enumerate(ordered, start=1)) / (len(values) * total)


def _student_share(values: list[int]) -> float | None:
    total = sum(values)
    if not values or total == 0:
        return None
    return sum(sorted(values, reverse=True)[:ceil(len(values) / 10)]) / total


def _repeat_rates(
    opportunities: list[ParticipationOpportunity],
) -> dict[tuple[int, str], float | None]:
    seen_exposure: set[tuple[int, int]] = set()
    seen_response: set[tuple[int, int]] = set()
    repeated: Counter[tuple[int, str]] = Counter()
    total: Counter[tuple[int, str]] = Counter()
    for item in opportunities:
        pair = (min(item.initiator_id, item.candidate_id),
                max(item.initiator_id, item.candidate_id))
        semester = item.semester
        total[semester, "exposure"] += 1
        repeated[semester, "exposure"] += pair in seen_exposure
        seen_exposure.add(pair)
        if item.participated:
            total[semester, "response"] += 1
            repeated[semester, "response"] += pair in seen_response
            seen_response.add(pair)
    return {
        (semester, kind): repeated[semester, kind] / count
        for (semester, kind), count in total.items()
    }


def _communities(graph: nx.DiGraph) -> dict[int, int]:
    projection = nx.Graph()
    projection.add_nodes_from(graph.nodes)
    projection.add_edges_from(graph.edges)
    groups = (
        list(nx.community.greedy_modularity_communities(projection, weight=None))
        if projection.number_of_edges() else [{node} for node in projection.nodes]
    )
    groups.sort(key=lambda group: (-len(group), min(group)))
    return {node: index for index, group in enumerate(groups) for node in group}


def _mixing(
    pairs: list[tuple[int, int]], membership: dict[int, int]
) -> float | None:
    if not pairs:
        return None
    return sum(membership[a] != membership[b] for a, b in pairs) / len(pairs)


def _base_graph(run: StoredRun) -> nx.DiGraph:
    graph = nx.DiGraph()
    for agent in run.agents:
        graph.add_node(
            agent.id, student_id=agent.id, sex=agent.sex.value,
            origin=agent.origin.value, interests_encoded=",".join(sorted(agent.interests)),
        )
    return graph


def _update_graphs(
    evaluation: nx.DiGraph, response: nx.DiGraph,
    evaluations: list[InteractionRecord], opportunities: list[ParticipationOpportunity],
) -> None:
    for record in evaluations:
        edge = (record.receiver_id, record.sender_id)
        old = evaluation.get_edge_data(*edge) or {}
        evaluation.add_edge(
            *edge, weight=record.relationship_after,
            interaction_count=int(old.get("interaction_count", 0)) + 1,
            last_interaction_semester=record.semester, observed=True,
        )
    for item in opportunities:
        if item.participated:
            edge = (item.candidate_id, item.initiator_id)  # message flow
            old = response.get_edge_data(*edge) or {}
            response.add_edge(
                *edge, weight=int(old.get("interaction_count", 0)) + 1,
                interaction_count=int(old.get("interaction_count", 0)) + 1,
                last_interaction_semester=item.semester, observed=True,
            )


def summarize_run(run: StoredRun, bank: TopicBank) -> MechanismTables:
    """Calculate all semester indicators using only persisted run records.

    Exposure and response pairs are undirected for repetition; active response
    graph edges follow message flow (responder -> initiator). Evaluation graph
    edges follow relationship direction (observer -> sender).
    """
    if not run.opportunities:
        raise ValueError("participation_attempts.parquet is required for mechanism summaries")
    if bank.topic_bank_version != run.metadata.topic_bank_version:
        raise ValueError("saved topic bank version differs from run metadata")
    by_sem_opps: dict[int, list[ParticipationOpportunity]] = defaultdict(list)
    by_sem_records: dict[int, list[InteractionRecord]] = defaultdict(list)
    by_sem_messages: dict[int, list[MessageRecord]] = defaultdict(list)
    for item in run.opportunities:
        by_sem_opps[item.semester].append(item)
    for record in run.interactions:
        by_sem_records[record.semester].append(record)
    for message in run.messages:
        by_sem_messages[message.semester].append(message)
    repeats = _repeat_rates(run.opportunities)
    topics_by_id = {topic.topic_id: topic for topic in bank.topics}
    evaluation = _base_graph(run)
    response = _base_graph(run)
    previous_membership: dict[int, int] | None = None
    previous_eval_activity: set[tuple[int, int]] = set()
    previous_response_activity: set[tuple[int, int]] = set()
    previous_strong: set[tuple[int, int]] = set()
    previous_student_stats: dict[int, tuple[int, int, float, float]] = {}
    seen_eval: set[tuple[int, int]] = set()
    interaction_rows: list[dict[str, Any]] = []
    relationship_rows: list[dict[str, Any]] = []
    topic_rows: list[dict[str, Any]] = []
    student_rows: list[dict[str, Any]] = []
    tone_rows: list[dict[str, Any]] = []
    interest_tone_rows: list[dict[str, Any]] = []
    graphs: list[tuple[nx.DiGraph, nx.DiGraph]] = []
    for semester in range(1, run.config.semesters + 1):
        opportunities = by_sem_opps[semester]
        records = by_sem_records[semester]
        messages = by_sem_messages[semester]
        replies = [item for item in opportunities if item.participated]
        _update_graphs(evaluation, response, records, opportunities)
        current_membership = _communities(evaluation)
        reference = previous_membership if previous_membership is not None else current_membership
        for graph in (evaluation, response):
            for node in graph.nodes:
                graph.nodes[node]["semester"] = semester
                graph.nodes[node]["community_id"] = current_membership[node]
        graphs.append((evaluation.copy(), response.copy()))
        eval_pairs = {(record.receiver_id, record.sender_id) for record in records}
        response_pairs = {(item.candidate_id, item.initiator_id) for item in replies}
        new_pairs = eval_pairs - seen_eval
        seen_eval.update(eval_pairs)
        strong = {
            (source, target) for source, target, attrs in evaluation.edges(data=True)
            if attrs["weight"] >= run.config.strong_relationship_threshold
        }
        common = {
            "scenario": run.config.scenario, "h": run.config.h,
            "seed": run.metadata.seed, "run_id": run.metadata.run_id,
            "semester": semester,
        }
        exposure_counts: Counter[tuple[int, int]] = Counter(
            (min(item.initiator_id, item.candidate_id),
             max(item.initiator_id, item.candidate_id)) for item in opportunities
        )
        response_counts: Counter[tuple[int, int]] = Counter(
            (min(item.initiator_id, item.candidate_id),
             max(item.initiator_id, item.candidate_id)) for item in replies
        )
        initiators = {item.initiator_id for item in opportunities}
        responders = {item.candidate_id for item in replies}
        values = [record.relationship_after - record.relationship_before for record in records]
        positive = [delta for delta in values if delta > 1e-9]
        negative = [delta for delta in values if delta < -1e-9]
        weights = [float(attrs["weight"]) for _, _, attrs in evaluation.edges(data=True)]
        potential_weights = weights + [run.config.initial_relationship] * (
            run.config.population_size * (run.config.population_size - 1) - len(weights)
        )
        strong_weights = [
            float(evaluation.edges[edge]["weight"]) for edge in strong
        ]
        response_by_student = Counter(item.candidate_id for item in replies)
        response_values = [response_by_student[node] for node in evaluation.nodes]
        agreement_values = [record.agreement for record in records]
        sentiment_values = [record.sentiment_valence for record in records]
        message_by_id = {message.message_id: message for message in messages}
        tone_groups = {
            tone: [record for record in records
                   if record.message_id in message_by_id
                   and message_by_id[record.message_id].sampled_tone == tone]
            for tone in ("negative", "neutral", "positive")
        }
        tone_metrics = {
            f"{tone}_message_rate": (
                sum(message.sampled_tone == tone for message in messages) / len(messages)
                if messages else None
            )
            for tone in ("negative", "neutral", "positive")
        }
        tone_metrics.update({
            "mean_expressed_valence": _mean([message.sampled_valence for message in messages]),
            "mean_evaluated_valence": _mean(sentiment_values) if messages else None,
        })
        for tone, tone_records in tone_groups.items():
            tone_metrics[f"mean_interaction_score_{tone}_tone"] = _mean(
                [record.interaction_score for record in tone_records]
            )
            tone_metrics[f"mean_relationship_delta_{tone}_tone"] = _mean(
                [record.relationship_after - record.relationship_before
                 for record in tone_records]
            )
        interaction_rows.append({
            **common, **tone_metrics,
            "conversation_count": len({item.conversation_id for item in opportunities}),
            "exposure_count": len(opportunities), "directed_evaluation_count": len(records),
            "response_count": len(replies), "unique_initiator_count": len(initiators),
            "unique_responder_count": len(responders),
            "unique_active_student_count": len(initiators | responders),
            "active_student_fraction": len(initiators | responders) / run.config.population_size,
            "participation_rate": len(replies) / len(opportunities) if opportunities else None,
            "mean_exposed_pair_similarity": _mean([item.similarity for item in opportunities]),
            "mean_responding_pair_similarity": _mean([item.similarity for item in replies]),
            "mean_exposed_previous_relationship": _mean(
                [item.relationship_before for item in opportunities]
            ),
            "mean_responding_previous_relationship": _mean(
                [item.relationship_before for item in replies]
            ),
            "mean_evaluation_pair_similarity": _mean([record.similarity for record in records]),
            "mean_evaluation_previous_relationship": _mean(
                [record.relationship_before for record in records]
            ),
            "repeated_unordered_exposure_rate": repeats.get((semester, "exposure")),
            "repeated_unordered_response_rate": repeats.get((semester, "response")),
            "top_10_percent_exposure_pair_share": _top_share(exposure_counts),
            "top_10_percent_response_pair_share": _top_share(response_counts),
            "mean_agreement": _mean(agreement_values),
            "median_agreement": median(agreement_values) if agreement_values else None,
            "std_agreement": stdev(agreement_values) if len(agreement_values) > 1 else None,
            "mean_sentiment_valence": _mean(sentiment_values),
            "median_sentiment_valence": median(sentiment_values) if sentiment_values else None,
            "std_sentiment_valence": stdev(sentiment_values)
            if len(sentiment_values) > 1 else None,
            "mean_interaction_score": _mean([record.interaction_score for record in records]),
            "mean_responses_per_student": _mean([float(value) for value in response_values]),
            "median_responses_per_student": median(response_values),
            "std_responses_per_student": stdev(response_values)
            if len(response_values) > 1 else None,
            "min_responses_per_student": min(response_values),
            "max_responses_per_student": max(response_values),
            "gini_active_responses": _gini(response_values),
            "top_10_percent_student_response_share": _student_share(response_values),
            "evaluation_activity_persistence_rate": (
                len(eval_pairs & previous_eval_activity) / len(previous_eval_activity)
                if previous_eval_activity else None
            ),
            "response_activity_persistence_rate": (
                len(response_pairs & previous_response_activity) / len(previous_response_activity)
                if previous_response_activity else None
            ),
            "between_community_evaluation_rate": _mixing(
                [(record.receiver_id, record.sender_id) for record in records], reference
            ),
            "between_community_response_rate": _mixing(
                [(item.candidate_id, item.initiator_id) for item in replies], reference
            ),
            "community_reference_semester": semester - 1 if semester > 1 else semester,
            "community_mixing_descriptive_only": semester == 1,
            "active_response_edge_count": response.number_of_edges(),
            "active_response_density": float(nx.density(response)),
        })
        for tone, tone_records in tone_groups.items():
            tone_rows.append({
                **common, "tone": tone,
                "message_count": sum(message.sampled_tone == tone for message in messages),
                "directed_evaluation_count": len(tone_records),
                "mean_interaction_score": _mean([
                    record.interaction_score for record in tone_records
                ]),
                "mean_relationship_delta": _mean([
                    record.relationship_after - record.relationship_before
                    for record in tone_records
                ]),
            })
        for interest in (0.0, 0.5, 1.0):
            interest_messages = [
                message for message in messages if message.sender_topic_interest == interest
            ]
            for tone in ("negative", "neutral", "positive"):
                count = sum(message.sampled_tone == tone for message in interest_messages)
                interest_tone_rows.append({
                    **common, "sender_topic_interest": interest, "tone": tone,
                    "message_count": count, "total_messages_at_interest": len(interest_messages),
                    "tone_rate": count / len(interest_messages) if interest_messages else None,
                })
        relationship_rows.append({
            **common, "observed_evaluation_relationship_count": evaluation.number_of_edges(),
            "active_evaluation_relationship_count": len(eval_pairs),
            "strong_relationship_count": len(strong),
            "strong_relationship_threshold": run.config.strong_relationship_threshold,
            "new_evaluation_relationship_count": len(new_pairs),
            "persistent_evaluation_activity_count": len(eval_pairs & previous_eval_activity),
            "persistent_response_activity_count": len(response_pairs & previous_response_activity),
            "persistent_strong_relationship_count": len(strong & previous_strong),
            "lost_strong_relationship_count": len(previous_strong - strong),
            "strong_relationship_persistence_rate": (
                len(strong & previous_strong) / len(previous_strong)
                if previous_strong else None
            ),
            "strengthened_evaluation_updates": len(positive),
            "weakened_evaluation_updates": len(negative),
            "unchanged_evaluation_updates": len(values) - len(positive) - len(negative),
            "mean_positive_relationship_delta": _mean(positive),
            "mean_negative_relationship_delta": _mean(negative),
            "mean_absolute_relationship_delta": _mean([abs(delta) for delta in values]),
            "mean_relationship_delta": _mean(values),
            "net_relationship_change": sum(values),
            "mean_observed_relationship_weight": _mean(weights),
            "median_observed_relationship_weight": median(weights) if weights else None,
            "std_observed_relationship_weight": stdev(weights) if len(weights) > 1 else None,
            "q25_observed_relationship_weight": _quantile(weights, 0.25),
            "q75_observed_relationship_weight": _quantile(weights, 0.75),
            "min_observed_relationship_weight": min(weights) if weights else None,
            "max_observed_relationship_weight": max(weights) if weights else None,
            "mean_potential_relationship_weight": _mean(potential_weights),
            "median_potential_relationship_weight": median(potential_weights),
            "mean_strong_relationship_weight": _mean(strong_weights),
        })
        by_topic_opps: dict[str, list[ParticipationOpportunity]] = defaultdict(list)
        by_topic_records: dict[str, list[InteractionRecord]] = defaultdict(list)
        for item in opportunities:
            by_topic_opps[item.topic_id].append(item)
        for record in records:
            by_topic_records[record.topic_id].append(record)
        for topic_id, topic_opps in sorted(by_topic_opps.items()):
            topic = topics_by_id[topic_id]
            topic_replies = [item for item in topic_opps if item.participated]
            topic_records = by_topic_records[topic_id]
            topic_rows.append({
                **common, "topic_id": topic_id, "category": topic.category,
                "subcategory": topic.subcategory,
                "conversation_count": len({item.conversation_id for item in topic_opps}),
                "exposure_count": len(topic_opps), "response_count": len(topic_replies),
                "participation_rate": len(topic_replies) / len(topic_opps),
                "directed_evaluation_count": len(topic_records),
                "mean_agreement": _mean([record.agreement for record in topic_records]),
                "mean_sentiment_valence": _mean(
                    [record.sentiment_valence for record in topic_records]
                ),
                "mean_interaction_score": _mean(
                    [record.interaction_score for record in topic_records]
                ),
                "mean_exposed_pair_similarity": _mean(
                    [item.similarity for item in topic_opps]
                ),
                "mean_responding_pair_similarity": _mean(
                    [item.similarity for item in topic_replies]
                ),
            })
        initiator_count = Counter(item.initiator_id for item in opportunities)
        response_count = Counter(item.candidate_id for item in replies)
        evaluation_count = Counter(record.receiver_id for record in records)
        for node in sorted(evaluation.nodes):
            current_stats = (
                int(evaluation.in_degree(node)), int(evaluation.out_degree(node)),
                float(evaluation.in_degree(node, weight="weight")),
                float(evaluation.out_degree(node, weight="weight")),
            )
            previous_stats = previous_student_stats.get(node)
            student_rows.append({
                **common, "student_id": node,
                "initiated_conversation_count": initiator_count[node],
                "active_response_count": response_count[node],
                "received_evaluation_count": evaluation_count[node],
                "evaluation_in_degree": current_stats[0],
                "evaluation_out_degree": current_stats[1],
                "evaluation_in_strength": current_stats[2],
                "evaluation_out_strength": current_stats[3],
                "evaluation_in_degree_change": current_stats[0] - previous_stats[0]
                if previous_stats else None,
                "evaluation_out_degree_change": current_stats[1] - previous_stats[1]
                if previous_stats else None,
                "evaluation_in_strength_change": current_stats[2] - previous_stats[2]
                if previous_stats else None,
                "evaluation_out_strength_change": current_stats[3] - previous_stats[3]
                if previous_stats else None,
                "active_response_in_degree": response.in_degree(node),
                "active_response_out_degree": response.out_degree(node),
            })
            previous_student_stats[node] = current_stats
        previous_membership = current_membership
        previous_eval_activity = eval_pairs
        previous_response_activity = response_pairs
        previous_strong = strong
    return MechanismTables(interaction_rows, relationship_rows, topic_rows, student_rows,
                           graphs, tone_rows, interest_tone_rows)


def summarize_saved_run(path: str | Path, bank: TopicBank) -> MechanismTables:
    """Recompute mechanism indicators from a saved run without any provider call."""
    return summarize_run(load_run(path), bank)
