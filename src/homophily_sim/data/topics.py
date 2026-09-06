"""Load and score a versioned taxonomy shared by interests and topics."""

from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from homophily_sim.domain.topic import Topic


class TopicBank(BaseModel):
    """A validated resource containing topics and related interest categories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic_bank_version: str = Field(min_length=1)
    taxonomy: dict[str, list[str]]
    related_categories: dict[str, list[str]]
    topics: tuple[Topic, ...]

    @model_validator(mode="after")
    def validate_contents(self) -> Self:
        if not self.taxonomy or not self.topics:
            raise ValueError("taxonomy and topics cannot be empty")
        terms: set[str] = set(self.taxonomy)
        for category, subcategories in self.taxonomy.items():
            if not category or not subcategories or len(subcategories) != len(set(subcategories)):
                raise ValueError("each category needs unique subcategories")
            if any(not term for term in subcategories):
                raise ValueError("subcategory names cannot be empty")
            if terms.intersection(subcategories):
                raise ValueError("categories and subcategories must not overlap")
            terms.update(subcategories)
        if set(self.related_categories) != set(self.taxonomy):
            raise ValueError("related_categories must cover every category")
        for category, neighbors in self.related_categories.items():
            if category in neighbors or len(neighbors) != len(set(neighbors)):
                raise ValueError("related categories cannot include self or duplicates")
            if any(neighbor not in self.taxonomy for neighbor in neighbors):
                raise ValueError("unknown related category")
            if any(category not in self.related_categories[neighbor] for neighbor in neighbors):
                raise ValueError("related categories must be symmetric")
        ids: set[str] = set()
        for topic in self.topics:
            if topic.topic_id in ids:
                raise ValueError("topic IDs must be unique")
            ids.add(topic.topic_id)
            if topic.category not in self.taxonomy:
                raise ValueError("topic has unknown category")
            if topic.subcategory not in self.taxonomy[topic.category]:
                raise ValueError("topic has unknown subcategory")
        return self

    @property
    def interest_terms(self) -> frozenset[str]:
        """Allowed interest labels from the same versioned taxonomy."""
        return frozenset(self.taxonomy).union(
            subcategory for names in self.taxonomy.values() for subcategory in names
        )


def validate_topic_bank(bank: TopicBank) -> TopicBank:
    """Revalidate a possibly modified bank before downstream use."""
    return TopicBank.model_validate(bank.model_dump())


def load_topics(path: str | Path) -> TopicBank:
    """Read a versioned topic bank from YAML."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return TopicBank.model_validate(raw)


def related_categories(category: str, bank: TopicBank) -> frozenset[str]:
    """Return directly related category labels."""
    if category not in bank.taxonomy:
        raise ValueError(f"unknown category: {category}")
    return frozenset(bank.related_categories[category])


def topic_interest_score(interests: set[str], topic: Topic, bank: TopicBank) -> float:
    """Exact category/subcategory match 1, related category 0.5, otherwise 0."""
    if interests - bank.interest_terms:
        raise ValueError("interests must use the versioned taxonomy")
    if topic.category in interests or topic.subcategory in interests:
        return 1.0
    related = related_categories(topic.category, bank)
    if any(
        interest in related
        or any(interest in bank.taxonomy[category] for category in related)
        for interest in interests
    ):
        return 0.5
    return 0.0
