"""
Transversal Engine — Cross-Layer Moves Through the 14-Layer Stack
==================================================================

A transversal move cuts ACROSS layers rather than going up/down within one.
This is the interoperability matrix that lets you translate patterns between:
  - Chemistry domain (bonding, valence, orbital shapes)
  - Sound domain (frequency, timbre, harmony)
  - Governance domain (risk, drift, decision)
  - Visual domain (color, spiral shape, spectral identity)

Six types of transversal moves:
  1. Cross-Domain Composition — bonding logic governs musical phrase connections
  2. Layer-Jumping — L3 pattern expressed at L9 (same structure, different medium)
  3. Matrix-Mediated Translation — run through the matrix, change medium
  4. Resonance Mapping — find sympathetic layer connections
  5. Phase-State Shifting — solid→liquid→gas→plasma equivalents
  6. Catalyst Moves — elements that accelerate without being consumed

@layer All layers (transversal)
@patent USPTO #63/961,403
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .tracker import (
    PHI, GOLDEN_ANGLE, FIBONACCI_SEQ,
    TONGUE_WEIGHTS, LAYER_TONGUE_RESONANCE,
    LayerSnapshot, DriftSignature, SpiralPoint,
)


# ---------------------------------------------------------------------------
#  Transversal Move Types
# ---------------------------------------------------------------------------

class MoveType(str, Enum):
    """The six transversal move types."""
    CROSS_DOMAIN = "cross_domain"          # Bonding logic across domains
    LAYER_JUMP = "layer_jump"              # Same pattern, different layer
    MATRIX_TRANSLATE = "matrix_translate"   # Change medium, keep relations
    RESONANCE_MAP = "resonance_map"        # Find sympathetic connections
    PHASE_SHIFT = "phase_shift"            # Phase-state transition
    CATALYST = "catalyst"                  # Accelerator without consumption


class PhaseState(str, Enum):
    """Phase states (chemistry → governance → sound)."""
    SOLID = "solid"        # Dense, structured, predictable → ALLOW → sustained tone
    LIQUID = "liquid"      # Fluid, adaptive, flowing → QUARANTINE review → flowing melody
    GAS = "gas"            # Energized, expansive, volatile → ESCALATE → buzzing texture
    PLASMA = "plasma"      # Ionized, extreme, dangerous → DENY → harsh noise


# Layer resonance pairs (overtone relationships)
RESONANCE_PAIRS = [
    (1, 14),   # Context ↔ Audit (Composition axiom)
    (2, 7),    # Realification ↔ Mobius phase
    (3, 8),    # Weighted transform ↔ Multi-well (Locality axiom)
    (4, 9),    # Poincare ↔ Spectral coherence
    (5, 12),   # Hyperbolic distance ↔ Harmonic wall
    (6, 11),   # Breathing ↔ Temporal (Causality axiom)
    (10, 13),  # Spin coherence ↔ Decision
]


# ---------------------------------------------------------------------------
#  Data Types
# ---------------------------------------------------------------------------

@dataclass
class LayerBridge:
    """A connection between two layers for transversal movement."""
    source_layer: int
    target_layer: int
    source_tongue: str
    target_tongue: str
    coupling_strength: float  # 0.0 = no coupling, 1.0 = perfect resonance
    move_type: MoveType
    transformation: str       # Description of what the move does

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_layer": self.source_layer,
            "target_layer": self.target_layer,
            "source_tongue": self.source_tongue,
            "target_tongue": self.target_tongue,
            "coupling_strength": round(self.coupling_strength, 4),
            "move_type": self.move_type.value,
            "transformation": self.transformation,
        }


@dataclass
class TransversalMove:
    """A specific transversal action taken on a governance evaluation."""
    move_type: MoveType
    source_layer: int
    target_layer: int
    source_value: float
    target_value: float
    transformation_factor: float  # How much the value changed
    phase_before: PhaseState
    phase_after: PhaseState
    energy_cost: float            # Harmonic wall cost of this move
    bridges_used: List[LayerBridge]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "move_type": self.move_type.value,
            "source_layer": self.source_layer,
            "target_layer": self.target_layer,
            "source_value": round(self.source_value, 6),
            "target_value": round(self.target_value, 6),
            "transformation_factor": round(self.transformation_factor, 6),
            "phase_before": self.phase_before.value,
            "phase_after": self.phase_after.value,
            "energy_cost": round(self.energy_cost, 6),
            "bridges": [b.to_dict() for b in self.bridges_used],
        }


# ---------------------------------------------------------------------------
#  Transversal Engine
# ---------------------------------------------------------------------------

class TransversalEngine:
    """
    Executes transversal moves across the 14-layer governance stack.

    This is the interoperability matrix — it knows which layers
    resonate with each other, how to translate patterns between
    domains, and what the energy cost of each move is.
    """

    def __init__(self):
        self._bridges = self._build_bridge_map()

    def _build_bridge_map(self) -> List[LayerBridge]:
        """Build the complete bridge map from resonance pairs."""
        bridges = []
        for src, tgt in RESONANCE_PAIRS:
            src_tongue = LAYER_TONGUE_RESONANCE[src]
            tgt_tongue = LAYER_TONGUE_RESONANCE[tgt]

            # Coupling strength: inverse of tongue weight distance
            src_w = TONGUE_WEIGHTS[src_tongue]
            tgt_w = TONGUE_WEIGHTS[tgt_tongue]
            coupling = 1.0 / (1.0 + abs(src_w - tgt_w))

            bridges.append(LayerBridge(
                source_layer=src,
                target_layer=tgt,
                source_tongue=src_tongue,
                target_tongue=tgt_tongue,
                coupling_strength=coupling,
                move_type=MoveType.RESONANCE_MAP,
                transformation=f"L{src}({src_tongue}) ↔ L{tgt}({tgt_tongue})",
            ))

        return bridges

    def classify_phase(self, snapshot: LayerSnapshot) -> PhaseState:
        """Determine the phase state of a governance evaluation."""
        risk = snapshot.risk_score
        if risk < 0.3:
            return PhaseState.SOLID
        elif risk < 0.6:
            return PhaseState.LIQUID
        elif risk < 0.85:
            return PhaseState.GAS
        return PhaseState.PLASMA

    def find_resonances(self, snapshot: LayerSnapshot) -> List[LayerBridge]:
        """Find which layer pairs are resonating (similar values)."""
        resonating = []
        for bridge in self._bridges:
            src_val = snapshot.values.get(bridge.source_layer, 0.0)
            tgt_val = snapshot.values.get(bridge.target_layer, 0.0)
            # Resonance: values are close AND both non-zero
            if src_val > 0.01 and tgt_val > 0.01:
                similarity = 1.0 - abs(src_val - tgt_val) / max(src_val, tgt_val)
                if similarity > 0.5:  # > 50% similar = resonating
                    bridge_copy = LayerBridge(
                        source_layer=bridge.source_layer,
                        target_layer=bridge.target_layer,
                        source_tongue=bridge.source_tongue,
                        target_tongue=bridge.target_tongue,
                        coupling_strength=similarity * bridge.coupling_strength,
                        move_type=MoveType.RESONANCE_MAP,
                        transformation=bridge.transformation,
                    )
                    resonating.append(bridge_copy)

        return resonating

    def layer_jump(
        self,
        snapshot: LayerSnapshot,
        source_layer: int,
        target_layer: int,
    ) -> TransversalMove:
        """
        Jump a pattern from one layer to another.

        The value is scaled by the Fibonacci ratio between the layers
        and the tongue weight ratio. This preserves the STRUCTURE
        while changing the SCALE — like a fractal zoom.
        """
        src_val = snapshot.values.get(source_layer, 0.0)
        src_tongue = LAYER_TONGUE_RESONANCE[source_layer]
        tgt_tongue = LAYER_TONGUE_RESONANCE[target_layer]

        # Scale by Fibonacci ratio
        src_fib = FIBONACCI_SEQ[source_layer - 1]
        tgt_fib = FIBONACCI_SEQ[target_layer - 1]
        fib_scale = tgt_fib / max(src_fib, 1)

        # Scale by tongue weight ratio
        tongue_scale = TONGUE_WEIGHTS[tgt_tongue] / TONGUE_WEIGHTS[src_tongue]

        # Combined transformation
        transform = fib_scale * tongue_scale
        tgt_val = src_val * transform

        # Energy cost: harmonic wall of the distance between layers
        layer_dist = abs(target_layer - source_layer) / 14.0
        energy_cost = PHI ** (layer_dist ** 2)  # Same exponential scaling

        phase_before = self.classify_phase(snapshot)

        # After jump, risk may change
        modified = LayerSnapshot(
            values={**snapshot.values, target_layer: min(tgt_val, 1.0)},
            tongue=snapshot.tongue,
            risk_score=snapshot.risk_score,
            decision=snapshot.decision,
            harmonic_wall=snapshot.harmonic_wall,
        )
        phase_after = self.classify_phase(modified)

        # Find relevant bridges
        bridges = [b for b in self._bridges
                   if b.source_layer == source_layer or b.target_layer == target_layer]

        return TransversalMove(
            move_type=MoveType.LAYER_JUMP,
            source_layer=source_layer,
            target_layer=target_layer,
            source_value=src_val,
            target_value=min(tgt_val, 1.0),
            transformation_factor=transform,
            phase_before=phase_before,
            phase_after=phase_after,
            energy_cost=energy_cost,
            bridges_used=bridges,
        )

    def phase_shift(self, snapshot: LayerSnapshot, target_phase: PhaseState) -> TransversalMove:
        """
        Shift the entire evaluation to a different phase state.

        This is the equivalent of heating/cooling a molecule.
        Solid → Liquid → Gas → Plasma maps to:
        ALLOW → QUARANTINE → ESCALATE → DENY
        """
        current_phase = self.classify_phase(snapshot)
        phase_order = [PhaseState.SOLID, PhaseState.LIQUID, PhaseState.GAS, PhaseState.PLASMA]
        current_idx = phase_order.index(current_phase)
        target_idx = phase_order.index(target_phase)
        shift_distance = abs(target_idx - current_idx)

        # Energy cost scales exponentially with phase distance
        energy_cost = PHI ** (shift_distance ** 2)

        # The transformation factor
        if target_idx > current_idx:
            transform = PHI ** shift_distance  # Heating: multiply
        else:
            transform = PHI ** (-shift_distance)  # Cooling: divide

        return TransversalMove(
            move_type=MoveType.PHASE_SHIFT,
            source_layer=0,  # All layers
            target_layer=0,
            source_value=snapshot.risk_score,
            target_value=min(snapshot.risk_score * transform, 1.0),
            transformation_factor=transform,
            phase_before=current_phase,
            phase_after=target_phase,
            energy_cost=energy_cost,
            bridges_used=[],
        )

    def find_catalyst(self, snapshot: LayerSnapshot) -> Optional[TransversalMove]:
        """
        Find a catalyst layer — one that can accelerate transformation
        in other layers without being consumed (its value stays stable).

        A catalyst layer has:
        1. High phi-coherence with its neighbors
        2. Low drift
        3. Moderate value (not too high, not too low)
        """
        best_catalyst = None
        best_score = 0.0

        for layer in range(1, 15):
            val = snapshot.values.get(layer, 0.0)

            # Catalyst criteria
            if val < 0.2 or val > 0.8:
                continue  # Too extreme

            # Check neighbor coherence
            neighbors = []
            if layer > 1:
                neighbors.append(snapshot.values.get(layer - 1, 0.0))
            if layer < 14:
                neighbors.append(snapshot.values.get(layer + 1, 0.0))

            if not neighbors:
                continue

            # Coherence: how well this layer mediates between neighbors
            neighbor_avg = sum(neighbors) / len(neighbors)
            coherence = 1.0 - abs(val - neighbor_avg) / max(val, neighbor_avg, 0.001)

            # Stability: low variance from the "golden zone" (PHI - 1 ≈ 0.618)
            golden_zone = PHI - 1
            stability = 1.0 - abs(val - golden_zone)

            score = coherence * 0.6 + stability * 0.4

            if score > best_score:
                best_score = score
                tongue = LAYER_TONGUE_RESONANCE[layer]
                best_catalyst = TransversalMove(
                    move_type=MoveType.CATALYST,
                    source_layer=layer,
                    target_layer=0,  # Affects all
                    source_value=val,
                    target_value=val,  # Unchanged — that's what makes it a catalyst
                    transformation_factor=best_score,
                    phase_before=self.classify_phase(snapshot),
                    phase_after=self.classify_phase(snapshot),
                    energy_cost=0.0,  # Catalysts are free
                    bridges_used=[b for b in self._bridges if b.source_layer == layer],
                )

        return best_catalyst

    def full_analysis(self, snapshot: LayerSnapshot) -> Dict[str, Any]:
        """Complete transversal analysis of a governance evaluation."""
        phase = self.classify_phase(snapshot)
        resonances = self.find_resonances(snapshot)
        catalyst = self.find_catalyst(snapshot)

        # Find the strongest transversal move available
        strongest_jump = None
        max_transform = 0.0
        for src, tgt in RESONANCE_PAIRS:
            jump = self.layer_jump(snapshot, src, tgt)
            if jump.transformation_factor > max_transform:
                max_transform = jump.transformation_factor
                strongest_jump = jump

        return {
            "phase_state": phase.value,
            "resonance_count": len(resonances),
            "resonances": [r.to_dict() for r in resonances],
            "catalyst": catalyst.to_dict() if catalyst else None,
            "strongest_jump": strongest_jump.to_dict() if strongest_jump else None,
            "available_bridges": len(self._bridges),
            "phase_transitions": {
                "to_solid": self.phase_shift(snapshot, PhaseState.SOLID).energy_cost
                if phase != PhaseState.SOLID else 0.0,
                "to_liquid": self.phase_shift(snapshot, PhaseState.LIQUID).energy_cost
                if phase != PhaseState.LIQUID else 0.0,
                "to_gas": self.phase_shift(snapshot, PhaseState.GAS).energy_cost
                if phase != PhaseState.GAS else 0.0,
                "to_plasma": self.phase_shift(snapshot, PhaseState.PLASMA).energy_cost
                if phase != PhaseState.PLASMA else 0.0,
            },
        }

    @property
    def bridges(self) -> List[LayerBridge]:
        return list(self._bridges)
