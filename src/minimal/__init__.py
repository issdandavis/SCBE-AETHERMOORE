"""
SCBE-AETHERMOORE Minimal Package
================================

A clean, minimal implementation of the SCBE risk scoring system.

Quick Start:
    from scbe_minimal import validate_action, Decision

    result = validate_action(
        context=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        action="read_data"
    )

    if result.decision == Decision.ALLOW:
        print("Safe to proceed")
    elif result.decision == Decision.QUARANTINE:
        print("Needs review")
    else:
        print("Denied")

Components:
    - SCBEGate: Main risk scoring gate
    - SacredTonguesEncoder: Domain-separated encoding (proven, 100% coverage)
    - RWPEnvelope: Tamper-evident message envelope
    - validate_action(): One-function API
"""

from .scbe_core import (
    SCBEGate,
    SCBEConfig,
    Decision,
    RiskResult,
    SacredTonguesEncoder,
    RWPEnvelope,
    validate_action,
)

__version__ = "1.0.0"
__all__ = [
    'SCBEGate',
    'SCBEConfig',
    'Decision',
    'RiskResult',
    'SacredTonguesEncoder',
    'RWPEnvelope',
    'validate_action',
]
