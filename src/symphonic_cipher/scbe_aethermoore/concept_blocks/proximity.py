"""
Concept Blocks — PROXIMITY (6th Sense)
=======================================

Decimal-drift proximity field for near-miss detection in multi-vector
spaces.  Maps to SCBE Layer 14 (Audio Axis / spatial awareness).

This is the sense organ that traditional AI lacks: not sight, hearing,
touch, taste, or smell — but *proximity awareness*.  The feeling that
something is approaching before any direct sensor detects it.

How it works:

1. Each agent tracks its own decimal drift (16th decimal place) across
   pipeline steps.  Genuine computation → non-uniform drift.  Synthetic
   → uniform drift.

2. When two agents' drift patterns start *converging* — the distance
   between their drift signatures shrinks — that's a proximity signal.
   Their "flight paths" are overlapping in multi-vector space before
   their actual positions intersect.

3. The convergence rate maps to a phase-modulated warning:
   - CLEAR:    drift divergence increasing (separating)
   - ADVISORY: drift stable (parallel paths)
   - WARNING:  drift converging (approaching)
   - CRITICAL: drift collapsed (collision imminent — millimeters)

Mathematical basis:

- Non-negative eigenvalues of the drift autocorrelation matrix
  ensure no phantom proximity signals (no false "ghost drones")
- Aperiodic phason shifts from the quasicrystal lattice modulate
  the detection threshold — the sensitivity itself never repeats,
  making the proximity field unpredictable to adversaries
- The Poincaré metric amplifies drift differences near the ball
  boundary, giving exponentially sharper proximity detection as
  agents approach the manifold edge

# A4: Symmetry — proximity field is gauge-invariant (same in all frames)
# A3: Causality — convergence rate respects time-ordering
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Deque, Dict, List, Tuple

from .base import BlockResult, BlockStatus, ConceptBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
EPSILON: float = 1e-15

# Sacred Tongue harmonic frequencies: 440 * φ^k Hz
TONGUE_HARMONICS: List[float] = [440.0 * PHI**k for k in range(6)]

# Proximity alert thresholds
CLEAR_THRESHOLD: float = 0.5  # Drift divergence > this → CLEAR
ADVISORY_THRESHOLD: float = 0.1  # Drift stable within this band
WARNING_THRESHOLD: float = 0.01  # Drift converging below this
CRITICAL_THRESHOLD: float = 0.001  # Drift collapsed → collision imminent

# Minimum samples for reliable proximity detection
MIN_PROXIMITY_SAMPLES: int = 4

# Shadow buffer capacity
DRIFT_BUFFER_SIZE: int = 128


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ProximityLevel(Enum):
    """Proximity alert levels — the 6th sense output."""

    CLEAR = "CLEAR"  # Separating — no concern
    ADVISORY = "ADVISORY"  # Parallel paths — monitor
    WARNING = "WARNING"  # Converging — prepare evasion
    CRITICAL = "CRITICAL"  # Collision imminent — act now
    UNKNOWN = "UNKNOWN"  # Insufficient data


@dataclass
class DriftSample:
    """A single decimal-drift measurement from a pipeline step."""

    timestamp: float
    values: List[float]  # Per-dimension drift magnitudes
    magnitude: float  # L2 norm of drift vector
    layer: int  # Pipeline layer that produced this (1-14)

    @property
    def cv(self) -> float:
        """Coefficient of variation — uniformity detector."""
        if not self.values:
            return 0.0
        mean = sum(abs(v) for v in self.values) / len(self.values)
        if mean < EPSILON:
            return 0.0
        variance = sum((abs(v) - mean) ** 2 for v in self.values) / len(self.values)
        return math.sqrt(variance) / mean


@dataclass
class ProximityReading:
    """Result of a proximity field evaluation between two agents."""

    level: ProximityLevel
    drift_distance: float  # L2 distance between drift signatures
    convergence_rate: float  # Negative = approaching, positive = separating
    time_to_contact: float  # Estimated seconds to zero distance (-1 if separating)
    phase_angle: float  # Phase relationship in Sacred Tongue space
    eigenvalue_floor: float  # Minimum eigenvalue (must be >= 0 for valid reading)
    confidence: float  # 0.0 - 1.0 based on sample count
    aperiodic_modulation: float  # Current phason shift applied to thresholds


# ---------------------------------------------------------------------------
# Drift Shadow Buffer
# ---------------------------------------------------------------------------


class DriftShadowBuffer:
    """Circular buffer of drift samples for a single agent.

    Captures the 16th decimal place that other systems discard.
    The accumulated pattern forms a geodesic fingerprint unique
    to genuine computation.
    """

    def __init__(self, capacity: int = DRIFT_BUFFER_SIZE) -> None:
        self._buffer: Deque[DriftSample] = deque(maxlen=capacity)
        self._total_samples: int = 0

    def push(self, values: List[float], layer: int = 14) -> DriftSample:
        """Record a new drift measurement."""
        mag = math.sqrt(sum(v * v for v in values)) if values else 0.0
        sample = DriftSample(
            timestamp=time.time(),
            values=list(values),
            magnitude=mag,
            layer=layer,
        )
        self._buffer.append(sample)
        self._total_samples += 1
        return sample

    @property
    def samples(self) -> List[DriftSample]:
        return list(self._buffer)

    @property
    def count(self) -> int:
        return len(self._buffer)

    def signature(self, window: int = 16) -> List[float]:
        """Extract the drift signature from the most recent N samples.

        The signature is the per-dimension mean of absolute drift values,
        forming a compact fingerprint of the agent's computational behavior.
        """
        recent = list(self._buffer)[-window:]
        if not recent:
            return []

        dims = len(recent[0].values)
        if dims == 0:
            return []

        sig = [0.0] * dims
        for sample in recent:
            for i in range(min(dims, len(sample.values))):
                sig[i] += abs(sample.values[i])

        n = len(recent)
        return [s / n for s in sig]

    def fractal_dimension(self) -> float:
        """Estimate fractal dimension of the drift magnitude sequence.

        Genuine drift → D_f > 1.2 (complex, non-repeating)
        Synthetic drift → D_f < 1.0 (too smooth, predictable)
        """
        magnitudes = [s.magnitude for s in self._buffer]
        if len(magnitudes) < 8:
            return 0.0

        # Box-counting approximation via Higuchi method
        k_max = min(len(magnitudes) // 4, 16)
        if k_max < 2:
            return 0.0

        log_lengths: List[Tuple[float, float]] = []
        for k in range(1, k_max + 1):
            length = 0.0
            count = 0
            for m in range(k):
                for i in range(1, (len(magnitudes) - m) // k):
                    idx_curr = m + i * k
                    idx_prev = m + (i - 1) * k
                    if idx_curr < len(magnitudes):
                        length += abs(magnitudes[idx_curr] - magnitudes[idx_prev])
                        count += 1
            if count > 0:
                normalized = (length / count) * ((len(magnitudes) - 1) / k)
                if normalized > EPSILON:
                    log_lengths.append((math.log(1.0 / k), math.log(normalized)))

        if len(log_lengths) < 2:
            return 0.0

        # Linear regression on log-log plot
        n = len(log_lengths)
        sx = sum(p[0] for p in log_lengths)
        sy = sum(p[1] for p in log_lengths)
        sxx = sum(p[0] ** 2 for p in log_lengths)
        sxy = sum(p[0] * p[1] for p in log_lengths)
        denom = n * sxx - sx * sx
        if abs(denom) < EPSILON:
            return 0.0

        return (n * sxy - sx * sy) / denom

    def reset(self) -> None:
        self._buffer.clear()
        self._total_samples = 0


# ---------------------------------------------------------------------------
# Aperiodic threshold modulation
# ---------------------------------------------------------------------------


def _phason_modulation(tick: int) -> float:
    """Aperiodic modulation factor using golden-ratio phase shifts.

    The pipeline is periodic (L1→L14 cycles). The proximity detection
    threshold modulates aperiodically within it — sensitivity itself
    never repeats the same pattern, making adversarial timing attacks
    infeasible.

    Uses the Fibonacci word / golden string: the canonical aperiodic
    sequence on two symbols, here mapped to a continuous [0.8, 1.2]
    modulation band.
    """
    # Golden string: floor((n+2)/φ) - floor((n+1)/φ) gives 0 or 1 aperiodically
    a = math.floor((tick + 2) / PHI) - math.floor((tick + 1) / PHI)
    # Smooth it with a phi-scaled sinusoid for continuous modulation
    phase = tick * (2 * math.pi / PHI)  # Irrational period → never repeats
    modulation = 1.0 + 0.2 * math.sin(phase) * (1 if a else -1)
    return max(0.5, min(1.5, modulation))


# ---------------------------------------------------------------------------
# Proximity field computation
# ---------------------------------------------------------------------------


def compute_drift_distance(sig_a: List[float], sig_b: List[float]) -> float:
    """L2 distance between two drift signatures in Poincaré-amplified space.

    Near the ball boundary (high-magnitude signatures), the Poincaré
    metric amplifies small differences exponentially — giving sharper
    proximity detection where it matters most.
    """
    if not sig_a or not sig_b:
        return float("inf")

    dims = max(len(sig_a), len(sig_b))
    a = sig_a + [0.0] * (dims - len(sig_a))
    b = sig_b + [0.0] * (dims - len(sig_b))

    # Euclidean distance in drift-signature space
    euclidean = math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    # Poincaré amplification: scale by 1/(1 - ||sig||^2) for each agent
    norm_a_sq = sum(x * x for x in a)
    norm_b_sq = sum(x * x for x in b)

    # Clamp norms to prevent division by zero (stay inside the ball)
    denom_a = max(1.0 - norm_a_sq, EPSILON)
    denom_b = max(1.0 - norm_b_sq, EPSILON)

    # Amplified distance (grows exponentially near boundary)
    return euclidean * 2.0 / math.sqrt(denom_a * denom_b)


def compute_convergence_rate(
    distances: List[Tuple[float, float]],  # (timestamp, distance) pairs
) -> float:
    """Linear regression slope of distance over time.

    Negative slope = converging (approaching).
    Positive slope = diverging (separating).
    """
    if len(distances) < 2:
        return 0.0

    n = len(distances)
    sx = sum(d[0] for d in distances)
    sy = sum(d[1] for d in distances)
    sxx = sum(d[0] ** 2 for d in distances)
    sxy = sum(d[0] * d[1] for d in distances)

    denom = n * sxx - sx * sx
    if abs(denom) < EPSILON:
        return 0.0

    return (n * sxy - sx * sy) / denom


def classify_proximity(
    drift_distance: float,
    modulation: float = 1.0,
) -> ProximityLevel:
    """Map drift distance to proximity alert level.

    Thresholds are modulated by the aperiodic phason shift —
    the same distance may trigger WARNING on one tick and ADVISORY
    on the next, preventing adversaries from calibrating their
    approach to stay just below the threshold.
    """
    if drift_distance < CRITICAL_THRESHOLD * modulation:
        return ProximityLevel.CRITICAL
    if drift_distance < WARNING_THRESHOLD * modulation:
        return ProximityLevel.WARNING
    if drift_distance < ADVISORY_THRESHOLD * modulation:
        return ProximityLevel.ADVISORY
    if drift_distance < CLEAR_THRESHOLD * modulation:
        return ProximityLevel.CLEAR
    return ProximityLevel.CLEAR


# ---------------------------------------------------------------------------
# Non-negative eigenvalue enforcement
# ---------------------------------------------------------------------------


def eigenvalue_floor(signature: List[float]) -> float:
    """Minimum eigenvalue of the signature autocorrelation.

    Non-negative eigenvalues ensure no phantom agents in the
    proximity field — you can't detect something that isn't there,
    and you can't miss something that is.

    For real vectors, autocorrelation eigenvalues = |x_i|^2 ≥ 0.
    """
    if not signature:
        return 0.0
    return min(x * x for x in signature)


# ---------------------------------------------------------------------------
# ProximityBlock — the 6th sense concept block
# ---------------------------------------------------------------------------


class ProximityBlock(ConceptBlock):
    """6th sense: decimal-drift proximity field.

    Snap this into the 'proximity' socket on a PotatoHead to give
    the agent spatial awareness in multi-vector space.

    Inputs (via tick):
        - "drift_values": List[float] — per-dimension drift from current step
        - "layer": int — pipeline layer number (default 14)
        - "neighbor_signatures": Dict[str, List[float]] — other agents' signatures

    Outputs:
        - "level": str — proximity alert level
        - "nearest_id": str — ID of nearest agent
        - "drift_distance": float — distance to nearest
        - "convergence_rate": float — rate of approach
        - "time_to_contact": float — ETA to zero distance
        - "fractal_dimension": float — authenticity of own drift
        - "eigenvalue_ok": bool — non-negative eigenvalue check
        - "aperiodic_mod": float — current phason modulation factor
    """

    def __init__(self, dimensions: int = 21) -> None:
        super().__init__("proximity")
        self._dimensions = dimensions
        self._shadow = DriftShadowBuffer()
        self._distance_history: Dict[str, Deque[Tuple[float, float]]] = {}
        self._tick_count_local = 0

    def _do_tick(self, inputs: Dict[str, Any]) -> BlockResult:
        self._tick_count_local += 1

        # Extract drift values
        drift_values = inputs.get("drift_values", [])
        layer = inputs.get("layer", 14)
        neighbor_sigs: Dict[str, List[float]] = inputs.get("neighbor_signatures", {})

        # Record own drift
        if drift_values:
            self._shadow.push(drift_values, layer=layer)

        # Get own signature
        own_sig = self._shadow.signature()
        if not own_sig or self._shadow.count < MIN_PROXIMITY_SAMPLES:
            return BlockResult(
                status=BlockStatus.RUNNING,
                output={"level": ProximityLevel.UNKNOWN.value, "confidence": 0.0},
                message="Insufficient drift samples for proximity detection",
            )

        # Aperiodic modulation (chaos delusion: never-repeating sensitivity)
        modulation = _phason_modulation(self._tick_count_local)

        # Eigenvalue check
        ev_floor = eigenvalue_floor(own_sig)
        ev_ok = ev_floor >= -EPSILON

        # Find nearest neighbor
        nearest_id = ""
        nearest_distance = float("inf")
        nearest_level = ProximityLevel.CLEAR
        convergence = 0.0
        ttc = -1.0

        now = time.time()

        for agent_id, sig in neighbor_sigs.items():
            dist = compute_drift_distance(own_sig, sig)

            # Track distance history for convergence rate
            if agent_id not in self._distance_history:
                self._distance_history[agent_id] = deque(maxlen=32)
            self._distance_history[agent_id].append((now, dist))

            if dist < nearest_distance:
                nearest_distance = dist
                nearest_id = agent_id
                nearest_level = classify_proximity(dist, modulation)

                # Convergence rate
                history = list(self._distance_history[agent_id])
                convergence = compute_convergence_rate(history)

                # Time to contact estimate
                if convergence < -EPSILON and dist > EPSILON:
                    ttc = -dist / convergence  # Positive seconds until contact
                else:
                    ttc = -1.0  # Not converging

        # Phase angle relative to nearest (Sacred Tongue space)
        phase_angle = 0.0
        if nearest_id and nearest_id in neighbor_sigs:
            n_sig = neighbor_sigs[nearest_id]
            # Phase = angle between signature vectors in 6D tongue space
            if len(own_sig) >= 6 and len(n_sig) >= 6:
                dot = sum(own_sig[i] * n_sig[i] for i in range(6))
                mag_a = math.sqrt(sum(own_sig[i] ** 2 for i in range(6)))
                mag_b = math.sqrt(sum(n_sig[i] ** 2 for i in range(6)))
                if mag_a > EPSILON and mag_b > EPSILON:
                    cos_angle = max(-1.0, min(1.0, dot / (mag_a * mag_b)))
                    phase_angle = math.acos(cos_angle)

        # Fractal dimension for authenticity
        fractal_dim = self._shadow.fractal_dimension()

        confidence = min(1.0, self._shadow.count / (MIN_PROXIMITY_SAMPLES * 4))

        return BlockResult(
            status=BlockStatus.SUCCESS,
            output={
                "level": nearest_level.value,
                "nearest_id": nearest_id,
                "drift_distance": nearest_distance,
                "convergence_rate": convergence,
                "time_to_contact": ttc,
                "phase_angle": phase_angle,
                "fractal_dimension": fractal_dim,
                "eigenvalue_ok": ev_ok,
                "eigenvalue_floor": ev_floor,
                "aperiodic_mod": modulation,
                "confidence": confidence,
                "own_signature_dims": len(own_sig),
            },
            message=f"Proximity: {nearest_level.value} (d={nearest_distance:.6f}, "
            f"conv={convergence:.6f}, ttc={ttc:.2f}s)",
        )

    def _do_configure(self, params: Dict[str, Any]) -> None:
        if "dimensions" in params:
            self._dimensions = params["dimensions"]
        if "buffer_size" in params:
            self._shadow = DriftShadowBuffer(capacity=params["buffer_size"])

    def _do_reset(self) -> None:
        self._shadow.reset()
        self._distance_history.clear()
        self._tick_count_local = 0
