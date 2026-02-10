"""
@file bounds_checker.py
@module agents/browser/bounds_checker
@layer Layer 4, 5, 8, 9, 10, 13
@component Geometric Bounds Checker
@version 1.0.0

Implements the BoundsChecker from the Geometric Bounds Specification.

The feasible set B is the intersection of multiple constraints:
    B = B_intent ∩ B_coherence ∩ B_spectral ∩ B_authority ∩ B_realm ∩ B_gfss

A proposed action is INSIDE bounds iff it satisfies ALL constraints.
Any single violation → OUTSIDE bounds.

Decision mapping:
    0 violations → ALLOW
    1-2 violations → QUARANTINE
    3+ violations → DENY

Author: Issac Davis
"""

from __future__ import annotations

import math
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)

EPSILON = 1e-10


# ============================================================================
# Data Structures
# ============================================================================

class Decision(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    DENY = "DENY"


@dataclass
class BoundsResult:
    """Result of a complete bounds check."""
    decision: Decision
    is_inside: bool
    violations: List[str]
    scores: Dict[str, float]
    embedding_norm: float
    hyperbolic_distance: float


@dataclass
class ActionContext:
    """Context for a proposed action."""
    risk_score: float          # 0-1 normalized risk
    scope_delta: float         # change in permissions (0 = none, 1 = full escalation)
    provenance_score: float    # memory trust (0 = untrusted, 1 = fully trusted)
    touches_secrets: bool      # does action access secrets?
    tool_class: str            # action type: navigate, click, type, execute, admin
    coherence: float           # current system coherence (0-1)

    # Optional HYDRA governance
    votes: Optional[List[str]] = None  # list of 'APPROVE' or 'DENY'
    agent_states: Optional[np.ndarray] = None  # agent state matrix for GFSS


# Tool class IDs for embedding
TOOL_CLASS_IDS = {
    "read": 0.1,
    "navigate": 0.2,
    "click": 0.3,
    "screenshot": 0.4,
    "type": 0.5,
    "evaluate": 0.6,
    "execute": 0.8,
    "admin": 1.0,
}

# Quorum requirements by risk tier
QUORUM_THRESHOLDS = {
    "low": 3,       # 3/6 for low risk
    "medium": 4,    # 4/6 for medium
    "high": 5,      # 5/6 for high
    "critical": 6,  # unanimous for critical
}


# ============================================================================
# Core Math (Poincaré Ball)
# ============================================================================

def realify(c: np.ndarray) -> np.ndarray:
    """L1-L2: Complex → Real (interleave real and imaginary parts)."""
    return np.concatenate([c.real, c.imag])


def weighted_transform(x: np.ndarray, metric_weights: Optional[np.ndarray] = None) -> np.ndarray:
    """L3: Apply SPD metric weights (golden ratio powers by default)."""
    phi = (1 + math.sqrt(5)) / 2
    if metric_weights is None:
        n = len(x)
        metric_weights = np.array([phi ** (i % 6) for i in range(n)])
    return np.sqrt(metric_weights) * x


def poincare_embed(x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """L4: Project into Poincaré ball via exponential map at origin."""
    norm = np.linalg.norm(x)
    if norm < EPSILON:
        return x
    scale = math.tanh(alpha * norm / 2.0)
    result = (scale / norm) * x
    # Ensure strictly inside ball
    result_norm = np.linalg.norm(result)
    if result_norm >= 1.0 - EPSILON:
        result = result * (1.0 - EPSILON) / result_norm
    return result


def hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
    """L5: Compute hyperbolic distance in Poincaré ball."""
    norm_u_sq = min(np.dot(u, u), 1.0 - EPSILON)
    norm_v_sq = min(np.dot(v, v), 1.0 - EPSILON)
    diff_sq = np.dot(u - v, u - v)

    delta = 2 * diff_sq / ((1 - norm_u_sq) * (1 - norm_v_sq))
    return float(np.arccosh(1 + max(delta, 0)))


def spectral_stability(signal: np.ndarray) -> float:
    """L9: Compute spectral stability from frequency content."""
    if len(signal) < 2:
        return 1.0
    fft_result = np.fft.fft(signal)
    magnitudes = np.abs(fft_result[:len(signal) // 2])
    total_energy = np.sum(magnitudes ** 2)
    if total_energy < EPSILON:
        return 1.0
    # High frequency = upper half of spectrum
    midpoint = len(magnitudes) // 2
    hf_energy = np.sum(magnitudes[midpoint:] ** 2)
    return float(1.0 - hf_energy / total_energy)


def spin_coherence(phasors: np.ndarray) -> float:
    """L10: Compute spin coherence from complex phasors."""
    total_norm = np.sum(np.abs(phasors))
    if total_norm < EPSILON:
        return 0.0
    return float(np.abs(np.sum(phasors)) / total_norm)


def graph_fourier_high_freq_energy(
    agent_states: np.ndarray,
    adjacency: Optional[np.ndarray] = None,
) -> float:
    """
    GFSS: Compute high-frequency energy from graph Fourier transform.

    Args:
        agent_states: (n_agents,) state vector
        adjacency: (n_agents, n_agents) adjacency matrix. If None, uses complete graph.

    Returns:
        High-frequency energy ratio in [0, 1]
    """
    n = len(agent_states)
    if n < 2:
        return 0.0

    # Build adjacency if not provided (complete graph)
    if adjacency is None:
        adjacency = np.ones((n, n)) - np.eye(n)

    # Degree matrix
    degrees = np.sum(adjacency, axis=1)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(degrees, EPSILON)))

    # Normalized Laplacian: L = I - D^(-1/2) A D^(-1/2)
    L = np.eye(n) - D_inv_sqrt @ adjacency @ D_inv_sqrt

    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(L)

    # Graph Fourier transform
    x_hat = eigenvectors.T @ agent_states

    # High-frequency = eigenvalues above median
    median_eig = np.median(eigenvalues)
    hf_mask = eigenvalues > median_eig
    total_energy = np.sum(x_hat ** 2)
    if total_energy < EPSILON:
        return 0.0
    hf_energy = np.sum(x_hat[hf_mask] ** 2)
    return float(hf_energy / total_energy)


# ============================================================================
# BoundsChecker
# ============================================================================

class BoundsChecker:
    """
    Geometric bounds checker implementing the feasible set:
        B = B_intent ∩ B_coherence ∩ B_spectral ∩ B_authority ∩ B_realm ∩ B_gfss

    Each bound is checked independently. The decision is:
        0 violations → ALLOW
        1-2 violations → QUARANTINE
        3+ violations → DENY
    """

    def __init__(
        self,
        mu_intent: Optional[np.ndarray] = None,
        R_intent: float = 0.5,
        realm_centers: Optional[np.ndarray] = None,
        R_realm: float = 0.8,
        threshold_spectral: float = 0.65,
        threshold_spin: float = 0.70,
        gfss_threshold: float = 0.6,
        embedding_dim: int = 12,  # 6 features → realified to 12
    ):
        self.embedding_dim = embedding_dim

        # Intent bounds (L5)
        if mu_intent is None:
            # Default: origin (safe actions embed near origin due to centering)
            mu_intent = np.zeros(embedding_dim)
        self.mu_intent = mu_intent
        self.R_intent = R_intent

        # Realm bounds (L8)
        if realm_centers is None:
            # Default: single realm at origin
            realm_centers = np.zeros((1, len(mu_intent)))
        self.realm_centers = realm_centers
        self.R_realm = R_realm

        # Spectral thresholds (L9, L10)
        self.threshold_spectral = threshold_spectral
        self.threshold_spin = threshold_spin

        # GFSS threshold
        self.gfss_threshold = gfss_threshold

    def embed_action(self, ctx: ActionContext) -> np.ndarray:
        """
        Φ(x, a): Embed an action context into the Poincaré ball.

        Pipeline: Features → Center (offset from safe baseline) → Complex (L1)
                  → Real (L2) → Weighted (L3) → Poincaré (L4)

        Key insight: features are centered around "safe baseline" so that
        safe actions embed near the origin and dangerous actions embed
        near the boundary. Without centering, golden ratio weights push
        everything to the boundary regardless of risk.
        """
        tool_id = TOOL_CLASS_IDS.get(ctx.tool_class.lower(), 0.5)

        # Raw features
        raw = np.array([
            ctx.risk_score,
            ctx.scope_delta,
            ctx.provenance_score,
            float(ctx.touches_secrets),
            tool_id,
            ctx.coherence,
        ])

        # Safe baseline: low risk, no escalation, high trust, no secrets, read, high coherence
        baseline = np.array([0.1, 0.0, 0.9, 0.0, 0.1, 0.9])

        # Center: deviation from safe baseline
        # For provenance and coherence, invert (higher = safer → lower deviation)
        deviation = np.array([
            raw[0] - baseline[0],       # risk: higher = more dangerous
            raw[1] - baseline[1],       # scope: higher = more escalation
            baseline[2] - raw[2],       # provenance: lower = more dangerous (inverted)
            raw[3] - baseline[3],       # secrets: 1 = dangerous
            raw[4] - baseline[4],       # tool: higher class = more dangerous
            baseline[5] - raw[5],       # coherence: lower = more dangerous (inverted)
        ])

        # Scale so safe actions have small deviation magnitude
        features = deviation * 0.5

        # L1: Real features as complex (imaginary = 0)
        c = features.astype(np.complex128)

        # L2: Realify
        x = realify(c)

        # L3: Weighted transform (uniform weights to avoid golden ratio inflation)
        x_g = weighted_transform(x, metric_weights=np.ones(len(x)))

        # L4: Poincaré embed
        u = poincare_embed(x_g)

        return u

    def check_intent_bounds(self, u: np.ndarray) -> Tuple[bool, float]:
        """B_intent: dH(u, μ) ≤ R"""
        d = hyperbolic_distance(u, self.mu_intent)
        return d <= self.R_intent, d

    def check_realm_bounds(self, u: np.ndarray) -> Tuple[bool, float]:
        """B_realm: min_k dH(u, μ_k) ≤ R_realm"""
        d_star = min(
            hyperbolic_distance(u, center) for center in self.realm_centers
        )
        return d_star <= self.R_realm, d_star

    def check_spectral_bounds(self, ctx: ActionContext) -> Tuple[bool, float]:
        """B_spectral: S_spec ≥ threshold"""
        # Generate a signal from the action context for spectral analysis
        # In production this would come from real telemetry
        signal = np.array([
            ctx.risk_score,
            ctx.scope_delta,
            ctx.provenance_score,
            ctx.coherence,
            1.0 - ctx.risk_score,
            ctx.coherence ** 2,
            math.sin(ctx.risk_score * math.pi),
            math.cos(ctx.coherence * math.pi),
        ])
        s_spec = spectral_stability(signal)
        return s_spec >= self.threshold_spectral, s_spec

    def check_spin_bounds(self, ctx: ActionContext) -> Tuple[bool, float]:
        """B_spin: C_spin ≥ threshold

        Phase alignment measures whether the action's "safety indicators"
        (coherence, provenance, inverse risk) point in the same direction.

        High coherence + high provenance + low risk = aligned phases → high C_spin.
        Mixed signals (high coherence but high risk) = misaligned → low C_spin.
        """
        # Safety indicators in [0, 1] — higher = safer
        safety_signals = np.array([
            ctx.coherence,
            ctx.provenance_score,
            1.0 - ctx.risk_score,
            1.0 - ctx.scope_delta,
            1.0 - float(ctx.touches_secrets),
            ctx.coherence * ctx.provenance_score,  # compound safety
        ])

        # Convert to phasors: safe (>0.5) → phase near 0, unsafe (<0.5) → phase near π
        # Use 2π range for stronger separation of mixed signals
        phases = (1.0 - safety_signals) * 2 * math.pi
        phasors = np.exp(1j * phases)
        c_spin = spin_coherence(phasors)
        return c_spin >= self.threshold_spin, c_spin

    def check_authority_bounds(self, ctx: ActionContext) -> Tuple[bool, float]:
        """B_authority: approvals ≥ quorum for risk tier"""
        if ctx.votes is None:
            # No HYDRA governance — pass by default for solo agent
            return True, 1.0

        # Classify risk tier
        if ctx.risk_score >= 0.8:
            tier = "critical"
        elif ctx.risk_score >= 0.5:
            tier = "high"
        elif ctx.risk_score >= 0.3:
            tier = "medium"
        else:
            tier = "low"

        required = QUORUM_THRESHOLDS[tier]
        approvals = sum(1 for v in ctx.votes if v.upper() == "APPROVE")
        ratio = approvals / max(len(ctx.votes), 1)
        return approvals >= required, ratio

    def check_gfss_bounds(self, ctx: ActionContext) -> Tuple[bool, float]:
        """B_gfss: high-frequency graph spectral energy ≤ threshold"""
        if ctx.agent_states is None:
            # No multi-agent data — pass by default
            return True, 0.0

        e_high = graph_fourier_high_freq_energy(ctx.agent_states)
        return e_high <= self.gfss_threshold, e_high

    def check_all_bounds(self, ctx: ActionContext) -> BoundsResult:
        """
        Complete bounds check: Φ(x, a) → [check all bounds] → Decision

        Returns BoundsResult with decision, violations, and scores.
        """
        u = self.embed_action(ctx)
        embedding_norm = float(np.linalg.norm(u))

        violations = []
        scores = {}

        # 1. Intent bounds (L5)
        ok, d = self.check_intent_bounds(u)
        scores["intent_distance"] = d
        if not ok:
            violations.append("intent")

        # 2. Realm bounds (L8)
        ok, d_star = self.check_realm_bounds(u)
        scores["realm_distance"] = d_star
        if not ok:
            violations.append("realm")

        # 3. Spectral bounds (L9)
        ok, s_spec = self.check_spectral_bounds(ctx)
        scores["spectral_stability"] = s_spec
        if not ok:
            violations.append("spectral")

        # 4. Spin bounds (L10)
        ok, c_spin = self.check_spin_bounds(ctx)
        scores["spin_coherence"] = c_spin
        if not ok:
            violations.append("spin")

        # 5. Authority bounds (HYDRA)
        ok, ratio = self.check_authority_bounds(ctx)
        scores["authority_ratio"] = ratio
        if not ok:
            violations.append("authority")

        # 6. GFSS bounds (HYDRA)
        ok, e_high = self.check_gfss_bounds(ctx)
        scores["gfss_energy"] = e_high
        if not ok:
            violations.append("gfss")

        # Decision: 0 → ALLOW, 1-2 → QUARANTINE, 3+ → DENY
        n_violations = len(violations)
        if n_violations == 0:
            decision = Decision.ALLOW
        elif n_violations <= 2:
            decision = Decision.QUARANTINE
        else:
            decision = Decision.DENY

        return BoundsResult(
            decision=decision,
            is_inside=(n_violations == 0),
            violations=violations,
            scores=scores,
            embedding_norm=embedding_norm,
            hyperbolic_distance=scores["intent_distance"],
        )
