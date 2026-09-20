"""Roundtrip checks for run provenance and typed tabular output."""

from datetime import UTC, datetime

import pytest

from homophily_sim.config import load_config
from homophily_sim.domain.agent import Origin, Sex, StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.io.metadata import make_run_metadata
from homophily_sim.io.results import load_run, save_run


def test_run_roundtrip(tmp_path):  # type: ignore[no-untyped-def]
    config = load_config("configs/homophily_medium.yaml").model_copy(
        update={"population_size": 2, "sections_per_course": 2}
    )
    agents = [
        StudentAgent(
            id=0,
            age=18,
            sex=Sex.FEMALE,
            origin=Origin.GUATEMALA_DEPARTMENT,
            semester=1,
            interests={"music", "technology"},
            extraversion=6.5,
            topic_orientations={"tech_ai_jobs": -0.25},
            course_assignments={1: ["C1"]},
            section_assignments={1: {"C1": "S1"}},
            relationships={1: 0.72},
        ),
        StudentAgent(
            id=1,
            age=19,
            sex=Sex.MALE,
            origin=Origin.REST_OF_COUNTRY,
            semester=1,
            interests={"music"},
            extraversion=3.0,
        ),
    ]
    moment = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    metadata = make_run_metadata(
        config,
        run_id="pilot-1",
        seed=42,
        prompt_version="v1",
        topic_bank_version="v1",
        demographic_calibration_version="v1",
        model_name="mock",
        start_time=moment,
        end_time=moment,
    )
    interaction = InteractionRecord(
        run_id="pilot-1",
        seed=42,
        semester=1,
        week=1,
        day=1,
        course_id="C1",
        section_id="S1",
        conversation_id="conversation-1",
        topic_id="tech_ai_jobs",
        sender_id=1,
        receiver_id=0,
        sender_text="Estoy de acuerdo.",
        receiver_interest=1.0,
        similarity=0.5,
        relationship_before=0.5,
        participation_probability=None,
        agreement=0.7,
        sentiment_valence=0.8,
        interaction_score=0.725,
        relationship_after=0.545,
        timestamp_simulation=moment,
    )
    reply = interaction.model_copy(
        update={
            "sender_id": 0,
            "receiver_id": 1,
            "participation_probability": 0.42,
        }
    )
    path = save_run(
        tmp_path,
        config=config,
        agents=agents,
        interactions=[interaction, reply],
        metadata=metadata,
    )
    assert {file.name for file in path.iterdir()} == {
        "config.json",
        "run_metadata.json",
        "agents.parquet",
        "interactions.parquet",
        "relationships.parquet",
    }
    restored = load_run(path)
    assert restored.config == config
    assert restored.metadata == metadata
    assert restored.agents == agents
    assert restored.interactions == [interaction, reply]
    assert restored.relationships.to_dict("records") == [
        {"observer_id": 0, "other_id": 1, "weight": 0.72}
    ]
    assert isinstance(restored.agents[0].course_assignments[1], list)
    assert isinstance(restored.interactions[0].timestamp_simulation, datetime)
    with pytest.raises(FileExistsError):
        save_run(
            tmp_path,
            config=config,
            agents=agents,
            interactions=[interaction, reply],
            metadata=metadata,
        )


def test_empty_interactions_and_relationships_roundtrip(tmp_path):  # type: ignore[no-untyped-def]
    config = load_config("configs/homophily_low.yaml").model_copy(
        update={"population_size": 1, "sections_per_course": 1}
    )
    agent = StudentAgent(
        id=0,
        age=18,
        sex=Sex.FEMALE,
        origin=Origin.GUATEMALA_DEPARTMENT,
        semester=1,
        interests={"music"},
        extraversion=5,
    )
    moment = datetime.now(UTC)
    metadata = make_run_metadata(
        config,
        run_id="empty",
        seed=1,
        prompt_version="v1",
        topic_bank_version="v1",
        demographic_calibration_version="v1",
        model_name="mock",
        start_time=moment,
        end_time=moment,
    )
    path = save_run(tmp_path, config=config, agents=[agent], interactions=[], metadata=metadata)
    restored = load_run(path)
    assert restored.interactions == []
    assert restored.relationships.empty
