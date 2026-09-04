"""Domain range and directed relationship checks."""

import pytest
from pydantic import ValidationError

from homophily_sim.domain.agent import Origin, Sex, StudentAgent
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
