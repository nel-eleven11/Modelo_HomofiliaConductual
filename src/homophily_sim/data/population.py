"""Reproducible synthetic cohort generation with independent random streams."""

import numpy as np

from homophily_sim.config import SimulationConfig
from homophily_sim.data.demographics import DemographicProfile
from homophily_sim.data.topics import TopicBank
from homophily_sim.domain.agent import Origin, Sex, StudentAgent


def _truncated_extraversion(rng: np.random.Generator, mean: float, std: float) -> float:
    """Resample a normal draw until it falls within the defined scale."""
    if std == 0:
        return mean
    while True:
        value = float(rng.normal(mean, std))
        if 0 <= value <= 10:
            return value


def generate_population(
    config: SimulationConfig,
    bank: TopicBank,
    profile: DemographicProfile,
    seed: int,
) -> list[StudentAgent]:
    """Create the same ordered cohort for equal inputs and seed."""
    if profile.name != config.demographic_profile:
        raise ValueError("demographic profile differs from configuration")
    streams = np.random.SeedSequence(seed).spawn(4)
    demographic_rng, interest_rng, extraversion_rng, orientation_rng = (
        np.random.default_rng(stream) for stream in streams
    )
    ages = sorted(profile.age_probabilities)
    age_weights = [profile.age_probabilities[age] for age in ages]
    terms = sorted(bank.interest_terms)
    if len(terms) < 5:
        raise ValueError("topic bank needs at least five interest terms")
    interest_counts = sorted(config.interest_count_probabilities)
    interest_weights = [config.interest_count_probabilities[count] for count in interest_counts]
    topic_ids = sorted(topic.topic_id for topic in bank.topics)
    population: list[StudentAgent] = []
    for student_id in range(config.population_size):
        interest_count = int(interest_rng.choice(interest_counts, p=interest_weights))
        interests = set(interest_rng.choice(terms, size=interest_count, replace=False).tolist())
        population.append(
            StudentAgent(
                id=student_id,
                age=int(demographic_rng.choice(ages, p=age_weights)),
                sex=(Sex.FEMALE if demographic_rng.random() < profile.female_probability
                     else Sex.MALE),
                origin=(Origin.GUATEMALA_DEPARTMENT
                        if demographic_rng.random() < profile.guatemala_department_probability
                        else Origin.REST_OF_COUNTRY),
                semester=1,
                interests=interests,
                extraversion=_truncated_extraversion(
                    extraversion_rng, config.extraversion_mean, config.extraversion_std
                ),
                topic_orientations={
                    topic_id: float(orientation_rng.uniform(-1, 1)) for topic_id in topic_ids
                },
            )
        )
    return population
