"""
SCBE Security Module

Contains security patches, hardening utilities, and shared secret store.
"""

from . import protobuf_patch
from . import secret_store
from . import privacy_token_vault
from .trajectory_risk_gate import (
    AccessLevel,
    IntentClass,
    RiskSignal,
    TrajectoryDecision,
    TrajectoryRiskDecision,
    TrajectoryRiskGate,
    evaluate_sequence,
)
from .phase_lattice_lookup import (
    PhaseLatticeHit,
    PhaseLatticeLookup,
    angular_phase_cells,
    best_attack_hit,
    default_attack_lookup,
    holographic_overlay_cells,
    origami_fold_path,
)

__all__ = [
    "AccessLevel",
    "IntentClass",
    "PhaseLatticeHit",
    "PhaseLatticeLookup",
    "RiskSignal",
    "TrajectoryDecision",
    "TrajectoryRiskDecision",
    "TrajectoryRiskGate",
    "angular_phase_cells",
    "best_attack_hit",
    "default_attack_lookup",
    "holographic_overlay_cells",
    "origami_fold_path",
    "evaluate_sequence",
    "protobuf_patch",
    "privacy_token_vault",
    "secret_store",
]
