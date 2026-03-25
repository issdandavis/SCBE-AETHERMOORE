"""
Tests for the Entropy Surface Defense Layer (Python reference).

Covers:
- Probing detection: legitimate vs adversarial query patterns
- Leakage budget: consumption, exhaustion, rate tracking
- Semantic nullification: sigmoid gating, signal degradation
- Entropy surface distance: boundary detection
- Stateful tracker: observation window, nullification application
- Anti-extraction property: probing yields diminishing information

@module tests/test_entropy_surface
@layer Layer 12, Layer 13
"""

import math
import random

import pytest

from symphonic_cipher.scbe_aethermoore.entropy_surface import (
    DefensePosture,
    EntropySurfaceConfig,
    EntropySurfaceTracker,
    LeakageBudget,
    NullificationDirective,
    ProbingClassification,
    ProbingSignature,
    QueryObservation,
    assess_entropy_surface,
    compute_coverage_breadth,
    compute_leakage_budget,
    compute_nullification,
    compute_repetition_score,
    detect_probing,
    detect_temporal_regularity,
    estimate_response_mi,
    shannon_entropy,
    sigmoid_gate,
    surface_distance,
)

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def make_obs(position, timestamp, response_mi=1.0):
    return QueryObservation(position=position, timestamp=timestamp, response_mi=response_mi)


def random_ball_point(max_norm=0.5):
    v = [random.uniform(-1, 1) for _ in range(6)]
    n = math.sqrt(sum(x * x for x in v))
    if n < 1e-10:
        return (0.1, 0.0, 0.0, 0.0, 0.0, 0.0)
    r = random.uniform(0, max_norm)
    return tuple(x / n * r for x in v)


# ═══════════════════════════════════════════════════════════════
# Shannon Entropy
# ═══════════════════════════════════════════════════════════════


class TestShannonEntropy:
    def test_uniform_distribution(self):
        assert abs(shannon_entropy([10, 10, 10, 10]) - 1.0) < 0.01

    def test_single_element(self):
        assert shannon_entropy([100]) == 0.0

    def test_empty(self):
        assert shannon_entropy([]) == 0.0

    def test_concentrated(self):
        assert shannon_entropy([100, 1, 1, 1]) < 0.5

    def test_bounded(self):
        for _ in range(20):
            counts = [random.randint(0, 50) for _ in range(10)]
            e = shannon_entropy(counts)
            assert 0.0 <= e <= 1.0


# ═══════════════════════════════════════════════════════════════
# Temporal Regularity
# ═══════════════════════════════════════════════════════════════


class TestTemporalRegularity:
    def test_regular_timing(self):
        ts = [1000 + i * 100 for i in range(20)]
        assert detect_temporal_regularity(ts) > 0.7

    def test_irregular_timing(self):
        ts = [1000]
        for i in range(1, 20):
            ts.append(ts[-1] + 5000 + random.uniform(-4000, 4000))
        assert detect_temporal_regularity(ts, 50) < 0.7

    def test_insufficient_data(self):
        assert detect_temporal_regularity([1000, 2000]) == 0.0

    def test_identical_timestamps(self):
        assert detect_temporal_regularity([1000, 1000, 1000, 1000]) == 1.0


# ═══════════════════════════════════════════════════════════════
# Coverage Breadth
# ═══════════════════════════════════════════════════════════════


class TestCoverageBreadth:
    def test_empty(self):
        assert compute_coverage_breadth([]) == 0.0

    def test_clustered(self):
        positions = [(0.1, 0.1, 0.1, 0.1, 0.1, 0.1)] * 20
        assert compute_coverage_breadth(positions) < 0.01

    def test_spread(self):
        positions = [random_ball_point(0.9) for _ in range(50)]
        assert compute_coverage_breadth(positions) > 0


# ═══════════════════════════════════════════════════════════════
# Repetition Score
# ═══════════════════════════════════════════════════════════════


class TestRepetitionScore:
    def test_insufficient_data(self):
        assert compute_repetition_score([(0, 0, 0, 0, 0, 0)]) == 0.0

    def test_identical_positions(self):
        positions = [(0.1, 0.2, 0.3, 0.1, 0.2, 0.3)] * 5
        assert compute_repetition_score(positions, 0.1) == 1.0

    def test_diverse_positions(self):
        positions = [
            (0.1, 0, 0, 0, 0, 0),
            (0, 0.5, 0, 0, 0, 0),
            (-0.3, 0, 0.4, 0, 0, 0),
            (0, 0, 0, 0.6, 0, 0),
            (0, 0, 0, 0, -0.4, 0.2),
        ]
        assert compute_repetition_score(positions, 0.1) == 0.0


