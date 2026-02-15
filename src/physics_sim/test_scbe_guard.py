"""
Tests for SCBE patrol/wall guard on physics simulation core.

Covers:
  A. Bug fixes (capacitor shadow, negative-T crash, CODATA 2018 masses)
  B. Patrol envelope (drift detection for implausible but non-fatal inputs)
  C. Wall enforcement (hard denial for non-physical inputs)
  D. Aggregated decisions (ALLOW → QUARANTINE → ESCALATE → DENY)
  E. Guarded simulation (end-to-end: guard + compute)
  F. Special checks (quantum numbers, emissivity, Carnot)
  G. Edge cases
"""

import math
import pytest

from .core import (
    C,
    ELECTRON_MASS,
    PROTON_MASS,
    NEUTRON_MASS,
    classical_mechanics,
    quantum_mechanics,
    electromagnetism,
    thermodynamics,
    relativity,
)
from .scbe_guard import (
    BOUNDS,
    GuardResult,
    PhysicsViolation,
    _compute_drift,
    guard_params,
    guarded_simulate,
)


# ═══════════════════════════════════════════════════════════════════════════
# A. Bug Fix Regression Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestBugFixes:
    """Verify the 3 audit-identified bugs stay fixed."""

    def test_a1_capacitor_does_not_shadow_speed_of_light(self):
        """Bug 1: capacitor local `C` must not shadow module-level C = 299792458."""
        result = electromagnetism(
            {
                "plate_area": 0.01,
                "plate_separation": 0.001,
                "voltage": 100,
                "em_frequency": 5e14,
            }
        )
        # EM wavelength should be ~600nm (visible light), NOT capacitance/frequency
        expected_wl = C / 5e14  # ~5.996e-7 m
        assert abs(result["em_wavelength"] - expected_wl) < 1e-12
        assert result["wave_type"] == "visible_light"
        # Capacitor should also be computed correctly
        assert result["capacitance"] > 0
        assert result["stored_energy"] > 0

    def test_a2_negative_temperature_does_not_crash(self):
        """Bug 2: T ≤ 0 must not reach math.sqrt(negative)."""
        # Should NOT raise ValueError
        result = thermodynamics({"temperature": -100, "molecular_mass": 4.65e-26})
        assert "rms_speed" not in result
        assert "average_kinetic_energy" not in result

    def test_a3_zero_temperature_does_not_crash(self):
        """Bug 2 (edge): T = 0 must not crash either."""
        result = thermodynamics({"temperature": 0, "molecular_mass": 4.65e-26})
        assert "rms_speed" not in result

    def test_a4_positive_temperature_still_works(self):
        """Bug 2 (regression): normal T > 0 must still compute."""
        result = thermodynamics({"temperature": 300, "molecular_mass": 4.65e-26})
        assert "rms_speed" in result
        assert result["rms_speed"] > 0
        assert "average_kinetic_energy" in result

    def test_a5_electron_mass_codata_2018(self):
        """Bug 3: electron mass should be CODATA 2018."""
        assert abs(ELECTRON_MASS - 9.1093837015e-31) < 1e-40

    def test_a6_proton_mass_codata_2018(self):
        """Bug 3: proton mass should be CODATA 2018."""
        assert abs(PROTON_MASS - 1.67262192369e-27) < 1e-37

    def test_a7_neutron_mass_codata_2018(self):
        """Bug 3: neutron mass — worst offender in the original."""
        assert abs(NEUTRON_MASS - 1.67492749804e-27) < 1e-37

    def test_a8_neutron_proton_mass_difference(self):
        """The n-p mass difference is critical for nuclear binding calculations."""
        delta = NEUTRON_MASS - PROTON_MASS
        # CODATA 2018: 1.29333236 MeV/c² = 2.30557435e-30 kg
        expected_delta = 2.30557435e-30
        # Allow 0.1% relative error
        assert abs(delta - expected_delta) / expected_delta < 0.001


# ═══════════════════════════════════════════════════════════════════════════
# B. Patrol Envelope (Drift Detection)
# ═══════════════════════════════════════════════════════════════════════════


