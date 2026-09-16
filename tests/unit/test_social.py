"""Small checks of the model's social equations."""

from math import exp
from pathlib import Path

import pytest

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.domain.agent import Origin, Sex, StudentAgent
from homophily_sim.social.evaluation import agreement, interaction_score, sentiment_valence
from homophily_sim.social.participation import participation_probability, sigmoid
from homophily_sim.social.relationships import update_relationship
from homophily_sim.social.similarity import age_similarity, agent_similarity, interest_jaccard

BASE = load_config(Path(__file__).resolve().parents[2] / "configs/base.yaml")


def probability(config: SimulationConfig, similarity: float, relationship: float) -> float:
    return participation_probability(5, 0.5, relationship, similarity, config)


def test_similarity_primitives_and_bounds() -> None:
    assert interest_jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert age_similarity(18, 40, 10) == 0
    assert age_similarity(19, 19, 10) == 1


def test_homophily_amplifies_similarity_and_relationship_effects() -> None:
    low = BASE.model_copy(update={"h": 0.2})
    high = BASE.model_copy(update={"h": 0.8})
    low_similarity_effect = probability(low, 1, 0.5) - probability(low, 0, 0.5)
    high_similarity_effect = probability(high, 1, 0.5) - probability(high, 0, 0.5)
    low_relationship_effect = probability(low, 0.5, 1) - probability(low, 0.5, 0)
    high_relationship_effect = probability(high, 0.5, 1) - probability(high, 0.5, 0)
    assert 0 < low_similarity_effect < high_similarity_effect
    assert 0 < low_relationship_effect < high_relationship_effect
    assert 0 < probability(BASE, 0.5, 0.5) < 1


def test_evaluation_and_relationship_blend() -> None:
    assert agreement(-1, 1) == 0
    assert agreement(0.3, 0.3) == 1
    assert sentiment_valence(0.2, 0.2, 0.6) == 0.7
    score = interaction_score(1, 0, BASE)
    assert score == 0.75
    assert update_relationship(0.5, score, BASE.alpha_relationship) == 0.55
    assert update_relationship(0.5, 0, 0.2) < 0.5
    assert update_relationship(0.5, 1, 0.2) > 0.5


def test_agent_similarity_stays_bounded() -> None:
    first = StudentAgent(id=0, age=18, sex=Sex.FEMALE,
                         origin=Origin.GUATEMALA_DEPARTMENT, semester=1,
                         interests={"technology"}, extraversion=5)
    second = StudentAgent(id=1, age=30, sex=Sex.MALE,
                          origin=Origin.REST_OF_COUNTRY, semester=1,
                          interests={"animals"}, extraversion=5)
    assert agent_similarity(first, first, BASE) == 1
    assert 0 <= agent_similarity(first, second, BASE) <= 1


def test_participation_matches_equation_and_handles_extremes() -> None:
    linear = -2.3 + 0.8 * 0.5 + 1.4 * 0.5 + (0.6 + 0.5) * 0.5 + 0.5 * 0.4
    expected = 1 / (1 + exp(-linear))
    assert participation_probability(5, 0.5, 0.5, 0.4, BASE) == pytest.approx(expected)
    assert sigmoid(-1000) == 0
    assert sigmoid(1000) == 1
    with pytest.raises(ValueError):
        participation_probability(11, 0.5, 0.5, 0.4, BASE)
