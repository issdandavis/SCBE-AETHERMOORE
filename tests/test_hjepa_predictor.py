"""Tests for the learnable H-JEPA L1->L2 predictor head."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from python.scbe.hjepa_embedding import hjepa_signature
from python.scbe.hjepa_predictor import (
    DEFAULT_WEIGHTS_PATH,
    INPUT_DIM,
    OUTPUT_DIM,
    SCHEMA_VERSION,
    HJEPAPredictorWeights,
    baseline_weights,
    build_training_pairs,
    fixture_corpus,
    initial_weights,
    load_weights,
    mse_loss,
    predict,
    predict_braid_learned,
    save_weights,
    train,
)
from python.scbe.poly_embedded_jepa import build_poly_embedding

# ---------------------------------------------------------------------------
# Schema and shape invariants
# ---------------------------------------------------------------------------


def test_schema_version_constant():
    assert SCHEMA_VERSION == "scbe_hjepa_predictor_v1"


def test_initial_weights_have_correct_shape():
    w = initial_weights()
    assert w.W.shape == (OUTPUT_DIM, INPUT_DIM)
    assert w.b.shape == (OUTPUT_DIM,)
    assert w.schema_version == SCHEMA_VERSION


def test_baseline_weights_are_pure_identity_stack():
    """No noise: W should be exactly [I; I] and b should be zero."""

    w = baseline_weights()
    expected_W = np.vstack([np.eye(INPUT_DIM), np.eye(INPUT_DIM)])
    np.testing.assert_array_equal(w.W, expected_W)
    np.testing.assert_array_equal(w.b, np.zeros(OUTPUT_DIM))


def test_baseline_predict_echoes_input_twice():
    """Identity stack: predicted (fast, memory) both equal the input."""

    w = baseline_weights()
    x = (0.1, -0.2, 0.3, -0.4, 0.5, -0.6)
    fast, memory = predict(w, x)
    assert fast == x
    assert memory == x


def test_predict_rejects_wrong_input_dimension():
    w = baseline_weights()
    with pytest.raises(ValueError, match="6-D"):
        predict(w, (0.1, 0.2, 0.3))


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------


def test_save_then_load_recovers_weights(tmp_path):
    w = initial_weights()
    target = tmp_path / "predictor.npz"
    save_weights(w, target)
    loaded = load_weights(target)
    assert loaded is not None
    np.testing.assert_array_equal(loaded.W, w.W)
    np.testing.assert_array_equal(loaded.b, w.b)
    assert loaded.schema_version == w.schema_version


def test_load_returns_none_for_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.npz"
    assert load_weights(missing) is None


def test_load_rejects_schema_mismatch(tmp_path):
    target = tmp_path / "predictor.npz"
    np.savez(
        target,
        W=np.zeros((OUTPUT_DIM, INPUT_DIM)),
        b=np.zeros(OUTPUT_DIM),
        schema_version=np.asarray("wrong_schema"),
        train_loss_history=np.asarray([], dtype=np.float64),
    )
    assert load_weights(target) is None


# ---------------------------------------------------------------------------
# Corpus and training pairs
# ---------------------------------------------------------------------------


def test_fixture_corpus_balanced():
    corpus = fixture_corpus()
    benign = sum(1 for label, _ in corpus if label == "benign")
    adversarial = sum(1 for label, _ in corpus if label == "adversarial")
    assert benign == adversarial
    assert benign > 0


def test_build_training_pairs_shapes():
    X, Y = build_training_pairs()
    assert X.ndim == 2
    assert Y.ndim == 2
    assert X.shape[0] == Y.shape[0]
    assert X.shape[1] == INPUT_DIM
    assert Y.shape[1] == OUTPUT_DIM


# ---------------------------------------------------------------------------
# Training reduces loss
# ---------------------------------------------------------------------------


def test_training_strictly_reduces_mse():
    X, Y = build_training_pairs()
    w0 = initial_weights(seed=42)
    initial_mse = mse_loss(w0, X, Y)
    trained = train(w0, X, Y, epochs=200, learning_rate=0.01, seed=42)
    final_mse = mse_loss(trained, X, Y)
    assert final_mse < initial_mse, f"training did not reduce loss: {initial_mse} -> {final_mse}"


def test_training_history_length_matches_epochs():
    X, Y = build_training_pairs()
    w0 = initial_weights(seed=42)
    trained = train(w0, X, Y, epochs=50, learning_rate=0.01, seed=42)
    assert len(trained.train_loss_history) == 50


def test_training_is_deterministic_under_fixed_seed():
    X, Y = build_training_pairs()
    w0 = initial_weights(seed=42)
    a = train(w0, X, Y, epochs=30, seed=99)
    b = train(w0, X, Y, epochs=30, seed=99)
    np.testing.assert_array_equal(a.W, b.W)
    np.testing.assert_array_equal(a.b, b.b)


# ---------------------------------------------------------------------------
# Predicted braid keeps governance pinned
# ---------------------------------------------------------------------------


def test_predict_braid_learned_preserves_governance():
    """Governance is content-independent; the learnable head must not perturb it."""

    poly = build_poly_embedding("plan a paired coding task")
    w = baseline_weights()  # identity stack: predicted_fast = predicted_memory = input
    learned_braid = predict_braid_learned(poly, w)
    # Compare against the actual braid's governance (which is a function of poly's
    # coding systems and is identical regardless of which fast/memory we pass in).
    from python.scbe.tri_braid_embedding import tri_braid_signature

    target_braid = tri_braid_signature(poly)
    assert learned_braid.governance == target_braid.governance


def test_predict_braid_learned_with_baseline_matches_deterministic():
    """With pure identity-stack weights, the learnable head should produce
    the same braid as the deterministic ``_predict_braid``.
    """

    from python.scbe.hjepa_embedding import _predict_braid

    poly = build_poly_embedding("plan a paired coding task")
    deterministic = _predict_braid(poly)
    learned = predict_braid_learned(poly, baseline_weights())
    assert learned.fast == deterministic.fast
    assert learned.memory == deterministic.memory
    assert learned.governance == deterministic.governance


# ---------------------------------------------------------------------------
# H-JEPA signature picks up the learned predictor when weights exist
# ---------------------------------------------------------------------------


def test_hjepa_signature_with_use_learned_predictor_returns_finite_loss():
    sig = hjepa_signature("plan a paired coding task", use_learned_predictor=True)
    for level in sig.levels:
        assert math.isfinite(level.loss)
        assert level.loss >= 0.0
    assert math.isfinite(sig.total_loss)


def test_hjepa_signature_use_learned_predictor_falls_back_when_weights_missing(tmp_path, monkeypatch):
    """Move the weights file aside; signature should fall back to deterministic."""

    monkeypatch.setattr(
        "python.scbe.hjepa_predictor.DEFAULT_WEIGHTS_PATH",
        tmp_path / "missing.npz",
    )
    sig = hjepa_signature("plan a paired coding task", use_learned_predictor=True)
    # Result should match the deterministic-baseline signature byte-for-byte.
    deterministic = hjepa_signature("plan a paired coding task", use_learned_predictor=False)
    assert sig.hjepa_hash == deterministic.hjepa_hash
    assert sig.total_loss == deterministic.total_loss


@pytest.mark.skipif(not DEFAULT_WEIGHTS_PATH.exists(), reason="weights file not built yet")
def test_learned_predictor_reduces_l2_loss_vs_deterministic():
    """If trained weights exist, the learned head should strictly reduce
    the H-JEPA L2 loss averaged across the fixture corpus relative to
    the deterministic baseline.
    """

    corpus = fixture_corpus()
    deterministic_total = 0.0
    learned_total = 0.0
    for _label, prompt in corpus:
        deterministic_total += hjepa_signature(prompt, use_learned_predictor=False).levels[1].loss
        learned_total += hjepa_signature(prompt, use_learned_predictor=True).levels[1].loss
    deterministic_mean = deterministic_total / len(corpus)
    learned_mean = learned_total / len(corpus)
    assert learned_mean < deterministic_mean, (
        f"learned head did not improve L2 loss: "
        f"deterministic={deterministic_mean:.6f} vs learned={learned_mean:.6f}"
    )
