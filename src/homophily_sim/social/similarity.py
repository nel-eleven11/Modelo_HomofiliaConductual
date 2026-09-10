"""Attribute similarity does not itself create relationships."""

from math import fsum

from homophily_sim.config import SimulationConfig
from homophily_sim.domain.agent import StudentAgent


def interest_jaccard(left: set[str], right: set[str]) -> float:
    """Jaccard overlap; two empty sets have no modelled common interest."""
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def age_similarity(age_i: int, age_j: int, max_age_difference: int) -> float:
    """Linear age proximity clipped to [0,1]."""
    if max_age_difference <= 0:
        raise ValueError("max_age_difference must be positive")
    return max(0.0, 1.0 - abs(age_i - age_j) / max_age_difference)


def agent_similarity(
    first: StudentAgent, second: StudentAgent, config: SimulationConfig
) -> float:
    """Weighted Jaccard, age, sex and origin similarity."""
    weighted = fsum((
        config.w_interest * interest_jaccard(first.interests, second.interests),
        config.w_age * age_similarity(first.age, second.age, config.max_age_difference),
        config.w_sex * float(first.sex == second.sex),
        config.w_origin * float(first.origin == second.origin),
    ))
    return min(1.0, max(0.0, weighted))
