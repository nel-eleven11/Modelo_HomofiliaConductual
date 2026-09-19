"""Offline neutral sentiment baseline."""

from homophily_sim.nlp.base import SentimentResult


class MockSentimentAnalyzer:
    """Return neutral sentiment so agreement drives the offline pilot."""

    def analyze(self, text: str) -> SentimentResult:
        return SentimentResult(p_negative=0, p_neutral=1, p_positive=0)
