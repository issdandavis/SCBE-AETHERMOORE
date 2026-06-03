from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_probe_module():
    root = Path(__file__).resolve().parents[1]
    probe_path = root / "scripts" / "research" / "prime_fog_of_war_probe.py"
    spec = importlib.util.spec_from_file_location("prime_fog_of_war_probe", probe_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_integer_magnifier_preserves_negative_orientation_and_verifies_abs_core():
    probe = load_probe_module()

    payload = probe.run_integer_magnifier([-7, 7, -4, 0], bins=16, shell_radius=1)
    rows = {row["raw"]: row for row in payload["rows"]}

    assert payload["schema_version"] == "prime_fog_integer_magnifier_v1"
    assert rows[-7]["core"] == 7
    assert rows[-7]["orientation"] == -1
    assert rows[-7]["negative_tracking"]["mirror"] == 7
    assert rows[-7]["exact_verifier"]["is_prime"] is True
    assert rows[-7]["ternary_state"] == 1

    assert rows[-4]["core"] == 4
    assert rows[-4]["exact_verifier"]["is_prime"] is False
    assert rows[-4]["factor_wave"]["relation"] == "2*2=4"
    assert rows[-4]["factor_vector"]["exponents"] == {"2": 2}
    assert rows[-4]["factor_vector"]["complete"] is True
    assert rows[-4]["residue_vector"]["residues"]["2"] == 0
    assert 2 in rows[-4]["residue_vector"]["shadow_hits"]

    assert rows[0]["exact_verifier"]["state"] == "outside_prime_domain"
    assert any(edge["relation"] == "negative_mirror_pair" for edge in payload["relation_edges"])


def test_integer_magnifier_factor_vector_leaves_bounded_residual_tail():
    probe = load_probe_module()

    payload = probe.run_integer_magnifier([97 * 101], bins=16, shell_radius=0, factor_primes=[2, 3, 5, 7])
    row = payload["rows"][0]

    assert row["factor_vector"]["exponents"] == {}
    assert row["factor_vector"]["residual"] == 97 * 101
    assert row["factor_vector"]["residual_state"] == "unresolved_composite_or_large_tail"
    assert row["factor_vector"]["complete"] is False
    assert payload["summary"]["factor_division_budget"] == 4


def test_generalized_harmonic_tensor_packs_six_ground_state_trits():
    probe = load_probe_module()

    tensor = probe.generalized_trit_tensor(
        mw=150.0,
        logp=2.0,
        tpsa=60.0,
        stability_score=1.0,
        stability_threshold=1.0,
        predicted_band=(100.0, 200.0),
        severity_min_dist=10.0,
    )

    assert tensor["law"] == "H(delta)=delta/(1+delta)"
    assert tensor["gate_order"] == ["mw", "severity", "predicted_band", "stability", "logp", "tpsa"]
    assert tensor["trits"] == [2, 2, 2, 2, 2, 2]
    assert probe.encode_trit_vector(tensor["trits"]) == 728
    assert tensor["mean_harmonic"] == 0.0


def test_generalized_harmonic_tensor_marks_cliff_and_collision_states():
    probe = load_probe_module()

    tensor = probe.generalized_trit_tensor(
        mw=925.0,
        logp=6.0,
        tpsa=205.0,
        stability_score=0.4,
        stability_threshold=1.0,
        predicted_band=None,
        severity_min_dist=0.25,
    )

    states = {state["name"]: state for state in tensor["states"]}
    assert tensor["trits"] == [0, 0, 1, 0, 1, 0]
    assert states["mw"]["delta"] > 1.0
    assert states["logp"]["trit"] == 1
    assert states["predicted_band"]["trit"] == 1


def test_path_c_digit_braid_rejects_decimal_impossible_twin_start():
    probe = load_probe_module()

    invalid = probe.digit_braid_score(103)
    valid = probe.digit_braid_score(101)

    assert invalid["score"] == 0.0
    assert invalid["reason"] == "base10_last_digit_elimination"
    assert valid["score"] > 0.0


def test_shadow_lattice_masks_seed_prime_semiprime_products():
    probe = load_probe_module()

    lattice = probe.build_shadow_lattice([11, 17], limit=500)
    shadow = probe.shadow_lattice_score(143, lattice)
    path_c = probe.path_c_score(143, lattice)

    assert shadow["exact_shadow"] is True
    assert shadow["shadow_value"] == 143
    assert shadow["witness"] == [11, 13]
    assert path_c["score"] == 0.0
    assert path_c["shadow_hit"] is True
