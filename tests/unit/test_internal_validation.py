"""Controlled checks of the model's stated causal directions."""

from pathlib import Path

from homophily_sim.config import load_config
from homophily_sim.experiments.validation import logical_probes


def test_logical_probes_cover_all_planned_extremes() -> None:
    root = Path(__file__).resolve().parents[2]
    probes = logical_probes(load_config(root / "configs/base.yaml"))
    names = {row["case"] for row in probes}
    assert names == {
        "h_zero_ignores_similarity",
        "h_high_increases_similarity_effect",
        "h_high_increases_relationship_effect",
        "same_vs_disjoint_interests",
        "relationship_fixed_neutral",
        "extreme_extraversion_participation",
        "zero_extraversion_can_initiate",
    }
    assert all(row["passed"] for row in probes)


def test_h_zero_has_no_similarity_effect() -> None:
    root = Path(__file__).resolve().parents[2]
    probes = logical_probes(load_config(root / "configs/base.yaml"))
    zero = next(row for row in probes if row["case"] == "h_zero_ignores_similarity")
    assert zero["observed_difference"] == 0
