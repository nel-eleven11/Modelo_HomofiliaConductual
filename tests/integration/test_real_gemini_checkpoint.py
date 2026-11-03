"""Offline checkpoint parity; never creates a Gemini client."""

from pathlib import Path

from homophily_sim.config import SimulationConfig, load_config
from homophily_sim.data.demographics import load_demographic_profile
from homophily_sim.data.topics import load_topics
from homophily_sim.experiments.real_gemini import USAGE_KEYS, WeekCheckpoint, estimated_cost
from homophily_sim.llm.mock import MockLanguageModelProvider
from homophily_sim.nlp.mock import MockSentimentAnalyzer
from homophily_sim.simulation.model import HomophilyModel


def test_weekly_checkpoint_restores_exact_next_week(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    base = load_config(root / "configs/base.yaml")
    config = SimulationConfig.model_validate({
        **base.model_dump(), "population_size": 20, "years": 1,
        "semesters": 2, "weeks_per_semester": 2,
    })
    bank = load_topics(root / "data/topics/topics_v1.yaml")
    profile = load_demographic_profile(
        root / "data/demographics/profiles_v1.yaml", config.demographic_profile
    )

    def new_model() -> HomophilyModel:
        return HomophilyModel(
            config, bank, profile, run_seed=1, run_id="checkpoint-test",
            language_model=MockLanguageModelProvider(),
            sentiment_analyzer=MockSentimentAnalyzer(),
        )

    baseline = new_model()
    for _ in range(3):
        baseline.step()
    checkpoint = WeekCheckpoint(tmp_path / "weeks.sqlite3", {"seed": 1})
    checkpoint.save_week(baseline, dict.fromkeys(USAGE_KEYS, 0))
    resumed = new_model()
    checkpoint.restore(resumed)
    assert resumed.steps == 3
    assert resumed.sections_by_course == baseline.sections_by_course
    baseline.step()
    resumed.step()
    assert resumed.students == baseline.students
    assert resumed.interactions == baseline.interactions
    assert resumed.opportunities == baseline.opportunities
    assert resumed.metric_history == baseline.metric_history
    checkpoint.save_week(resumed, dict.fromkeys(USAGE_KEYS, 0))
    assert checkpoint.count("interactions") == len(resumed.interactions)
    assert checkpoint.count("opportunities") == len(resumed.opportunities)


def test_cost_includes_non_candidate_tokens() -> None:
    usage = dict.fromkeys(USAGE_KEYS, 0)
    usage.update(prompt_tokens=1_000_000, output_tokens=100_000, total_tokens=1_200_000)
    assert estimated_cost(usage) == 0.8
