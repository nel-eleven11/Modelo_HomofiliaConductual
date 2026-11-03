"""Operational expressed-tone probabilities and seeded draws."""

from pathlib import Path

import pytest

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.llm.base import UtteranceRequest
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.tone import sample_tone

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "configs/base.yaml")


@pytest.mark.parametrize(
    ("interest", "neutral"), [(0.0, 0.7), (0.5, 0.5), (1.0, 0.3)]
)
def test_interest_controls_emotional_expression_without_sign_bias(
    interest: float, neutral: float,
) -> None:
    sample = sample_tone(interest, CONFIG, 42, "message-1")
    assert sample.neutral_probability == pytest.approx(neutral)
    assert sample.negative_probability == pytest.approx((1 - neutral) / 2)
    assert sample.positive_probability == sample.negative_probability
    assert sample == sample_tone(interest, CONFIG, 42, "message-1")
    assert sample.valence == {"negative": 0.0, "neutral": 0.5,
                              "positive": 1.0}[sample.tone]


def test_controls_and_invalid_parameters() -> None:
    neutral = CONFIG.model_copy(update={"sentiment_rule": "neutral_constant"})
    fixed = CONFIG.model_copy(update={"sentiment_rule": "fixed_random"})
    assert sample_tone(1.0, neutral, 1, "a").tone == "neutral"
    assert sample_tone(1.0, fixed, 1, "a").neutral_probability == 0.7
    assert sample_tone(0.0, fixed, 1, "a").neutral_probability == 0.7
    with pytest.raises(ValueError, match="interest"):
        sample_tone(1.1, CONFIG, 1, "a")
    with pytest.raises(ValueError, match="neutral probability"):
        SimulationConfig.model_validate({
            **CONFIG.model_dump(), "sentiment_neutral_base": 0.2,
            "sentiment_interest_effect": 0.4,
        })


def test_mock_text_keeps_stance_separate_from_tone() -> None:
    provider = MockLanguageModelProvider()
    request = UtteranceRequest(
        agent_id=1, topic_id="topic", topic_prompt="¿Te parece bien?",
        orientation=-1, relevant_interests=(), extraversion=5, max_words=40,
        tone="positive",
    )
    friendly_disagreement = provider.generate_utterance(request).text
    critical_disagreement = provider.generate_utterance(
        request.model_copy(update={"tone": "negative"})
    ).text
    assert "No estoy a favor" in friendly_disagreement
    assert "No estoy a favor" in critical_disagreement
    assert friendly_disagreement != critical_disagreement
