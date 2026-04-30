from __future__ import annotations

import pytest

pytest.importorskip(
    "scripts.mathbac_cross_primary_atomic",
    reason="benchmark depends on uncommitted scripts/mathbac_cross_primary_atomic.py",
)

from scripts.experiments.basket_weave_consistency_gate import run


def test_basket_weave_consistency_gate_maps_prior_layers(tmp_path) -> None:
    report = run(tmp_path)

    assert report["version"] == "basket-weave-consistency-gate-v1"
    assert report["passed"] is True
    assert report["checks"]["workflow_exports_geometry_lane"] is True
    assert report["checks"]["default_lane_is_available_in_cross_braid"] is True
    assert report["checks"]["cross_best_has_above_chance_closure"] is True
    assert report["checks"]["semantic_gate_blocks_unapproved_blends"] is True
    assert report["semantic_gate"]["decision"] == "QUARANTINE"
    assert report["semantic_gate"]["allowed_sources"] == ["fact"]
    assert set(report["semantic_gate"]["blocked_sources"]) == {
        "analogy",
        "experimental",
    }
    assert "layered_geometry_semantic" in report["lanes"]["workflow_export_lanes"]
