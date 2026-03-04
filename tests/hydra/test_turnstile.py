"""
Tests for HYDRA Turnstile -- domain-aware containment policy.
=============================================================

Covers:
- ALLOW pass-through for all domains
- DENY -> domain-specific action mapping (STOP, PIVOT, ISOLATE, HONEYPOT)
- QUARANTINE -> HOLD (browser), PIVOT (vehicle), DEGRADE/ISOLATE (fleet)
- ESCALATE with require_human flag
- Antibody load exponential decay math
- Membrane stress computation
- Edge cases: NaN / Infinity / negative inputs
"""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.turnstile import (
    resolve_turnstile,
    compute_antibody_load,
    compute_membrane_stress,
    TurnstileOutcome,
)


# =========================================================================
# ALLOW pass-through
# =========================================================================


class TestAllowPassthrough:
    """ALLOW decision should always yield action=ALLOW regardless of domain."""

    @pytest.mark.parametrize("domain", ["browser", "vehicle", "fleet", "antivirus", "default"])
    def test_allow_all_domains(self, domain: str):
        outcome = resolve_turnstile(decision="ALLOW", domain=domain)
        assert outcome.action == "ALLOW"
        assert outcome.continue_execution is True
        assert outcome.require_human is False
        assert outcome.isolate is False
        assert outcome.deploy_honeypot is False

    def test_allow_preserves_antibody_and_stress(self):
        outcome = resolve_turnstile(
            decision="ALLOW", domain="browser", suspicion=0.3, geometry_norm=0.5
        )
        assert outcome.action == "ALLOW"
        # antibody_load and membrane_stress should still be computed
        assert 0.0 <= outcome.antibody_load <= 1.0
        assert 0.0 <= outcome.membrane_stress <= 1.0


# =========================================================================
# DENY -> domain-specific mapping
# =========================================================================


class TestDenyRouting:
    """DENY decision routes to domain-specific containment action."""

    def test_deny_default_stops(self):
        outcome = resolve_turnstile(decision="DENY", domain="default")
        assert outcome.action == "STOP"
        assert outcome.continue_execution is False

    def test_deny_vehicle_pivots(self):
        outcome = resolve_turnstile(decision="DENY", domain="vehicle")
        assert outcome.action == "PIVOT"
        assert outcome.continue_execution is True
        assert outcome.isolate is False

    def test_deny_fleet_isolates(self):
        outcome = resolve_turnstile(decision="DENY", domain="fleet")
        assert outcome.action == "ISOLATE"
        assert outcome.isolate is True
        assert outcome.continue_execution is True

    def test_deny_antivirus_isolates_and_halts(self):
        outcome = resolve_turnstile(decision="DENY", domain="antivirus")
        assert outcome.action == "ISOLATE"
        assert outcome.isolate is True
        assert outcome.continue_execution is False

    def test_deny_browser_holds_for_human(self):
        outcome = resolve_turnstile(decision="DENY", domain="browser")
        assert outcome.action == "HOLD"
        assert outcome.require_human is True
        assert outcome.continue_execution is False


# =========================================================================
# QUARANTINE -> domain-specific mapping
# =========================================================================


class TestQuarantineRouting:
    """QUARANTINE decision routes differently per domain."""

    def test_quarantine_browser_holds_and_isolates(self):
        outcome = resolve_turnstile(decision="QUARANTINE", domain="browser")
        assert outcome.action == "HOLD"
        assert outcome.require_human is True
        assert outcome.isolate is True  # QUARANTINE sets isolate=True for browser
        assert outcome.continue_execution is False

    def test_quarantine_vehicle_pivots(self):
        outcome = resolve_turnstile(decision="QUARANTINE", domain="vehicle")
        assert outcome.action == "PIVOT"
        assert outcome.continue_execution is True
        assert outcome.isolate is False

    def test_quarantine_fleet_isolates(self):
        """QUARANTINE on fleet (not ESCALATE) -> ISOLATE action."""
        outcome = resolve_turnstile(decision="QUARANTINE", domain="fleet", quorum_ok=True)
        assert outcome.action == "ISOLATE"
        assert outcome.isolate is True
        assert outcome.continue_execution is True

    def test_quarantine_fleet_no_quorum_isolates(self):
        outcome = resolve_turnstile(decision="QUARANTINE", domain="fleet", quorum_ok=False)
        assert outcome.action == "ISOLATE"
        assert outcome.isolate is True

    def test_quarantine_default_stops(self):
        outcome = resolve_turnstile(decision="QUARANTINE", domain="default")
        assert outcome.action == "STOP"
        assert outcome.continue_execution is False


# =========================================================================
# ESCALATE
# =========================================================================


class TestEscalateRouting:
    """ESCALATE decision should propagate require_human where domain allows."""

    def test_escalate_browser_requires_human(self):
        outcome = resolve_turnstile(decision="ESCALATE", domain="browser")
        assert outcome.require_human is True
        assert outcome.action == "HOLD"

    def test_escalate_fleet_degrades(self):
        """Fleet ESCALATE -> DEGRADE (safe mode), no isolation."""
        outcome = resolve_turnstile(decision="ESCALATE", domain="fleet", quorum_ok=True)
        assert outcome.action == "DEGRADE"
        assert outcome.isolate is False
        assert outcome.continue_execution is True

    def test_escalate_vehicle_pivots(self):
        outcome = resolve_turnstile(decision="ESCALATE", domain="vehicle")
        assert outcome.action == "PIVOT"
        assert outcome.continue_execution is True

    def test_escalate_default_stops(self):
        outcome = resolve_turnstile(decision="ESCALATE", domain="default")
        assert outcome.action == "STOP"
        assert outcome.continue_execution is False


