"""Participation probability; Bernoulli sampling stays with the engine."""

from math import exp

from homophily_sim.config import SimulationConfig


def sigmoid(value: float) -> float:
    """Stable logistic transform for either sign of the input."""
    if value >= 0:
        return 1 / (1 + exp(-value))
    positive = exp(value)
    return positive / (1 + positive)


def participation_probability(
    receiver_extraversion: float,
    receiver_interest: float,
    relationship_receiver_to_initiator: float,
    similarity: float,
    config: SimulationConfig,
) -> float:
    """Compute P_ij with independent homophily and relationship parameters."""
    if not 0 <= receiver_extraversion <= 10:
        raise ValueError("receiver_extraversion must be in [0, 10]")
    if any(not 0 <= value <= 1 for value in (
        receiver_interest, relationship_receiver_to_initiator, similarity
    )):
        raise ValueError("interest, relationship and similarity must be in [0, 1]")
    normalized_extraversion = receiver_extraversion / 10
    linear = (
        config.beta_0
        + config.beta_E * normalized_extraversion
        + config.beta_I * receiver_interest
        + (config.beta_R + config.lambda_R * config.h)
        * relationship_receiver_to_initiator
        + config.lambda_S * config.h * similarity
    )
    return sigmoid(linear)
