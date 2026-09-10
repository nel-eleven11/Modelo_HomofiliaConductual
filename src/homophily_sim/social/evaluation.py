"""Instant agreement and sentiment-based evaluation."""

from homophily_sim.config import SimulationConfig


def agreement(orientation_i: float, orientation_j: float) -> float:
    """Equal orientations score one; opposite extremes score zero."""
    if not -1 <= orientation_i <= 1 or not -1 <= orientation_j <= 1:
        raise ValueError("orientations must be in [-1, 1]")
    return 1 - abs(orientation_i - orientation_j) / 2


def sentiment_valence(p_negative: float, p_neutral: float, p_positive: float) -> float:
    """Convert normalized three-class sentiment to [0, 1] valence."""
    probabilities = (p_negative, p_neutral, p_positive)
    if any(not 0 <= value <= 1 for value in probabilities):
        raise ValueError("sentiment probabilities must be in [0, 1]")
    if abs(sum(probabilities) - 1) > 1e-6:
        raise ValueError("sentiment probabilities must sum to 1")
    return p_positive + 0.5 * p_neutral


def interaction_score(agreement_value: float, valence: float, config: SimulationConfig) -> float:
    """Combine agreement and valence without adding topical interest again."""
    if not 0 <= agreement_value <= 1 or not 0 <= valence <= 1:
        raise ValueError("agreement and valence must be in [0, 1]")
    return config.w_agreement * agreement_value + config.w_sentiment * valence
