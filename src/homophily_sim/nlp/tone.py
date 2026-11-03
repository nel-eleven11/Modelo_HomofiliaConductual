"""Seeded expressed-tone rule for offline messages, independent of stance."""

from dataclasses import dataclass
from hashlib import sha256
from random import Random
from typing import Literal

from homophily_sim.config import SimulationConfig

Tone = Literal["negative", "neutral", "positive"]
RULE_VERSION = "expressed-tone-v1"


@dataclass(frozen=True, slots=True)
class ToneSample:
    tone: Tone
    valence: float
    negative_probability: float
    neutral_probability: float
    positive_probability: float
    rng_stream: str


def sample_tone(interest: float, config: SimulationConfig, seed: int, identity: str) -> ToneSample:
    """Use a per-message stream so tone draws never consume participation RNG."""
    if not 0 <= interest <= 1:
        raise ValueError("sender topic interest must be in [0, 1]")
    if config.sentiment_rule == "neutral_constant":
        neutral = 1.0
    elif config.sentiment_rule == "fixed_random":
        neutral = config.sentiment_neutral_base
    else:
        neutral = config.sentiment_neutral_base - config.sentiment_interest_effect * interest
    side = (1.0 - neutral) / 2
    stream = f"{RULE_VERSION}:{seed}:{identity}"
    draw = Random(int.from_bytes(sha256(stream.encode()).digest()[:8], "big")).random()
    tone: Tone = "negative" if draw < side else "neutral" if draw < side + neutral else "positive"
    return ToneSample(tone, {"negative": 0.0, "neutral": 0.5, "positive": 1.0}[tone],
                      side, neutral, side, stream)
