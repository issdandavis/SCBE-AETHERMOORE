"""Shared types for the TernaryHybridEncoder pipeline.

@layer Layer 9, Layer 12, Layer 13
@component HybridEncoder.Types
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

Decision = Literal["ALLOW", "QUARANTINE", "DENY"]
TONGUE_NAMES: List[str] = ["KO", "AV", "RU", "CA", "UM", "DR"]


@dataclass(frozen=True)
class HybridRepresentation:
    """Simultaneous ternary + binary representation of a value.

    Balanced ternary trits {-1, 0, +1} and negabinary bits {0, 1}
    encode the same integer from two perspectives, exposing
    polarity structure that neither representation reveals alone.
    """
    ternary_trits: Tuple[int, ...]
    binary_bits: Tuple[int, ...]
    ternary_int: int
    binary_int: int
    tongue_polarity: str  # KO/AV/RU from negabinary polarity analysis


@dataclass(frozen=True)
class NegativeSpaceEmbedding:
    """What this signal IS NOT -- the complement trit vector.

    Knowing what something IS NOT is as informative as knowing
    what it IS.  In balanced ternary, the complement is trivial:
    flip every trit via Kleene NOT (-1 <-> +1, 0 stays 0).
    """
    complement_trits: Tuple[int, ...]
    excluded_tongues: List[str]  # tongues with complement == -1 (denied)
    anti_energy: float           # energy of the complement configuration


@dataclass(frozen=True)
class MolecularBond:
    """A bond between two code elements in molecular mapping.

    Code constructs map to molecular structures:
      Functions = molecules, Variables = atoms,
      Imports = ionic bonds, Calls = covalent bonds,
      Comments = hydrogen bonds.
    """
    element_a: str
    element_b: str
    bond_type: str   # "covalent" | "ionic" | "hydrogen"
    valence: int
    tongue_affinity: str  # which Sacred Tongue this bond resonates with


@dataclass
class EncoderInput:
    """Input to the TernaryHybridEncoder pipeline.

    Provide exactly one of: state_21d, raw_signal, or code_text.
    The StateAdapter routes to the appropriate conversion.
    """
    state_21d: Optional[List[float]] = None
    raw_signal: Optional[float] = None
    code_text: Optional[str] = None
    tongue_hint: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncoderResult:
    """Complete output of the encoding pipeline.

    Contains results from all 7 modules plus the negative-space,
    molecular, and Hamiltonian traversal extensions.
    """
    decision: Decision
    hybrid: HybridRepresentation
    negative_space: NegativeSpaceEmbedding
    gate_state: Any           # GateTriState from gate_swap
    lattice_valid: bool
    lattice_distance: float
    chemistry_blocked: bool
    chemistry_energy: float
    ternary_packed: Any       # BalancedTernary governance word
    governance_summary: Dict[str, Any]
    threat_score: float
    defect_score: float
    state_21d_used: List[float]
    tongue_trits: List[int]
    traversal_valid: bool     # Hamiltonian path constraint
    molecular_bonds: List[MolecularBond]
    audit_trail: List[Dict[str, Any]]
