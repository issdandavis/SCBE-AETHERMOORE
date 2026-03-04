"""
Tests for audit bug fixes, SCBE patrol/wall validation, tongue routing,
and dual-formula harmonic scaling.

Covers:
  Bug 1: Capacitor variable no longer shadows speed-of-light constant C
  Bug 2: Negative temperature no longer crashes Maxwell-Boltzmann
  Bug 3: Particle masses updated to CODATA 2018
  Patrol: Non-physical inputs detected and classified correctly
  Tongue: Physics domains classified into 6D Sacred Tongue vectors
  Harmonic: Dual-formula regime (patrol tanh / wall exp) with crossover
"""

import math
import json
from .core import (
    electromagnetism,
    thermodynamics,
    classical_mechanics,
    quantum_mechanics,
    relativity,
    lambda_handler,
    C,
    ELECTRON_MASS,
    PROTON_MASS,
    NEUTRON_MASS,
    VACUUM_PERMITTIVITY,
)
from .patrol import (
    validate_params,
    validated_simulation,
    Decision,
    TongueProfile,
    classify_physics_tongue,
    harmonic_patrol,
    harmonic_wall,
    harmonic_risk,
    D_STAR_CROSSOVER,
    PATROL_ALPHA,
    PATROL_BETA,
    _compute_param_distance,
    _tongue_strictness,
)


# =========================================================================
# BUG FIX TESTS
# =========================================================================

def test_bug1_capacitor_does_not_shadow_c():
    """
    Bug 1: Capacitor section used 'C' as local variable, shadowing
    the module-level speed-of-light constant.
    """
    result = electromagnetism({
        'plate_area': 0.01,
        'plate_separation': 0.001,
        'voltage': 100,
        'em_frequency': 5e14,
    })
    expected_cap = VACUUM_PERMITTIVITY * 0.01 / 0.001
    assert abs(result['capacitance'] - expected_cap) / expected_cap < 1e-10
    expected_wavelength = C / 5e14
    assert abs(result['em_wavelength'] - expected_wavelength) / expected_wavelength < 1e-10
    assert 1e-7 < result['em_wavelength'] < 1e-6
    print("  Bug 1 FIXED: capacitor variable no longer shadows C")


def test_bug2_negative_temperature_no_crash():
    """Bug 2: thermodynamics() crashed with ValueError on negative temperature."""
    result = thermodynamics({'temperature': -100, 'molecular_mass': 4.65e-26})
    assert 'average_kinetic_energy' in result
    assert 'rms_speed' not in result

    result_zero = thermodynamics({'temperature': 0, 'molecular_mass': 4.65e-26})
    assert 'rms_speed' not in result_zero

    result_pos = thermodynamics({'temperature': 300, 'molecular_mass': 4.65e-26})
    assert 'rms_speed' in result_pos
    assert result_pos['rms_speed'] > 0
    print("  Bug 2 FIXED: negative/zero temperature no longer crashes")


def test_bug3_codata_2018_masses():
    """Bug 3: Particle masses updated from CODATA 2014 to CODATA 2018."""
    assert ELECTRON_MASS == 9.1093837015e-31
    assert PROTON_MASS == 1.67262192369e-27
    assert NEUTRON_MASS == 1.67492749804e-27
    print("  Bug 3 FIXED: particle masses match CODATA 2018")


# =========================================================================
# PATROL / WALL VALIDATION TESTS
# =========================================================================

def test_patrol_allows_valid_classical():
    result = validate_params('classical', {'mass': 10, 'acceleration': 5})
    assert result.decision == Decision.ALLOW
    assert not result.violations
    assert not result.warnings
    print("  Patrol ALLOW: valid classical inputs")


def test_wall_denies_negative_mass():
    result = validate_params('classical', {'mass': -5, 'acceleration': 10})
    assert result.decision == Decision.DENY
    assert any('Mass' in v for v in result.violations)
    print("  Wall DENY: negative mass")


def test_wall_denies_zero_distance():
    result = validate_params('electromagnetism', {
        'charge1': 1.6e-19, 'charge2': 1.6e-19, 'distance': 0,
    })
    assert result.decision == Decision.DENY
    print("  Wall DENY: zero distance")


