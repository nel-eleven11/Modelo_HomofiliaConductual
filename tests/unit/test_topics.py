"""Versioned taxonomy validation and deterministic affinity."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from homophily_sim.data.topics import TopicBank, load_topics, topic_interest_score

BANK = load_topics(Path(__file__).resolve().parents[2] / "data/topics/topics_v1.yaml")


def test_topic_bank_is_versioned_and_unique() -> None:
    assert BANK.topic_bank_version == "v1"
    assert 30 <= len(BANK.topics) <= 50
    assert len({topic.topic_id for topic in BANK.topics}) == len(BANK.topics)
    assert all(topic.category in BANK.taxonomy for topic in BANK.topics)


def test_interest_score_uses_taxonomy() -> None:
    topic = next(topic for topic in BANK.topics if topic.category == "programming")
    assert topic_interest_score({topic.subcategory}, topic, BANK) == 1
    assert topic_interest_score({"technology"}, topic, BANK) == 0.5
    assert topic_interest_score({"animals"}, topic, BANK) == 0
    assert topic_interest_score({"technology"}, topic, BANK) == 0.5


def test_duplicate_ids_are_rejected() -> None:
    raw = BANK.model_dump()
    raw["topics"] = [*raw["topics"], raw["topics"][0]]
    with pytest.raises(ValidationError):
        TopicBank.model_validate(raw)
