"""
EntropicLayer: Escape detection, adaptive-k, and expansion tracking (Python Reference).
========================================================================================

Consolidates entropy-related mechanics into a unified module:
- Escape detection: monitors state volume growth (hyperbolic volume proxy)
- Adaptive k: dynamically adjusts governance k based on coherence
- Expansion volume: approximates hyperbolic volume for 6D manifold

Escape velocity theorem: k > 2*C_quantum / sqrt(N0)
where C_quantum is the quantum coupling constant and N0 is initial node count.

Integration: feeds into Layer 12 (harmonic wall) and Layer 13 (risk decision).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_VOLUME = 1e6
PHI = (1 + math.sqrt(5)) / 2
MIN_K = 1
MAX_K = 50


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class EntropicState:
    """State with position and velocity in Poincare ball."""
    position: List[float]
    velocity: List[float]


@dataclass
class EntropicConfig:
    """Configuration for EntropicLayer."""
    max_volume: float = DEFAULT_MAX_VOLUME
    base_k: int = 5
    c_quantum: float = 1.0
    n0: int = 100


@dataclass
class EscapeAssessment:
    """Result of escape detection."""
    escaped: bool
    volume: float
    volume_ratio: float
    escape_velocity_bound: float
    radial_velocity: float


# ---------------------------------------------------------------------------
# Gamma function helper
# ---------------------------------------------------------------------------


def _gamma(n: float) -> float:
    """Gamma function approximation for integer and half-integer values."""
    if n == 1:
        return 1.0
    if n == 2:
        return 1.0
    if n == 3:
        return 2.0
    if n == 4:
        return 6.0
    if n == 0.5:
        return math.sqrt(math.pi)
    if n == 1.5:
        return math.sqrt(math.pi) / 2
    if n == 2.5:
        return (3 * math.sqrt(math.pi)) / 4
    if n == 3.5:
        return (15 * math.sqrt(math.pi)) / 8
    # Stirling's approximation for other values
    return math.sqrt((2 * math.pi) / n) * math.pow(n / math.e, n)


# ---------------------------------------------------------------------------
# EntropicLayer
# ---------------------------------------------------------------------------


class EntropicLayer:
    """Escape detection, adaptive-k, and expansion tracking."""

    def __init__(self, config: Optional[EntropicConfig] = None):
        self.config = config or EntropicConfig()

    def compute_expansion_volume(self, position: List[float]) -> float:
        """Compute approximate hyperbolic volume for a state position.

        For a point at radius r in the Poincare ball in d dimensions,
        the hyperbolic volume of the ball of that radius is approximately:
          V ~ (pi^(d/2) * r^d / Gamma(d/2+1)) * exp((d-1) * r)

        For 6D (our Sacred Tongues manifold):
          V ~ (pi^3 * r^6 / 6) * exp(5r)
        """
        r_sq = sum(x * x for x in position)
        r = math.sqrt(r_sq)
        d = len(position)

        # Euclidean volume factor: pi^(d/2) * r^d / Gamma(d/2 + 1)
        half_d = d / 2
        euc_factor = math.pow(math.pi, half_d) * math.pow(r, d) / _gamma(half_d + 1)

        # Hyperbolic expansion factor: exp((d-1) * r)
        hyp_factor = math.exp(min((d - 1) * r, 50))  # cap to avoid overflow

        return euc_factor * hyp_factor

    def detect_escape(self, state: EntropicState) -> EscapeAssessment:
        """Detect whether a state has escaped the safe operational region.

        Escape occurs when:
        1. Expansion volume exceeds threshold, OR
        2. Radial velocity exceeds escape velocity bound
        """
        volume = self.compute_expansion_volume(state.position)
        volume_ratio = volume / self.config.max_volume

        # Escape velocity bound: k > 2*C_quantum / sqrt(N0)
        escape_velocity_bound = (2 * self.config.c_quantum) / math.sqrt(self.config.n0)

        # Radial velocity (dot product of velocity with normalized position)
        r_sq = 0.0
        v_dot_r = 0.0
        for i in range(len(state.position)):
            r_sq += state.position[i] * state.position[i]
            v_dot_r += state.velocity[i] * state.position[i]

        r = math.sqrt(r_sq)
        radial_velocity = v_dot_r / r if r > 1e-10 else 0.0

        escaped = volume > self.config.max_volume or radial_velocity > escape_velocity_bound

        return EscapeAssessment(
            escaped=escaped,
            volume=volume,
            volume_ratio=volume_ratio,
            escape_velocity_bound=escape_velocity_bound,
            radial_velocity=radial_velocity,
        )

    def adaptive_k(self, coherence: float) -> int:
        """Compute adaptive k (governance nodes) based on coherence.

        Low coherence -> fewer governance nodes (tighter control).
        High coherence -> more nodes (broader participation).

        Formula: k = floor(baseK * coherence) + 1
        """
        clamped = max(0.0, min(1.0, coherence))
        k = int(math.floor(self.config.base_k * clamped)) + 1
        return max(MIN_K, min(MAX_K, k))

    def escape_velocity_bound_satisfied(self, current_k: int) -> bool:
        """Check if escape velocity theorem is satisfied.

        Theorem: For stable operation, k > 2*C_quantum / sqrt(N0)
        """
        bound = (2 * self.config.c_quantum) / math.sqrt(self.config.n0)
        return current_k > bound

    def update_config(self, **kwargs: Any) -> None:
        """Update configuration at runtime."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def get_config(self) -> EntropicConfig:
        """Get current configuration (copy)."""
        return EntropicConfig(
            max_volume=self.config.max_volume,
            base_k=self.config.base_k,
            c_quantum=self.config.c_quantum,
            n0=self.config.n0,
        )
