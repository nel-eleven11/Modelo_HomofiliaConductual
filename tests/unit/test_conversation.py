"""Mock conversations use seeded choices and directed relationship updates."""

from math import ceil
from pathlib import Path
from random import Random

import pytest

from homophily_sim.config import load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.population import generate_population
from homophily_sim.data.topics import TopicBank, load_topics
from homophily_sim.domain.agent import Origin, Sex, StudentAgent
from homophily_sim.domain.topic import PolarizationLevel, Topic
from homophily_sim.llm.base import UtteranceRequest
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.calendar import generate_academic_calendar
from homophily_sim.simulation.conversation import (
    ConversationContext,
    ConversationEvent,
    run_conversation,
    simulate_week,
    start_weights,
)
from homophily_sim.simulation.enrollment import enroll_semester

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "configs/base.yaml")
BANK = load_topics(ROOT / "data/topics/topics_v1.yaml")
PROFILE = load_demographic_profile(
    ROOT / "data/demographics/profiles_v1.yaml", CONFIG.demographic_profile
)


def small_week(seed: int) -> tuple[list[StudentAgent], list[ConversationEvent]]:
    config = CONFIG.model_copy(update={"population_size": 20})
    students = generate_population(config, BANK, PROFILE, seed)
    schedule = generate_academic_calendar(config, seed)[0]
    sections = enroll_semester(students, schedule, config, seed)
    events = simulate_week(
        students, schedule, sections, BANK, config, run_seed=seed, week=1,
        run_id="pilot", language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    return students, events


def test_mock_language_and_sentiment_need_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mock attempted network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    provider = MockLanguageModelProvider()
    request = UtteranceRequest(
        agent_id=1, topic_id="technology_privacy", topic_prompt="¿Te preocupa la privacidad?",
        orientation=-1, relevant_interests=("technology",), extraversion=5,
        previous_message=None, max_words=30,
    )
    result = provider.generate_utterance(request)
    assert result.text and len(result.text.split()) <= 30
    assert result.text.startswith("No estoy a favor")
    assert provider.generate_utterance(request) == result
    positive = provider.generate_utterance(request.model_copy(update={"orientation": 1}))
    assert positive.text.startswith("Estoy a favor")
    sentiment = MockSentimentAnalyzer().analyze(result.text)
    assert (sentiment.p_negative, sentiment.p_neutral, sentiment.p_positive) == (0, 1, 0)


def test_start_weights_stay_positive_and_normalized() -> None:
    students = [
        StudentAgent(id=0, age=18, sex=Sex.FEMALE, origin=Origin.GUATEMALA_DEPARTMENT,
                     semester=1, interests={"technology"}, extraversion=0),
        StudentAgent(id=1, age=18, sex=Sex.MALE, origin=Origin.REST_OF_COUNTRY,
                     semester=1, interests={"technology"}, extraversion=10),
    ]
    weights = start_weights(students, CONFIG.epsilon_start)
    assert all(weight > 0 for weight in weights)
    assert sum(weights) == pytest.approx(1)
    assert weights[1] > weights[0]


def test_exposure_and_reply_update_opposite_directions() -> None:
    topic = Topic(
        topic_id="privacy", category="technology", subcategory="privacy",
        prompt="¿Te importa la privacidad?", polarization_level=PolarizationLevel.LOW,
    )
    bank = TopicBank(
        topic_bank_version="test", taxonomy={"technology": ["privacy"]},
        related_categories={"technology": []}, topics=(topic,),
    )
    students = [
        StudentAgent(id=0, age=18, sex=Sex.FEMALE, origin=Origin.GUATEMALA_DEPARTMENT,
                     semester=1, interests={"technology"}, extraversion=0,
                     topic_orientations={"privacy": 1}),
        StudentAgent(id=1, age=18, sex=Sex.MALE, origin=Origin.REST_OF_COUNTRY,
                     semester=1, interests={"technology"}, extraversion=10,
                     topic_orientations={"privacy": -1}),
    ]
    context = ConversationContext(
        run_id="pilot", seed=1, semester=1, week=1, day=1, period=1,
        course_id="C01", section_id="A",
    )
    always_reply = CONFIG.model_copy(update={"beta_0": 100})
    event = run_conversation(
        students, bank, always_reply, MockLanguageModelProvider(),
        MockSentimentAnalyzer(), Random(1), context,
    )
    assert len(event.exposed_ids) == len(event.participant_ids) == 1
    assert len(event.records) == 2
    first, reply = event.records
    assert (first.sender_id, first.receiver_id) == (reply.receiver_id, reply.sender_id)
    assert first.relationship_before == reply.relationship_before == 0.5
    assert students[first.receiver_id].relationships[first.sender_id] == first.relationship_after
    assert students[reply.receiver_id].relationships[reply.sender_id] == reply.relationship_after
    assert all(record.run_id == context.run_id and record.seed == context.seed
               for record in event.records)

    never_reply = CONFIG.model_copy(update={"beta_0": -100})
    fresh = [student.model_copy(deep=True) for student in students]
    event_without_reply = run_conversation(
        fresh, bank, never_reply, MockLanguageModelProvider(),
        MockSentimentAnalyzer(), Random(1), context,
    )
    assert len(event_without_reply.exposed_ids) == 1
    assert event_without_reply.participant_ids == ()
    assert len(event_without_reply.records) == 1

    baseline_outcomes = {
        bool(run_conversation(
            [student.model_copy(deep=True) for student in students], bank, CONFIG,
            MockLanguageModelProvider(), MockSentimentAnalyzer(), Random(seed), context,
        ).participant_ids)
        for seed in range(16)
    }
    assert baseline_outcomes == {False, True}


def test_one_week_with_twenty_agents_is_reproducible() -> None:
    students, events = small_week(42)
    students_again, events_again = small_week(42)
    assert len(events) == 36  # 12 weekly course sessions, each with three sections.
    assert events == events_again
    assert [student.relationships for student in students] == [
        student.relationships for student in students_again
    ]
    assert len({event.conversation_id for event in events}) == 36
    for event in events:
        assert len(event.exposed_ids) == ceil(20 / 3 / 4)
        assert set(event.participant_ids) <= set(event.exposed_ids)
        assert event.initiator_id not in event.exposed_ids
        assert len(event.records) == len(event.exposed_ids) + len(event.participant_ids)
        assert all(0 <= record.relationship_after <= 1 for record in event.records)
