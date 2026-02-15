"""
Tests for audit bug fixes and SCBE patrol/wall input validation.

Covers:
  Bug 1: Capacitor variable no longer shadows speed-of-light constant C
  Bug 2: Negative temperature no longer crashes Maxwell-Boltzmann
  Bug 3: Particle masses updated to CODATA 2018
  Patrol: Non-physical inputs detected and classified correctly
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
from .patrol import validate_params, validated_simulation, Decision


# =========================================================================
# BUG FIX TESTS
# =========================================================================

def test_bug1_capacitor_does_not_shadow_c():
    """
    Bug 1: Capacitor section used 'C' as local variable, shadowing
    the module-level speed-of-light constant.  After fix, sending both
    plate_area and em_frequency in the same call must produce correct
    EM wavelength (not capacitance / frequency).
    """
    result = electromagnetism({
        'plate_area': 0.01,
        'plate_separation': 0.001,
        'voltage': 100,
        'em_frequency': 5e14,  # visible light ~500 THz
    })

    # Capacitor should still work
    expected_cap = VACUUM_PERMITTIVITY * 0.01 / 0.001
    assert abs(result['capacitance'] - expected_cap) / expected_cap < 1e-10, \
        f"Capacitance wrong: {result['capacitance']}"

    # EM wavelength must be c/f, NOT capacitance/f
    expected_wavelength = C / 5e14  # ~6e-7 m (visible light)
    assert abs(result['em_wavelength'] - expected_wavelength) / expected_wavelength < 1e-10, \
        f"EM wavelength wrong: {result['em_wavelength']} (expected {expected_wavelength})"

    # Sanity: wavelength should be in visible range, not ~1e-25
    assert 1e-7 < result['em_wavelength'] < 1e-6, \
        f"Wavelength {result['em_wavelength']} not in visible range"

    print("  Bug 1 FIXED: capacitor variable no longer shadows C")


def test_bug2_negative_temperature_no_crash():
    """
    Bug 2: thermodynamics() crashed with ValueError on negative temperature
    when molecular_mass was also provided (math.sqrt of negative number).
    After fix, it should return avg_KE (which can be negative) but skip
    the speed calculations.
    """
    # Negative temperature: should not crash
    result = thermodynamics({
        'temperature': -100,
        'molecular_mass': 4.65e-26,
    })
    # avg_KE is computed (negative, which is fine as a number)
    assert 'average_kinetic_energy' in result
    # Speed calculations should be skipped (no sqrt of negative)
    assert 'rms_speed' not in result, "rms_speed should not be computed for T < 0"
    assert 'average_speed' not in result
    assert 'most_probable_speed' not in result

    # Zero temperature: also should not crash
    result_zero = thermodynamics({
        'temperature': 0,
        'molecular_mass': 4.65e-26,
    })
    assert 'rms_speed' not in result_zero, "rms_speed should not be computed for T = 0"

    # Positive temperature: should still work normally
    result_pos = thermodynamics({
        'temperature': 300,
        'molecular_mass': 4.65e-26,
    })
    assert 'rms_speed' in result_pos
    assert result_pos['rms_speed'] > 0

    print("  Bug 2 FIXED: negative/zero temperature no longer crashes")


def test_bug3_codata_2018_masses():
    """
    Bug 3: Particle masses were from CODATA 2014.  Verify they now match
    CODATA 2018 recommended values to full available precision.
    """
    # NIST CODATA 2018 values
    nist_electron = 9.1093837015e-31
    nist_proton = 1.67262192369e-27
    nist_neutron = 1.67492749804e-27

    assert ELECTRON_MASS == nist_electron, \
        f"Electron mass {ELECTRON_MASS} != NIST {nist_electron}"
    assert PROTON_MASS == nist_proton, \
        f"Proton mass {PROTON_MASS} != NIST {nist_proton}"
    assert NEUTRON_MASS == nist_neutron, \
        f"Neutron mass {NEUTRON_MASS} != NIST {nist_neutron}"

    print("  Bug 3 FIXED: particle masses match CODATA 2018")


# =========================================================================
# PATROL / WALL VALIDATION TESTS
# =========================================================================

def test_patrol_allows_valid_classical():
    """Valid classical mechanics inputs should pass."""
    result = validate_params('classical', {
        'mass': 10,
        'acceleration': 5,
    })
    assert result.decision == Decision.ALLOW
    assert not result.violations
    assert not result.warnings
    print("  Patrol ALLOW: valid classical inputs")


def test_wall_denies_negative_mass():
    """Negative mass is non-physical and must be denied."""
    result = validate_params('classical', {'mass': -5, 'acceleration': 10})
    assert result.decision == Decision.DENY
    assert any('Mass' in v for v in result.violations)
    print("  Wall DENY: negative mass")


def test_wall_denies_zero_distance():
    """Zero distance would cause division by zero."""
    result = validate_params('electromagnetism', {
        'charge1': 1.6e-19,
        'charge2': 1.6e-19,
        'distance': 0,
    })
    assert result.decision == Decision.DENY
    assert any('Distance' in v for v in result.violations)
    print("  Wall DENY: zero distance")


def test_wall_denies_negative_temperature():
    """Temperature below absolute zero must be denied."""
    result = validate_params('thermodynamics', {
        'temperature': -50,
        'molecular_mass': 4.65e-26,
    })
    assert result.decision == Decision.DENY
    assert any('below absolute zero' in v for v in result.violations)
    print("  Wall DENY: negative temperature")


def test_wall_denies_superluminal_velocity():
    """Velocity >= c must be denied for relativity simulations."""
    result = validate_params('relativity', {
        'velocity': C * 1.1,
        'proper_time': 1,
    })
    assert result.decision == Decision.DENY
    assert any('speed of light' in v for v in result.violations)
    print("  Wall DENY: superluminal velocity")


def test_patrol_warns_fast_classical():
    """Classical simulation at > 10% c should warn about relativistic effects."""
    result = validate_params('classical', {
        'mass': 1,
        'velocity': 0.5 * C,
    })
    assert result.decision == Decision.WARN
    assert any('relativistic' in w for w in result.warnings)
    print("  Patrol WARN: fast classical velocity")


def test_patrol_warns_zero_temperature():
    """T = 0 should warn about division-by-zero risk."""
    result = validate_params('thermodynamics', {
        'temperature': 0,
        'surface_area': 1,
    })
    assert result.decision == Decision.WARN
    assert any('absolute zero' in w for w in result.warnings)
    print("  Patrol WARN: T = 0 K")


def test_patrol_warns_inverted_carnot():
    """T_hot <= T_cold should produce a warning."""
    result = validate_params('thermodynamics', {
        'hot_temperature': 200,
        'cold_temperature': 300,
    })
    assert result.decision == Decision.WARN
    assert any('Carnot' in w for w in result.warnings)
    print("  Patrol WARN: inverted Carnot temperatures")


def test_wall_denies_nan_input():
    """NaN inputs must be denied."""
    result = validate_params('classical', {
        'mass': float('nan'),
        'acceleration': 5,
    })
    assert result.decision == Decision.DENY
    assert any('non-finite' in v for v in result.violations)
    print("  Wall DENY: NaN input")


def test_wall_denies_inf_input():
    """Inf inputs must be denied."""
    result = validate_params('quantum', {
        'wavelength': float('inf'),
    })
    assert result.decision == Decision.DENY
    assert any('non-finite' in v for v in result.violations)
    print("  Wall DENY: Inf input")


def test_wall_denies_non_integer_quantum_number():
    """Quantum numbers must be integers."""
    result = validate_params('quantum', {
        'principal_quantum_number': 2.5,
    })
    assert result.decision == Decision.DENY
    assert any('integer' in v for v in result.violations)
    print("  Wall DENY: non-integer quantum number")


def test_wall_denies_emissivity_out_of_range():
    """Emissivity must be in [0, 1]."""
    result = validate_params('thermodynamics', {
        'temperature': 300,
        'surface_area': 1,
        'emissivity': 1.5,
    })
    assert result.decision == Decision.DENY
    assert any('Emissivity' in v for v in result.violations)
    print("  Wall DENY: emissivity > 1")


def test_validated_simulation_deny():
    """validated_simulation should return 422 when wall denies."""
    sims = {
        'classical': classical_mechanics,
        'quantum': quantum_mechanics,
    }
    response = validated_simulation('classical', {'mass': -1, 'acceleration': 5}, sims)
    assert response['statusCode'] == 422
    body = json.loads(response['body'])
    assert body['decision'] == 'deny'
    print("  validated_simulation returns 422 on DENY")


def test_validated_simulation_allow():
    """validated_simulation should run simulation and return 200 on valid input."""
    sims = {
        'classical': classical_mechanics,
        'quantum': quantum_mechanics,
    }
    response = validated_simulation('classical', {'mass': 10, 'acceleration': 5}, sims)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['results']['force'] == 50
    assert body['validation']['decision'] == 'allow'
    print("  validated_simulation returns 200 on ALLOW")


# =========================================================================
# RUNNER
# =========================================================================

def run_all():
    print("\n" + "=" * 60)
    print(" BUG FIX & PATROL/WALL TESTS")
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

    print("\n" + "=" * 60)
    print(" ALL BUG FIX & PATROL/WALL TESTS PASSED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all()
