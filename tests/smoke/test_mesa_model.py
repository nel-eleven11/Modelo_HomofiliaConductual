"""Four academic weeks in Mesa using only local mock providers."""

from pathlib import Path

import mesa  # type: ignore[import-untyped]

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel, StudentMesaAgent


def test_twenty_mesa_agents_run_four_weeks_with_mocks() -> None:
    root = Path(__file__).resolve().parents[2]
    base = load_config(root / "configs/base.yaml")
    config = SimulationConfig.model_validate(
        {
            **base.model_dump(),
            "population_size": 20,
            "years": 1,
            "semesters": 2,
            "weeks_per_semester": 4,
        }
    )
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )
    model = HomophilyModel(
        config,
        bank,
        profile,
        run_seed=42,
        run_id="mesa-smoke",
        language_model=MockLanguageModelProvider(),
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    assert isinstance(model, mesa.Model)
    assert len(model.agents) == 20
    assert all(isinstance(agent, StudentMesaAgent) for agent in model.agents)
    for _ in range(4):
        model.step()
    assert model.steps == 4
    assert (model.current_semester, model.current_week) == (1, 4)
    assert model.conversation_count == 4 * 36
    assert len(model.interactions) >= 4 * 72
    assert len(model.snapshots) == 1
    assert model.snapshots[0].graph.number_of_nodes() == 20
    assert model.metric_history[0][0] == 1
    history = model.datacollector.get_model_vars_dataframe()
    assert history["week"].tolist() == [1, 2, 3, 4]
    assert history["interactions"].is_monotonic_increasing
