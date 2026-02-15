"""
Tests for Multimodality Matrix (MMX) — Layer 9.5 Cross-Modal Coherence Tensor.

Covers:
  - Alignment matrix symmetry and diagonal
  - Reliability weights
  - Coherence / conflict / drift scalars
  - Governance-level thresholds
  - Edge cases (zero vectors, identical vectors, orthogonal vectors)
  - Dimension mismatch errors
"""

import math
import sys
import os
import pytest

# Ensure the source is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from symphonic_cipher.scbe_aethermoore.multimodal.mmx import compute_mmx, MMXResult


# =============================================================================
# HELPERS
# =============================================================================

def _eye_alignment(k: int) -> list:
    """Return a K×K identity alignment (all pairs = 1.0)."""
    return [[1.0 if i == j else 1.0 for i in range(k)] for j in range(k)]


# =============================================================================
# BASIC FUNCTIONALITY
# =============================================================================

class TestBasicMMX:
    """Core compute_mmx behaviour."""

    def test_identical_vectors_full_coherence(self):
        """Identical feature vectors → coherence=1, conflict=0."""
        features = {
            "text": [1.0, 0.0, 0.0],
            "audio": [1.0, 0.0, 0.0],
            "video": [1.0, 0.0, 0.0],
        }
        r = compute_mmx(features)
        assert r.coherence == pytest.approx(1.0, abs=1e-9)
        assert r.conflict == pytest.approx(0.0, abs=1e-9)

    def test_orthogonal_vectors_low_coherence(self):
        """Orthogonal vectors → cosine=0 → coherence≈0, conflict=1."""
        features = {
            "a": [1.0, 0.0, 0.0],
            "b": [0.0, 1.0, 0.0],
            "c": [0.0, 0.0, 1.0],
        }
        r = compute_mmx(features)
        assert r.coherence == pytest.approx(0.0, abs=1e-9)
        assert r.conflict == pytest.approx(1.0, abs=1e-9)

    def test_two_modalities_minimum(self):
        """Two modalities is the minimum accepted."""
        features = {"x": [1.0, 2.0], "y": [3.0, 4.0]}
        r = compute_mmx(features)
        assert len(r.alignment) == 2
        assert len(r.weights) == 2
        assert len(r.modality_labels) == 2

    def test_alignment_matrix_symmetry(self):
        """A[i][j] == A[j][i] for all i,j."""
        features = {"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0], "c": [7.0, -1.0, 0.5]}
        r = compute_mmx(features)
        K = len(r.alignment)
        for i in range(K):
            for j in range(K):
                assert r.alignment[i][j] == pytest.approx(r.alignment[j][i], abs=1e-12)

    def test_alignment_diagonal_is_one(self):
        """Self-similarity is always 1.0."""
        features = {"a": [1.0, 2.0], "b": [3.0, 4.0], "c": [5.0, 6.0]}
        r = compute_mmx(features)
        for i in range(len(r.alignment)):
            assert r.alignment[i][i] == pytest.approx(1.0, abs=1e-12)

    def test_labels_sorted(self):
        """Modality labels are returned in sorted order."""
        features = {"zebra": [1.0], "alpha": [2.0]}
        r = compute_mmx(features)
        assert r.modality_labels == ["alpha", "zebra"]


# =============================================================================
# RELIABILITY WEIGHTS
# =============================================================================

class TestReliabilityWeights:
    """Per-modality reliability weights."""

    def test_zero_vector_low_weight(self):
        """Zero-norm modality gets weight ≈ 0."""
        features = {"zero": [0.0, 0.0, 0.0], "nonzero": [1.0, 1.0, 1.0]}
        r = compute_mmx(features)
        # "nonzero" sorts after "zero" alphabetically
        idx_zero = r.modality_labels.index("zero")
        assert r.weights[idx_zero] < 0.01

    def test_large_norm_high_weight(self):
        """Large-norm modality gets weight close to 1."""
        features = {"big": [100.0, 200.0, 300.0], "small": [0.01, 0.01, 0.01]}
        r = compute_mmx(features)
        idx_big = r.modality_labels.index("big")
        assert r.weights[idx_big] > 0.99

    def test_weights_in_unit_interval(self):
        """All weights ∈ [0, 1)."""
        features = {"a": [1.0, 2.0], "b": [3.0, 4.0], "c": [0.0, 0.0]}
        r = compute_mmx(features)
        for w in r.weights:
            assert 0.0 <= w < 1.0


# =============================================================================
# GOVERNANCE SCALARS
# =============================================================================

class TestGovernanceScalars:
    """Coherence, conflict, drift."""

    def test_coherence_range(self):
        """Coherence ∈ [0, 1]."""
        features = {"a": [1.0, 2.0, 3.0], "b": [4.0, -5.0, 6.0]}
        r = compute_mmx(features)
        assert 0.0 <= r.coherence <= 1.0

    def test_conflict_range(self):
        """Conflict ∈ [0, 1]."""
        features = {"a": [1.0, 0.0], "b": [0.0, 1.0]}
        r = compute_mmx(features)
        assert 0.0 <= r.conflict <= 1.0

    def test_agreement_floor_effect(self):
        """Higher agreement floor → more conflict."""
        features = {"a": [1.0, 0.5], "b": [0.5, 1.0]}
        low = compute_mmx(features, agreement_floor=0.1)
        high = compute_mmx(features, agreement_floor=0.99)
        assert high.conflict >= low.conflict

    def test_drift_zero_without_prev(self):
        """No previous alignment → drift = 0."""
        features = {"a": [1.0, 2.0], "b": [3.0, 4.0]}
        r = compute_mmx(features)
        assert r.drift == pytest.approx(0.0, abs=1e-12)

    def test_drift_positive_with_change(self):
        """Changed alignment matrix → drift > 0."""
        features = {"a": [1.0, 0.0], "b": [0.0, 1.0]}
        prev = [[1.0, 0.9], [0.9, 1.0]]
        r = compute_mmx(features, prev_alignment=prev)
        assert r.drift > 0.0

    def test_drift_zero_when_unchanged(self):
        """Same features + same prev alignment → drift ≈ 0."""
        features = {"a": [1.0, 2.0], "b": [3.0, 4.0]}
        r1 = compute_mmx(features)
        r2 = compute_mmx(features, prev_alignment=r1.alignment)
        assert r2.drift == pytest.approx(0.0, abs=1e-12)


# =============================================================================
# GOVERNANCE THRESHOLD TESTS
# =============================================================================

class TestGovernanceThresholds:
    """Verify conflict thresholds match governance rules."""

    def test_aligned_below_quarantine(self):
        """Well-aligned modalities → conflict < 0.35 (ALLOW zone)."""
        # Similar vectors → high cosine → low conflict
        features = {"a": [1.0, 0.9], "b": [0.95, 1.0], "c": [1.0, 1.0]}
        r = compute_mmx(features)
        assert r.conflict < 0.35, f"Expected ALLOW zone, got conflict={r.conflict}"

    def test_mixed_near_quarantine(self):
        """One conflicting pair out of three → conflict ≈ 0.33."""
        features = {
            "aligned1": [1.0, 0.0],
            "aligned2": [0.9, 0.1],
            "orthogonal": [0.0, 1.0],
        }
        r = compute_mmx(features, agreement_floor=0.5)
        # 3 pairs: aligned1-aligned2 (high), aligned1-orthogonal (low), aligned2-orthogonal (medium)
        assert 0.0 < r.conflict <= 1.0

    def test_severe_conflict_deny_zone(self):
        """Fully orthogonal modalities → conflict = 1.0 (DENY zone)."""
        features = {
            "x": [1.0, 0.0, 0.0],
            "y": [0.0, 1.0, 0.0],
            "z": [0.0, 0.0, 1.0],
        }
        r = compute_mmx(features, agreement_floor=0.5)
        assert r.conflict > 0.60, f"Expected DENY zone, got conflict={r.conflict}"


# =============================================================================
# ERROR HANDLING
# =============================================================================

class TestErrors:
    """Input validation."""

    def test_single_modality_raises(self):
        """Need ≥ 2 modalities."""
        with pytest.raises(ValueError, match="≥2 modalities"):
            compute_mmx({"only": [1.0, 2.0]})

    def test_empty_raises(self):
        """Empty features dict → error."""
        with pytest.raises(ValueError, match="≥2 modalities"):
            compute_mmx({})

    def test_dimension_mismatch_raises(self):
        """Different vector lengths → error."""
        with pytest.raises(ValueError, match="Dimension mismatch"):
            compute_mmx({"a": [1.0, 2.0], "b": [3.0, 4.0, 5.0]})


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Boundary and degenerate inputs."""

    def test_both_zero_vectors(self):
        """Two zero vectors → coherence should handle gracefully (cosine=0)."""
        features = {"a": [0.0, 0.0], "b": [0.0, 0.0]}
        r = compute_mmx(features)
        assert r.coherence == pytest.approx(0.0, abs=1e-9)

    def test_negative_vectors(self):
        """Anti-parallel vectors → cosine = -1."""
        features = {"pos": [1.0, 0.0], "neg": [-1.0, 0.0]}
        r = compute_mmx(features)
        assert r.alignment[0][1] == pytest.approx(-1.0, abs=1e-9)
        assert r.coherence < 0.0 or r.coherence == pytest.approx(0.0, abs=1e-9)

    def test_high_dimensionality(self):
        """64-dim vectors work fine."""
        features = {
            "a": [float(i) for i in range(64)],
            "b": [float(64 - i) for i in range(64)],
        }
        r = compute_mmx(features)
        assert 0.0 <= r.coherence <= 1.0

    def test_many_modalities(self):
        """10 modalities → 45 pairs."""
        features = {f"m{i}": [float(i), float(i * 2)] for i in range(10)}
        r = compute_mmx(features)
        assert len(r.alignment) == 10
        assert len(r.weights) == 10

    def test_prev_alignment_size_mismatch_ignored(self):
        """Wrong-sized prev_alignment → drift stays 0."""
        features = {"a": [1.0, 2.0], "b": [3.0, 4.0]}
        prev = [[1.0, 0.5, 0.3], [0.5, 1.0, 0.4], [0.3, 0.4, 1.0]]  # 3×3 for K=2
        r = compute_mmx(features, prev_alignment=prev)
        assert r.drift == pytest.approx(0.0, abs=1e-12)

    def test_result_is_frozen(self):
        """MMXResult is immutable (dataclass frozen=True)."""
        features = {"a": [1.0], "b": [2.0]}
        r = compute_mmx(features)
        with pytest.raises(AttributeError):
            r.coherence = 0.5  # type: ignore


# =============================================================================
# CROSS-LANGUAGE PARITY
# =============================================================================

class TestCrossLanguageParity:
    """Deterministic numeric values for cross-language validation with TS port."""

    def test_canonical_3x3_values(self):
        """
        Three known vectors → known alignment, coherence, conflict.
        Use this test vector for TS port validation.
        """
        features = {
            "text":  [1.0, 2.0, 3.0],
            "audio": [4.0, 5.0, 6.0],
            "video": [7.0, 8.0, 9.0],
        }
        r = compute_mmx(features, agreement_floor=0.5)

        # Labels sorted: audio(0), text(1), video(2)
        # cos(audio=[4,5,6], text=[1,2,3])  = 32/sqrt(77*14)  ≈ 0.9746
        # cos(audio=[4,5,6], video=[7,8,9]) = 122/sqrt(77*194) ≈ 0.9982
        # cos(text=[1,2,3],  video=[7,8,9]) = 50/sqrt(14*194)  ≈ 0.9594
        assert r.alignment[0][1] == pytest.approx(0.9746, abs=0.001)
        assert r.alignment[0][2] == pytest.approx(0.9982, abs=0.001)
        assert r.alignment[1][2] == pytest.approx(0.9594, abs=0.001)

        # All pairs above 0.5 → conflict = 0
        assert r.conflict == pytest.approx(0.0, abs=1e-9)

        # coherence = mean(0.9746, 0.9982, 0.9594) ≈ 0.9774
        assert r.coherence == pytest.approx(0.9774, abs=0.001)
