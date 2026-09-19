"""Balanced, reproducible enrollment with relationship-aware later semesters."""

from collections import Counter
from pathlib import Path

import pytest

from homophily_sim.config import load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.population import generate_population
from homophily_sim.data.topics import load_topics
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.simulation.calendar import generate_academic_calendar
from homophily_sim.simulation.enrollment import enroll_semester, section_preference_score

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "configs/base.yaml")
BANK = load_topics(ROOT / "data/topics/topics_v1.yaml")
PROFILE = load_demographic_profile(
    ROOT / "data/demographics/profiles_v1.yaml", CONFIG.demographic_profile
)


def cohort(seed: int) -> list[StudentAgent]:
    return generate_population(CONFIG, BANK, PROFILE, seed)


@pytest.mark.parametrize("seed", range(30))
def test_every_course_has_unique_balanced_assignment(seed: int) -> None:
    students = cohort(seed)
    calendar = generate_academic_calendar(CONFIG, seed)
    first = enroll_semester(students, calendar[0], CONFIG, seed)
    assert len(first) == CONFIG.courses_per_semester
    for course_id, sections in first.items():
        assert sorted(len(section.student_ids) for section in sections) == [26, 27, 27]
        assigned = Counter(
            student_id for section in sections for student_id in section.student_ids
        )
        assert assigned == {student.id: 1 for student in students}
        assert all(section.course_id == course_id for section in sections)
        assert all(course_id in student.course_assignments[1] for student in students)
        assert all(course_id in student.section_assignments[1] for student in students)

    second = enroll_semester(students, calendar[1], CONFIG, seed)
    assert len(second) == CONFIG.courses_per_semester
    for sections in second.values():
        assert sorted(len(section.student_ids) for section in sections) == [26, 27, 27]
        assert len({student_id for section in sections for student_id in section.student_ids}) == 80
    assert all(student.semester == 2 for student in students)
    assert all(len(student.course_assignments[1]) == len(student.course_assignments[2]) == 6
               for student in students)


def test_same_seed_reproduces_enrollment() -> None:
    calendar = generate_academic_calendar(CONFIG, 42)
    first_students = cohort(42)
    again_students = cohort(42)
    changed_relationships = cohort(42)
    changed_relationships[0].relationships[1] = 1.0
    first = enroll_semester(first_students, calendar[0], CONFIG, 42)
    again = enroll_semester(again_students, calendar[0], CONFIG, 42)
    altered = enroll_semester(changed_relationships, calendar[0], CONFIG, 42)
    assert first == again == altered  # The first semester ignores prior bonds.
    assert enroll_semester(first_students, calendar[1], CONFIG, 42) == enroll_semester(
        again_students, calendar[1], CONFIG, 42
    )


def test_relationship_weight_controls_preference() -> None:
    student = cohort(1)[0]
    student.relationships[1] = 1.0
    student.relationships[2] = 0.0
    relationship_only = CONFIG.model_copy(update={"gamma_section": 1.0})
    random_only = CONFIG.model_copy(update={"gamma_section": 0.0})
    assert section_preference_score(student, [1], relationship_only, 0.0) == 1.0
    assert section_preference_score(student, [2], relationship_only, 1.0) == 0.0
    assert section_preference_score(student, [1], random_only, 0.25) == 0.25
    assert section_preference_score(student, [], relationship_only, 0.0) == 0.5
