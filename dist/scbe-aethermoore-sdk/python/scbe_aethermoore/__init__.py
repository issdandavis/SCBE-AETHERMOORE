"""
SCBE-AETHERMOORE Python SDK

Spectral Context-Bound Encryption + Hyperbolic Governance for AI-to-AI Communication.

Usage:
    from scbe_aethermoore import Agent6D, SecurityGate, SCBE

    # Create an agent in 6D space
    alice = Agent6D("Alice", [1, 2, 3, 0.5, 1.5, 2.5])

    # Evaluate risk
    scbe = SCBE()
    risk = scbe.evaluate_risk({"action": "transfer", "amount": 10000})

    # Security gate check
    gate = SecurityGate()
    result = await gate.check(alice, "delete", {"source": "external"})
"""

from .core import (
    Agent6D,
    SecurityGate,
    SCBE,
    Roundtable,
    harmonic_complexity,
    get_pricing_tier,
    hyperbolic_distance,
    project_to_ball,
)

from .envelope import (
    sign_roundtable,
    verify_roundtable,
    RWPEnvelope,
)

__version__ = "3.0.0"
__all__ = [
    "Agent6D",
    "SecurityGate",
    "SCBE",
    "Roundtable",
    "harmonic_complexity",
    "get_pricing_tier",
    "hyperbolic_distance",
    "project_to_ball",
    "sign_roundtable",
    "verify_roundtable",
    "RWPEnvelope",
]
