"""
AETHERMOORE Mathematical Foundations
====================================
Core mathematical primitives for AI swarm governance.

Modules:
- constants: Cox constant, Mars frequency, Q16.16 scale
- hyperbolic: Hyperbolic geometry for trust routing
- lorentz: Relativistic path dilation for threat response
- soliton: Self-healing message propagation
- fixed_point: Deterministic cross-platform arithmetic
- swarm: Multi-agent consensus timing
"""

from .constants import (
    COX_CONSTANT,
    MARS_FREQUENCY_HZ,
    MARS_TICK_MS,
    Q16_16_SCALE,
)
from .hyperbolic import (
    hyperbolic_distance,
    poincare_to_klein,
    trust_cost,
)
from .lorentz import (
    lorentz_factor,
    dilated_path_cost,
    threat_velocity,
)
from .soliton import (
    nlse_soliton,
    soliton_integrity_check,
)
from .fixed_point import Q16_16
from .swarm import (
    swarm_consensus_time,
    byzantine_rounds,
    tick_synchronization,
)
from .horadam import (
    HoradamTranscript,
    HoradamSequence,
    DriftTelemetry,
    DriftVector,
    DriftLevel,
    compute_triadic_invariant,
    verify_triadic_bounds,
    TONGUES,
    PHI,
)

__all__ = [
    # Constants
    "COX_CONSTANT",
    "MARS_FREQUENCY_HZ",
    "MARS_TICK_MS",
    "Q16_16_SCALE",
    # Hyperbolic
    "hyperbolic_distance",
    "poincare_to_klein",
    "trust_cost",
    # Lorentz
    "lorentz_factor",
    "dilated_path_cost",
    "threat_velocity",
    # Soliton
    "nlse_soliton",
    "soliton_integrity_check",
    # Fixed Point
    "Q16_16",
    # Swarm
    "swarm_consensus_time",
    "byzantine_rounds",
    "tick_synchronization",
    # Horadam
    "HoradamTranscript",
    "HoradamSequence",
    "DriftTelemetry",
    "DriftVector",
    "DriftLevel",
    "compute_triadic_invariant",
    "verify_triadic_bounds",
    "TONGUES",
    "PHI",
]