# =========================================================================
# Honeypot override (high stress / antibody)
# =========================================================================


class TestHoneypotOverride:
    """When membrane stress >= 0.9 or antibody >= 0.85, honeypot is deployed."""

    def test_honeypot_triggered_by_high_antibody(self):
        outcome = resolve_turnstile(
            decision="DENY",
            domain="default",
            suspicion=0.95,
            previous_antibody_load=0.9,
        )
        assert outcome.action == "HONEYPOT"
        assert outcome.deploy_honeypot is True
        assert outcome.isolate is True
        assert outcome.continue_execution is True

    def test_honeypot_triggered_by_high_membrane_stress(self):
        outcome = resolve_turnstile(
            decision="DENY",
            domain="default",
            geometry_norm=1.5,  # well above threshold -> stress ~1.0
        )
        assert outcome.action == "HONEYPOT"
        assert outcome.deploy_honeypot is True

    def test_honeypot_not_triggered_on_allow(self):
        """Even with extreme values, ALLOW should not trigger honeypot."""
        outcome = resolve_turnstile(
            decision="ALLOW",
            domain="default",
            suspicion=1.0,
            geometry_norm=5.0,
            previous_antibody_load=1.0,
        )
        assert outcome.action == "ALLOW"
        assert outcome.deploy_honeypot is False


# =========================================================================
# Antibody load math
# =========================================================================


class TestAntibodyLoadMath:
    """Validate antibody load decay formula."""

    def test_zero_suspicion_decays(self):
        """With 0 suspicion, antibody load decays toward 0."""
        load = compute_antibody_load(suspicion=0.0, previous_load=1.0, dt=100.0)
        assert load < 0.01  # should be very close to 0 after many time steps

    def test_full_suspicion_saturates(self):
        """With suspicion=1.0, load moves toward 1.0."""
        load = compute_antibody_load(suspicion=1.0, previous_load=0.0, dt=100.0)
        assert load > 0.9

    def test_half_life_property(self):
        """After one half-life with zero suspicion, load halves (approximately)."""
        half_life = 12.0
        initial = 0.8
        load = compute_antibody_load(
            suspicion=0.0, previous_load=initial, dt=half_life, half_life=half_life
        )
        # decay * initial where decay = exp(-ln2) = 0.5
        assert abs(load - initial * 0.5) < 0.01

    def test_clamped_to_unit_interval(self):
        load = compute_antibody_load(suspicion=2.0, previous_load=5.0, dt=1.0)
        assert 0.0 <= load <= 1.0

    def test_nan_suspicion_returns_one(self):
        load = compute_antibody_load(suspicion=float("nan"))
        assert load == 1.0

    def test_inf_suspicion_returns_one(self):
        load = compute_antibody_load(suspicion=float("inf"))
        assert load == 1.0

    def test_negative_inf_suspicion_returns_one(self):
        load = compute_antibody_load(suspicion=float("-inf"))
        assert load == 1.0


# =========================================================================
# Membrane stress math
# =========================================================================


class TestMembraneStressMath:
    """Validate membrane stress computation."""

    def test_below_threshold_is_zero(self):
        stress = compute_membrane_stress(norm_value=0.5, threshold=0.98)
        assert stress == 0.0

    def test_at_threshold_is_zero(self):
        stress = compute_membrane_stress(norm_value=0.98, threshold=0.98)
        assert stress == pytest.approx(0.0, abs=1e-6)

    def test_above_threshold_positive(self):
        stress = compute_membrane_stress(norm_value=0.99, threshold=0.98)
        assert stress > 0.0
        assert stress <= 1.0

    def test_well_above_threshold_clamps_to_one(self):
        stress = compute_membrane_stress(norm_value=5.0, threshold=0.98)
        assert stress == 1.0

    def test_nan_norm_returns_one(self):
        stress = compute_membrane_stress(norm_value=float("nan"))
        assert stress == 1.0

    def test_inf_norm_returns_one(self):
        stress = compute_membrane_stress(norm_value=float("inf"))
        assert stress == 1.0

    def test_negative_norm_is_zero(self):
        stress = compute_membrane_stress(norm_value=-1.0, threshold=0.98)
        assert stress == 0.0


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    """Edge cases and invalid inputs."""

    def test_unknown_decision_treated_as_deny(self):
        outcome = resolve_turnstile(decision="FOOBAR", domain="default")
        # FOOBAR normalizes to DENY -> default -> STOP
        assert outcome.action == "STOP"
        assert outcome.continue_execution is False

    def test_unknown_domain_treated_as_default(self):
        outcome = resolve_turnstile(decision="DENY", domain="spaceship")
        assert outcome.action == "STOP"

    def test_case_insensitive_decision(self):
        outcome = resolve_turnstile(decision="allow", domain="browser")
        assert outcome.action == "ALLOW"

    def test_case_insensitive_domain(self):
        outcome = resolve_turnstile(decision="DENY", domain="VEHICLE")
        assert outcome.action == "PIVOT"

    def test_outcome_is_frozen_dataclass(self):
        outcome = resolve_turnstile(decision="ALLOW", domain="default")
        with pytest.raises(AttributeError):
            outcome.action = "DENY"  # type: ignore[misc]