# ═══════════════════════════════════════════════════════════════
# Probing Detection
# ═══════════════════════════════════════════════════════════════


class TestProbingDetection:
    def test_sparse_queries_legitimate(self):
        obs = [make_obs(ORIGIN, 1000)]
        result = detect_probing(obs)
        assert result.classification == ProbingClassification.LEGITIMATE
        assert result.confidence == 0.0

    def test_repetitive_probing(self):
        obs = [make_obs((0.3, 0.3, 0, 0, 0, 0), i * 100, 1.0) for i in range(20)]
        result = detect_probing(obs)
        assert result.repetition_score == 1.0
        assert result.confidence > 0.3

    def test_natural_usage(self):
        ts = [1000]
        for i in range(1, 15):
            ts.append(ts[-1] + 5000 + random.uniform(-2000, 2000))
        obs = [make_obs(random_ball_point(0.3), t, 0.5) for t in ts]
        result = detect_probing(obs)
        assert result.confidence < 0.5


# ═══════════════════════════════════════════════════════════════
# Leakage Budget
# ═══════════════════════════════════════════════════════════════


class TestLeakageBudget:
    def test_full_budget(self):
        result = compute_leakage_budget([])
        assert result.remaining == 128
        assert result.consumed == 0
        assert result.exhausted is False

    def test_consumption(self):
        obs = [make_obs(ORIGIN, i * 100, 5.0) for i in range(10)]
        result = compute_leakage_budget(obs)
        assert result.consumed == 50
        assert result.remaining == 78

    def test_exhaustion(self):
        obs = [make_obs(ORIGIN, i * 100, 3.0) for i in range(50)]
        result = compute_leakage_budget(obs)
        assert result.exhausted is True
        assert result.pressure >= 1.0

    def test_monotonic_consumption(self):
        """A3: Causality — budget consumption is monotonically non-decreasing."""
        obs = []
        prev = 0.0
        for i in range(30):
            obs.append(make_obs(ORIGIN, i * 100, 1.0))
            budget = compute_leakage_budget(obs)
            assert budget.consumed >= prev
            prev = budget.consumed

    def test_windowed(self):
        config = EntropySurfaceConfig(window_size=5)
        obs = [make_obs(ORIGIN, i * 100, 2.0) for i in range(20)]
        result = compute_leakage_budget(obs, config)
        assert result.consumed == 10  # Only last 5


# ═══════════════════════════════════════════════════════════════
# Sigmoid Gate
# ═══════════════════════════════════════════════════════════════


class TestSigmoidGate:
    def test_low_pressure(self):
        assert sigmoid_gate(0, 10) > 0.99

    def test_threshold(self):
        assert abs(sigmoid_gate(0.5, 10, 0.5) - 0.5) < 0.1

    def test_high_pressure(self):
        assert sigmoid_gate(1.0, 10) < 0.01

    def test_monotonically_decreasing(self):
        prev = 1.0
        for p_int in range(21):
            p = p_int / 20
            v = sigmoid_gate(p, 10)
            assert v <= prev + 1e-10
            prev = v


# ═══════════════════════════════════════════════════════════════
# Semantic Nullification
# ═══════════════════════════════════════════════════════════════


class TestNullification:
    def test_nominal(self):
        probing = detect_probing([])
        leakage = compute_leakage_budget([])
        result = compute_nullification(probing, leakage)
        assert result.active is False
        assert result.signal_retention > 0.95
        assert result.reason == "NOMINAL"

    def test_budget_exhausted(self):
        probing = detect_probing([])
        leakage = LeakageBudget(
            total_budget=128, consumed=200, remaining=0,
            current_rate=5, exhausted=True, pressure=1.56,
        )
        result = compute_nullification(probing, leakage)
        assert result.active is True
        assert result.strength > 0.9
        assert result.reason == "BUDGET_EXHAUSTED"

    def test_probing_detected(self):
        probing = ProbingSignature(
            query_entropy=0.2, temporal_regularity=0.9,
            coverage_breadth=0.5, repetition_score=0.8,
            confidence=0.85, classification=ProbingClassification.PROBING,
        )
        leakage = compute_leakage_budget([])
        result = compute_nullification(probing, leakage)
        assert result.active is True
        assert result.strength > 0.5
        assert result.reason == "PROBING_DETECTED"


