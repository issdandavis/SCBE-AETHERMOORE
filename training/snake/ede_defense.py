"""Stage 5.5: EDE Defense Scoring — Entropic Defense Engine integration.

Wraps the ChemistryAgent immune system to score each record's defensive
properties. The squared-energy model maps directly onto tongue activation:
  - Small legitimate inputs → stable (low energy, no refraction)
  - Large adversarial inputs → exponential energy → refraction → sink

Integration points from the EDE:
  squared_energy(x) = log(1 + x²)     — tongue magnitude → energy
  ray_refraction(v, threat)            — deflect high-energy records
  harmonic_sink(v, depth)              — absorb deflected energy
  equilibrium_force(x, x_eq, k)       — restoring force toward balance
  self_heal(current, target, rate)     — recovery trajectory

The threat_level per record is derived from:
  - HYDRA extinction count (how many tongues voted to kill)
  - Friction max value (high friction = high threat surface)
  - Hyperbolic distance (far from center = more adversarial)

The defense score feeds into Stage 6 (multilang forge) to determine
which records need adversarial training variants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .config import PHI, TONGUES, TONGUE_WEIGHTS

# Import EDE components
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from symphonic_cipher.scbe_aethermoore.ede.chemistry_agent import (
        squared_energy,
        ray_refraction,
        harmonic_sink,
        self_heal,
        equilibrium_force,
        quick_defense_check,
        ChemistryAgent,
        ThreatType,
        THREAT_LEVEL_MIN,
        THREAT_LEVEL_MAX,
    )
    EDE_AVAILABLE = True
except ImportError:
    EDE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Fallback implementations if EDE import fails
# ---------------------------------------------------------------------------

if not EDE_AVAILABLE:
    def squared_energy(x: float) -> float:
        return math.log(1 + x ** 2)

    def ray_refraction(value: float, threat_level: int, max_refraction: float = 0.8) -> float:
        strength = (threat_level / 10) * max_refraction
        return value * (1 - strength)

    def harmonic_sink(value: float, depth: int = 3) -> float:
        return value / (PHI ** depth)

    def self_heal(current: float, target: float, rate: float = 0.1) -> float:
        return current + (target - current) * rate

    def equilibrium_force(position: float, eq: float, k: float = 1.0) -> float:
        return -k * (position - eq)

    def quick_defense_check(value: float, threat_level: int = 5):
        energy = squared_energy(abs(value))
        threshold = 5.0 - (threat_level * 0.3)
        if energy > threshold:
            deflected = ray_refraction(value, threat_level)
            absorbed = harmonic_sink(abs(deflected), min(6, threat_level))
            return absorbed, True, energy
        return value, False, energy

    THREAT_LEVEL_MIN = 1
    THREAT_LEVEL_MAX = 10


# ---------------------------------------------------------------------------
# Defense result
# ---------------------------------------------------------------------------


@dataclass
class EDEDefenseResult:
    """Output of EDE defense scoring for a single record."""

    # Energy model
    tongue_energy: float          # squared_energy of tongue magnitude
    tongue_energies: dict[str, float]  # Per-tongue squared energies
    total_energy: float           # Sum of all tongue energies

    # Threat assessment
    threat_level: int             # Derived threat level (1-10)
    threat_sources: list[str]    # What contributed to the threat level

    # Defense response
    was_deflected: bool           # Did refraction trigger?
    deflected_value: float        # Value after refraction
    sink_absorption: float        # Energy absorbed by harmonic sink
    sink_depth: int               # Which harmonic depth absorbed it

    # Equilibrium
    equilibrium_delta: float      # Distance from tongue equilibrium
    restoring_force: float        # Force pulling back to balance
    healing_trajectory: float     # Projected health after self-heal

    # Composite scores
    defense_score: float          # 0-1, overall defensive posture
    vulnerability_index: float    # 0-1, exposure to attack
    ede_available: bool           # Whether real EDE was used

    def to_dict(self) -> dict[str, Any]:
        return {
            "tongue_energy": self.tongue_energy,
            "total_energy": self.total_energy,
            "threat_level": self.threat_level,
            "threat_sources": self.threat_sources,
            "was_deflected": self.was_deflected,
            "deflected_value": self.deflected_value,
            "sink_absorption": self.sink_absorption,
            "sink_depth": self.sink_depth,
            "equilibrium_delta": self.equilibrium_delta,
            "restoring_force": self.restoring_force,
            "healing_trajectory": self.healing_trajectory,
            "defense_score": self.defense_score,
            "vulnerability_index": self.vulnerability_index,
            "ede_available": self.ede_available,
        }


# ---------------------------------------------------------------------------
# Threat level derivation
# ---------------------------------------------------------------------------


def _derive_threat_level(
    extinction_count: int,
    max_friction: float,
    hyperbolic_distance: float,
    oscillation: float,
) -> tuple[int, list[str]]:
    """Derive a 1-10 threat level from pipeline metadata.

    Each source contributes to the overall threat assessment:
    - Extinction count: how many HYDRA tongues voted to kill
    - Max friction: peak boundary friction (high = contentious)
    - Hyperbolic distance: distance from safe center
    - Oscillation: HYDRA viability disagreement (high = ambiguous)
    """
    threat = 1.0
    sources = []

    # Extinction: each killed tongue adds 1.5 threat
    if extinction_count > 0:
        extinction_threat = min(extinction_count * 1.5, 5.0)
        threat += extinction_threat
        sources.append(f"extinction:{extinction_count}")

    # Friction: high friction = high attack surface
    if max_friction > 0.5:
        friction_threat = min(max_friction * 3.0, 3.0)
        threat += friction_threat
        sources.append(f"friction:{max_friction:.2f}")

    # Hyperbolic distance: far from center = adversarial territory
    if hyperbolic_distance > 1.0:
        distance_threat = min(hyperbolic_distance * 0.5, 2.0)
        threat += distance_threat
        sources.append(f"distance:{hyperbolic_distance:.2f}")

    # Oscillation: high disagreement = ambiguous content (could be adversarial)
    if oscillation > 0.3:
        osc_threat = min(oscillation * 2.0, 1.5)
        threat += osc_threat
        sources.append(f"oscillation:{oscillation:.4f}")

    level = max(THREAT_LEVEL_MIN, min(THREAT_LEVEL_MAX, int(round(threat))))
    return level, sources


# ---------------------------------------------------------------------------
# Tongue equilibrium computation
# ---------------------------------------------------------------------------


def _tongue_equilibrium(profile: dict[str, float]) -> float:
    """Compute how far a tongue profile is from perfect equilibrium.

    Perfect equilibrium = all tongues at 1/6 ≈ 0.167.
    Returns the phi-weighted L2 distance from the balanced state.
    """
    balanced = 1.0 / len(TONGUES)
    delta_sq = 0.0
    for t in TONGUES:
        diff = (profile.get(t, 0.0) - balanced) * TONGUE_WEIGHTS[t]
        delta_sq += diff * diff
    return math.sqrt(delta_sq)


def _tongue_magnitude(profile: dict[str, float]) -> float:
    """Compute phi-weighted magnitude of a tongue profile.

    This is the 'input value' for the squared-energy model.
    Higher magnitude = more extreme profile = more energy.
    """
    mag_sq = 0.0
    for t in TONGUES:
        val = profile.get(t, 0.0) * TONGUE_WEIGHTS[t]
        mag_sq += val * val
    return math.sqrt(mag_sq)


# ---------------------------------------------------------------------------
# Main defense scoring
# ---------------------------------------------------------------------------


def ede_score(
    tongue_profile: dict[str, float],
    extinction_count: int = 0,
    max_friction: float = 0.0,
    hyperbolic_distance: float = 0.0,
    oscillation: float = 0.0,
    safety_score: float = 1.0,
) -> EDEDefenseResult:
    """Score a record through the Entropic Defense Engine.

    Computes energy, threat level, refraction, sink absorption,
    equilibrium forces, and composite defense/vulnerability scores.

    Args:
        tongue_profile: 6D tongue activation dict
        extinction_count: Number of HYDRA tongues that voted to kill
        max_friction: Peak friction value from Stage 5
        hyperbolic_distance: Distance from Poincare ball center
        oscillation: HYDRA viability oscillation
        safety_score: Harmonic wall safety score from Stage 4
    """
    # === ENERGY MODEL ===

    # Per-tongue squared energies
    tongue_energies = {}
    for t in TONGUES:
        val = tongue_profile.get(t, 0.0) * TONGUE_WEIGHTS[t]
        tongue_energies[t] = round(squared_energy(val), 6)

    # Total profile magnitude → squared energy
    magnitude = _tongue_magnitude(tongue_profile)
    tongue_energy = round(squared_energy(magnitude), 6)
    total_energy = round(sum(tongue_energies.values()), 6)

    # === THREAT ASSESSMENT ===

    threat_level, threat_sources = _derive_threat_level(
        extinction_count, max_friction, hyperbolic_distance, oscillation
    )

    # === DEFENSE RESPONSE ===

    # Run through quick_defense_check with the tongue magnitude as input
    processed, was_deflected, energy = quick_defense_check(magnitude, threat_level)

    # If deflected, compute sink depth and absorption
    if was_deflected:
        sink_depth = min(6, threat_level)
        sink_absorption = round(abs(magnitude) - abs(processed), 6)
        deflected_value = round(processed, 6)
    else:
        sink_depth = 0
        sink_absorption = 0.0
        deflected_value = round(magnitude, 6)

    # === EQUILIBRIUM ===

    eq_delta = round(_tongue_equilibrium(tongue_profile), 6)
    restoring = round(equilibrium_force(magnitude, 1.0 / len(TONGUES), PHI), 6)

    # Self-healing: project where health would be after one heal step
    # Current "health" = safety_score * 100, target = 100
    current_health = safety_score * 100
    healed = round(self_heal(current_health, 100.0, 0.1), 4)
    healing_trajectory = round(healed / 100.0, 6)

    # === COMPOSITE SCORES ===

    # Defense score: high safety + low energy + not deflected = well defended
    # Range [0, 1] where 1 = maximally defended
    defense_raw = safety_score * (1.0 / (1.0 + total_energy * 0.1))
    if was_deflected:
        defense_raw *= 0.8  # Deflection means threat was real
    defense_score = round(max(0.0, min(1.0, defense_raw)), 6)

    # Vulnerability: high threat + high energy + far from equilibrium = exposed
    # Range [0, 1] where 1 = maximally vulnerable
    vuln_raw = (threat_level / THREAT_LEVEL_MAX) * 0.4
    vuln_raw += (total_energy / max(total_energy + 1, 10)) * 0.3
    vuln_raw += min(eq_delta / 5.0, 1.0) * 0.3
    vulnerability_index = round(max(0.0, min(1.0, vuln_raw)), 6)

    return EDEDefenseResult(
        tongue_energy=tongue_energy,
        tongue_energies=tongue_energies,
        total_energy=total_energy,
        threat_level=threat_level,
        threat_sources=threat_sources,
        was_deflected=was_deflected,
        deflected_value=deflected_value,
        sink_absorption=sink_absorption,
        sink_depth=sink_depth,
        equilibrium_delta=eq_delta,
        restoring_force=restoring,
        healing_trajectory=healing_trajectory,
        defense_score=defense_score,
        vulnerability_index=vulnerability_index,
        ede_available=EDE_AVAILABLE,
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"EDE Defense Scoring (EDE available: {EDE_AVAILABLE})")

    profiles = [
        ("Balanced", {"KO": 0.17, "AV": 0.17, "RU": 0.17, "CA": 0.17, "UM": 0.16, "DR": 0.16}),
        ("Security-heavy", {"KO": 0.05, "AV": 0.10, "RU": 0.15, "CA": 0.20, "UM": 0.35, "DR": 0.15}),
        ("Extreme UM", {"KO": 0.02, "AV": 0.02, "RU": 0.02, "CA": 0.02, "UM": 0.90, "DR": 0.02}),
    ]

    for name, profile in profiles:
        result = ede_score(
            profile,
            extinction_count=2,
            max_friction=0.7,
            hyperbolic_distance=1.5,
            oscillation=0.4,
            safety_score=0.3,
        )
        print(f"\n  {name}:")
        print(f"    Tongue energy:    {result.tongue_energy}")
        print(f"    Total energy:     {result.total_energy}")
        print(f"    Threat level:     {result.threat_level}/10 ({result.threat_sources})")
        print(f"    Was deflected:    {result.was_deflected}")
        print(f"    Sink absorption:  {result.sink_absorption} (depth {result.sink_depth})")
        print(f"    Equilibrium Δ:    {result.equilibrium_delta}")
        print(f"    Restoring force:  {result.restoring_force}")
        print(f"    Defense score:    {result.defense_score}")
        print(f"    Vulnerability:    {result.vulnerability_index}")