def test_wall_denies_negative_temperature():
    result = validate_params('thermodynamics', {
        'temperature': -50, 'molecular_mass': 4.65e-26,
    })
    assert result.decision == Decision.DENY
    assert any('below absolute zero' in v for v in result.violations)
    print("  Wall DENY: negative temperature")


def test_wall_denies_superluminal_velocity():
    result = validate_params('relativity', {'velocity': C * 1.1, 'proper_time': 1})
    assert result.decision == Decision.DENY
    assert any('speed of light' in v for v in result.violations)
    print("  Wall DENY: superluminal velocity")


def test_patrol_warns_fast_classical():
    result = validate_params('classical', {'mass': 1, 'velocity': 0.5 * C})
    assert result.decision == Decision.WARN
    assert any('relativistic' in w for w in result.warnings)
    print("  Patrol WARN: fast classical velocity")


def test_patrol_warns_zero_temperature():
    result = validate_params('thermodynamics', {'temperature': 0, 'surface_area': 1})
    assert result.decision == Decision.WARN
    print("  Patrol WARN: T = 0 K")


def test_patrol_warns_inverted_carnot():
    result = validate_params('thermodynamics', {
        'hot_temperature': 200, 'cold_temperature': 300,
    })
    assert result.decision == Decision.WARN
    assert any('Carnot' in w for w in result.warnings)
    print("  Patrol WARN: inverted Carnot temperatures")


def test_wall_denies_nan_input():
    result = validate_params('classical', {'mass': float('nan'), 'acceleration': 5})
    assert result.decision == Decision.DENY
    print("  Wall DENY: NaN input")


def test_wall_denies_inf_input():
    result = validate_params('quantum', {'wavelength': float('inf')})
    assert result.decision == Decision.DENY
    print("  Wall DENY: Inf input")


def test_wall_denies_non_integer_quantum_number():
    result = validate_params('quantum', {'principal_quantum_number': 2.5})
    assert result.decision == Decision.DENY
    print("  Wall DENY: non-integer quantum number")


def test_wall_denies_emissivity_out_of_range():
    result = validate_params('thermodynamics', {
        'temperature': 300, 'surface_area': 1, 'emissivity': 1.5,
    })
    assert result.decision == Decision.DENY
    print("  Wall DENY: emissivity > 1")


def test_validated_simulation_deny():
    sims = {'classical': classical_mechanics, 'quantum': quantum_mechanics}
    response = validated_simulation('classical', {'mass': -1, 'acceleration': 5}, sims)
    assert response['statusCode'] == 422
    body = json.loads(response['body'])
    assert body['decision'] == 'deny'
    print("  validated_simulation returns 422 on DENY")


def test_validated_simulation_allow():
    sims = {'classical': classical_mechanics, 'quantum': quantum_mechanics}
    response = validated_simulation('classical', {'mass': 10, 'acceleration': 5}, sims)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['results']['force'] == 50
    assert body['validation']['decision'] == 'allow'
    assert body['validation']['tongue'] is not None
    assert body['validation']['tongue']['dominant'] in ('DR', 'RU', 'CA', 'KO', 'AV', 'UM')
    assert body['validation']['risk_score'] >= 0
    print("  validated_simulation returns 200 on ALLOW with tongue data")


# =========================================================================
# HARMONIC SCALING TESTS
# =========================================================================

def test_harmonic_patrol_identity():
    """Patrol formula at d*=0 should return 1.0 (identity)."""
    assert harmonic_patrol(0) == 1.0
    print("  Harmonic patrol: H(0) = 1.0")


def test_harmonic_patrol_bounded():
    """Patrol formula is bounded at 1 + alpha."""
    h_100 = harmonic_patrol(100.0)
    assert abs(h_100 - (1.0 + PATROL_ALPHA)) < 0.01
    print(f"  Harmonic patrol: H(100) = {h_100:.2f} (bounded at {1 + PATROL_ALPHA})")


def test_harmonic_wall_identity():
    """Wall formula at d*=0 should return 1.0."""
    assert harmonic_wall(0) == 1.0
    print("  Harmonic wall: H(0) = 1.0")


