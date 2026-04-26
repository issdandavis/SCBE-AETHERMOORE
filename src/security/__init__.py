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

__all__ = [
    "AccessLevel",
    "IntentClass",
    "RiskSignal",
    "TrajectoryDecision",
    "TrajectoryRiskDecision",
    "TrajectoryRiskGate",
    "evaluate_sequence",
    "protobuf_patch",
    "privacy_token_vault",
    "secret_store",
]
