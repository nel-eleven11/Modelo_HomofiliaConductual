"""Small labeled Spanish fixture reports agreement with its manual labels."""

from pathlib import Path

import pytest

from homophily_sim.experiments.sentiment_pilot import evaluate_fixture
from homophily_sim.nlp.base import SentimentResult


class ExampleAnalyzer:
    def analyze(self, text: str) -> SentimentResult:
        if "Me alegra" in text:
            return SentimentResult(p_negative=0.1, p_neutral=0.1, p_positive=0.8)
        return SentimentResult(p_negative=0.1, p_neutral=0.8, p_positive=0.1)


def test_fixture_evaluation_counts_predictions(tmp_path: Path) -> None:
    fixture = tmp_path / "sentences.json"
    fixture.write_text(
        '[{"text":"Me alegra aprender.","label":"positive"},'
        '{"text":"Tengo clase mañana.","label":"neutral"},'
        '{"text":"No me gusta esperar.","label":"negative"}]',
        encoding="utf-8",
    )
    rows, correct = evaluate_fixture(ExampleAnalyzer(), fixture)
    assert [row["predicted"] for row in rows] == ["positive", "neutral", "neutral"]
    assert correct == 2
    assert rows[0]["valence"] == pytest.approx(0.85)
