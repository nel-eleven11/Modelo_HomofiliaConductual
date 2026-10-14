"""The local classifier adapter preserves the three-class sentiment contract."""

import pytest

from homophily_sim.nlp.sentiment import TransformersSentimentAnalyzer
from homophily_sim.social.evaluation import sentiment_valence


def test_three_scores_are_mapped_and_normalized() -> None:
    def classifier(text: str, *, top_k: None, truncation: bool) -> list[dict[str, object]]:
        assert text == "Me encanta programar."
        assert top_k is None and truncation
        return [
            {"label": "positive", "score": 0.6},
            {"label": "negative", "score": 0.1},
            {"label": "neutral", "score": 0.3},
        ]

    analyzer = TransformersSentimentAnalyzer(classifier=classifier)
    result = analyzer.analyze("Me encanta programar.")

    assert (result.p_negative, result.p_neutral, result.p_positive) == pytest.approx(
        (0.1, 0.3, 0.6)
    )
    valence = sentiment_valence(result.p_negative, result.p_neutral, result.p_positive)
    assert valence == pytest.approx(0.75)


@pytest.mark.parametrize(
    "scores",
    [
        [{"label": "positive", "score": 1.0}],
        [
            {"label": "negative", "score": 0.2},
            {"label": "neutral", "score": 0.2},
            {"label": "unknown", "score": 0.6},
        ],
        [
            {"label": "negative", "score": -1.0},
            {"label": "neutral", "score": 0.5},
            {"label": "positive", "score": 0.5},
        ],
    ],
)
def test_invalid_classifier_outputs_are_rejected(scores: list[dict[str, object]]) -> None:
    def classifier(text: str, *, top_k: None, truncation: bool) -> list[dict[str, object]]:
        return scores

    analyzer = TransformersSentimentAnalyzer(classifier=classifier)
    with pytest.raises(ValueError, match="sentiment classifier"):
        analyzer.analyze("Un mensaje")


def test_blank_text_is_rejected_before_classification() -> None:
    def classifier(text: str, *, top_k: None, truncation: bool) -> list[dict[str, object]]:
        raise AssertionError("classifier should not run")

    analyzer = TransformersSentimentAnalyzer(classifier=classifier)
    with pytest.raises(ValueError, match="empty"):
        analyzer.analyze("  ")


def test_repeated_utterance_is_classified_once() -> None:
    calls = 0

    def classifier(text: str, *, top_k: None, truncation: bool) -> list[dict[str, object]]:
        nonlocal calls
        calls += 1
        return [
            {"label": "negative", "score": 0.0},
            {"label": "neutral", "score": 1.0},
            {"label": "positive", "score": 0.0},
        ]

    analyzer = TransformersSentimentAnalyzer(classifier=classifier)
    assert analyzer.analyze("La misma intervención.") == analyzer.analyze("La misma intervención.")
    assert calls == 1