def test_harmonic_wall_superexponential():
    """Wall formula grows superexponentially."""
    h1 = harmonic_wall(1.0)
    h2 = harmonic_wall(2.0)
    h3 = harmonic_wall(3.0)
    assert h1 < h2 < h3
    assert abs(h1 - math.exp(1)) < 0.01
    assert abs(h2 - math.exp(4)) < 0.01
    assert abs(h3 - math.exp(9)) < 0.01
    print(f"  Harmonic wall: H(1)={h1:.1f}, H(2)={h2:.1f}, H(3)={h3:.0f}")


def test_harmonic_risk_max_regime():
    """harmonic_risk = max(patrol, wall) at every point."""
    for d in [0.0, 0.1, 0.5, 1.0, 1.4, 2.0, 3.0]:
        h = harmonic_risk(d)
        hp = harmonic_patrol(d)
        hw = harmonic_wall(d)
        assert abs(h - max(hp, hw)) < 1e-10, f"At d*={d}: risk={h} != max({hp}, {hw})"
    # Patrol dominates at small d*, wall at large d*
    assert harmonic_patrol(0.5) > harmonic_wall(0.5)
    assert harmonic_wall(3.0) > harmonic_patrol(3.0)
    print("  Harmonic risk: max(patrol, wall) at all test points")


def test_harmonic_monotonic():
    """Both formulas should be monotonically increasing for d* > 0."""
    prev = harmonic_risk(0.0)
    for d in [0.1, 0.5, 0.926, 1.0, 1.5, 2.0, 3.0]:
        h = harmonic_risk(d)
        assert h >= prev, f"Not monotonic: H({d}) = {h} < {prev}"
        prev = h
    print("  Harmonic risk: monotonically increasing")


# =========================================================================
# TONGUE CLASSIFICATION TESTS
# =========================================================================

def test_tongue_classical_dominant_dr():
    """Classical mechanics should be DR-dominant (forge/structure)."""
    tp = classify_physics_tongue('classical', {'mass': 10, 'acceleration': 5})
    assert tp.dominant == 'DR'
    assert tp.scores['DR'] > tp.scores['KO']
    print(f"  Tongue classical: dominant={tp.dominant} (scores: DR={tp.scores['DR']:.1f})")


def test_tongue_quantum_dominant_ru():
    """Quantum mechanics should be RU-dominant (knowledge)."""
    tp = classify_physics_tongue('quantum', {'principal_quantum_number': 3})
    assert tp.dominant == 'RU'
    print(f"  Tongue quantum: dominant={tp.dominant}")


def test_tongue_relativity_dominant_ru_or_um():
    """Relativity should be RU or UM dominant depending on params."""
    tp_base = classify_physics_tongue('relativity', {'mass': 1})
    assert tp_base.dominant == 'RU'
    tp_bh = classify_physics_tongue('relativity', {'black_hole_mass': 1.989e30})
    assert tp_bh.scores['UM'] > tp_base.scores['UM']
    print(f"  Tongue relativity: base={tp_base.dominant}, black_hole={tp_bh.dominant}")


def test_tongue_near_light_speed_um_boost():
    """Velocity near c should boost UM (beyond/limit)."""
    tp_slow = classify_physics_tongue('relativity', {'velocity': 1000, 'proper_time': 1})
    tp_fast = classify_physics_tongue('relativity', {'velocity': 0.99 * C, 'proper_time': 1})
    assert tp_fast.scores['UM'] > tp_slow.scores['UM']
    print(f"  Tongue UM boost: slow={tp_slow.scores['UM']:.2f}, fast={tp_fast.scores['UM']:.2f}")


def test_tongue_profile_normalized():
    """Normalized tongue profile should sum to 1."""
    tp = classify_physics_tongue('classical', {'mass': 10, 'velocity': 5})
    norm = tp.normalized()
    total = sum(norm.values())
    assert abs(total - 1.0) < 1e-10
    assert all(0 <= v <= 1 for v in norm.values())
    print(f"  Tongue normalized: sum={total:.10f}")


def test_tongue_strictness_ru_heavy():
    """RU-heavy profile should produce strictness > 1.0."""
    tp = TongueProfile(
        scores={"KO": 0, "AV": 0, "RU": 10, "CA": 0, "UM": 0, "DR": 0},
        dominant="RU", confidence=1.0,
    )
    s = _tongue_strictness(tp)
    assert s > 1.0, f"RU-heavy strictness {s} should be > 1.0"
    print(f"  Tongue strictness (RU-heavy): {s:.3f}")


