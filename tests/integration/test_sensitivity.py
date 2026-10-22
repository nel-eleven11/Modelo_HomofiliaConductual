"""One-at-a-time configurations and a small paired sensitivity run."""

import csv
import json
from pathlib import Path

from homophily_sim.experiments.scenarios import load_homophily_scenarios
from homophily_sim.experiments.sensitivity import build_variants, run_sensitivity


def test_local_variants_preserve_weights_and_other_parameters() -> None:
    root = Path(__file__).resolve().parents[2]
    base = load_homophily_scenarios(root)["homophily_medium"]
    variants = build_variants(base)
    assert len(variants) == 15
    assert len({variant.key for variant in variants}) == 15
    for variant in variants[1:]:
        changed = {
            name for name, value in variant.config.model_dump().items()
            if value != base.model_dump()[name]
        }
        expected = {"scenario", variant.parameter}
        if variant.parameter == "w_interest":
            expected.update(("w_age", "w_sex", "w_origin"))
        if variant.parameter == "w_agreement":
            expected.add("w_sentiment")
        assert changed == expected
        assert variant.config.h == base.h
        assert abs(
            variant.config.w_interest + variant.config.w_age
            + variant.config.w_sex + variant.config.w_origin - 1
        ) < 1e-9
        assert abs(variant.config.w_agreement + variant.config.w_sentiment - 1) < 1e-9


def test_short_sensitivity_run_is_paired_and_resumable(tmp_path: Path) -> None:
    destination = run_sensitivity(
        output_root=tmp_path / "sensitivity", seeds=(1,),
        parameters=("alpha_relationship",), smoke=True,
    )
    summary = json.loads((destination / "sensitivity_summary.json").read_text())
    with (destination / "run_inventory.csv").open(newline="", encoding="utf-8") as source:
        inventory = list(csv.DictReader(source))
    assert summary["run_count"] == 9
    assert summary["semester_rows"] == 18
    assert len(inventory) == 9
    assert len(summary["paired_deltas"]) == 3 * 2 * 2 * 10
    assert {float(item["h"]) for item in inventory} == {0.2, 0.5, 0.8}
    assert run_sensitivity(
        output_root=destination, seeds=(1,), parameters=("alpha_relationship",),
        smoke=True,
    ) == destination
