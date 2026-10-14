"""The first pilot keeps a presentation-ready audit beside the persisted run."""

import csv
import json

from homophily_sim.experiments.pilot_1 import run_pilot_1
from homophily_sim.io.results import load_run
from homophily_sim.nlp.mock import MockSentimentAnalyzer


def test_pilot_1_saves_diagnostics_and_final_results(tmp_path):  # type: ignore[no-untyped-def]
    destination = run_pilot_1(
        output_root=tmp_path,
        run_id="pilot-1-test",
        seed=42,
        sentiment_analyzer=MockSentimentAnalyzer(),
    )
    run = load_run(destination)
    summary = json.loads((destination / "pilot_1_summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((destination / "pilot_1_network_metrics.csv").open()))
    conversations = list(csv.DictReader((destination / "pilot_1_conversations.csv").open()))

    assert summary["run_id"] == "pilot-1-test"
    assert summary["population_size"] == 20
    assert summary["simulated_weeks"] == 2
    assert summary["conversation_count"] == 72
    assert summary["exposure_count"] == 144
    assert summary["interaction_count"] == len(run.interactions)
    assert summary["interaction_count"] == summary["exposure_count"] + summary["participant_count"]
    assert summary["participation_probability"]["count"] == summary["exposure_count"]
    assert summary["llm_api_calls"] == 0
    assert summary["llm_cost_usd"] == 0
    assert all(summary["checks"].values())
    assert [int(row["semester"]) for row in rows] == [1, 2]
    assert len(conversations) == summary["conversation_count"]
    assert sum(len(json.loads(row["participant_ids"])) for row in conversations) == summary[
        "participant_count"
    ]
    assert (destination / "pilot_1_report.md").is_file()
    assert (destination / "network_final.png").is_file()
