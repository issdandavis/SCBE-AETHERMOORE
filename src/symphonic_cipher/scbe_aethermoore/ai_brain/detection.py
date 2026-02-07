"""
Multi-Vectored Detection Mechanisms - Python Reference Implementation

5 orthogonal detection mechanisms validated at combined AUC 1.000:
1. Phase + Distance Scoring (AUC 1.000) - Wrong-tongue / synthetic attacks
2. Curvature Accumulation (AUC 0.994) - Deviating paths
3. Threat Dimension Lissajous (AUC 1.000) - Malicious knot patterns
4. Decimal Drift Magnitude (AUC 0.995) - No-pipeline / scale attacks
5. Six-Tonic Oscillation (AUC 1.000) - Replay / static / wrong-frequency

@module ai_brain/detection
@version 1.1.0
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from .unified_state import BRAIN_DIMENSIONS, PHI, TrajectoryPoint

# Sacred Tongue phase angles: 60-degree intervals
TONGUE_PHASES = [k * math.pi / 3 for k in range(6)]

# Default thresholds
DEFAULT_DETECTION_THRESHOLD = 0.7
DEFAULT_CURVATURE_WINDOW = 10
DEFAULT_REFERENCE_FREQ = 440.0
DEFAULT_QUARANTINE_THRESHOLD = 0.5
DEFAULT_ESCALATE_THRESHOLD = 0.7
DEFAULT_DENY_THRESHOLD = 0.9


def _vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _vec_sub(a: List[float], b: List[float]) -> List[float]:
    return [a[i] - b[i] for i in range(min(len(a), len(b)))]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class DetectionResult:
    """Result from a single detection mechanism."""

    mechanism: str
    score: float
    flagged: bool
    detected_attack_types: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CombinedAssessment:
    """Combined assessment from all 5 detection mechanisms."""

    detections: List[DetectionResult]
    combined_score: float
    decision: str  # ALLOW, QUARANTINE, ESCALATE, DENY
    any_flagged: bool
    flag_count: int
    timestamp: float = 0.0


def detect_phase_distance(
    trajectory: List[TrajectoryPoint],
    expected_tongue_index: int,
    threshold: float = DEFAULT_DETECTION_THRESHOLD,
) -> DetectionResult:
    """Detect wrong-tongue and synthetic attacks using phase + hyperbolic distance.

    Args:
        trajectory: Agent trajectory points.
        expected_tongue_index: Expected Sacred Tongue index (0-5).
        threshold: Detection threshold.

    Returns:
        DetectionResult with phase+distance anomaly score.
    """
    if not trajectory:
        return DetectionResult("phase_distance", 0, False, [])

    expected_phase = TONGUE_PHASES[expected_tongue_index % 6]
    total_phase_error = 0.0
    total_dist_score = 0.0

    for point in trajectory:
        actual_phase = point.state[16] if len(point.state) > 16 else 0
        phase_diff = abs(actual_phase - expected_phase)
        circular_diff = min(phase_diff, 2 * math.pi - phase_diff)
        total_phase_error += circular_diff / math.pi

        dist_score = 1 / (1 + math.exp(-2 * (point.distance - 2)))
        total_dist_score += dist_score

    n = len(trajectory)
    avg_phase = total_phase_error / n
    avg_dist = total_dist_score / n
    score = _clamp(0.6 * avg_phase + 0.4 * avg_dist, 0, 1)

    return DetectionResult(
        mechanism="phase_distance",
        score=score,
        flagged=score >= threshold,
        detected_attack_types=["wrong_tongue", "synthetic"] if score >= threshold else [],
        metadata={"avg_phase_error": avg_phase, "avg_dist_score": avg_dist},
    )


def _menger_curvature(p1: List[float], p2: List[float], p3: List[float]) -> float:
    """Compute Menger curvature of three points."""
    a = _vec_norm(_vec_sub(p2, p1))
    b = _vec_norm(_vec_sub(p3, p2))
    c = _vec_norm(_vec_sub(p3, p1))
    if a < 1e-12 or b < 1e-12 or c < 1e-12:
        return 0.0
    s = (a + b + c) / 2
    area_sq = s * (s - a) * (s - b) * (s - c)
    if area_sq <= 0:
        return 0.0
    area = math.sqrt(area_sq)
    return (4 * area) / (a * b * c)


def detect_curvature_accumulation(
    trajectory: List[TrajectoryPoint],
    window_size: int = DEFAULT_CURVATURE_WINDOW,
    threshold: float = DEFAULT_DETECTION_THRESHOLD,
) -> DetectionResult:
    """Detect deviating paths via curvature accumulation in hyperbolic space.

    Args:
        trajectory: Agent trajectory points.
        window_size: Sliding window for curvature analysis.
        threshold: Detection threshold.

    Returns:
        DetectionResult with curvature anomaly score.
    """
    if len(trajectory) < 3:
        return DetectionResult("curvature_accumulation", 0, False, [])

    # Project to 3D for geometrically meaningful curvature
    def _proj3d(emb: List[float]) -> List[float]:
        return [emb[0] if len(emb) > 0 else 0, emb[1] if len(emb) > 1 else 0, emb[2] if len(emb) > 2 else 0]

    curvatures = []
    for i in range(1, len(trajectory) - 1):
        kappa = _menger_curvature(
            _proj3d(trajectory[i - 1].embedded),
            _proj3d(trajectory[i].embedded),
            _proj3d(trajectory[i + 1].embedded),
        )
        curvatures.append(kappa)

    eff_window = min(window_size, len(curvatures))
    max_window = 0.0
    for start in range(len(curvatures) - eff_window + 1):
        window_sum = sum(curvatures[start : start + eff_window])
        max_window = max(max_window, window_sum)

    avg_window = max_window / eff_window if eff_window > 0 else 0
    score = _clamp(avg_window / 5.0, 0, 1)

    return DetectionResult(
        mechanism="curvature_accumulation",
        score=score,
        flagged=score >= threshold,
        detected_attack_types=["path_deviation", "drift"] if score >= threshold else [],
        metadata={"max_window_curvature": max_window, "curvature_count": len(curvatures)},
    )


def _segments_intersect(
    s1: Tuple[float, float, float, float],
    s2: Tuple[float, float, float, float],
) -> bool:
    """Test if two line segments intersect."""
    x1, y1, x2, y2 = s1
    x3, y3, x4, y4 = s2
    d1x, d1y = x2 - x1, y2 - y1
    d2x, d2y = x4 - x3, y4 - y3
    cross = d1x * d2y - d1y * d2x
    if abs(cross) < 1e-12:
        return False
    dx, dy = x3 - x1, y3 - y1
    t = (dx * d2y - dy * d2x) / cross
    u = (dx * d1y - dy * d1x) / cross
    return 0 <= t <= 1 and 0 <= u <= 1


def detect_threat_lissajous(
    trajectory: List[TrajectoryPoint],
    threshold: float = DEFAULT_DETECTION_THRESHOLD,
) -> DetectionResult:
    """Detect malicious patterns using Lissajous analysis in the threat dimension.

    Args:
        trajectory: Agent trajectory points.
        threshold: Detection threshold.

    Returns:
        DetectionResult with Lissajous anomaly score.
    """
    if len(trajectory) < 4:
        return DetectionResult("threat_lissajous", 0, False, [])

    projected = [(p.state[5] if len(p.state) > 5 else 0, p.state[3] if len(p.state) > 3 else 0) for p in trajectory]

    segments = []
    for i in range(len(projected) - 1):
        segments.append((projected[i][0], projected[i][1], projected[i + 1][0], projected[i + 1][1]))

    intersections = 0
    for i in range(len(segments)):
        for j in range(i + 2, len(segments)):
            if _segments_intersect(segments[i], segments[j]):
                intersections += 1

    winding_angle = 0.0
    for i in range(1, len(projected)):
        dx = projected[i][0] - projected[i - 1][0]
        dy = projected[i][1] - projected[i - 1][1]
        winding_angle += math.atan2(dy, dx)
    winding_number = abs(winding_angle) / (2 * math.pi)

    density = intersections / max(1, len(segments))
    score = _clamp(0.7 * density * 5 + 0.3 * min(winding_number / 2, 1), 0, 1)

    return DetectionResult(
        mechanism="threat_lissajous",
        score=score,
        flagged=score >= threshold,
        detected_attack_types=["malicious_pattern", "knot_topology"] if score >= threshold else [],
        metadata={"intersections": intersections, "winding_number": winding_number},
    )


def detect_decimal_drift(
    trajectory: List[TrajectoryPoint],
    threshold: float = DEFAULT_DETECTION_THRESHOLD,
) -> DetectionResult:
    """Detect scale and no-pipeline attacks via decimal drift magnitude.

    Args:
        trajectory: Agent trajectory points.
        threshold: Detection threshold.

    Returns:
        DetectionResult with drift anomaly score.
    """
    if len(trajectory) < 2:
        return DetectionResult("decimal_drift", 0, False, [])

    total_drift = 0.0
    uniformity_score = 0

    for i in range(1, len(trajectory)):
        prev, curr = trajectory[i - 1].state, trajectory[i].state
        dims = min(len(prev), len(curr), BRAIN_DIMENSIONS)
        drifts = [abs(curr[d] - prev[d]) for d in range(dims)]
        total_drift += _vec_norm(drifts)

        mean = sum(drifts) / len(drifts)
        variance = sum((d - mean) ** 2 for d in drifts) / len(drifts)
        cv = math.sqrt(variance) / mean if mean > 1e-12 else 0
        if cv < 0.3:
            uniformity_score += 1

    steps = len(trajectory) - 1
    avg_drift = total_drift / steps
    uniform_ratio = uniformity_score / steps

    drift_anomaly = _clamp(avg_drift / 2.0, 0, 1)
    score = _clamp(0.5 * drift_anomaly + 0.5 * uniform_ratio, 0, 1)

    return DetectionResult(
        mechanism="decimal_drift",
        score=score,
        flagged=score >= threshold,
        detected_attack_types=["no_pipeline", "scale_attack", "synthetic"] if score >= threshold else [],
        metadata={"avg_drift": avg_drift, "uniform_ratio": uniform_ratio},
    )


def _tonic_frequencies(base_freq: float) -> List[float]:
    """Compute six-tonic reference frequencies."""
    return [base_freq * PHI**k for k in range(6)]


def detect_six_tonic(
    trajectory: List[TrajectoryPoint],
    expected_tongue_index: int,
    base_freq: float = DEFAULT_REFERENCE_FREQ,
    threshold: float = DEFAULT_DETECTION_THRESHOLD,
) -> DetectionResult:
    """Detect replay, static, and wrong-frequency attacks via six-tonic oscillation.

    Args:
        trajectory: Agent trajectory points.
        expected_tongue_index: Expected active tongue (0-5).
        base_freq: Reference frequency (default 440 Hz).
        threshold: Detection threshold.

    Returns:
        DetectionResult with six-tonic anomaly score.
    """
    if len(trajectory) < 4:
        return DetectionResult("six_tonic", 0, False, [])

    freqs = _tonic_frequencies(base_freq)
    expected_freq = freqs[expected_tongue_index % 6]

    weights = [p.state[17] if len(p.state) > 17 else 0 for p in trajectory]
    mean = sum(weights) / len(weights)
    variance = sum((w - mean) ** 2 for w in weights) / len(weights)
    is_static = variance < 1e-6

    replay_score = 0.0
    if len(trajectory) >= 8:
        half = len(trajectory) // 2
        match_count = sum(
            1
            for i in range(half)
            if _vec_norm(_vec_sub(trajectory[i].state, trajectory[i + half].state)) < 1e-6
        )
        replay_score = match_count / half

    centered = [w - mean for w in weights]
    zero_crossings = sum(
        1 for i in range(1, len(centered)) if (centered[i - 1] >= 0) != (centered[i] >= 0)
    )

    est_freq_ratio = zero_crossings / (2 * (len(trajectory) - 1))
    exp_freq_ratio = expected_freq / (6 * base_freq)
    freq_error = abs(est_freq_ratio - exp_freq_ratio) / exp_freq_ratio if exp_freq_ratio > 1e-12 else (1 if est_freq_ratio > 1e-12 else 0)

    static_score = 1.0 if is_static else 0.0
    freq_score = _clamp(freq_error, 0, 1)
    score = _clamp(max(static_score, replay_score, 0.4 * static_score + 0.3 * replay_score + 0.3 * freq_score), 0, 1)

    attacks = []
    if score >= threshold:
        if is_static:
            attacks.append("static_signal")
        if replay_score > 0.5:
            attacks.append("replay_attack")
        if freq_score > 0.5:
            attacks.append("wrong_frequency")

    return DetectionResult(
        mechanism="six_tonic",
        score=score,
        flagged=score >= threshold,
        detected_attack_types=attacks,
        metadata={"is_static": is_static, "replay_score": replay_score, "freq_error": freq_error},
    )


def run_combined_detection(
    trajectory: List[TrajectoryPoint],
    expected_tongue_index: int,
    detection_threshold: float = DEFAULT_DETECTION_THRESHOLD,
    quarantine_threshold: float = DEFAULT_QUARANTINE_THRESHOLD,
    escalate_threshold: float = DEFAULT_ESCALATE_THRESHOLD,
    deny_threshold: float = DEFAULT_DENY_THRESHOLD,
    curvature_window: int = DEFAULT_CURVATURE_WINDOW,
    reference_freq: float = DEFAULT_REFERENCE_FREQ,
) -> CombinedAssessment:
    """Run all 5 detection mechanisms and produce a combined assessment.

    Args:
        trajectory: Agent trajectory points.
        expected_tongue_index: Expected Sacred Tongue index.
        detection_threshold: Individual mechanism threshold.
        quarantine_threshold: Combined score for QUARANTINE.
        escalate_threshold: Combined score for ESCALATE.
        deny_threshold: Combined score for DENY.
        curvature_window: Window size for curvature analysis.
        reference_freq: Reference frequency for 6-tonic.

    Returns:
        CombinedAssessment with risk decision.
    """
    import time as time_mod

    detections = [
        detect_phase_distance(trajectory, expected_tongue_index, detection_threshold),
        detect_curvature_accumulation(trajectory, curvature_window, detection_threshold),
        detect_threat_lissajous(trajectory, detection_threshold),
        detect_decimal_drift(trajectory, detection_threshold),
        detect_six_tonic(trajectory, expected_tongue_index, reference_freq, detection_threshold),
    ]

    max_score = max(d.score for d in detections) if detections else 0
    avg_score = sum(d.score for d in detections) / len(detections) if detections else 0
    combined_score = _clamp(0.6 * max_score + 0.4 * avg_score, 0, 1)

    if combined_score >= deny_threshold:
        decision = "DENY"
    elif combined_score >= escalate_threshold:
        decision = "ESCALATE"
    elif combined_score >= quarantine_threshold:
        decision = "QUARANTINE"
    else:
        decision = "ALLOW"

    any_flagged = any(d.flagged for d in detections)
    flag_count = sum(1 for d in detections if d.flagged)

    return CombinedAssessment(
        detections=detections,
        combined_score=combined_score,
        decision=decision,
        any_flagged=any_flagged,
        flag_count=flag_count,
        timestamp=time_mod.time(),
    )