class TestPatrolEnvelope:
    """Parameters within wall but outside patrol range trigger drift signals."""

    def test_b1_normal_params_no_drift(self):
        """Textbook values produce zero drift → ALLOW."""
        g = guard_params("classical", {"mass": 1.0, "velocity": 10.0, "distance": 1.0})
        assert g.decision == "ALLOW"
        assert g.max_drift == 0.0
        assert len(g.violations) == 0

    def test_b2_extreme_mass_triggers_patrol(self):
        """Mass of 1e42 kg (above patrol_max 1e40) triggers drift."""
        g = guard_params("classical", {"mass": 1e42})
        patrol_vs = [v for v in g.violations if v.severity == "patrol"]
        assert len(patrol_vs) == 1
        assert patrol_vs[0].param == "mass"
        assert patrol_vs[0].drift > 0

    def test_b3_drift_is_zero_inside_patrol(self):
        """Value squarely in patrol range → drift = 0."""
        d = _compute_drift(1.0, 1e-35, 1e40)
        assert d == 0.0

    def test_b4_drift_increases_with_distance(self):
        """Farther from patrol envelope → higher drift."""
        d1 = _compute_drift(1e41, 1e-35, 1e40)
        d2 = _compute_drift(1e45, 1e-35, 1e40)
        assert d2 > d1 > 0

    def test_b5_near_light_speed_triggers_patrol(self):
        """0.999c is inside wall but outside patrol (>0.99c)."""
        g = guard_params("relativity", {"velocity": 0.999 * C})
        patrol_vs = [v for v in g.violations if v.severity == "patrol"]
        assert len(patrol_vs) >= 1

    def test_b6_low_frequency_triggers_patrol(self):
        """1e-5 Hz is within wall but below patrol min (1e-3)."""
        g = guard_params("quantum", {"frequency": 1e-5})
        assert any(v.param == "frequency" for v in g.violations)


# ═══════════════════════════════════════════════════════════════════════════
# C. Wall Enforcement (Hard Denial)
# ═══════════════════════════════════════════════════════════════════════════


class TestWallEnforcement:
    """Non-physical parameters hit the wall → instant DENY."""

    def test_c1_negative_mass_denied(self):
        """Mass ≤ 0 is non-physical → wall violation."""
        g = guard_params("classical", {"mass": -5.0})
        assert g.decision == "DENY"
        wall_vs = [v for v in g.violations if v.severity == "wall"]
        assert len(wall_vs) >= 1

    def test_c2_zero_mass_denied(self):
        """Mass = 0 hits wall_min (0 is exclusive)."""
        g = guard_params("classical", {"mass": 0})
        assert g.decision == "DENY"

    def test_c3_superluminal_velocity_denied(self):
        """v ≥ c violates special relativity → wall."""
        g = guard_params("relativity", {"velocity": C})
        assert g.decision == "DENY"

    def test_c4_negative_distance_denied(self):
        """Distance ≤ 0 is non-physical."""
        g = guard_params("classical", {"mass": 1.0, "distance": -1.0})
        wall_vs = [v for v in g.violations if v.severity == "wall" and v.param == "distance"]
        assert len(wall_vs) == 1

    def test_c5_negative_temperature_denied(self):
        """T ≤ 0 K violates thermodynamics (classical regime)."""
        g = guard_params("thermodynamics", {"temperature": -50})
        assert g.decision == "DENY"

    def test_c6_zero_temperature_denied(self):
        """T = 0 K is the wall boundary (exclusive) — unattainable in thermodynamics."""
        g = guard_params("thermodynamics", {"temperature": 0})
        assert g.decision == "DENY"

    def test_c7_negative_wavelength_denied(self):
        """Wavelength must be > 0."""
        g = guard_params("quantum", {"wavelength": -1e-9})
        assert g.decision == "DENY"

    def test_c8_wall_violations_have_inf_drift(self):
        """Wall violations produce infinite drift."""
        g = guard_params("classical", {"mass": -1.0})
        for v in g.violations:
            if v.severity == "wall":
                assert v.drift == float("inf")


# ═══════════════════════════════════════════════════════════════════════════
# D. Aggregated Decisions
# ═══════════════════════════════════════════════════════════════════════════


