"""
SCBE Governance — Canonical Harmonic Scaling + Ternary Decision Surface
=======================================================================

This package is the SINGLE SOURCE OF TRUTH for the three H formulas
and their ternary decomposition. All other modules (layer_13.py,
governance_saas.py, harmonicScaling.ts) must derive from or agree
with the definitions here.

Components:
    - harmonic_scaling: H_score, H_wall, H_exp (three canonical formulas)
    - harmonic_trits: TritVector, ternary_vector, trit_decision
    - grand_unified: 9D manifold governance (ManifoldController)

Governance Principle:
    Actions are not forbidden by policy;
    Invalid actions cannot exist on the manifold
    without violating causality or information balance.

Canonical reference: docs/L12_HARMONIC_SCALING_CANON.md
"""

from .harmonic_scaling import (
    PHI,
    H_score,
    H_wall,
    H_exp,
    harmonic_cost,
    security_bits,
)
from .harmonic_trits import (
    TritVector,
    h_trit,
    ternary_vector,
    trit_decision,
    trit_label,
    TRIT_LABELS,
    ALLOW,
    QUARANTINE,
    ESCALATE,
    DENY,
)

__all__ = [
    "PHI",
    "H_score",
    "H_wall",
    "H_exp",
    "harmonic_cost",
    "security_bits",
    "TritVector",
    "h_trit",
    "ternary_vector",
    "trit_decision",
    "trit_label",
    "TRIT_LABELS",
    "ALLOW",
    "QUARANTINE",
    "ESCALATE",
    "DENY",
]
