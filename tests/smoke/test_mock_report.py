"""One short offline run produces the persisted report and every planned PNG."""

import json
from pathlib import Path

from homophily_sim.experiments.mock_mvp import run_mock_mvp
from homophily_sim.io.results import load_run


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
