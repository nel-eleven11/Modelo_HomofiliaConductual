"""One offline academic week with a small synthetic cohort."""

from pathlib import Path

from homophily_sim.config import load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.population import generate_population
from homophily_sim.data.topics import load_topics
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.calendar import generate_academic_calendar
from homophily_sim.simulation.conversation import simulate_week
from homophily_sim.simulation.enrollment import enroll_semester


def test_twenty_students_one_week_without_external_services() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_config(root / "configs/base.yaml").model_copy(update={"population_size": 20})
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )
    students = generate_population(config, bank, profile, seed=42)
    schedule = generate_academic_calendar(config, run_seed=42)[0]
    sections = enroll_semester(students, schedule, config, run_seed=42)
    events = simulate_week(
        students, schedule, sections, bank, config, run_seed=42, week=1,
        run_id="smoke", language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    assert len(events) == 36
    assert sum(len(event.records) for event in events) >= 72
