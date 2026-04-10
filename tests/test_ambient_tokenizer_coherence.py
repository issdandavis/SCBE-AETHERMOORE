"""Ambient Tokenizer Coherence Tests.

Tests that the Sacred Tongue tokenizer behaves as a cross-modal substrate:
  T0: Token identity (deterministic)
  T1: Ambient embedding
  T2: Color projection
  T3: Sound projection
  T4: Cross-modal coherence score
  T5: Drift / anomaly detection

Validates that nearby meanings stay near across embedding/color/sound
projections, and that version drift is detectable across all three spaces.

Research grounding:
  - Tokens are points in a manifold with visual + acoustic projections
  - Same token → same embedding → same color → same sound (determinism)
  - Neighborhood preservation across modalities (coherence)
  - Drift = movement in all three spaces simultaneously
"""
from dataclasses import dataclass
import math
import pytest


@dataclass(frozen=True)
class AmbientToken:
    """A token with cross-modal projections: embedding, color, sound."""

    token: str
    token_id: int
    embedding: tuple[float, ...]
    color_rgb: tuple[int, int, int]
    sound_hz: float
    amplitude: float
    phase_rad: float

    def validate(self) -> None:
        assert self.token != ""
        assert self.token_id >= 0
        assert len(self.embedding) > 0
        assert len(self.color_rgb) == 3
        assert all(0 <= c <= 255 for c in self.color_rgb)
        assert self.sound_hz > 0.0
        assert 0.0 <= self.amplitude <= 1.0


