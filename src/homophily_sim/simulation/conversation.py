"""One conversation per section meeting, with directed interaction records."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil, fsum
from random import Random

import numpy as np

from homophily_sim.config import SimulationConfig
from homophily_sim.data.topics import TopicBank, topic_interest_score
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.domain.section import Section
from homophily_sim.domain.topic import Topic
from homophily_sim.llm.base import LanguageModelProvider, UtteranceRequest
from homophily_sim.nlp.base import SentimentAnalyzer
from homophily_sim.simulation.calendar import SemesterSchedule
from homophily_sim.social.evaluation import agreement, interaction_score, sentiment_valence
from homophily_sim.social.participation import participation_probability
from homophily_sim.social.relationships import update_relationship
from homophily_sim.social.similarity import agent_similarity


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Identifiers and simulation time for a section meeting."""

    run_id: str
    seed: int
    semester: int
    week: int
    day: int
    period: int
    course_id: str
    section_id: str

    @property
    def conversation_id(self) -> str:
        return (
            f"{self.run_id}:s{self.semester}:w{self.week}:d{self.day}:"
            f"p{self.period}:{self.course_id}:{self.section_id}"
        )


@dataclass(frozen=True, slots=True)
class ConversationEvent:
    """One main conversation and every directed message evaluation in it."""

    conversation_id: str
    initiator_id: int
    topic_id: str
    exposed_ids: tuple[int, ...]
    participant_ids: tuple[int, ...]
    initial_text: str
    records: tuple[InteractionRecord, ...]


def start_weights(students: Sequence[StudentAgent], epsilon_start: float) -> tuple[float, ...]:
    """Normalize strictly positive initiation weights among attendees."""
    if not students or not 0 < epsilon_start <= 1:
        raise ValueError("present students and epsilon_start > 0 are required")
    weights = [
        epsilon_start + (1 - epsilon_start) * student.extraversion / 10
        for student in students
    ]
    total = fsum(weights)
    return tuple(weight / total for weight in weights)


def _relevant_interests(student: StudentAgent, topic: Topic, bank: TopicBank) -> tuple[str, ...]:
    categories = {topic.category, *bank.related_categories[topic.category]}
    terms = categories | {
        subcategory for category in categories for subcategory in bank.taxonomy[category]
    }
    return tuple(sorted(student.interests & terms))


def _utterance_request(
    student: StudentAgent,
    topic: Topic,
    bank: TopicBank,
    config: SimulationConfig,
    previous_message: str | None,
) -> UtteranceRequest:
    return UtteranceRequest(
        agent_id=student.id,
        topic_id=topic.topic_id,
        topic_prompt=topic.prompt,
        orientation=student.topic_orientations[topic.topic_id],
        relevant_interests=_relevant_interests(student, topic, bank),
        extraversion=student.extraversion,
        previous_message=previous_message,
        max_words=config.utterance_max_words,
    )


def _simulation_timestamp(
    context: ConversationContext, config: SimulationConfig, record_index: int
) -> datetime:
    academic_day = (
        ((context.semester - 1) * config.weeks_per_semester + context.week - 1)
        * config.days_per_week + context.day - 1
    )
    return datetime(2000, 1, 1, 8) + timedelta(
        days=academic_day, hours=context.period - 1, seconds=record_index
    )


def _evaluate_message(
    sender: StudentAgent,
    receiver: StudentAgent,
    sender_text: str,
    topic: Topic,
    bank: TopicBank,
    config: SimulationConfig,
    sentiment_analyzer: SentimentAnalyzer,
    context: ConversationContext,
    participation_chance: float,
    record_index: int,
) -> InteractionRecord:
    before = receiver.relationship_to(sender.id, config.initial_relationship)
    agreement_value = agreement(
        receiver.topic_orientations[topic.topic_id], sender.topic_orientations[topic.topic_id]
    )
    sentiment = sentiment_analyzer.analyze(sender_text)
    valence = sentiment_valence(
        sentiment.p_negative, sentiment.p_neutral, sentiment.p_positive
    )
    score = interaction_score(agreement_value, valence, config)
    after = update_relationship(before, score, config.alpha_relationship)
    record = InteractionRecord(
        run_id=context.run_id,
        seed=context.seed,
        semester=context.semester,
        week=context.week,
        day=context.day,
        course_id=context.course_id,
        section_id=context.section_id,
        conversation_id=context.conversation_id,
        topic_id=topic.topic_id,
        sender_id=sender.id,
        receiver_id=receiver.id,
        sender_text=sender_text,
        receiver_interest=topic_interest_score(receiver.interests, topic, bank),
        similarity=agent_similarity(sender, receiver, config),
        relationship_before=before,
        participation_probability=participation_chance,
        agreement=agreement_value,
        sentiment_valence=valence,
        interaction_score=score,
        relationship_after=after,
        timestamp_simulation=_simulation_timestamp(context, config, record_index),
    )
    receiver.relationships[sender.id] = after
    return record


