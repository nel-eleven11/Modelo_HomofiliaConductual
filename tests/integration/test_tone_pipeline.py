"""A small offline run preserves message-level tone through saved summaries."""

from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean

import pytest

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.io.mechanisms import export_mechanisms
from homophily_sim.io.metadata import RunMetadata
from homophily_sim.io.results import load_run, save_run
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel

ROOT = Path(__file__).resolve().parents[2]


def test_offline_tone_records_and_summaries_rebuild(tmp_path: Path) -> None:
    base = load_config(ROOT / "configs/base.yaml")
    config = SimulationConfig.model_validate({
        **base.model_dump(), "population_size": 20, "years": 1,
        "semesters": 2, "weeks_per_semester": 1,
    })
    bank = load_topics(ROOT / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        ROOT / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )
    model = HomophilyModel(
        config, bank, profile, run_seed=42, run_id="tone-smoke",
        language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    model.run_to_completion()
    assert model.conversation_count == 72
    assert len(model.messages) == model.conversation_count + sum(
        item.participated for item in model.opportunities
    )
    assert len(model.interactions) == len(model.opportunities) + sum(
        item.participated for item in model.opportunities
    )
    message_by_id = {message.message_id: message for message in model.messages}
    assert len(message_by_id) == len(model.messages)
    assert {message.sampled_tone for message in model.messages} == {
        "negative", "neutral", "positive"
    }
    for record in model.interactions:
        assert record.message_id is not None
        assert record.sentiment_valence == message_by_id[record.message_id].sampled_valence
    assert all(
        item.relationship_before == next(
            record.relationship_before for record in model.interactions
            if record.conversation_id == item.conversation_id
            and record.receiver_id == item.candidate_id
            and record.sender_id == item.initiator_id
        )
        for item in model.opportunities
    )
    now = datetime.now(UTC)
    metadata = RunMetadata(
        run_id="tone-smoke", seed=42, scenario=config.scenario,
        git_commit="test", software_versions={"python": "test"},
        prompt_version="mock-v1", topic_bank_version=bank.topic_bank_version,
        demographic_calibration_version=profile.version,
        model_name="mock", sentiment_model_name="expressed-tone-v1",
        start_time=now, end_time=now,
    )
    destination = save_run(
        tmp_path, config=config, agents=model.students,
        interactions=model.interactions, metadata=metadata,
        opportunities=model.opportunities, messages=model.messages,
    )
    restored = load_run(destination)
    assert restored.messages == model.messages
    first = export_mechanisms(destination, bank)
    second = export_mechanisms(destination, bank)
    assert first.interaction == second.interaction
    assert first.tones == second.tones
    assert len(first.interaction) == 2
    for semester, row in enumerate(first.interaction, start=1):
        messages = [message for message in restored.messages if message.semester == semester]
        records = [record for record in restored.interactions if record.semester == semester]
        assert row["mean_expressed_valence"] == pytest.approx(
            fmean(message.sampled_valence for message in messages)
        )
        assert row["mean_evaluated_valence"] == pytest.approx(
            fmean(record.sentiment_valence for record in records)
        )
        assert sum(row[f"{tone}_message_rate"] for tone in (
            "negative", "neutral", "positive"
        )) == pytest.approx(1)
    assert (destination / "tone_summary.csv").exists()
    assert (destination / "tone_by_interest.csv").exists()