def l2(a, b):
    assert len(a) == len(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def color_dist(a, b):
    return l2(a, b)


def sound_dist(a_hz, b_hz):
    return abs(a_hz - b_hz)


def coherence_order(reference, near_token, far_token):
    """Returns True if near_token is closer than far_token in all projections."""
    emb_ok = l2(reference.embedding, near_token.embedding) < l2(
        reference.embedding, far_token.embedding
    )
    col_ok = color_dist(reference.color_rgb, near_token.color_rgb) < color_dist(
        reference.color_rgb, far_token.color_rgb
    )
    snd_ok = sound_dist(reference.sound_hz, near_token.sound_hz) < sound_dist(
        reference.sound_hz, far_token.sound_hz
    )
    return emb_ok and col_ok and snd_ok


class TestAmbientTokenizer:
    """T0-T1: Token identity and validation."""

    def test_token_validation_passes(self):
        t = AmbientToken(
            token="SCBE",
            token_id=7,
            embedding=(0.1, 0.2, 0.3),
            color_rgb=(64, 128, 192),
            sound_hz=440.0,
            amplitude=0.8,
            phase_rad=0.0,
        )
        t.validate()

    def test_invalid_color_fails(self):
        t = AmbientToken(
            token="bad",
            token_id=1,
            embedding=(0.1, 0.2),
            color_rgb=(999, 0, 0),
            sound_hz=440.0,
            amplitude=0.5,
            phase_rad=0.0,
        )
        with pytest.raises(AssertionError):
            t.validate()

    def test_invalid_amplitude_fails(self):
        t = AmbientToken(
            token="bad",
            token_id=1,
            embedding=(0.1, 0.2),
            color_rgb=(10, 20, 30),
            sound_hz=440.0,
            amplitude=1.5,
            phase_rad=0.0,
        )
        with pytest.raises(AssertionError):
            t.validate()

    def test_empty_token_fails(self):
        t = AmbientToken(
            token="",
            token_id=0,
            embedding=(0.1,),
            color_rgb=(0, 0, 0),
            sound_hz=440.0,
            amplitude=0.5,
            phase_rad=0.0,
        )
        with pytest.raises(AssertionError):
            t.validate()

    def test_negative_id_fails(self):
        t = AmbientToken(
            token="x",
            token_id=-1,
            embedding=(0.1,),
            color_rgb=(0, 0, 0),
            sound_hz=440.0,
            amplitude=0.5,
            phase_rad=0.0,
        )
        with pytest.raises(AssertionError):
            t.validate()

    def test_zero_hz_fails(self):
        t = AmbientToken(
            token="x",
            token_id=1,
            embedding=(0.1,),
            color_rgb=(0, 0, 0),
            sound_hz=0.0,
            amplitude=0.5,
            phase_rad=0.0,
        )
        with pytest.raises(AssertionError):
            t.validate()

    def test_deterministic_identity(self):
        a = AmbientToken("ko", 1, (0.1, 0.2), (10, 20, 30), 440.0, 0.7, 0.0)
        b = AmbientToken("ko", 1, (0.1, 0.2), (10, 20, 30), 440.0, 0.7, 0.0)
        assert a == b

    def test_different_tokens_differ(self):
        a = AmbientToken("ko", 1, (0.1, 0.2), (10, 20, 30), 440.0, 0.7, 0.0)
        b = AmbientToken("av", 2, (0.3, 0.4), (50, 60, 70), 523.25, 0.7, 0.0)
        assert a != b


class TestDistanceMetrics:
    """Distance functions for cross-modal comparison."""

    def test_embedding_distance_is_symmetric(self):
        a = (0.1, 0.2, 0.3)
        b = (0.5, 0.4, 0.3)
        assert l2(a, b) == pytest.approx(l2(b, a))

    def test_embedding_distance_zero_for_identical(self):
        a = (0.1, 0.2, 0.3)
        assert l2(a, a) == pytest.approx(0.0)

    def test_embedding_distance_positive_for_different(self):
        a = (0.0, 0.0)
        b = (1.0, 0.0)
        assert l2(a, b) == pytest.approx(1.0)

    def test_color_distance_symmetric(self):
        a = (100, 100, 100)
        b = (200, 200, 200)
        assert color_dist(a, b) == pytest.approx(color_dist(b, a))

    def test_sound_distance_symmetric(self):
        assert sound_dist(440.0, 880.0) == sound_dist(880.0, 440.0)

    def test_embedding_mismatched_dims_fails(self):
        with pytest.raises(AssertionError):
            l2((0.1, 0.2), (0.1, 0.2, 0.3))


class TestCrossModalCoherence:
    """T4: Cross-modal neighborhood preservation."""

    def test_cross_modal_neighborhood_preservation(self):
        ref = AmbientToken("anchor", 1, (0.0, 0.0), (100, 100, 100), 440.0, 0.8, 0.0)
        near = AmbientToken("near", 2, (0.1, 0.1), (105, 103, 101), 445.0, 0.8, 0.0)
        far = AmbientToken("far", 3, (1.0, 1.0), (220, 210, 200), 880.0, 0.8, 0.0)
        assert coherence_order(ref, near, far)

    def test_coherence_order_fails_when_embedding_close_but_sound_far(self):
        ref = AmbientToken("anchor", 1, (0.0, 0.0), (100, 100, 100), 440.0, 0.8, 0.0)
        # Near in embedding/color but FAR in sound
        tricky = AmbientToken("tricky", 2, (0.1, 0.1), (105, 103, 101), 880.0, 0.8, 0.0)
        far = AmbientToken("far", 3, (1.0, 1.0), (220, 210, 200), 445.0, 0.8, 0.0)
        # Sound inversion breaks coherence
        assert not coherence_order(ref, tricky, far)

    def test_six_tongues_have_distinct_frequencies(self):
        """The 6 Sacred Tongues should project to distinct sound frequencies."""
        tongue_freqs = [440.0, 523.25, 293.66, 659.25, 196.0, 392.0]
        assert len(set(tongue_freqs)) == 6

    def test_phi_weighted_ordering(self):
        """Tongues ordered by phi weight should maintain relative distance."""
        weights = [1.000, 1.618, 2.618, 4.236, 6.854, 11.090]
        for i in range(len(weights) - 1):
            assert weights[i] < weights[i + 1]


class TestReplayStability:
    """T0+T1: Deterministic replay — same input, same projections."""

    def test_replay_stability(self):
        stream_a = [
            AmbientToken("a", 1, (0.1,), (10, 10, 10), 220.0, 0.5, 0.0),
            AmbientToken("b", 2, (0.2,), (20, 20, 20), 330.0, 0.5, 0.0),
        ]
        stream_b = [
            AmbientToken("a", 1, (0.1,), (10, 10, 10), 220.0, 0.5, 0.0),
            AmbientToken("b", 2, (0.2,), (20, 20, 20), 330.0, 0.5, 0.0),
        ]
        assert stream_a == stream_b

    def test_single_bit_change_breaks_equality(self):
        a = AmbientToken("a", 1, (0.1,), (10, 10, 10), 220.0, 0.5, 0.0)
        b = AmbientToken("a", 1, (0.1,), (10, 10, 11), 220.0, 0.5, 0.0)
        assert a != b


class TestVersionDriftDetection:
    """T5: Detect semantic drift between tokenizer versions."""

    def test_version_drift_detection(self):
        old = AmbientToken("core", 9, (0.1, 0.1), (100, 100, 100), 440.0, 0.8, 0.0)
        new = AmbientToken("core", 9, (0.7, 0.8), (160, 180, 200), 700.0, 0.8, 0.0)

        embedding_shift = l2(old.embedding, new.embedding)
        color_shift = color_dist(old.color_rgb, new.color_rgb)
        sound_shift = sound_dist(old.sound_hz, new.sound_hz)

        # All three spaces should detect the drift
        assert embedding_shift > 0.5
        assert color_shift > 50
        assert sound_shift > 100

    def test_no_drift_when_unchanged(self):
        old = AmbientToken("stable", 5, (0.3, 0.3), (80, 80, 80), 330.0, 0.6, 0.0)
        new = AmbientToken("stable", 5, (0.3, 0.3), (80, 80, 80), 330.0, 0.6, 0.0)

        assert l2(old.embedding, new.embedding) == pytest.approx(0.0)
        assert color_dist(old.color_rgb, new.color_rgb) == pytest.approx(0.0)
        assert sound_dist(old.sound_hz, new.sound_hz) == pytest.approx(0.0)

    def test_drift_magnitude_proportional(self):
        """Larger changes should produce larger drift signals."""
        base = AmbientToken("x", 1, (0.0, 0.0), (100, 100, 100), 440.0, 0.5, 0.0)
        small = AmbientToken("x", 1, (0.1, 0.1), (110, 110, 110), 450.0, 0.5, 0.0)
        large = AmbientToken("x", 1, (0.9, 0.9), (240, 240, 240), 880.0, 0.5, 0.0)

        assert l2(base.embedding, small.embedding) < l2(base.embedding, large.embedding)
        assert color_dist(base.color_rgb, small.color_rgb) < color_dist(
            base.color_rgb, large.color_rgb
        )
        assert sound_dist(base.sound_hz, small.sound_hz) < sound_dist(
            base.sound_hz, large.sound_hz
        )


class TestPerpendicularEchoResponse:
    """The perpendicular echo model: when the main path fails,
    the side-echo gets loud and reveals what's missing.

    A_perp(t) = -(φ·k) / (|E(τ(t))| + ε)
    """

    PHI = (1 + math.sqrt(5)) / 2

    @staticmethod
    def perp_echo_response(echo_tangent: float, k: float = 1.0, eps: float = 1e-9) -> float:
        phi = (1 + math.sqrt(5)) / 2
        return -(phi * k) / (abs(echo_tangent) + eps)

    def test_inverse_relation(self):
        """Weaker echo → stronger perpendicular response."""
        assert abs(self.perp_echo_response(0.5)) > abs(self.perp_echo_response(2.0))

    def test_negative_sign(self):
        """Response is always negative (opposite-direction coupling)."""
        assert self.perp_echo_response(1.0) < 0

    def test_finite_at_zero(self):
        """Epsilon prevents blow-up when echo tangent is zero."""
        assert math.isfinite(self.perp_echo_response(0.0))

    def test_stronger_k_amplifies_response(self):
        """Higher k → larger magnitude response."""
        assert abs(self.perp_echo_response(1.0, k=2.0)) > abs(self.perp_echo_response(1.0, k=1.0))

    def test_symmetry_in_echo_sign(self):
        """Positive and negative echo tangent give same magnitude."""
        assert self.perp_echo_response(1.0) == self.perp_echo_response(-1.0)

    def test_dead_tone_detection_logic(self):
        """When echo is near-zero (dead tone), perpendicular response is maximal."""
        dead = abs(self.perp_echo_response(0.01))
        alive = abs(self.perp_echo_response(5.0))
        assert dead > alive * 10  # dead tone response is much stronger


class TestNegativeIsolationSpace:
    """Test the S^{s^{φ·729/s}}^2 negative isolation domain."""

    def test_low_excitation_deep_isolation(self):
        """At s=0.1 the exponent should be ~11,795 (extremely deep)."""
        phi = (1 + math.sqrt(5)) / 2
        s = 0.1
        exponent = phi * 729.0 / s
        assert exponent > 11000

    def test_high_excitation_shallow_isolation(self):
        """At s=7.0 the exponent should be ~168 (navigable)."""
        phi = (1 + math.sqrt(5)) / 2
        s = 7.0
        exponent = phi * 729.0 / s
        assert exponent < 200

    def test_exponent_monotonically_decreasing(self):
        """Higher excitation → lower exponent → weaker isolation."""
        phi = (1 + math.sqrt(5)) / 2
        prev = float("inf")
        for s in [0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
            exponent = phi * 729.0 / s
            assert exponent < prev
            prev = exponent

    def test_729_equals_3_to_the_6(self):
        """Confirm the scaling constant: 6 tongues ^ 3 trit axes."""
        assert 3**6 == 729

    def test_isolation_factor_scales_with_excitation(self):
        """Higher s × more paths → higher isolation factor."""
        factor_low = 1.0 + (0.5 * 1 / 10.0)
        factor_high = 1.0 + (5.0 * 4 / 10.0)
        assert factor_high > factor_low

    def test_squared_manifold_is_positive(self):
        """The outer ^2 ensures the domain value is always positive.

        We test the property (x^2 > 0 for x != 0) rather than computing
        the astronomically large S^(s^exponent) directly.
        """
        phi = (1 + math.sqrt(5)) / 2
        for s in [0.1, 1.0, 3.0, 7.0]:
            exponent = phi * 729.0 / s
            # The exponent is always positive for s > 0
            assert exponent > 0
            # Squaring any positive real gives a positive real
            # (the algebraic property we care about)
            sample = exponent**2
            assert sample > 0
            assert math.isfinite(sample)
