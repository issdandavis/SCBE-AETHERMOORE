"""
Seal Entity — Companion System (Python reference).

Mirrors src/game/companion.ts.
Companions are 21D canonical state vectors with behavioral evolution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .types import (
    BondType,
    CanonicalState,
    DisciplineTrait,
    EggType,
    EmotionalState,
    EvolutionStage,
    EVOLUTION_THRESHOLDS,
    FormationRole,
    OVER_EVOLUTION_THRESHOLD,
    TongueCode,
    TongueVector,
    TONGUE_CODES,
    default_canonical_state,
    tongue_norm,
)


@dataclass
class DerivedCombatStats:
    speed: float
    insight: float
    perception: float
    risk_tolerance: float
    entropy_affinity: float
    resilience: float
    proof_power: float
    authority: float


def derive_combat_stats(state: CanonicalState) -> DerivedCombatStats:
    """Derive combat stats from 21D canonical state. Never set directly."""
    clamp = lambda x: max(0.0, min(100.0, x * 100))
    return DerivedCombatStats(
        speed=clamp(state.flux),
        insight=clamp(state.coherence_s),
        perception=clamp(state.coherence_tri),
        risk_tolerance=clamp(state.risk),
        entropy_affinity=clamp(state.entropy_rate),
        resilience=clamp(state.stabilization),
        proof_power=clamp(state.radius),
        authority=clamp(state.harmonic_energy),
    )


@dataclass
class Companion:
    """A Seal Entity — companion built on 21D canonical state."""

    id: str
    species_id: str
    name: str
    state: CanonicalState
    seal_integrity: float = 100.0
    max_seal_integrity: float = 100.0
    drift_level: float = 0.0
    bond_level: int = 1
    bond_xp: int = 0
    formation_role: FormationRole = "storm"
    discipline_trait: DisciplineTrait = "collaborative"
    emotional_state: EmotionalState = "content"
    evolution_stage: EvolutionStage = "spark"
    evolution_line: List[str] = field(default_factory=list)
    egg_origin: EggType = "mono_KO"
    bond_type: BondType = "amplifier"
    scar_count: int = 0
    hollow_exposure: int = 0

    @property
    def derived_stats(self) -> DerivedCombatStats:
        return derive_combat_stats(self.state)


def create_companion(
    id: str,
    species_id: str,
    name: str,
    egg_type: EggType,
    bond_type: BondType,
    initial_tongue: TongueVector,
) -> Companion:
    """Create a new companion from a hatched egg."""
    state = CanonicalState(tongue_position=initial_tongue, radius=0.1)
    return Companion(
        id=id,
        species_id=species_id,
        name=name,
        state=state,
        evolution_line=[species_id],
        egg_origin=egg_type,
        bond_type=bond_type,
    )


def apply_tongue_experience(comp: Companion, tongue: TongueCode, amount: float) -> None:
    """Shift tongue position toward the given tongue. A2: Unitarity preserved."""
    idx = TONGUE_CODES.index(tongue)
    pos = list(comp.state.tongue_position)
    old_norm = tongue_norm(tuple(pos))  # type: ignore[arg-type]
    pos[idx] = min(1.0, pos[idx] + amount * 0.1)
    new_norm = tongue_norm(tuple(pos))  # type: ignore[arg-type]

    if new_norm > 0 and old_norm > 0:
        target_norm = min(1.0, old_norm + amount * 0.02)
        scale = target_norm / new_norm
        pos = [x * scale for x in pos]

    comp.state = CanonicalState(
        tongue_position=tuple(pos),  # type: ignore[arg-type]
        phase_angles=comp.state.phase_angles,
        flux=comp.state.flux,
        coherence_s=comp.state.coherence_s,
        coherence_bi=comp.state.coherence_bi,
        coherence_tri=comp.state.coherence_tri,
        risk=comp.state.risk,
        entropy_rate=comp.state.entropy_rate,
        stabilization=comp.state.stabilization,
        radius=comp.state.radius,
        harmonic_energy=comp.state.harmonic_energy,
    )


def apply_combat_result(comp: Companion, won: bool, difficulty: int) -> None:
    """Apply combat result to companion state."""
    diff_norm = difficulty / 10.0

    if won:
        radius_gain = 0.01 + diff_norm * 0.02
        coh_gain = 0.005 + diff_norm * 0.01
        comp.state = CanonicalState(
            tongue_position=comp.state.tongue_position,
            phase_angles=comp.state.phase_angles,
            flux=comp.state.flux,
            coherence_s=min(1.0, comp.state.coherence_s + coh_gain),
            coherence_bi=comp.state.coherence_bi,
            coherence_tri=comp.state.coherence_tri,
            risk=comp.state.risk,
            entropy_rate=comp.state.entropy_rate,
            stabilization=min(1.0, comp.state.stabilization + coh_gain * 0.5),
            radius=min(1.0, comp.state.radius + radius_gain),
            harmonic_energy=min(1.0, comp.state.harmonic_energy + 0.005),
        )
        comp.bond_xp += 5 + difficulty
    else:
        comp.scar_count += 1
        entropy_gain = diff_norm * 0.03
        comp.state = CanonicalState(
            tongue_position=comp.state.tongue_position,
            phase_angles=comp.state.phase_angles,
            flux=comp.state.flux,
            coherence_s=comp.state.coherence_s,
            coherence_bi=comp.state.coherence_bi,
            coherence_tri=comp.state.coherence_tri,
            risk=min(1.0, comp.state.risk + 0.01),
            entropy_rate=min(1.0, comp.state.entropy_rate + entropy_gain),
            stabilization=comp.state.stabilization,
            radius=comp.state.radius,
            harmonic_energy=comp.state.harmonic_energy,
        )
        comp.seal_integrity = max(0, comp.seal_integrity - (10 + difficulty * 3))
        comp.bond_xp += 2

    # Bond level up
    xp_for_next = comp.bond_level * 10
    if comp.bond_xp >= xp_for_next and comp.bond_level < 10:
        comp.bond_level += 1
        comp.bond_xp -= xp_for_next


def current_evolution_stage(radius: float) -> EvolutionStage:
    """Determine evolution stage from radius."""
    if radius >= EVOLUTION_THRESHOLDS["transcendent"]:
        return "transcendent"
    if radius >= EVOLUTION_THRESHOLDS["apex"]:
        return "apex"
    if radius >= EVOLUTION_THRESHOLDS["prime"]:
        return "prime"
    if radius >= EVOLUTION_THRESHOLDS["form"]:
        return "form"
    return "spark"


def is_over_evolved(comp: Companion) -> bool:
    """Check if companion is unstable (radius > 0.95)."""
    return comp.state.radius > OVER_EVOLUTION_THRESHOLD