class TestDecisions:
    """Guard aggregates violations into ALLOW/QUARANTINE/ESCALATE/DENY."""

    def test_d1_clean_params_allow(self):
        """Normal inputs → ALLOW."""
        g = guard_params("classical", {"mass": 10, "velocity": 5, "distance": 100})
        assert g.decision == "ALLOW"
        assert g.safe is True

    def test_d2_mild_drift_quarantine(self):
        """Moderate drift → QUARANTINE (default threshold 2.0)."""
        g = guard_params(
            "classical",
            {"mass": 1e42},  # 2 orders above patrol max
            thresholds={"quarantine": 1.0, "escalate": 5.0, "deny": 10.0},
        )
        assert g.decision in ("QUARANTINE", "ESCALATE", "DENY")
        assert g.max_drift >= 1.0

    def test_d3_wall_always_deny(self):
        """Any wall violation → DENY regardless of drift threshold."""
        g = guard_params(
            "classical",
            {"mass": -1},
            thresholds={"quarantine": 100, "escalate": 200, "deny": 300},
        )
        assert g.decision == "DENY"

    def test_d4_custom_thresholds(self):
        """Custom thresholds shift decision boundaries."""
        params = {"mass": 1.0, "velocity": 10.0}
        # Very permissive thresholds
        g = guard_params("classical", params, {"quarantine": 100, "escalate": 200, "deny": 300})
        assert g.decision == "ALLOW"

    def test_d5_to_dict_structure(self):
        """GuardResult.to_dict() has all expected keys."""
        g = guard_params("classical", {"mass": 1.0})
        d = g.to_dict()
        assert "decision" in d
        assert "safe" in d
        assert "max_drift" in d
        assert "tongue_class" in d
        assert "violations" in d
        assert d["tongue_class"] == ["RU", "CA", "KO"]


# ═══════════════════════════════════════════════════════════════════════════
# E. Guarded Simulation (End-to-End)
# ═══════════════════════════════════════════════════════════════════════════


class TestGuardedSimulation:
    """guarded_simulate() runs guard then compute (or denies)."""

    def test_e1_valid_classical_executes(self):
        """Valid params → guard ALLOW + simulation results."""
        r = guarded_simulate("classical", {"mass": 10, "acceleration": 9.8})
        assert r["statusCode"] == 200
        assert r["denied"] is False
        assert r["results"]["force"] == pytest.approx(98.0)
        assert r["guard"]["decision"] == "ALLOW"

    def test_e2_invalid_params_denied(self):
        """Non-physical params → guard DENY, no results."""
        r = guarded_simulate("classical", {"mass": -5, "acceleration": 9.8})
        assert r["statusCode"] == 403
        assert r["denied"] is True
        assert r["results"] is None

    def test_e3_invalid_simulation_type(self):
        """Unknown simulation type → 400."""
        r = guarded_simulate("alchemy", {"mass": 1.0})
        assert r["statusCode"] == 400
        assert "error" in r

    def test_e4_quantum_hydrogen_executes(self):
        """Valid quantum params → hydrogen energy levels."""
        r = guarded_simulate("quantum", {"principal_quantum_number": 2})
        assert r["statusCode"] == 200
        assert r["results"]["hydrogen_energy_eV"] == pytest.approx(-3.4, abs=0.01)

    def test_e5_thermodynamics_ideal_gas(self):
        """Valid thermo params → ideal gas law."""
        r = guarded_simulate(
            "thermodynamics", {"pressure": 101325, "volume": 0.0224, "moles": 1.0}
        )
        assert r["statusCode"] == 200
        assert "temperature" in r["results"]
        # PV/nR ≈ 273 K
        assert r["results"]["temperature"] == pytest.approx(273.15, rel=0.01)

    def test_e6_relativity_lorentz(self):
        """Valid relativity params → Lorentz factor."""
        r = guarded_simulate("relativity", {"velocity": 0.8 * C, "mass": 1.0})
        assert r["statusCode"] == 200
        gamma = r["results"]["lorentz_factor"]
        assert gamma == pytest.approx(1 / math.sqrt(1 - 0.64), rel=1e-6)

    def test_e7_em_capacitor_and_wave(self):
        """The capacitor shadow bug fix: both results correct in single call."""
        r = guarded_simulate(
            "electromagnetism",
            {
                "plate_area": 0.01,
                "plate_separation": 0.001,
                "voltage": 100,
                "em_frequency": 5e14,
            },
        )
        assert r["statusCode"] == 200
        assert r["results"]["wave_type"] == "visible_light"
        assert r["results"]["em_wavelength"] == pytest.approx(C / 5e14, rel=1e-10)


# ═══════════════════════════════════════════════════════════════════════════
# F. Special Checks
# ═══════════════════════════════════════════════════════════════════════════


