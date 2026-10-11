"""One short offline run produces the persisted report and every planned PNG."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from homophily_sim.experiments.mock_mvp import run_mock_mvp
from homophily_sim.io.results import load_run
from homophily_sim.llm.cache import SqliteUtteranceCache
from homophily_sim.llm.gemini import GeminiLanguageModelProvider


def test_mock_report_writes_complete_visual_output(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    destination = run_mock_mvp(
        config_path=root / "configs/homophily_medium.yaml",
        topic_path=root / "data/topics/topics_v1.yaml",
        demographic_path=root / "data/demographics/profiles_v1.yaml",
        output_root=tmp_path,
        run_id="phase11-smoke",
        seed=42,
        smoke=True,
    )
    expected = {
        "network_semester_01.png",
        "network_semester_02.png",
        "network_final.png",
        "density_over_time.png",
        "assortativity_over_time.png",
        "modularity_over_time.png",
        "relationship_distribution.png",
    }
    for name in expected:
        assert (destination / name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    metrics = json.loads((destination / "metrics_by_semester.json").read_text(encoding="utf-8"))
    assert [item["semester"] for item in metrics] == [1, 2]
    restored = load_run(destination)
    assert len(restored.agents) == 20
    assert restored.interactions


def test_gemini_provider_runs_mesa_report_with_mocked_sdk(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(text="Una opinión breve.")
    provider = GeminiLanguageModelProvider(
        client=client, cache=SqliteUtteranceCache(tmp_path / "cache.sqlite3"),
        generation_seed=42,
    )
    destination = run_mock_mvp(
        config_path=root / "configs/homophily_medium.yaml",
        topic_path=root / "data/topics/topics_v1.yaml",
        demographic_path=root / "data/demographics/profiles_v1.yaml",
        output_root=tmp_path,
        run_id="phase13-mocked-gemini",
        seed=42,
        smoke=True,
        language_model=provider,
    )
    restored = load_run(destination)
    assert restored.metadata.model_name == "gemini-2.5-flash-lite"
    assert restored.metadata.prompt_version == "student-spanish-v1"
    assert restored.metadata.language_settings["generation_seed"] == 42
    assert restored.interactions
    assert provider.api_calls > 0
    assert client.models.generate_content.call_count == provider.api_calls
