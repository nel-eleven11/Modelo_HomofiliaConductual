"""Manually inspect a local classifier against labeled Spanish utterances."""

import argparse
import json
from pathlib import Path

from homophily_sim.nlp.base import SentimentAnalyzer
from homophily_sim.nlp.sentiment import DEFAULT_SENTIMENT_MODEL, TransformersSentimentAnalyzer
from homophily_sim.social.evaluation import sentiment_valence


def evaluate_fixture(
    analyzer: SentimentAnalyzer, path: Path
) -> tuple[list[dict[str, str | float]], int]:
    """Return individual predictions and the number matching manual labels."""
    examples = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(examples, list) or not examples:
        raise ValueError("sentiment fixture must contain a nonempty list")
    rows: list[dict[str, str | float]] = []
    correct = 0
    for example in examples:
        if not isinstance(example, dict):
            raise ValueError("sentiment fixture entries must be objects")
        phrase = example.get("text")
        expected = example.get("label")
        if not isinstance(phrase, str) or not phrase.strip() or expected not in {
            "negative",
            "neutral",
            "positive",
        }:
            raise ValueError("sentiment fixture entries require text and a valid label")
        result = analyzer.analyze(phrase)
        scores = {
            "negative": result.p_negative,
            "neutral": result.p_neutral,
            "positive": result.p_positive,
        }
        predicted = max(scores, key=scores.__getitem__)
        correct += predicted == expected
        rows.append(
            {
                "text": phrase,
                "expected": expected,
                "predicted": predicted,
                "valence": sentiment_valence(
                    result.p_negative, result.p_neutral, result.p_positive
                ),
            }
        )
    return rows, correct


def main() -> None:
    """Load local weights once and display each comparison plus accuracy."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture", type=Path, default=Path("data/sentiment/validation_es_v1.json")
    )
    parser.add_argument("--model", default=DEFAULT_SENTIMENT_MODEL)
    args = parser.parse_args()
    analyzer = TransformersSentimentAnalyzer(model_name=args.model)
    rows, correct = evaluate_fixture(analyzer, args.fixture)
    for row in rows:
        print(f"{row['expected']:>8} -> {row['predicted']:<8} V={row['valence']:.3f} {row['text']}")
    print(f"Coincidencias: {correct}/{len(rows)}")


if __name__ == "__main__":
    main()
