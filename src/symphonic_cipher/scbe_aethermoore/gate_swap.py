"""
Gate Swap: 2-Gate (Negabinary) -> 3-Gate (Balanced Ternary) Governance
======================================================================

Maps a 6-element gate vector from federated nodes through the
negabinary -> balanced ternary conversion pipeline, then applies
tri-manifold governance decisions.

Pipeline:
  1. Aggregate 6-element gate vector into 3 dimensional pairs
  2. Convert each aggregated value: int -> negabinary -> balanced ternary
  3. Extract Most Significant Digit (MSD) from balanced ternary
  4. Apply governance decision based on trit sum and t3 (Commit+Sig)

Governance Decision Logic:
  DENY:       t3 == -1 OR sum(t1, t2, t3) < 0
  QUARANTINE: sum(t1, t2, t3) == 0 AND t3 != -1
  ALLOW:      sum(t1, t2, t3) > 0 AND t3 != -1

The t3 dimension (Commit + Signature) acts as a hard-deny gate:
if the integrity dimension shows destructive interference (-1),
the node is denied regardless of other dimensions.

@module gate_swap
@layer Layer 9 (Spectral), Layer 12 (Entropy), Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .negabinary import NegaBinary, negabinary_to_balanced_ternary

# ---------------------------------------------------------------------------
# Gate Tri-Manifold State
# ---------------------------------------------------------------------------


@dataclass
class GateTriState:
    """Tri-manifold governance state derived from a 6-element gate vector.

    Three dimensions mapped from paired gate values:
      t1: First pair (e.g., Auth + Enc)
      t2: Second pair (e.g., Policy + Audit)
      t3: Third pair (Commit + Sig) — integrity dimension, hard-deny gate

    Each trit is the Most Significant Digit of the balanced ternary
    representation obtained via the negabinary conversion pipeline.
    """

    t1: int = 0  # -1, 0, or +1
    t2: int = 0
    t3: int = 0

    @property
    def trit_sum(self) -> int:
        """Sum of all three trits."""
        return self.t1 + self.t2 + self.t3

    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.t1, self.t2, self.t3)


# ---------------------------------------------------------------------------
# Federated Node
# ---------------------------------------------------------------------------


@dataclass
class FederatedNode:
    """A federated node with a 6-element gate vector for governance evaluation.

    The gate vector encodes security/integrity signals:
      [g0, g1, g2, g3, g4, g5]

    Aggregated into 3 dimensional pairs:
      dim1 = g0 + g1   (e.g., Auth + Enc)
      dim2 = g2 + g3   (e.g., Policy + Audit)
      dim3 = g4 + g5   (Commit + Sig — integrity)
    """

    name: str
    gate_vector: List[int] = field(default_factory=lambda: [0] * 6)


# ---------------------------------------------------------------------------
# MSD Extraction
# ---------------------------------------------------------------------------


def _extract_msd(n: int) -> int:
    """Extract the Most Significant Digit from the balanced ternary
    representation of an integer, obtained via the negabinary pipeline.

    Pipeline: int -> NegaBinary -> BalancedTernary -> MSD

    Returns:
        -1, 0, or +1 (the MSD trit value).
    """
    nb = NegaBinary.from_int(n)
    bt = negabinary_to_balanced_ternary(nb)
    # MSD is the first element of trits_msb (most significant first)
    return bt.trits_msb[0].value


# ---------------------------------------------------------------------------
# Gate Mapping
# ---------------------------------------------------------------------------


def map_gates_to_trimanifold(gate_vector: List[int]) -> GateTriState:
    """Map a 6-element gate vector to a GateTriState via negabinary pipeline.

    Steps:
      1. Aggregate into 3 pairs: (g0+g1), (g2+g3), (g4+g5)
      2. For each aggregate: int -> negabinary -> balanced ternary -> MSD
      3. Pack MSDs into GateTriState(t1, t2, t3)

    Args:
        gate_vector: 6-element list of non-negative integers.

    Returns:
        GateTriState with t1, t2, t3 trit values.

    Raises:
        ValueError: If gate_vector doesn't have exactly 6 elements.
    """
    if len(gate_vector) != 6:
        raise ValueError(f"Gate vector must have 6 elements, got {len(gate_vector)}")

    dim1 = gate_vector[0] + gate_vector[1]
    dim2 = gate_vector[2] + gate_vector[3]
    dim3 = gate_vector[4] + gate_vector[5]

    t1 = _extract_msd(dim1)
    t2 = _extract_msd(dim2)
    t3 = _extract_msd(dim3)

    return GateTriState(t1=t1, t2=t2, t3=t3)


# ---------------------------------------------------------------------------
# Governance Decision
# ---------------------------------------------------------------------------


def apply_tri_manifold_governance(state: GateTriState) -> str:
    """Apply tri-manifold governance decision based on trit state.

    Decision logic:
      DENY:       t3 == -1 (integrity failure) OR sum < 0
      QUARANTINE: sum == 0 AND t3 != -1
      ALLOW:      sum > 0 AND t3 != -1

    The t3 dimension (Commit + Signature) is a hard-deny gate:
    if it shows destructive interference (-1), the node is denied
    regardless of what other dimensions indicate.

    Args:
        state: GateTriState with t1, t2, t3 values.

    Returns:
        "ALLOW", "QUARANTINE", or "DENY".
    """
    # Hard-deny: integrity dimension shows destructive interference
    if state.t3 == -1:
        return "DENY"

    trit_sum = state.trit_sum

    if trit_sum < 0:
        return "DENY"
    elif trit_sum == 0:
        return "QUARANTINE"
    else:
        return "ALLOW"


# ---------------------------------------------------------------------------
# Convenience: evaluate a FederatedNode end-to-end
# ---------------------------------------------------------------------------


def evaluate_node(node: FederatedNode) -> Tuple[GateTriState, str]:
    """Evaluate a FederatedNode through the full gate-swap governance pipeline.

    Args:
        node: FederatedNode with name and gate_vector.

    Returns:
        Tuple of (GateTriState, decision_string).
    """
    state = map_gates_to_trimanifold(node.gate_vector)
    decision = apply_tri_manifold_governance(state)
    return state, decision
