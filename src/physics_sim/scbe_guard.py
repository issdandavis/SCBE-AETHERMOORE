"""
SCBE Patrol/Wall Guard for Physics Simulation Core

Validates physics inputs using the dual-regime harmonic scaling model:
  - PATROL: flags drift from physically plausible parameter ranges
  - WALL: hard denial for non-physical or numerically dangerous inputs

Tongue classification:
  Primary: RU (established knowledge — textbook physics)
  Secondary: CA (physical computation — numerical engine)
  Tertiary: KO (binding math to reality — dimensional coupling)

@layer Layer 5-6 (patrol drift monitoring), Layer 12 (wall governance)
@module physics_sim/scbe_guard
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from .core import C, G, PLANCK, BOLTZMANN, ELECTRON_MASS

# ─── Physical Bounds ────────────────────────────────────────────────────────
# These define the patrol envelope: parameters outside these ranges trigger
# drift signals. Wall bounds are the absolute hard limits (non-physical).

# fmt: off
BOUNDS = {
    # key: (wall_min, patrol_min, patrol_max, wall_max, unit)
    "mass":              (0,     1e-35,   1e40,   1e55,   "kg"),
    "velocity":          (-C,    -0.99*C, 0.99*C, C,      "m/s"),
    "distance":          (0,     1e-18,   1e27,   1e30,   "m"),
    "temperature":       (0,     0.001,   1e10,   1e15,   "K"),
    "charge":            (-1e6,  -1e3,    1e3,    1e6,    "C"),
    "frequency":         (0,     1e-3,    1e25,   1e30,   "Hz"),
    "wavelength":        (0,     1e-20,   1e8,    1e12,   "m"),
    "pressure":          (0,     1e-10,   1e15,   1e20,   "Pa"),
    "volume":            (0,     1e-30,   1e12,   1e20,   "m³"),
    "moles":             (0,     1e-15,   1e10,   1e15,   "mol"),
    "energy":            (0,     1e-40,   1e45,   1e55,   "J"),
    "time":              (0,     1e-25,   1e20,   1e25,   "s"),
    "current":           (-1e10, -1e7,    1e7,    1e10,   "A"),
    "magnetic_field":    (0,     1e-15,   1e6,    1e12,   "T"),
    "acceleration":      (None,  -1e15,   1e15,   None,   "m/s²"),
    "height":            (None,  -1e7,    1e9,    None,   "m"),
    "force":             (None,  -1e30,   1e30,   None,   "N"),
    "momentum":          (0,     1e-40,   1e30,   1e40,   "kg·m/s"),
    "molecular_mass":    (0,     1e-30,   1e-23,  1e-20,  "kg"),
    "plate_area":        (0,     1e-12,   1e4,    1e8,    "m²"),
    "plate_separation":  (0,     1e-12,   1e0,    1e3,    "m"),
    "surface_area":      (0,     1e-20,   1e15,   1e20,   "m²"),
    "box_length":        (0,     1e-15,   1e-6,   1e0,    "m"),
    "spring_constant":   (0,     1e-6,    1e8,    1e12,   "N/m"),
    "radius":            (0,     1e-18,   1e27,   1e30,   "m"),
    "particle_mass":     (0,     1e-35,   1e-20,  1e-15,  "kg"),
    "particle_velocity": (-C,    -0.99*C, 0.99*C, C,      "m/s"),
    "black_hole_mass":   (0,     1e20,    1e45,   1e55,   "kg"),
}
# fmt: on

# Aliases — some parameters appear under multiple names
PARAM_ALIASES = {
    "m1": "mass",
    "m2": "mass",
    "charge1": "charge",
    "charge2": "charge",
    "hot_temperature": "temperature",
    "cold_temperature": "temperature",
    "em_frequency": "frequency",
    "source_frequency": "frequency",
    "proper_time": "time",
    "proper_length": "distance",
    "voltage": "energy",  # eV-scale; use energy bounds loosely
    "specific_heat": None,  # no bounds (material property)
    "temperature_change": None,  # can be negative
    "heat": None,  # can be negative
    "emissivity": None,  # 0-1 checked separately
    "gravity": "acceleration",
    "angle": None,  # radians, any value
    "scattering_angle": None,  # radians
    "quantum_number": None,  # integer ≥ 1, checked separately
    "principal_quantum_number": None,
    "n_initial": None,
    "n_final": None,
    "position_uncertainty": "distance",
    "momentum_uncertainty": "momentum",
    "electric_field_strength": None,  # derived quantity
}


# ─── Violation Classes ──────────────────────────────────────────────────────

class PhysicsViolation:
    """A single parameter violation with drift distance."""

    __slots__ = ("param", "value", "severity", "reason", "drift")

    def __init__(
        self,
        param: str,
        value: float,
        severity: str,
        reason: str,
        drift: float = 0.0,
    ):
        self.param = param
        self.value = value
        self.severity = severity  # "patrol" | "wall"
        self.reason = reason
        self.drift = drift  # normalized distance from safe center [0, ∞)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param": self.param,
            "value": self.value,
            "severity": self.severity,
            "reason": self.reason,
            "drift": self.drift,
        }


class GuardResult:
    """Aggregated guard outcome with per-parameter diagnostics."""

    __slots__ = ("violations", "decision", "max_drift", "tongue_class")

    def __init__(self):
        self.violations: List[PhysicsViolation] = []
        self.decision: str = "ALLOW"  # ALLOW | QUARANTINE | ESCALATE | DENY
        self.max_drift: float = 0.0
        self.tongue_class: Tuple[str, str, str] = ("RU", "CA", "KO")

    @property
    def safe(self) -> bool:
        return self.decision == "ALLOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "safe": self.safe,
            "max_drift": self.max_drift,
            "tongue_class": list(self.tongue_class),
            "violations": [v.to_dict() for v in self.violations],
        }


# ─── Guard Logic ────────────────────────────────────────────────────────────

def _compute_drift(value: float, patrol_min: float, patrol_max: float) -> float:
    """
    Compute normalized drift distance from the patrol envelope.
    Returns 0 if value is within [patrol_min, patrol_max].
    Returns log-scaled distance otherwise (since physics spans many orders of magnitude).
    """
    if patrol_min <= value <= patrol_max:
        return 0.0
    if value < patrol_min:
        if patrol_min <= 0:
            return abs(value - patrol_min)
        return abs(math.log10(abs(value) + 1e-100) - math.log10(patrol_min))
    # value > patrol_max
    if patrol_max <= 0:
        return abs(value - patrol_max)
    return abs(math.log10(abs(value) + 1e-100) - math.log10(patrol_max))


def guard_params(
    simulation_type: str,
    params: Dict[str, Any],
    thresholds: Optional[Dict[str, float]] = None,
) -> GuardResult:
    """
    Validate physics parameters against the SCBE patrol/wall envelope.

    Args:
        simulation_type: One of "classical", "quantum", "electromagnetism",
                         "thermodynamics", "relativity"
        params: The parameter dict to validate
        thresholds: Optional drift thresholds for decisions
                    {quarantine: float, escalate: float, deny: float}

    Returns:
        GuardResult with decision, violations, and max drift
    """
    if thresholds is None:
        thresholds = {"quarantine": 2.0, "escalate": 5.0, "deny": 10.0}

    result = GuardResult()

    for key, value in params.items():
        if not isinstance(value, (int, float)):
            continue

        # Resolve the bounds key
        bounds_key = key
        if key in PARAM_ALIASES:
            alias = PARAM_ALIASES[key]
            if alias is None:
                continue  # no bounds for this param
            bounds_key = alias

        if bounds_key not in BOUNDS:
            continue

        wall_min, patrol_min, patrol_max, wall_max, unit = BOUNDS[bounds_key]

        # ── Wall check (hard denial) ──
        if wall_min is not None and value <= wall_min:
            v = PhysicsViolation(
                key, value, "wall",
                f"{key}={value} violates hard minimum ({wall_min} {unit})",
                drift=float("inf"),
            )
            result.violations.append(v)
            continue

        if wall_max is not None and value >= wall_max:
            v = PhysicsViolation(
                key, value, "wall",
                f"{key}={value} violates hard maximum ({wall_max} {unit})",
                drift=float("inf"),
            )
            result.violations.append(v)
            continue

        # ── Patrol check (drift monitoring) ──
        drift = _compute_drift(value, patrol_min, patrol_max)
        if drift > 0:
            v = PhysicsViolation(
                key, value, "patrol",
                f"{key}={value} drifts from plausible range "
                f"[{patrol_min}, {patrol_max}] {unit} (drift={drift:.3f})",
                drift=drift,
            )
            result.violations.append(v)

    # ── Special checks ──

    # Quantum numbers must be positive integers
    for qn_key in ("quantum_number", "principal_quantum_number", "n_initial", "n_final"):
        if qn_key in params:
            val = params[qn_key]
            if not isinstance(val, int) or val < 1:
                result.violations.append(PhysicsViolation(
                    qn_key, val, "wall",
                    f"{qn_key} must be a positive integer, got {val}",
                    drift=float("inf"),
                ))

    # Emissivity must be in [0, 1]
    if "emissivity" in params:
        eps = params["emissivity"]
        if isinstance(eps, (int, float)) and (eps < 0 or eps > 1):
            result.violations.append(PhysicsViolation(
                "emissivity", eps, "wall",
                f"emissivity must be in [0,1], got {eps}",
                drift=float("inf"),
            ))

    # Carnot: T_hot must exceed T_cold
    if "hot_temperature" in params and "cold_temperature" in params:
        t_h = params["hot_temperature"]
        t_c = params["cold_temperature"]
        if isinstance(t_h, (int, float)) and isinstance(t_c, (int, float)):
            if t_c >= t_h:
                result.violations.append(PhysicsViolation(
                    "cold_temperature", t_c, "patrol",
                    f"T_cold ({t_c} K) >= T_hot ({t_h} K) — violates 2nd law",
                    drift=3.0,
                ))

    # Superluminal velocity — hard wall
    if "velocity" in params:
        v = params["velocity"]
        if isinstance(v, (int, float)) and abs(v) >= C:
            # Already caught by wall bounds, but be explicit
            pass

    # ── Aggregate decision ──
    max_drift = 0.0
    has_wall = False
    for v in result.violations:
        if v.severity == "wall":
            has_wall = True
        if v.drift != float("inf"):
            max_drift = max(max_drift, v.drift)
        else:
            max_drift = float("inf")

    result.max_drift = max_drift

    if has_wall:
        result.decision = "DENY"
    elif max_drift >= thresholds["deny"]:
        result.decision = "DENY"
    elif max_drift >= thresholds["escalate"]:
        result.decision = "ESCALATE"
    elif max_drift >= thresholds["quarantine"]:
        result.decision = "QUARANTINE"
    else:
        result.decision = "ALLOW"

    return result


def guarded_simulate(
    simulation_type: str,
    params: Dict[str, Any],
    simulations: Optional[Dict] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Run a physics simulation with SCBE guard.

    If guard returns DENY, the simulation is NOT executed.
    If guard returns QUARANTINE or ESCALATE, a warning is attached.

    Args:
        simulation_type: Simulation domain
        params: Input parameters
        simulations: Optional simulation function dispatch table
        thresholds: Optional drift thresholds

    Returns:
        Dict with 'guard', 'results' (if allowed), and 'statusCode'
    """
    from .core import (
        classical_mechanics,
        quantum_mechanics,
        electromagnetism,
        thermodynamics,
        relativity,
    )

    if simulations is None:
        simulations = {
            "classical": classical_mechanics,
            "quantum": quantum_mechanics,
            "electromagnetism": electromagnetism,
            "thermodynamics": thermodynamics,
            "relativity": relativity,
        }

    if simulation_type not in simulations:
        return {
            "statusCode": 400,
            "error": f"Invalid simulation type: {simulation_type}",
            "valid_types": list(simulations.keys()),
        }

    # Run guard
    guard = guard_params(simulation_type, params, thresholds)

    if guard.decision == "DENY":
        return {
            "statusCode": 403,
            "guard": guard.to_dict(),
            "results": None,
            "denied": True,
        }

    # Run simulation
    results = simulations[simulation_type](params)

    return {
        "statusCode": 200,
        "guard": guard.to_dict(),
        "results": results,
        "denied": False,
    }