def run_conversation(
    students: Sequence[StudentAgent],
    bank: TopicBank,
    config: SimulationConfig,
    language_model: LanguageModelProvider,
    sentiment_analyzer: SentimentAnalyzer,
    rng: Random,
    context: ConversationContext,
) -> ConversationEvent:
    """Run one section meeting, with exposure separate from participation."""
    if len(students) < 2 or len({student.id for student in students}) != len(students):
        raise ValueError("a conversation needs at least two distinct students")
    initiator = rng.choices(
        list(students), weights=start_weights(students, config.epsilon_start)
    )[0]
    topic = rng.choice(bank.topics)
    initial_text = language_model.generate_utterance(
        _utterance_request(initiator, topic, bank, config, previous_message=None)
    ).text
    exposed = rng.sample(
        [student for student in students if student.id != initiator.id],
        k=ceil(len(students) / 4),
    )
    participants: list[tuple[StudentAgent, float]] = []
    records: list[InteractionRecord] = []
    for receiver in exposed:
        chance = participation_probability(
            receiver.extraversion,
            topic_interest_score(receiver.interests, topic, bank),
            receiver.relationship_to(initiator.id, config.initial_relationship),
            agent_similarity(initiator, receiver, config),
            config,
        )
        if rng.random() < chance:
            participants.append((receiver, chance))
        records.append(_evaluate_message(
            initiator, receiver, initial_text, topic, bank, config,
            sentiment_analyzer, context, chance, len(records),
        ))
    for responder, chance in participants:
        response_text = language_model.generate_utterance(
            _utterance_request(responder, topic, bank, config, previous_message=initial_text)
        ).text
        records.append(_evaluate_message(
            responder, initiator, response_text, topic, bank, config,
            sentiment_analyzer, context, chance, len(records),
        ))
    return ConversationEvent(
        conversation_id=context.conversation_id,
        initiator_id=initiator.id,
        topic_id=topic.topic_id,
        exposed_ids=tuple(student.id for student in exposed),
        participant_ids=tuple(student.id for student, _ in participants),
        initial_text=initial_text,
        records=tuple(records),
    )


def simulate_week(
    students: Sequence[StudentAgent],
    schedule: SemesterSchedule,
    sections_by_course: Mapping[str, Sequence[Section]],
    bank: TopicBank,
    config: SimulationConfig,
    run_seed: int,
    week: int,
    run_id: str,
    language_model: LanguageModelProvider,
    sentiment_analyzer: SentimentAnalyzer,
) -> list[ConversationEvent]:
    """Run one conversation per class and section, using a derived RNG stream."""
    schedule.week_sessions(week)
    if (
        len(students) != config.population_size
        or len({student.id for student in students}) != len(students)
    ):
        raise ValueError("week simulation requires the configured unique cohort")
    student_by_id = {student.id: student for student in students}
    course_ids = {session.course_id for session in schedule.sessions}
    if set(sections_by_course) != course_ids:
        raise ValueError("section assignments must match the semester schedule")
    for course_sections in sections_by_course.values():
        if len(course_sections) != config.sections_per_course or Counter(
            student_id for section in course_sections for student_id in section.student_ids
        ) != {student.id: 1 for student in students}:
            raise ValueError("each course must assign every student exactly once")
    stream = np.random.SeedSequence([run_seed, schedule.semester, week, 8])
    rng = Random(int(stream.generate_state(1)[0]))
    events: list[ConversationEvent] = []
    for session in schedule.sessions:
        for section in sections_by_course[session.course_id]:
            context = ConversationContext(
                run_id=run_id,
                seed=run_seed,
                semester=schedule.semester,
                week=week,
                day=session.day,
                period=session.period,
                course_id=session.course_id,
                section_id=section.section_id,
            )
            events.append(run_conversation(
                [student_by_id[student_id] for student_id in section.student_ids],
                bank, config, language_model, sentiment_analyzer, rng, context,
            ))
    return events
