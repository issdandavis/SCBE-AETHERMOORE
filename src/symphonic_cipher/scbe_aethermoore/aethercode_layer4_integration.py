#!/usr/bin/env python3
"""
Aethercode → Layer 4 Poincaré Integration
==========================================

Wires Aethercode's 6D position to Layer 4 Poincaré embedding:
- Position6D (6 Tongue axes) → normalized input
- Layer 4 Poincaré embedding → hyperbolic ball representation
- Enables governance based on agent position in Spiralverse

Integration Points:
- Aethercode's Position6D → Layer 4 input
- Layer 4 output → Layer 5 hyperbolic distance
- Enables spatial governance decisions

Date: February 2026
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Spiralverse imports
try:
    from ...spiralverse.vector_6d import Position6D, Axis, AXIS_INFO
    from ...spiralverse.aethercode import AetherContext, TongueID, TONGUE_DOMAINS
    SPIRALVERSE_AVAILABLE = True
except ImportError:
    SPIRALVERSE_AVAILABLE = False

    # Stub for Position6D when not available
    @dataclass
    class Position6D:
        axiom: float = 0.0
        flow: float = 0.0
        glyph: float = 0.0
        oracle: float = 0.0
        charm: float = 0.0
        ledger: int = 0

        @property
        def full_vector(self):
            return np.array([
                self.axiom, self.flow, self.glyph,
                self.oracle, self.charm, self.ledger
            ])


# =============================================================================
# CONSTANTS
# =============================================================================

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618

# Normalization ranges for each axis (based on AXIS_INFO)
AXIS_NORMALIZATION = {
    0: {'name': 'AXIOM', 'scale': 1000.0},   # Spatial: normalize to ±1000m
    1: {'name': 'FLOW', 'scale': 1000.0},    # Spatial
    2: {'name': 'GLYPH', 'scale': 1000.0},   # Spatial
    3: {'name': 'ORACLE', 'scale': 100.0},   # Velocity: 0-100 m/s
    4: {'name': 'CHARM', 'scale': 1.0},      # Already [-1, 1]
    5: {'name': 'LEDGER', 'scale': 255.0},   # Security: 0-255
}

# Tongue weights for Layer 3 weighting (golden ratio powers)
TONGUE_WEIGHTS = {
    'AXIOM': PHI ** 0,   # 1.0
    'FLOW': PHI ** 1,    # 1.618
    'GLYPH': PHI ** 2,   # 2.618
    'ORACLE': PHI ** 3,  # 4.236
    'CHARM': PHI ** 4,   # 6.854
    'LEDGER': PHI ** 5,  # 11.09
}


# =============================================================================
# POINCARÉ EMBEDDING (Layer 4)
# =============================================================================

def poincare_embedding(
    x: np.ndarray,
    alpha: float = 1.0,
    eps_ball: float = 0.01
) -> np.ndarray:
    """
    Layer 4: Poincaré Ball Embedding with Clamping.

    Input: x ∈ ℝ^n (normalized weighted vector)
    Output: u ∈ 𝔹^n (Poincaré ball)

    A4: Ψ_α(x) = tanh(α||x||) · x/||x|| with clamping to 𝔹^n_{1-ε}

    Args:
        x: Input vector (normalized)
        alpha: Scaling parameter (controls embedding curvature)
        eps_ball: Ball boundary epsilon (prevents singularities)

    Returns:
        Point in Poincaré ball
    """
    norm = np.linalg.norm(x)

    if norm < 1e-12:
        return np.zeros_like(x)

    # Poincaré embedding: u = tanh(α||x||) · x/||x||
    scaled_norm = np.tanh(alpha * norm)
    u = (scaled_norm / norm) * x

    # A4: Clamping Π_ε: ensure ||u|| ≤ 1-ε
    u_norm = np.linalg.norm(u)
    max_norm = 1.0 - eps_ball

    if u_norm > max_norm:
        u = (max_norm / u_norm) * u

    return u


def hyperbolic_distance(
    u: np.ndarray,
    v: np.ndarray,
    eps: float = 1e-5
) -> float:
    """
    Layer 5: Poincaré Ball Metric.

    A5: d_ℍ(u,v) = arcosh(1 + 2||u-v||²/[(1-||u||²)(1-||v||²)])

    Args:
        u: First point in Poincaré ball
        v: Second point in Poincaré ball
        eps: Numerical stability epsilon

    Returns:
        Hyperbolic distance
    """
    diff_norm_sq = np.sum((u - v) ** 2)
    u_norm_sq = np.sum(u ** 2)
    v_norm_sq = np.sum(v ** 2)

    # Clamp to ensure we stay inside the ball
    u_norm_sq = min(u_norm_sq, 1.0 - eps)
    v_norm_sq = min(v_norm_sq, 1.0 - eps)

    # Hyperbolic distance formula
    denominator = (1 - u_norm_sq) * (1 - v_norm_sq)
    denominator = max(denominator, eps)

    cosh_arg = 1.0 + 2.0 * diff_norm_sq / denominator
    cosh_arg = max(cosh_arg, 1.0)  # arcosh domain: [1, ∞)

    return float(np.arccosh(cosh_arg))


# =============================================================================
# POSITION6D → LAYER 4 INTEGRATION
# =============================================================================

@dataclass
class PoincarePosition:
    """
    Result of embedding a Position6D into the Poincaré ball.
    """
    # Original position
    original: np.ndarray
    normalized: np.ndarray
    weighted: np.ndarray

    # Embedded position
    embedded: np.ndarray

    # Metadata
    norm_in_ball: float  # ||embedded|| < 1
    axis_contributions: Dict[str, float]  # Per-axis contribution

    def distance_to(self, other: 'PoincarePosition') -> float:
        """Hyperbolic distance to another embedded position."""
        return hyperbolic_distance(self.embedded, other.embedded)

    @property
    def is_valid(self) -> bool:
        """Check if position is within Poincaré ball."""
        return self.norm_in_ball < 1.0


class AethercodeLayer4Bridge:
    """
    Bridge between Aethercode's Position6D and Layer 4 Poincaré embedding.

    This enables:
    - Spatial governance based on agent position
    - Hyperbolic distance metrics for risk assessment
    - Position-based intent analysis

    Usage:
        bridge = AethercodeLayer4Bridge()
        poincare_pos = bridge.embed_position(position_6d)
        distance = bridge.compute_distance(pos1, pos2)
    """

    def __init__(
        self,
        alpha: float = 1.0,
        eps_ball: float = 0.01,
        use_golden_weights: bool = True,
    ):
        """
        Initialize the bridge.

        Args:
            alpha: Poincaré embedding curvature parameter
            eps_ball: Ball boundary epsilon
            use_golden_weights: Use golden ratio weights (Layer 3)
        """
        self.alpha = alpha
        self.eps_ball = eps_ball
        self.use_golden_weights = use_golden_weights

        # Precompute normalized weights
        if use_golden_weights:
            weights = list(TONGUE_WEIGHTS.values())
            total = sum(weights)
            self.weights = np.array([w / total for w in weights])
        else:
            self.weights = np.ones(6) / 6

    def normalize_position(self, pos: Position6D) -> np.ndarray:
        """
        Normalize Position6D to [-1, 1] range for each axis.

        Args:
            pos: 6D position

        Returns:
            Normalized 6D vector
        """
        vec = pos.full_vector.astype(float)
        normalized = np.zeros(6)

        for i, val in enumerate(vec):
            scale = AXIS_NORMALIZATION[i]['scale']
            # Normalize to [-1, 1] using tanh for smooth clamping
            normalized[i] = np.tanh(val / scale)

        return normalized

    def apply_golden_weights(self, x: np.ndarray) -> np.ndarray:
        """
        Apply Layer 3 golden ratio weighting.

        Args:
            x: Normalized 6D vector

        Returns:
            Weighted vector
        """
        return x * np.sqrt(self.weights)

    def embed_position(self, pos: Position6D) -> PoincarePosition:
        """
        Embed a Position6D into the Poincaré ball.

        Pipeline: Position6D → Normalize → Weight → Poincaré Embed

        Args:
            pos: 6D position from Aethercode

        Returns:
            PoincarePosition with embedded coordinates
        """
        original = pos.full_vector.astype(float)

        # Step 1: Normalize to [-1, 1]
        normalized = self.normalize_position(pos)

        # Step 2: Apply golden ratio weights (Layer 3)
        weighted = self.apply_golden_weights(normalized)

        # Step 3: Poincaré embedding (Layer 4)
        embedded = poincare_embedding(weighted, self.alpha, self.eps_ball)

        # Compute axis contributions
        contributions = {}
        axes = ['AXIOM', 'FLOW', 'GLYPH', 'ORACLE', 'CHARM', 'LEDGER']
        total = np.sum(embedded ** 2)
        for i, axis in enumerate(axes):
            contributions[axis] = float(embedded[i] ** 2 / total) if total > 0 else 0.0

        return PoincarePosition(
            original=original,
            normalized=normalized,
            weighted=weighted,
            embedded=embedded,
            norm_in_ball=float(np.linalg.norm(embedded)),
            axis_contributions=contributions,
        )

    def compute_distance(
        self,
        pos1: Position6D,
        pos2: Position6D
    ) -> float:
        """
        Compute hyperbolic distance between two 6D positions.

        Args:
            pos1: First position
            pos2: Second position

        Returns:
            Hyperbolic distance (Layer 5 metric)
        """
        emb1 = self.embed_position(pos1)
        emb2 = self.embed_position(pos2)
        return emb1.distance_to(emb2)

    def compute_distance_to_origin(self, pos: Position6D) -> float:
        """
        Compute hyperbolic distance from origin (safe center).

        This is useful for risk assessment - further from origin
        means higher deviation from "safe" state.

        Args:
            pos: Position to measure

        Returns:
            Hyperbolic distance from origin
        """
        emb = self.embed_position(pos)
        origin = np.zeros(6)
        return hyperbolic_distance(emb.embedded, origin)

    def embed_context(self, ctx: 'AetherContext') -> Optional[PoincarePosition]:
        """
        Embed an Aethercode execution context's position.

        Args:
            ctx: Aethercode execution context

        Returns:
            PoincarePosition or None if context not available
        """
        if not SPIRALVERSE_AVAILABLE:
            return None

        if hasattr(ctx, 'position'):
            return self.embed_position(ctx.position)
        return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_bridge(**kwargs) -> AethercodeLayer4Bridge:
    """Factory function to create the bridge."""
    return AethercodeLayer4Bridge(**kwargs)


def embed_position_simple(
    axiom: float = 0.0,
    flow: float = 0.0,
    glyph: float = 0.0,
    oracle: float = 0.0,
    charm: float = 0.0,
    ledger: int = 0,
    alpha: float = 1.0,
) -> np.ndarray:
    """
    Simple function to embed 6D coordinates into Poincaré ball.

    Args:
        axiom: X coordinate (meters)
        flow: Y coordinate (meters)
        glyph: Z coordinate (meters)
        oracle: Velocity (m/s)
        charm: Harmony coefficient [-1, 1]
        ledger: Security level [0, 255]
        alpha: Embedding curvature

    Returns:
        6D point in Poincaré ball
    """
    pos = Position6D(
        axiom=axiom,
        flow=flow,
        glyph=glyph,
        oracle=oracle,
        charm=charm,
        ledger=int(ledger)
    )
    bridge = AethercodeLayer4Bridge(alpha=alpha)
    result = bridge.embed_position(pos)
    return result.embedded


def position_risk_score(
    pos: Position6D,
    safe_position: Optional[Position6D] = None
) -> Dict[str, Any]:
    """
    Compute risk score based on position in Poincaré ball.

    Higher distance from origin/safe position = higher risk.

    Args:
        pos: Current position
        safe_position: Reference safe position (default: origin)

    Returns:
        Risk assessment dict
    """
    bridge = AethercodeLayer4Bridge()

    # Distance from origin
    dist_origin = bridge.compute_distance_to_origin(pos)

    # Distance from safe position
    if safe_position:
        dist_safe = bridge.compute_distance(pos, safe_position)
    else:
        dist_safe = dist_origin

    # Embed for analysis
    emb = bridge.embed_position(pos)

    # Risk score: normalized distance (sigmoid-like scaling)
    risk_raw = dist_origin
    risk_normalized = 1.0 - np.exp(-risk_raw / 2.0)  # Maps to [0, 1)

    return {
        'distance_from_origin': dist_origin,
        'distance_from_safe': dist_safe,
        'risk_score': float(risk_normalized),
        'norm_in_ball': emb.norm_in_ball,
        'axis_contributions': emb.axis_contributions,
        'is_near_boundary': emb.norm_in_ball > 0.9,
    }


# =============================================================================
# PIPELINE INTEGRATION
# =============================================================================

class Layer4PositionPipeline:
    """
    Complete pipeline for position-based governance.

    Layers:
    - Input: Position6D from Aethercode
    - Layer 3: Golden ratio weighting
    - Layer 4: Poincaré embedding
    - Layer 5: Hyperbolic distance
    - Output: Risk metrics for Layer 13
    """

    def __init__(self, alpha: float = 1.0):
        self.bridge = AethercodeLayer4Bridge(alpha=alpha)
        self.history: List[PoincarePosition] = []

    def process(self, pos: Position6D) -> Dict[str, Any]:
        """
        Process a position through Layers 3-5.

        Args:
            pos: Input 6D position

        Returns:
            Pipeline results including risk metrics
        """
        # Embed position
        embedded = self.bridge.embed_position(pos)
        self.history.append(embedded)

        # Compute distances
        dist_origin = self.bridge.compute_distance_to_origin(pos)

        # Compute velocity (change from last position)
        velocity = 0.0
        if len(self.history) >= 2:
            prev = self.history[-2]
            velocity = hyperbolic_distance(embedded.embedded, prev.embedded)

        # Risk assessment
        risk = position_risk_score(pos)

        return {
            'layer_3_weighted': embedded.weighted.tolist(),
            'layer_4_embedded': embedded.embedded.tolist(),
            'layer_5_distance': dist_origin,
            'velocity': velocity,
            'risk': risk,
            'valid': embedded.is_valid,
        }

    def get_trajectory(self) -> List[np.ndarray]:
        """Get trajectory of all processed positions."""
        return [p.embedded for p in self.history]
