"""Local multilingual text classifier behind the sentiment analyzer contract."""

import math
from collections.abc import Callable

from homophily_sim.nlp.base import SentimentResult

DEFAULT_SENTIMENT_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
_LABELS = {"negative", "neutral", "positive"}


class TransformersSentimentAnalyzer:
    """Classify Spanish utterances locally with a three-class Transformers model."""

    def __init__(
        self,
        model_name: str = DEFAULT_SENTIMENT_MODEL,
        *,
        classifier: Callable[..., object] | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("sentiment model name cannot be empty")
        self.model_name = model_name
        if classifier is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "Local sentiment analysis requires transformers and torch; "
                    "install requirements-nlp.txt"
                ) from exc
            classifier = pipeline(
                "text-classification", model=model_name, framework="pt", device=-1
            )
        self.classifier = classifier
        self._cache: dict[str, SentimentResult] = {}

    def analyze(self, text: str) -> SentimentResult:
        """Return normalized probabilities for negative, neutral and positive."""
        if not text.strip():
            raise ValueError("sentiment text cannot be empty")
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        raw = self.classifier(text, top_k=None, truncation=True)
        if not isinstance(raw, list) or len(raw) != 3:
            raise ValueError("sentiment classifier must return three scores")
        scores: dict[str, float] = {}
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError("sentiment classifier returned an invalid score")
            label = entry.get("label")
            score = entry.get("score")
            if (
                not isinstance(label, str)
                or label.lower() not in _LABELS
                or label.lower() in scores
                or not isinstance(score, (float, int))
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                raise ValueError("sentiment classifier returned an invalid score")
            scores[label.lower()] = float(score)
        if scores.keys() != _LABELS:
            raise ValueError("sentiment classifier labels are incomplete")
        total = sum(scores.values())
        if total <= 0:
            raise ValueError("sentiment classifier scores sum to zero")
        result = SentimentResult(
            p_negative=scores["negative"] / total,
            p_neutral=scores["neutral"] / total,
            p_positive=scores["positive"] / total,
        )
        if len(self._cache) >= 4096:
            self._cache.pop(next(iter(self._cache)))
        self._cache[text] = result
        return result
