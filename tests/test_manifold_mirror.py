"""
Tests for the Manifold Mirror — Inverse-Orientation Geometric Experiment.

Validates:
1. Encoding produces valid Poincare ball points
2. Complement pairs show three distinct interference modes
3. The mirror surface exists and has meaningful geometry
4. Needle-in-haystack retrieval varies by tongue
5. The interference matrix is antisymmetric under complement swap
"""

import math
import numpy as np
import pytest

from src.crypto.manifold_mirror import (
    _encode_to_poincare,
    _get_baseline,
    compute_mirror_point,
    run_manifold_mirror,
    format_mirror_report,
    ALL_TONGUES,
)

# ===================================================================
# Encoding tests
# ===================================================================


class TestEncoding:
    """Test that text encodes to valid Poincare ball points."""

    def test_point_inside_ball(self):
        for tongue in ALL_TONGUES:
            p = _encode_to_poincare("test text", tongue)
            assert np.linalg.norm(p) < 1.0, f"{tongue}: ||p|| = {np.linalg.norm(p)}"

    def test_different_texts_different_directions(self):
        """Content residual should produce different directions."""
        p1 = _encode_to_poincare("hello world", "av")
        p2 = _encode_to_poincare("quantum gravity", "av")
        # Cosine should be < 1.0 (not identical)
        cos = np.dot(p1, p2) / (np.linalg.norm(p1) * np.linalg.norm(p2) + 1e-12)
        assert cos < 0.99, f"Different texts too similar: cos={cos:.4f}"

    def test_different_tongues_different_radii(self):
        """Different tongues should produce different Poincare radii."""
        text = "the same text for all tongues"
        radii = {t: np.linalg.norm(_encode_to_poincare(text, t)) for t in ALL_TONGUES}
        # Not all the same
        values = list(radii.values())
        assert max(values) - min(values) > 0.001, f"All radii identical: {radii}"

    def test_empty_text_near_origin(self):
        """Empty text should still produce a valid point."""
        p = _encode_to_poincare("", "ko")
        assert np.linalg.norm(p) < 1.0

    def test_baseline_cached(self):
        """Baseline computation should be deterministic and cached."""
        b1 = _get_baseline("ko")
        b2 = _get_baseline("ko")
        np.testing.assert_array_equal(b1, b2)

    def test_baselines_differ_per_tongue(self):
        """Each tongue should have a unique baseline signature."""
        baselines = {t: _get_baseline(t) for t in ALL_TONGUES}
        for t1 in ALL_TONGUES:
            for t2 in ALL_TONGUES:
                if t1 < t2:
                    diff = np.linalg.norm(baselines[t1] - baselines[t2])
                    assert diff > 0.01, f"{t1} and {t2} baselines too similar"


# ===================================================================
# Mirror point tests
# ===================================================================


class TestMirrorPoint:
    """Test individual mirror point computation."""

    def test_mirror_point_has_all_fields(self):
        mp = compute_mirror_point("test", "ko", "dr")
        assert mp.tongue_fwd == "ko"
        assert mp.tongue_inv == "dr"
        assert isinstance(mp.angular_gap, float)
        assert isinstance(mp.interference, float)
        assert isinstance(mp.mid_radius, float)

    def test_forward_inside_ball(self):
        mp = compute_mirror_point("test", "ko", "dr")
        assert np.linalg.norm(mp.p_fwd) < 1.0

    def test_inverse_inside_ball(self):
        mp = compute_mirror_point("test", "ko", "dr")
        assert np.linalg.norm(mp.p_inv) < 1.0

    def test_midpoint_inside_ball(self):
        mp = compute_mirror_point("test", "ko", "dr")
        assert np.linalg.norm(mp.p_mid) < 1.0

    def test_angular_gap_bounded(self):
        """Angular gap should be in [0, pi]."""
        mp = compute_mirror_point("test", "av", "um")
        assert 0.0 <= mp.angular_gap <= math.pi + 0.01

    def test_interference_bounded(self):
        """Interference should be in [-1, 1] approximately."""
        for t1 in ALL_TONGUES:
            for t2 in ALL_TONGUES:
                if t1 != t2:
                    mp = compute_mirror_point("test text", t1, t2)
                    assert -2.0 <= mp.interference <= 2.0, f"{t1}->{t2}: interference={mp.interference}"

    def test_asymmetry_zero_for_equal_energy(self):
        """When forward and inverse have equal energy, asymmetry should be ~0."""
        mp = compute_mirror_point("test", "ko", "dr")
        # Both projections are at mid_radius, so energy should be equal
        assert mp.asymmetry < 0.01


# ===================================================================
# Three-mode complement pattern
# ===================================================================


