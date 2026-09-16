"""Domain range and directed relationship checks."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from homophily_sim.domain.agent import Origin, Sex, StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.domain.section import Section
from homophily_sim.domain.topic import PolarizationLevel, Topic


def make_student(student_id: int) -> StudentAgent:
    return StudentAgent(
        id=student_id, age=19, sex=Sex.FEMALE, origin=Origin.GUATEMALA_DEPARTMENT,
        semester=1, interests={"technology"}, extraversion=5,
        topic_orientations={"tech_ai_jobs": 0.2},
    )


def test_relationships_are_directed_with_neutral_prior() -> None:
    first = make_student(1)
    second = make_student(2)
    assert first.relationship_to(2) == second.relationship_to(1) == 0.5
    first.relationships[2] = 0.8
    assert first.relationship_to(2) == 0.8
    assert second.relationship_to(1) == 0.5


def test_out_of_range_student_fields_rejected() -> None:
    data = make_student(1).model_dump()
    for field, invalid in (("extraversion", 11), ("topic_orientations", {"x": -1.1}),
                           ("relationships", {2: 1.1}), ("interests", set())):
        with pytest.raises(ValidationError):
            StudentAgent.model_validate({**data, field: invalid})


def test_topic_requires_metadata() -> None:
    with pytest.raises(ValidationError):
        Topic(
            topic_id="x", category="", subcategory="s", prompt="p",
            polarization_level=PolarizationLevel.LOW,
        )


def test_section_rejects_duplicate_student_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Section(course_id="C01", section_id="A", student_ids=[1, 1])


def test_interaction_record_tracks_directed_evaluation() -> None:
    data = {
        "run_id": "run-42", "seed": 42, "semester": 1, "week": 1, "day": 1,
        "course_id": "C01", "section_id": "A", "conversation_id": "conv-1",
        "topic_id": "technology_privacy", "sender_id": 1, "receiver_id": 2,
        "sender_text": "Creo que sí.", "receiver_interest": 1.0,
        "similarity": 0.4, "relationship_before": 0.5,
        "participation_probability": 0.3, "agreement": 0.75,
        "sentiment_valence": 0.5, "interaction_score": 0.6875,
        "relationship_after": 0.5375,
        "timestamp_simulation": datetime(2026, 9, 2, 8, 0),
    }
    record = InteractionRecord.model_validate(data)
    assert (record.sender_id, record.receiver_id) == (1, 2)
    assert record.relationship_after == 0.5375
    with pytest.raises(ValidationError, match="sender"):
        InteractionRecord.model_validate({**data, "receiver_id": 1})
    with pytest.raises(ValidationError):
        InteractionRecord.model_validate({**data, "participation_probability": 1.2})