class TestSpecialChecks:
    """Domain-specific validation beyond simple bounds."""

    def test_f1_quantum_number_must_be_positive_int(self):
        """n = 0 or n = -1 → wall."""
        g = guard_params("quantum", {"quantum_number": 0})
        assert g.decision == "DENY"
        g2 = guard_params("quantum", {"quantum_number": -3})
        assert g2.decision == "DENY"

    def test_f2_quantum_number_float_denied(self):
        """n = 2.5 is not a valid quantum number."""
        g = guard_params("quantum", {"principal_quantum_number": 2.5})
        # 2.5 is not int → wall
        assert g.decision == "DENY"

    def test_f3_valid_quantum_number_allowed(self):
        """n = 3 is fine."""
        g = guard_params("quantum", {"principal_quantum_number": 3})
        assert g.decision == "ALLOW"

    def test_f4_emissivity_out_of_range(self):
        """Emissivity > 1 is non-physical."""
        g = guard_params("thermodynamics", {"emissivity": 1.5, "temperature": 300, "surface_area": 1.0})
        assert any(v.param == "emissivity" for v in g.violations)

    def test_f5_carnot_cold_exceeds_hot(self):
        """T_cold ≥ T_hot violates 2nd law."""
        g = guard_params(
            "thermodynamics", {"hot_temperature": 300, "cold_temperature": 400}
        )
        assert any("2nd law" in v.reason for v in g.violations)

    def test_f6_valid_carnot_allowed(self):
        """T_hot > T_cold → no violation."""
        g = guard_params(
            "thermodynamics", {"hot_temperature": 500, "cold_temperature": 300}
        )
        carnot_vs = [v for v in g.violations if "2nd law" in v.reason]
        assert len(carnot_vs) == 0


# ═══════════════════════════════════════════════════════════════════════════
# G. Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_g1_empty_params(self):
        """No params → ALLOW with no violations."""
        g = guard_params("classical", {})
        assert g.decision == "ALLOW"
        assert len(g.violations) == 0

    def test_g2_non_numeric_params_ignored(self):
        """String params are silently skipped (not physics values)."""
        g = guard_params("classical", {"label": "test", "mass": 1.0})
        assert g.decision == "ALLOW"

    def test_g3_param_aliases_resolved(self):
        """m1/m2 resolve to 'mass' bounds."""
        g = guard_params("classical", {"m1": -1.0, "m2": 1.0, "distance": 1.0})
        assert g.decision == "DENY"
        assert any(v.param == "m1" for v in g.violations)

    def test_g4_multiple_violations_aggregated(self):
        """Multiple bad params → all violations collected."""
        g = guard_params(
            "classical", {"mass": -1.0, "distance": -5.0, "velocity": 0}
        )
        assert len(g.violations) >= 2

    def test_g5_violation_to_dict(self):
        """PhysicsViolation.to_dict() has required fields."""
        v = PhysicsViolation("mass", -1.0, "wall", "negative mass", drift=float("inf"))
        d = v.to_dict()
        assert d["param"] == "mass"
        assert d["value"] == -1.0
        assert d["severity"] == "wall"
        assert d["drift"] == float("inf")

    def test_g6_guard_result_safe_property(self):
        """safe = True only when decision is ALLOW."""
        r = GuardResult()
        r.decision = "ALLOW"
        assert r.safe is True
        r.decision = "QUARANTINE"
        assert r.safe is False
        r.decision = "DENY"
        assert r.safe is False

    def test_g7_bounds_coverage(self):
        """All defined bounds have 5-tuple structure."""
        for key, bounds in BOUNDS.items():
            assert len(bounds) == 5, f"BOUNDS[{key}] should be 5-tuple"
            wall_min, patrol_min, patrol_max, wall_max, unit = bounds
            assert isinstance(unit, str)
            if patrol_min is not None and patrol_max is not None:
                assert patrol_min < patrol_max, f"BOUNDS[{key}]: patrol_min >= patrol_max"
            if wall_min is not None and patrol_min is not None:
                assert wall_min <= patrol_min, f"BOUNDS[{key}]: wall_min > patrol_min"
            if wall_max is not None and patrol_max is not None:
                assert wall_max >= patrol_max, f"BOUNDS[{key}]: wall_max < patrol_max"

    def test_g8_schwarzschild_radius_valid(self):
        """Solar mass black hole → valid Schwarzschild radius."""
        solar_mass = 1.989e30
        r = guarded_simulate("relativity", {"black_hole_mass": solar_mass})
        assert r["statusCode"] == 200
        # r_s ≈ 2954 m for solar mass
        assert r["results"]["schwarzschild_radius"] == pytest.approx(2954, rel=0.01)
