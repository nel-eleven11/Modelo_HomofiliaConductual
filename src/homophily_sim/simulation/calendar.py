"""Seeded academic schedules fixed throughout each semester."""

from dataclasses import dataclass
from random import Random

import numpy as np

from homophily_sim.config import SimulationConfig


@dataclass(frozen=True, slots=True)
class ClassSession:
    """One recurring weekly period for a course."""

    course_id: str
    day: int
    period: int


@dataclass(frozen=True, slots=True)
class SemesterSchedule:
    """Weekly schedule repeated without change for all semester weeks."""

    semester: int
    weeks_per_semester: int
    sessions: tuple[ClassSession, ...]

    def week_sessions(self, week: int) -> tuple[ClassSession, ...]:
        """Return the fixed course timetable for a valid week number."""
        if not 1 <= week <= self.weeks_per_semester:
            raise ValueError("week outside semester")
        return self.sessions


def generate_semester_schedule(
    config: SimulationConfig,
    semester: int,
    rng: Random,
) -> SemesterSchedule:
    """Assign each of six courses to two distinct days with balanced loads."""
    if not 1 <= semester <= config.semesters:
        raise ValueError("semester outside configured cohort")
    if (config.days_per_week, config.courses_per_semester,
            config.sessions_per_course_per_week) != (5, 6, 2):
        raise ValueError("calendar v1 requires five days, six courses and two weekly meetings")
    capacities = [2, 2, 2, 3, 3]
    rng.shuffle(capacities)
    courses = [f"S{semester:02d}_C{number:02d}" for number in range(1, 7)]
    rng.shuffle(courses)
    assigned: list[list[str]] = [[] for _ in range(5)]

    def assign(course_index: int) -> bool:
        if course_index == len(courses):
            return True
        candidates = [
            (left, right)
            for left in range(5) for right in range(left + 1, 5)
            if len(assigned[left]) < capacities[left] and len(assigned[right]) < capacities[right]
        ]
        rng.shuffle(candidates)
        for left, right in candidates:
            assigned[left].append(courses[course_index])
            assigned[right].append(courses[course_index])
            if assign(course_index + 1):
                return True
            assigned[left].pop()
            assigned[right].pop()
        return False

    if not assign(0):
        raise RuntimeError("unable to satisfy semester schedule constraints")
    sessions: list[ClassSession] = []
    for day, day_courses in enumerate(assigned, start=1):
        rng.shuffle(day_courses)
        sessions.extend(
            ClassSession(course_id=course_id, day=day, period=period)
            for period, course_id in enumerate(day_courses, start=1)
        )
    return SemesterSchedule(
        semester=semester,
        weeks_per_semester=config.weeks_per_semester,
        sessions=tuple(sessions),
    )


def generate_academic_calendar(
    config: SimulationConfig, run_seed: int
) -> tuple[SemesterSchedule, ...]:
    """Derive one independent schedule seed for each of ten semesters."""
    seeds = np.random.SeedSequence(run_seed).spawn(config.semesters)
    return tuple(
        generate_semester_schedule(
            config,
            semester,
            Random(int(seed.generate_state(1)[0])),
        )
        for semester, seed in enumerate(seeds, start=1)
    )
