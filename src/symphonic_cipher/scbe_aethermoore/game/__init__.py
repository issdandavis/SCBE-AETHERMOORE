"""
Spiral Forge RPG — Python Reference Implementation
====================================================

Mirrors the TypeScript canonical implementation in src/game/.
All game types grounded in SCBE 21D canonical state and Sacred Tongues.

Modules:
    types       — Core types, tongue definitions, canonical state
    companion   — Seal Entity companion system
    combat      — Cl(4,0) bivector type advantage + math combat
    sacred_eggs — Behavioral egg hatching in B^6
    evolution   — Branching evolution system
    symbiotic_network — Graph Laplacian topology
    skill_tree  — Player 6-path skill tree
    regions     — Tongue regions + 100-floor tower
    codex_terminal — SCBE-gated internet access
"""

from .types import (
    TONGUE_CODES,
    TONGUE_WEIGHTS,
    TONGUE_NAMES,
    HODGE_DUAL_PAIRS,
    PHI,
    TongueVector,
    CanonicalState,
    default_canonical_state,
    state_to_array,
    array_to_state,
)
from .companion import Companion, create_companion, derive_combat_stats
from .combat import compute_type_advantage, calculate_damage
from .sacred_eggs import check_hatchable_eggs, egg_starting_tongue
from .symbiotic_network import SymbioticNetwork
from .regions import REGIONS, get_tower_floor, get_rank

__all__ = [
    "TONGUE_CODES",
    "TONGUE_WEIGHTS",
    "TONGUE_NAMES",
    "HODGE_DUAL_PAIRS",
    "PHI",
    "TongueVector",
    "CanonicalState",
    "default_canonical_state",
    "state_to_array",
    "array_to_state",
    "Companion",
    "create_companion",
    "derive_combat_stats",
    "compute_type_advantage",
    "calculate_damage",
    "check_hatchable_eggs",
    "egg_starting_tongue",
    "SymbioticNetwork",
    "REGIONS",
    "get_tower_floor",
    "get_rank",
]
