"""
Entropy Surface Defense — Semantic Nullification, Probing Detection, Leakage Budget.

Python reference implementation (canonical is TypeScript).

Implements "controlled entropy surface" defense:

  1. Probing Detection: Distinguishes adversarial probing from legitimate use.
  2. Leakage Budget: Information-theoretic bound on emitted signal bits.
  3. Semantic Nullification: Controlled degradation to plausible-but-inert output.

Core insight: model extraction requires stable (input → output) mappings.
Under probing, this layer ensures outputs carry near-zero mutual information
with the true function, so surrogate models converge to noise.

Mathematical basis:
  - Signal retention:  σ(p) = 1 / (1 + e^{k(p - θ)})
  - Leakage rate:      λ(t) = Σ_{i∈W} I(x_i; y_i)
  - Nullification:     N(x) = σ · f(x) + (1 - σ) · U

@layer Layer 12, Layer 13
@version 1.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

EPSILON = 1e-10


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

Vector6D = Tuple[float, float, float, float, float, float]


class ProbingClassification(Enum):
    LEGITIMATE = "LEGITIMATE"
    AMBIGUOUS = "AMBIGUOUS"
    PROBING = "PROBING"


class DefensePosture(Enum):
    TRANSPARENT = "TRANSPARENT"
    GUARDED = "GUARDED"
    OPAQUE = "OPAQUE"
    SILENT = "SILENT"


@dataclass
class ProbingSignature:
    """Signature of a potential probing attempt."""

    query_entropy: float
    temporal_regularity: float
    coverage_breadth: float
    repetition_score: float
    confidence: float
    classification: ProbingClassification


@dataclass
class LeakageBudget:
    """Information leakage budget tracker."""

    total_budget: float
    consumed: float
    remaining: float
    current_rate: float
    exhausted: bool
    pressure: float


@dataclass
class NullificationDirective:
    """Semantic nullification directive."""

    active: bool
    strength: float
    entropy_injection: float
    signal_retention: float
    reason: str


@dataclass
class EntropySurfaceAssessment:
    """Full entropy surface defense assessment."""

    probing: ProbingSignature
    leakage: LeakageBudget
    nullification: NullificationDirective
    surface_distance: float
    posture: DefensePosture


@dataclass
class QueryObservation:
    """A query observation for the entropy surface tracker."""

    position: Vector6D
    timestamp: float
    response_mi: float


@dataclass
class EntropySurfaceConfig:
    """Configuration for the entropy surface defense."""

    leakage_budget_bits: float = 128.0
    window_size: int = 50
    probing_threshold_low: float = 0.3
    probing_threshold_high: float = 0.6
    sigmoid_k: float = 10.0
    timing_jitter_threshold: float = 50.0
    coverage_threshold: float = 0.4
    repetition_dist_threshold: float = 0.1


# ═══════════════════════════════════════════════════════════════
# Hyperbolic geometry (minimal, matches TS chsfn.ts)
# ═══════════════════════════════════════════════════════════════


def _poincare_norm(v: Vector6D) -> float:
    return math.sqrt(sum(x * x for x in v))


def _hyperbolic_distance_6d(u: Vector6D, v: Vector6D) -> float:
    """Poincaré ball hyperbolic distance in 6D."""
    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    u_sq = sum(x * x for x in u)
    v_sq = sum(x * x for x in v)
    u_factor = max(EPSILON, 1 - u_sq)
    v_factor = max(EPSILON, 1 - v_sq)
    arg = 1 + 2 * diff_sq / (u_factor * v_factor)
    return math.acosh(max(1.0, arg))


# ═══════════════════════════════════════════════════════════════
# 1. Probing Detection
# ═══════════════════════════════════════════════════════════════


def shannon_entropy(counts: List[int]) -> float:
    """Normalized Shannon entropy in [0, 1]."""
    total = sum(counts)
    if total == 0:
        return 0.0

    non_zero = [c for c in counts if c > 0]
    entropy = 0.0
    for c in non_zero:
        p = c / total
        entropy -= p * math.log2(p)

    max_entropy = math.log2(max(len(non_zero), 1))
    return entropy / max_entropy if max_entropy > 0 else 0.0


def detect_temporal_regularity(
    timestamps: List[float], jitter_threshold: float = 50.0
) -> float:
    """Detect temporal regularity in query timing. Returns [0, 1]."""
    if len(timestamps) < 3:
        return 0.0

    intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
    mean = sum(intervals) / len(intervals)
    if mean < EPSILON:
        return 1.0

    variance = sum((x - mean) ** 2 for x in intervals) / len(intervals)
    std = math.sqrt(variance)
    cv = std / mean
    normalized_cv = cv * mean / max(jitter_threshold, 1.0)
    return 1.0 / (1.0 + normalized_cv)


def compute_coverage_breadth(positions: List[Vector6D], bin_count: int = 5) -> float:
    """Compute input-space coverage breadth. Returns [0, 1]."""
    if not positions:
        return 0.0

    visited: set = set()
    for pos in positions:
        key = tuple(
            min(bin_count - 1, max(0, int(((v + 1) / 2) * bin_count))) for v in pos
        )
        visited.add(key)

    max_bins = bin_count**6
    return len(visited) / max_bins


def compute_repetition_score(
    positions: List[Vector6D], dist_threshold: float = 0.1
) -> float:
    """Compute repetition score. Returns [0, 1]."""
    if len(positions) < 2:
        return 0.0

    near_pairs = 0
    total_pairs = 0
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            total_pairs += 1
            d = _hyperbolic_distance_6d(positions[i], positions[j])
            if d < dist_threshold:
                near_pairs += 1

    return near_pairs / total_pairs if total_pairs > 0 else 0.0


def detect_probing(
    observations: List[QueryObservation],
    config: Optional[EntropySurfaceConfig] = None,
) -> ProbingSignature:
    """Analyze query history to detect adversarial probing."""
    if config is None:
        config = EntropySurfaceConfig()

    if len(observations) < 2:
        return ProbingSignature(
            query_entropy=1.0,
            temporal_regularity=0.0,
            coverage_breadth=0.0,
            repetition_score=0.0,
            confidence=0.0,
            classification=ProbingClassification.LEGITIMATE,
        )

    positions = [o.position for o in observations]
    timestamps = [o.timestamp for o in observations]

    # 1. Query distribution entropy
    bin_count = 5
    bin_counts: dict = {}
    for pos in positions:
        key = tuple(
            min(bin_count - 1, max(0, int(((v + 1) / 2) * bin_count))) for v in pos
        )
        bin_counts[key] = bin_counts.get(key, 0) + 1
    query_entropy = shannon_entropy(list(bin_counts.values()))

    # 2. Temporal regularity
    temporal_regularity = detect_temporal_regularity(
        timestamps, config.timing_jitter_threshold
    )

    # 3. Coverage breadth
    coverage_breadth = compute_coverage_breadth(positions, bin_count)

    # 4. Repetition
    repetition_score = compute_repetition_score(
        positions, config.repetition_dist_threshold
    )

    # Composite confidence
    entropy_signal = 1.0 - query_entropy
    confidence = min(
        1.0,
        0.25 * entropy_signal
        + 0.25 * temporal_regularity
        + 0.25 * min(coverage_breadth / max(config.coverage_threshold, EPSILON), 1.0)
        + 0.25 * repetition_score,
    )

    if confidence >= config.probing_threshold_high:
        classification = ProbingClassification.PROBING
    elif confidence >= config.probing_threshold_low:
        classification = ProbingClassification.AMBIGUOUS
    else:
        classification = ProbingClassification.LEGITIMATE

    return ProbingSignature(
        query_entropy=query_entropy,
        temporal_regularity=temporal_regularity,
        coverage_breadth=coverage_breadth,
        repetition_score=repetition_score,
        confidence=confidence,
        classification=classification,
    )


# ═══════════════════════════════════════════════════════════════
# 2. Information Leakage Budget
# ═══════════════════════════════════════════════════════════════


def estimate_response_mi(response_position: Vector6D) -> float:
    """Estimate mutual information of a response in bits."""
    origin: Vector6D = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    dist = _hyperbolic_distance_6d(response_position, origin)
    return math.log2(1 + dist)


def compute_leakage_budget(
    observations: List[QueryObservation],
    config: Optional[EntropySurfaceConfig] = None,
) -> LeakageBudget:
    """Compute the current leakage budget state."""
    if config is None:
        config = EntropySurfaceConfig()

    window = observations[-config.window_size :]
    consumed = sum(o.response_mi for o in window)
    remaining = max(0.0, config.leakage_budget_bits - consumed)
    current_rate = consumed / len(window) if window else 0.0
    exhausted = remaining <= 0
    pressure = min(1.0, consumed / max(config.leakage_budget_bits, EPSILON))

    return LeakageBudget(
        total_budget=config.leakage_budget_bits,
        consumed=consumed,
        remaining=remaining,
        current_rate=current_rate,
        exhausted=exhausted,
        pressure=pressure,
    )


# ═══════════════════════════════════════════════════════════════
# 3. Semantic Nullification
# ═══════════════════════════════════════════════════════════════


def sigmoid_gate(pressure: float, k: float = 10.0, theta: float = 0.5) -> float:
    """Sigmoid gating: σ(p) = 1 / (1 + e^{k(p - θ)})."""
    return 1.0 / (1.0 + math.exp(k * (pressure - theta)))


def compute_nullification(
    probing: ProbingSignature,
    leakage: LeakageBudget,
    config: Optional[EntropySurfaceConfig] = None,
) -> NullificationDirective:
    """Compute semantic nullification directive."""
    if config is None:
        config = EntropySurfaceConfig()

    pressure = max(probing.confidence, leakage.pressure)
    signal_retention = sigmoid_gate(pressure, config.sigmoid_k)
    strength = 1.0 - signal_retention
    entropy_injection = strength * max(leakage.remaining, 0.0)
    active = strength > 0.05

    if leakage.exhausted:
        reason = "BUDGET_EXHAUSTED"
    elif probing.classification == ProbingClassification.PROBING:
        reason = "PROBING_DETECTED"
    elif probing.classification == ProbingClassification.AMBIGUOUS:
        reason = "AMBIGUOUS_INTENT"
    elif leakage.pressure > 0.5:
        reason = "BUDGET_PRESSURE"
    else:
        reason = "NOMINAL"

    return NullificationDirective(
        active=active,
        strength=strength,
        entropy_injection=entropy_injection,
        signal_retention=signal_retention,
        reason=reason,
    )


# ═══════════════════════════════════════════════════════════════
# 4. Entropy Surface Distance
# ═══════════════════════════════════════════════════════════════


def surface_distance(
    probing: ProbingSignature, leakage: LeakageBudget, theta: float = 0.5
) -> float:
    """Signed distance to entropy surface boundary."""
    pressure = max(probing.confidence, leakage.pressure)
    return pressure - theta


# ═══════════════════════════════════════════════════════════════
# 5. Unified Assessment
# ═══════════════════════════════════════════════════════════════


def assess_entropy_surface(
    observations: List[QueryObservation],
    config: Optional[EntropySurfaceConfig] = None,
) -> EntropySurfaceAssessment:
    """Perform full entropy surface defense assessment."""
    if config is None:
        config = EntropySurfaceConfig()

    probing = detect_probing(observations, config)
    leakage = compute_leakage_budget(observations, config)
    nullification = compute_nullification(probing, leakage, config)
    dist = surface_distance(probing, leakage)

    if nullification.strength > 0.9 or leakage.exhausted:
        posture = DefensePosture.SILENT
    elif nullification.strength > 0.5:
        posture = DefensePosture.OPAQUE
    elif nullification.active:
        posture = DefensePosture.GUARDED
    else:
        posture = DefensePosture.TRANSPARENT

    return EntropySurfaceAssessment(
        probing=probing,
        leakage=leakage,
        nullification=nullification,
        surface_distance=dist,
        posture=posture,
    )


# ═══════════════════════════════════════════════════════════════
# 6. Stateful Tracker
# ═══════════════════════════════════════════════════════════════


class EntropySurfaceTracker:
    """Stateful entropy surface tracker with sliding window."""

    def __init__(self, config: Optional[EntropySurfaceConfig] = None) -> None:
        self.config = config or EntropySurfaceConfig()
        self._observations: List[QueryObservation] = []
        self._last_assessment: Optional[EntropySurfaceAssessment] = None

    def observe(
        self,
        position: Vector6D,
        response_mi: float,
        timestamp: Optional[float] = None,
    ) -> EntropySurfaceAssessment:
        """Record a new query observation and return updated assessment."""
        import time as _time

        if timestamp is None:
            timestamp = _time.time() * 1000  # ms

        self._observations.append(
            QueryObservation(position=position, timestamp=timestamp, response_mi=response_mi)
        )

        max_history = self.config.window_size * 2
        if len(self._observations) > max_history:
            self._observations = self._observations[-max_history:]

        self._last_assessment = assess_entropy_surface(self._observations, self.config)
        return self._last_assessment

    @property
    def last_assessment(self) -> Optional[EntropySurfaceAssessment]:
        return self._last_assessment

    @property
    def observation_count(self) -> int:
        return len(self._observations)

    def reset(self) -> None:
        self._observations = []
        self._last_assessment = None

    def nullify(self, response: Vector6D) -> Vector6D:
        """Apply nullification to a response vector."""
        if self._last_assessment is None or not self._last_assessment.nullification.active:
            return response

        sigma = self._last_assessment.nullification.signal_retention
        return tuple(v * sigma for v in response)  # type: ignore[return-value]
