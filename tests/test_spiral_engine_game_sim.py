import math

from src.scbe_governance_math import Point3
from scripts.spiral_engine_game_sim import (
    PlayerState,
    compute_x_factor,
    encode_voxel_keys,
    generate_mission,
    harm_score_from_wall,
    load_world_profile,
    quantize_floor,
    run_simulation,
    runtime_wall_cost,
    sheaf_obstruction,
    sheaf_stability_from_obstruction,
    simulate_tick,
    tarski_postfixpoint,
    triadic_risk,
)


def test_generate_mission_is_deterministic_for_seed_and_tick():
    m1 = generate_mission("seed-alpha", 3)
    m2 = generate_mission("seed-alpha", 3)
    assert m1 == m2
    assert m1.region
    assert m1.faction


def test_load_world_profile_defaults_when_missing():
    world = load_world_profile("config/game/worlds/does-not-exist.json")
    assert world["world_id"] == "aethermoor"
    assert "mission_archetypes" in world


def test_quantize_floor_is_stable_on_boundaries():
    bins = 36
    q1 = quantize_floor(0.5, 0.0, 1.0, bins)
    q2 = quantize_floor(0.5 + 1e-12, 0.0, 1.0, bins)
    assert q2 >= q1
    assert q1 == 18


def test_runtime_wall_and_harm_are_monotone():
    x_low = compute_x_factor(accumulated_intent=0.0, trust=1.0)
    x_high = compute_x_factor(accumulated_intent=8.0, trust=0.0)

    h_low = runtime_wall_cost(d=0.3, x=x_low)
    h_high = runtime_wall_cost(d=0.9, x=x_high)

    assert h_high > h_low
    assert harm_score_from_wall(h_high) < harm_score_from_wall(h_low)


def test_tarski_postfixpoint_moves_values_downward_or_equal():
    sections = {
        "fast": 0.9,
        "memory": 0.4,
        "governance": 0.7,
        "spectral": 0.2,
    }
    fixed = tarski_postfixpoint(sections)
    for key, value in sections.items():
        assert 0.0 <= fixed[key] <= value


def test_sheaf_obstruction_zero_for_constant_sections():
    sections = {
        "fast": 0.4,
        "memory": 0.4,
        "governance": 0.4,
        "spectral": 0.4,
    }
    obstruction = sheaf_obstruction(sections)
    stability = sheaf_stability_from_obstruction(obstruction)

    assert obstruction == 0.0
    assert stability == 1.0


def test_triadic_risk_bounded_by_inputs():
    values = (0.2, 0.8, 0.5)
    d_tri = triadic_risk(*values)
    assert min(values) <= d_tri <= max(values)


def test_simulate_tick_emits_dual_output_contract():
    state = PlayerState()
    mission = generate_mission("mvp-seed", 0)
    out = simulate_tick(
        state,
        mission,
        pad="ENGINEERING",
        tongue="KO",
        action_intensity=0.65,
    )

    assert "StateVector" in out
    assert "DecisionRecord" in out
    assert out["DecisionRecord"]["action"] in {"ALLOW", "QUARANTINE", "DENY"}
    assert "signature" in out["DecisionRecord"]
    assert "voxel_base_key" in out["StateVector"]
    assert "hud" in out["StateVector"]
    assert "watcher_rings" in out["StateVector"]["hud"]
    assert "gate_locks" in out["StateVector"]["hud"]


def test_voxel_key_and_shard_are_deterministic():
    s = PlayerState(position=Point3(0.2, -0.1, 0.3))
    key1, per1, shard1 = encode_voxel_keys(s, d=0.6, h_eff=2.5, tongue_levels=s.tongue_levels)
    key2, per2, shard2 = encode_voxel_keys(s, d=0.6, h_eff=2.5, tongue_levels=s.tongue_levels)

    assert key1 == key2
    assert per1 == per2
    assert shard1 == shard2
    assert 0 <= shard1 < 64


def test_run_simulation_produces_tick_history():
    out = run_simulation(
        seed="aethermoor-test",
        ticks=5,
        pad="SYSTEMS",
        tongue="DR",
        action_intensity=0.6,
    )

    assert out["ticks"] == 5
    assert out["world_id"] == "aethermoor"
    assert len(out["history"]) == 5
    assert "final_state" in out
