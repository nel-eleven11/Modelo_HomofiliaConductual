"""Directed, accumulated relationship update."""


def update_relationship(old: float, score: float, alpha: float) -> float:
    """Blend an observer's prior bond with this interaction's score."""
    if any(not 0 <= value <= 1 for value in (old, score, alpha)):
        raise ValueError("old relationship, score and alpha must be in [0, 1]")
    return (1 - alpha) * old + alpha * score
