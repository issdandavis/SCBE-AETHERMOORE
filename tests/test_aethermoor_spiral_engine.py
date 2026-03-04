from __future__ import annotations

import pytest

from src.spiralverse.aethermoor_spiral_engine import (
    Action,
    AethermoorSpiralEngine,
    run_demo,
)
from src.scbe_math_reference import triadic_risk


def test_world_generation_is_deterministic_by_seed() -> None:
    a = AethermoorSpiralEngine(seed=123, region_count=8)
    b = AethermoorSpiralEngine(seed=123, region_count=8)
    hazards_a = [round(r.hazard, 8) for r in a.world]
    hazards_b = [round(r.hazard, 8) for r in b.world]
    assert hazards_a == hazards_b


def test_sheaf_obstruction_penalizes_stability() -> None:
    eng = AethermoorSpiralEngine(seed=5, region_count=8)
    stable, obs = eng._triadic_obstruction(distance=0.9, entropy=0.8, trust=0.1)  # noqa: SLF001
    assert obs >= 1
    assert 0.0 <= stable <= 1.0


def test_crafting_consumes_resources_and_creates_item() -> None:
    eng = AethermoorSpiralEngine(seed=9, region_count=8)
    eng.inventory.alloy = 3
    eng.inventory.crystal = 2
    before_alloy = eng.inventory.alloy
    ok = eng.craft("consensus_seal")
    assert ok is True
    assert eng.inventory.consensus_seal == 1
    assert eng.inventory.alloy == before_alloy - 2


def test_step_produces_valid_decision_and_progress_fields() -> None:
    eng = AethermoorSpiralEngine(seed=21, region_count=10)
    out = eng.step(Action.ROUTE)
    assert out.decision in {"ALLOW", "QUARANTINE", "DENY", "EXILE"}
    assert 0.0 <= out.omega <= 1.0
    assert out.permission_color in {"green", "amber", "red"}
    assert out.friction_multiplier >= 1.0
    assert out.weakest_lock in {"pqc_factor", "harm_score", "drift_factor", "triadic_stable", "spectral_score", "trust_exile"}
    assert isinstance(out.lock_vector, dict)
    assert "harm_score" in out.lock_vector
    assert len(out.voxel_key.split(":")) == 6
    assert out.terrain in {"glow_meadow", "crystal_garden", "storm_maw", "shadow_brush", "rift_spines", "ember_steppe"}
    assert isinstance(out.voxel_discovered, bool)
    assert 0.0 <= out.watcher_fast <= 1.0
    assert 0.0 <= out.watcher_memory <= 1.0
    assert 0.0 <= out.watcher_governance <= 1.0
    assert 0.0 <= out.d_tri <= 1.0
    assert 0.0 <= out.triadic_from_rings <= 1.0
    assert 0.0 <= out.triadic_from_sheaf <= 1.0
    assert 0.0 <= out.triadic_stable <= 1.0
    expected_d_tri = triadic_risk(out.watcher_fast, out.watcher_memory, out.watcher_governance)
    assert out.d_tri == pytest.approx(expected_d_tri, rel=1e-6)
    routed, target = out.mission_progress
    assert 0 <= routed <= target


def test_run_demo_is_reproducible() -> None:
    a = run_demo(seed=17, turns=10)
    b = run_demo(seed=17, turns=10)
    assert a["final"]["mission"] == b["final"]["mission"]
    assert a["final"]["voxels"] == b["final"]["voxels"]
    assert a["history"][0]["watchers"] == b["history"][0]["watchers"]
    assert a["history"][0]["omega_factors"] == b["history"][0]["omega_factors"]
    proj_a = [(h["tick"], h["action"], h["decision"], tuple(h["progress"])) for h in a["history"]]
    proj_b = [(h["tick"], h["action"], h["decision"], tuple(h["progress"])) for h in b["history"]]
    assert proj_a == proj_b


def test_coherence_shapes_terrain_classification() -> None:
    # High coherence + low hazard should map to safe-biome terrain.
    terrain_hi = AethermoorSpiralEngine._terrain_from_coherence(0.20, 0.90, 0.05)  # noqa: SLF001
    # Low coherence + high hazard should map to hostile-biome terrain.
    terrain_lo = AethermoorSpiralEngine._terrain_from_coherence(0.85, 0.20, 0.60)  # noqa: SLF001
    assert terrain_hi == "glow_meadow"
    assert terrain_lo == "storm_maw"