# ═══════════════════════════════════════════════════════════════
# Surface Distance
# ═══════════════════════════════════════════════════════════════


class TestSurfaceDistance:
    def test_safe_zone(self):
        probing = detect_probing([])
        leakage = compute_leakage_budget([])
        d = surface_distance(probing, leakage)
        assert d < 0

    def test_nullified_zone(self):
        probing = ProbingSignature(
            query_entropy=0.2, temporal_regularity=0.9,
            coverage_breadth=0.5, repetition_score=0.8,
            confidence=0.85, classification=ProbingClassification.PROBING,
        )
        leakage = compute_leakage_budget([])
        d = surface_distance(probing, leakage)
        assert d > 0


# ═══════════════════════════════════════════════════════════════
# Unified Assessment
# ═══════════════════════════════════════════════════════════════


class TestAssessment:
    def test_transparent_for_empty(self):
        result = assess_entropy_surface([])
        assert result.posture == DefensePosture.TRANSPARENT
        assert result.nullification.active is False

    def test_escalation(self):
        obs = [make_obs(ORIGIN, i * 100, 3.0) for i in range(60)]
        result = assess_entropy_surface(obs)
        assert result.leakage.pressure > 0.5
        assert result.posture != DefensePosture.TRANSPARENT


# ═══════════════════════════════════════════════════════════════
# Stateful Tracker
# ═══════════════════════════════════════════════════════════════


class TestTracker:
    def test_initial_state(self):
        tracker = EntropySurfaceTracker()
        assert tracker.last_assessment is None
        assert tracker.observation_count == 0

    def test_observe(self):
        tracker = EntropySurfaceTracker()
        result = tracker.observe(ORIGIN, 1.0, 1000)
        assert result is not None
        assert tracker.observation_count == 1

    def test_window_trim(self):
        tracker = EntropySurfaceTracker(EntropySurfaceConfig(window_size=5))
        for i in range(20):
            tracker.observe(ORIGIN, 0.1, i * 100)
        assert tracker.observation_count <= 10

    def test_nullify_transparent(self):
        tracker = EntropySurfaceTracker()
        tracker.observe(ORIGIN, 0.001, 1000)
        response = (0.5, 0.3, 0.2, 0.4, 0.1, 0.6)
        assert tracker.nullify(response) == response

    def test_nullify_under_pressure(self):
        tracker = EntropySurfaceTracker()
        for i in range(60):
            tracker.observe(ORIGIN, 5.0, i * 100)
        response = (0.5, 0.3, 0.2, 0.4, 0.1, 0.6)
        nullified = tracker.nullify(response)
        orig_norm = math.sqrt(sum(x * x for x in response))
        null_norm = math.sqrt(sum(x * x for x in nullified))
        assert null_norm < orig_norm

    def test_reset(self):
        tracker = EntropySurfaceTracker()
        tracker.observe(ORIGIN, 1.0, 1000)
        tracker.reset()
        assert tracker.observation_count == 0
        assert tracker.last_assessment is None


# ═══════════════════════════════════════════════════════════════
# Anti-Extraction Property
# ═══════════════════════════════════════════════════════════════


class TestAntiExtraction:
    def test_diminishing_information(self):
        """Probing should yield diminishing information over time."""
        tracker = EntropySurfaceTracker(EntropySurfaceConfig(leakage_budget_bits=50))
        retentions = []
        for i in range(40):
            pos = (math.sin(i * 0.5) * 0.3, math.cos(i * 0.5) * 0.3, 0, 0, 0, 0)
            assessment = tracker.observe(pos, 2.0, i * 100)
            retentions.append(assessment.nullification.signal_retention)

        first_quarter = sum(retentions[:10]) / 10
        last_quarter = sum(retentions[-10:]) / 10
        assert last_quarter < first_quarter

    def test_legitimate_use_high_retention(self):
        """Legitimate sparse use should maintain high signal retention."""
        tracker = EntropySurfaceTracker()
        t = 1000.0
        for i in range(10):
            pos = random_ball_point(0.3)
            t += 5000 + random.uniform(0, 10000)  # 5-15s apart (irregular)
            assessment = tracker.observe(pos, 0.1, t)
            assert assessment.nullification.signal_retention > 0.9