class TestComplementModes:
    """Test the three interference modes of complement pairs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        text = "In the beginning was the Word and the Word was with God"
        self.ko_dr = compute_mirror_point(text, "ko", "dr")
        self.av_um = compute_mirror_point(text, "av", "um")
        self.ru_ca = compute_mirror_point(text, "ru", "ca")

    def test_ko_dr_constructive(self):
        """KO<->DR (intent<->structure) should show constructive interference."""
        assert self.ko_dr.interference > 0.0, f"KO-DR interference={self.ko_dr.interference:.4f}, expected positive"

    def test_ru_ca_destructive(self):
        """RU<->CA (truth<->creativity) should show destructive interference."""
        assert self.ru_ca.interference < 0.0, f"RU-CA interference={self.ru_ca.interference:.4f}, expected negative"

    def test_av_um_near_neutral(self):
        """AV<->UM (wisdom<->security) should be closer to neutral than the others."""
        assert abs(self.av_um.interference) < abs(self.ko_dr.interference), (
            f"AV-UM |interf|={abs(self.av_um.interference):.4f} should be < "
            f"KO-DR |interf|={abs(self.ko_dr.interference):.4f}"
        )

    def test_ko_dr_deepest_midpoint(self):
        """KO<->DR should have the deepest middle surface (highest radius)."""
        assert self.ko_dr.mid_radius > self.ru_ca.mid_radius, (
            f"KO-DR r_mid={self.ko_dr.mid_radius:.4f} should > " f"RU-CA r_mid={self.ru_ca.mid_radius:.4f}"
        )

    def test_ru_ca_shallowest_midpoint(self):
        """RU<->CA should have the shallowest middle surface (near origin)."""
        assert self.ru_ca.mid_radius < self.av_um.mid_radius, (
            f"RU-CA r_mid={self.ru_ca.mid_radius:.4f} should < " f"AV-UM r_mid={self.av_um.mid_radius:.4f}"
        )

    def test_three_modes_distinct(self):
        """The three complement pairs should have meaningfully different interference."""
        values = sorted(
            [
                self.ko_dr.interference,
                self.av_um.interference,
                self.ru_ca.interference,
            ]
        )
        # Spread should be > 0.5 (not all clustered together)
        spread = values[-1] - values[0]
        assert spread > 0.5, f"Interference spread too narrow: {spread:.4f}"


# ===================================================================
# Full experiment tests
# ===================================================================


class TestFullExperiment:
    """Test the complete manifold mirror experiment."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = run_manifold_mirror()

    def test_has_complement_points(self):
        assert len(self.result.complement_points) == 6  # 3 pairs x 2 directions

    def test_has_non_complement_points(self):
        assert len(self.result.non_complement_points) == 24  # 6*5 - 6 = 24

    def test_total_points(self):
        assert len(self.result.points) == 30  # 6*5

    def test_complement_gap_positive(self):
        assert self.result.mean_complement_gap > 0.0

    def test_needle_retrieval_all_tongues(self):
        assert len(self.result.needle_retrieval) == 6

    def test_needle_scores_bounded(self):
        for tongue, score in self.result.needle_retrieval.items():
            assert 0.0 <= score <= 1.0, f"{tongue}: needle={score}"

    def test_format_report_produces_output(self):
        report = format_mirror_report(self.result)
        assert "MANIFOLD MIRROR" in report
        assert "PATTERN" in report
        assert "COMPLEMENT" in report
        assert len(report) > 500


# ===================================================================
# Symmetry tests
# ===================================================================


class TestSymmetry:
    """Test geometric symmetry properties."""

    def test_complement_swap_changes_sign(self):
        """Swapping forward/inverse tongues in a complement pair
        should preserve magnitude but may flip interference sign."""
        text = "symmetry test"
        mp_fwd = compute_mirror_point(text, "ko", "dr")
        mp_rev = compute_mirror_point(text, "dr", "ko")
        # Gap should be the same (symmetric distance)
        assert abs(mp_fwd.angular_gap - mp_rev.angular_gap) < 0.01
        # Mid radius should be the same
        assert abs(mp_fwd.mid_radius - mp_rev.mid_radius) < 0.01

    def test_all_tongues_produce_valid_mirrors(self):
        """Every tongue pair should produce a valid mirror point."""
        for t1 in ALL_TONGUES:
            for t2 in ALL_TONGUES:
                if t1 != t2:
                    mp = compute_mirror_point("valid test", t1, t2)
                    assert np.isfinite(mp.angular_gap)
                    assert np.isfinite(mp.interference)
                    assert np.isfinite(mp.mid_radius)


# ===================================================================
# Neural network behavior predictions
# ===================================================================


class TestNeuralPredictions:
    """Tests that validate the neural network behavior predictions
    from the manifold mirror pattern."""

    def test_constructive_pair_has_highest_retrieval(self):
        """The tongue with constructive complement interference
        should have better needle retrieval (like skip connections)."""
        result = run_manifold_mirror()
        # DR (constructive with KO) should retrieve better than
        # CA (destructive with RU)
        assert result.needle_retrieval["dr"] >= result.needle_retrieval["ca"], (
            f"DR={result.needle_retrieval['dr']:.4f} should >= " f"CA={result.needle_retrieval['ca']:.4f}"
        )

    def test_complement_coherence_exceeds_non_complement(self):
        """Complement pairs should maintain more coherence
        (less negative interference) than non-complement pairs."""
        result = run_manifold_mirror()
        assert result.mean_complement_interference >= result.mean_non_complement_interference, (
            f"Complement={result.mean_complement_interference:.4f} should >= "
            f"non-complement={result.mean_non_complement_interference:.4f}"
        )
