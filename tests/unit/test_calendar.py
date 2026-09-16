"""Academic timetable constraints and reproducibility."""

from collections import Counter
from pathlib import Path

import pytest

from homophily_sim.config import load_config
from homophily_sim.simulation.calendar import generate_academic_calendar

CONFIG = load_config(Path(__file__).resolve().parents[2] / "configs/base.yaml")


def test_full_calendar_is_seeded_and_balanced() -> None:
    first = generate_academic_calendar(CONFIG, 42)
    again = generate_academic_calendar(CONFIG, 42)
    assert first == again
    assert len(first) == 10
    for semester in first:
        sessions = semester.week_sessions(1)
        assert semester.week_sessions(20) is sessions
        assert len(sessions) == 12
        assert sorted(Counter(session.day for session in sessions).values()) == [2, 2, 2, 3, 3]
        assert set(Counter(session.course_id for session in sessions).values()) == {2}
        assert len({(session.day, session.course_id) for session in sessions}) == 12
        assert all(1 <= session.period <= 3 for session in sessions)
    with pytest.raises(ValueError):
        first[0].week_sessions(21)


def test_schedule_constraints_hold_across_seeds() -> None:
    for seed in range(12):
        calendar = generate_academic_calendar(CONFIG, seed)
        for semester in calendar:
            sessions = semester.sessions
            by_day = Counter(session.day for session in sessions)
            by_course = Counter(session.course_id for session in sessions)
            assert sorted(by_day.values()) == [2, 2, 2, 3, 3]
            assert len(by_course) == 6 and set(by_course.values()) == {2}
            assert len({(session.course_id, session.day) for session in sessions}) == 12
            assert len({(session.day, session.period) for session in sessions}) == 12