def test_tongue_strictness_ca_heavy():
    """CA-heavy profile should produce strictness < 1.0."""
    tp = TongueProfile(
        scores={"KO": 0, "AV": 0, "RU": 0, "CA": 10, "UM": 0, "DR": 0},
        dominant="CA", confidence=1.0,
    )
    s = _tongue_strictness(tp)
    assert s < 1.0, f"CA-heavy strictness {s} should be < 1.0"
    print(f"  Tongue strictness (CA-heavy): {s:.3f}")


def test_tongue_in_validation_result():
    """validate_params should include tongue profile and risk score."""
    result = validate_params('quantum', {'principal_quantum_number': 1})
    assert result.tongue is not None
    assert result.tongue.dominant in ('RU', 'KO', 'CA', 'DR', 'AV', 'UM')
    assert result.risk_score >= 0
    print(f"  Validation result: tongue={result.tongue.dominant}, risk={result.risk_score:.4f}")


# =========================================================================
# SEMANTIC DISTANCE TESTS
# =========================================================================

def test_distance_normal_request():
    """Normal parameters should give d* near 0."""
    d = _compute_param_distance({'mass': 10, 'acceleration': 5}, 'classical')
    assert d == 0.0
    print(f"  Distance normal: d*={d}")


def test_distance_near_light_speed():
    """Near-c velocity should give elevated d*."""
    d = _compute_param_distance({'velocity': 0.99 * C}, 'relativity')
    assert d > 2.0
    print(f"  Distance near-c: d*={d:.2f}")


def test_distance_extreme_temperature():
    """Stellar temperature should give elevated d*."""
    d = _compute_param_distance({'temperature': 1e9}, 'thermodynamics')
    assert d > 0.5
    print(f"  Distance stellar T: d*={d:.2f}")


def test_distance_black_hole():
    """Black hole requests are always elevated."""
    d = _compute_param_distance({'black_hole_mass': 1.989e30}, 'relativity')
    assert d >= 1.0
    print(f"  Distance black hole: d*={d:.2f}")


# =========================================================================
# RUNNER
# =========================================================================

def run_all():
    print("\n" + "=" * 60)
    print(" BUG FIX, PATROL/WALL, TONGUE & HARMONIC TESTS")
    print("=" * 60)

    print("\n--- Bug Fix Tests ---")
    test_bug1_capacitor_does_not_shadow_c()
    test_bug2_negative_temperature_no_crash()
    test_bug3_codata_2018_masses()

    print("\n--- Patrol/Wall Validation Tests ---")
    test_patrol_allows_valid_classical()
    test_wall_denies_negative_mass()
    test_wall_denies_zero_distance()
    test_wall_denies_negative_temperature()
    test_wall_denies_superluminal_velocity()
    test_patrol_warns_fast_classical()
    test_patrol_warns_zero_temperature()
    test_patrol_warns_inverted_carnot()
    test_wall_denies_nan_input()
    test_wall_denies_inf_input()
    test_wall_denies_non_integer_quantum_number()
    test_wall_denies_emissivity_out_of_range()
    test_validated_simulation_deny()
    test_validated_simulation_allow()

    print("\n--- Harmonic Scaling Tests ---")
    test_harmonic_patrol_identity()
    test_harmonic_patrol_bounded()
    test_harmonic_wall_identity()
    test_harmonic_wall_superexponential()
    test_harmonic_risk_max_regime()
    test_harmonic_monotonic()

    print("\n--- Tongue Classification Tests ---")
    test_tongue_classical_dominant_dr()
    test_tongue_quantum_dominant_ru()
    test_tongue_relativity_dominant_ru_or_um()
    test_tongue_near_light_speed_um_boost()
    test_tongue_profile_normalized()
    test_tongue_strictness_ru_heavy()
    test_tongue_strictness_ca_heavy()
    test_tongue_in_validation_result()

    print("\n--- Semantic Distance Tests ---")
    test_distance_normal_request()
    test_distance_near_light_speed()
    test_distance_extreme_temperature()
    test_distance_black_hole()

    print("\n" + "=" * 60)
    print(" ALL TESTS PASSED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all()
