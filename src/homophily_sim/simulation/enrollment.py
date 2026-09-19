"""Balanced section assignment for a single synthetic cohort."""

from collections import Counter
from collections.abc import Sequence
from random import Random
from statistics import fmean

import numpy as np

from homophily_sim.config import SimulationConfig
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.course import Course
from homophily_sim.domain.section import Section
from homophily_sim.simulation.calendar import SemesterSchedule


def section_preference_score(
    student: StudentAgent,
    member_ids: Sequence[int],
    config: SimulationConfig,
    random_component: float,
) -> float:
    """Mix mean directed bond to members with one uniform random draw."""
    if not 0 <= random_component <= 1:
        raise ValueError("random component must be in [0, 1]")
    if not 0 <= config.gamma_section <= 1:
        raise ValueError("gamma_section must be in [0, 1]")
    mean_relationship = (
        fmean(
            student.relationship_to(peer_id, config.initial_relationship)
            for peer_id in member_ids
        )
        if member_ids else config.initial_relationship
    )
    return (
        config.gamma_section * mean_relationship
        + (1 - config.gamma_section) * random_component
    )


def assign_course_sections(
    course: Course,
    students: Sequence[StudentAgent],
    config: SimulationConfig,
    rng: Random,
) -> tuple[Section, ...]:
    """Assign every student once, with section sizes differing by at most one."""
    if len(students) != config.population_size:
        raise ValueError("student count differs from configuration")
    student_ids = [student.id for student in students]
    if len(set(student_ids)) != len(student_ids):
        raise ValueError("student IDs must be unique")
    if not 1 <= config.sections_per_course <= config.population_size:
        raise ValueError("invalid number of sections")

    base, remainder = divmod(len(students), config.sections_per_course)
    capacities = [base + (index < remainder) for index in range(config.sections_per_course)]
    rng.shuffle(capacities)
    members: list[list[int]] = [[] for _ in capacities]
    order = list(students)
    rng.shuffle(order)

    if course.semester == 1:
        offset = 0
        for section_index, capacity in enumerate(capacities):
            members[section_index].extend(student.id for student in order[offset:offset + capacity])
            offset += capacity
    else:
        for student in order:
            available = [
                index for index, capacity in enumerate(capacities)
                if len(members[index]) < capacity
            ]
            selected = max(
                available,
                key=lambda index: section_preference_score(
                    student, members[index], config, rng.random()
                ),
            )
            members[selected].append(student.id)

    return tuple(
        Section(
            course_id=course.course_id,
            section_id=f"{course.course_id}_S{index + 1}",
            student_ids=student_ids,
        )
        for index, student_ids in enumerate(members)
    )


def enroll_semester(
    students: Sequence[StudentAgent],
    schedule: SemesterSchedule,
    config: SimulationConfig,
    run_seed: int,
) -> dict[str, tuple[Section, ...]]:
    """Assign all courses, then record each student's semester enrollment."""
    if (
        len(students) != config.population_size
        or len({student.id for student in students}) != len(students)
    ):
        raise ValueError("semester enrollment requires the configured unique cohort")
    if any(student.semester > schedule.semester for student in students):
        raise ValueError("cannot enroll students in an earlier semester")
    if not 1 <= schedule.semester <= config.semesters:
        raise ValueError("semester outside configured cohort")
    counts = Counter(session.course_id for session in schedule.sessions)
    if len(counts) != config.courses_per_semester or set(counts.values()) != {
        config.sessions_per_course_per_week
    }:
        raise ValueError("schedule must contain each configured course")

    course_ids = sorted(counts)
    streams = np.random.SeedSequence([run_seed, schedule.semester, 7]).spawn(len(course_ids))
    sections_by_course = {
        course_id: assign_course_sections(
            Course(course_id=course_id, semester=schedule.semester),
            students,
            config,
            Random(int(stream.generate_state(1)[0])),
        )
        for course_id, stream in zip(course_ids, streams, strict=True)
    }
    assignments = {
        student.id: {
            course_id: section.section_id
            for course_id, sections in sections_by_course.items()
            for section in sections
            if student.id in section.student_ids
        }
        for student in students
    }
    for student in students:
        student.semester = schedule.semester
        student.course_assignments[schedule.semester] = course_ids.copy()
        student.section_assignments[schedule.semester] = assignments[student.id]
    return sections_by_course
