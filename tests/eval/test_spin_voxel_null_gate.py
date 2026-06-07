from __future__ import annotations

from scripts.eval.spin_voxel_null_gate import (
    _auc,
    build_same_inventory_samples,
    run_probe,
)


def test_same_inventory_pairs_only_change_order() -> None:
    samples = build_same_inventory_samples(sample_pairs=1, spin_count=16, seed=7)
    smooth, boundary = samples

    assert smooth.label == 0
    assert boundary.label == 1
    assert sorted(smooth.spins) == sorted(boundary.spins)
    assert smooth.spins != boundary.spins


def test_auc_handles_ties_and_separation() -> None:
    assert _auc([0, 0, 1, 1], [0.1, 0.1, 0.9, 0.9]) == 1.0
    assert _auc([0, 1], [0.5, 0.5]) == 0.5


def test_spin_voxel_topology_signal_beats_inventory_shuffle_null() -> None:
    payload = run_probe(
        sample_pairs=12, spin_count=32, null_trials=60, seed=123, margin=0.05
    )
    metric = payload["metric"]
    multipliers = payload["multipliers"]

    assert payload["verdict"] == "FIELD_TOPOLOGY_SIGNAL"
    assert (
        metric["real_auc"]
        > metric["shuffle_inventory_null_auc_p95"] + metric["margin_required"]
    )
    assert multipliers["boundary_median"] > multipliers["smooth_median"]
