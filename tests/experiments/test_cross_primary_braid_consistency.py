from __future__ import annotations

from scripts.experiments.cross_primary_braid_consistency import (
    DEFAULT_INPUT,
    cross_primary_cycles,
    run,
)
from scripts.experiments.atomic_tokenizer_rename_benchmark import (
    _load_samples,
    make_layered_geometry_semantic_feature,
)


def test_cross_primary_cycles_cover_all_ordered_primary_pairs() -> None:
    samples = _load_samples(DEFAULT_INPUT)
    sources = [sample.source for sample in samples]
    cycles = cross_primary_cycles(
        samples,
        sources,
        "layered_geometry_semantic",
        make_layered_geometry_semantic_feature(),
    )

    assert len(cycles) == 6 * 5 * 14
    assert {cycle.start_primary for cycle in cycles} == {"AV", "CA", "DR", "KO", "RU", "UM"}
    assert all(cycle.start_primary != cycle.bridge_primary for cycle in cycles)


def test_braid_report_selects_measured_best_feature(tmp_path) -> None:
    report = run(DEFAULT_INPUT, tmp_path)

    assert report["version"] == "cross-primary-braid-consistency-v1"
    assert report["sample_count"] == 84
    assert report["best_closure_feature"] in report["features"]
    assert report["features"][report["best_closure_feature"]]["overall"]["closure_accuracy"] >= 0.0
    assert (tmp_path / "cross_primary_braid_consistency.json").exists()


def test_dual_lane_braid_is_above_chance(tmp_path) -> None:
    report = run(DEFAULT_INPUT, tmp_path)
    dual = report["features"]["dual_lane_chemistry_semantic_hex"]["overall"]

    assert dual["cycle_count"] == 420
    assert dual["first_hop_accuracy"] > 1 / 14
    assert dual["closure_accuracy"] > 1 / 14
