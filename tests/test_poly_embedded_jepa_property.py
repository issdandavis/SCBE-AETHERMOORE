"""Property-based tests for the poly-embedded JEPA harness.

These tests pin the public contract under random inputs and remain
stable across internal refactors. They use only exported names from
``python.scbe.poly_embedded_jepa``.
"""

from dataclasses import asdict

import pytest
from hypothesis import HealthCheck, assume, given, settings, strategies as st

from python.scbe.atomic_tokenization import TONGUES
from python.scbe.poly_embedded_jepa import (
    CODING_SYSTEMS,
    batch_verify,
    build_poly_embedding,
    deterministic_masked_tiles,
    jepa_llm_loss_mix,
    predict_masked_latent,
    predict_masked_latent_unnormalized,
    production_ready_coding_systems,
    safe_unnormalized_residual_lambda,
    verify_poly_embedding,
)
from python.scbe.tile_lang import lang_at_tile

CONCEPTS = st.from_regex(r"[A-Za-z][A-Za-z0-9 _\-]{0,60}", fullmatch=True)
ROWS = st.integers(min_value=0, max_value=5)
COLS = st.integers(min_value=0, max_value=5)
VALID_MASK = st.floats(min_value=1e-6, max_value=0.5, allow_nan=False, allow_infinity=False)
VALID_LAMBDA = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
PROGRESS = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

PROP_SETTINGS = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@PROP_SETTINGS
@given(CONCEPTS, ROWS, COLS, VALID_MASK, VALID_LAMBDA)
def test_build_then_verify_always_passes(concept, row, col, mask_ratio, residual_lambda):
    embedding = build_poly_embedding(
        concept,
        masked_row=row,
        masked_col=col,
        mask_ratio=mask_ratio,
        residual_lambda=residual_lambda,
    )
    report = verify_poly_embedding(embedding)
    assert report["ok"] is True, report["failed"]


@PROP_SETTINGS
@given(ROWS, COLS)
def test_tile_tongue_always_matches_grid(row, col):
    embedding = build_poly_embedding("probe", masked_row=row, masked_col=col)
    assert embedding.tile_node.tongue == lang_at_tile(row, col)
    assert embedding.tile_node.tongue in TONGUES


@PROP_SETTINGS
@given(PROGRESS)
def test_loss_mix_partition_of_unity(p):
    mix = jepa_llm_loss_mix(p)
    assert mix["jepa_latent_weight"] + mix["llm_decode_weight"] == pytest.approx(1.0)
    assert 0.5 <= mix["jepa_latent_weight"] <= 0.75
    assert 0.25 <= mix["llm_decode_weight"] <= 0.5


@PROP_SETTINGS
@given(PROGRESS, PROGRESS)
def test_loss_mix_jepa_is_monotone_non_increasing(p1, p2):
    mix1 = jepa_llm_loss_mix(p1)
    mix2 = jepa_llm_loss_mix(p2)
    if p1 <= p2:
        assert mix1["jepa_latent_weight"] >= mix2["jepa_latent_weight"]


@PROP_SETTINGS
@given(CONCEPTS, ROWS, COLS, VALID_LAMBDA)
def test_predict_masked_latent_is_deterministic(concept, row, col, residual_lambda):
    a = predict_masked_latent(concept, row, col, residual_lambda=residual_lambda)
    b = predict_masked_latent(concept, row, col, residual_lambda=residual_lambda)
    assert a == b
    assert len(a) == 6


@PROP_SETTINGS
@given(CONCEPTS, ROWS, COLS)
def test_unnormalized_predictor_respects_safe_bound(concept, row, col):
    safe = safe_unnormalized_residual_lambda()
    out = predict_masked_latent_unnormalized(concept, row, col)
    assert len(out) == 6
    with pytest.raises(ValueError, match="safe unnormalized contraction bound"):
        predict_masked_latent_unnormalized(concept, row, col, residual_lambda=safe + 0.05)


@PROP_SETTINGS
@given(CONCEPTS, ROWS, COLS)
def test_tampered_binary_packet_always_rejected(concept, row, col):
    embedding = asdict(build_poly_embedding(concept, masked_row=row, masked_col=col))
    embedding["binary_packet_sha256"] = "deadbeef" * 8
    report = verify_poly_embedding(embedding)
    assert report["ok"] is False
    assert "binary_packet_matches_surfaces" in report["failed"]


@PROP_SETTINGS
@given(CONCEPTS, ROWS, COLS)
def test_tampered_tile_tongue_always_rejected(concept, row, col):
    embedding = asdict(build_poly_embedding(concept, masked_row=row, masked_col=col))
    embedding["tile_node"]["tongue"] = "not-a-real-tongue"
    report = verify_poly_embedding(embedding)
    assert report["ok"] is False
    assert "tile_tongue_matches_grid" in report["failed"]


@PROP_SETTINGS
@given(CONCEPTS, VALID_MASK)
def test_deterministic_mask_set_is_stable_and_sized(concept, mask_ratio):
    a = deterministic_masked_tiles(concept, mask_ratio)
    b = deterministic_masked_tiles(concept, mask_ratio)
    assert a == b
    assert 1 <= len(a) <= 36
    for tile in a:
        prefix, r, c = tile.split(":")
        assert prefix == "tile"
        assert 0 <= int(r) <= 5
        assert 0 <= int(c) <= 5


@PROP_SETTINGS
@given(st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False))
def test_mask_ratio_outside_gate_raises(bad_ratio):
    assume(not (0.0 < bad_ratio <= 0.5))
    with pytest.raises(ValueError, match="mask_ratio"):
        build_poly_embedding("probe", mask_ratio=bad_ratio)


@PROP_SETTINGS
@given(st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False))
def test_normalized_lambda_outside_gate_raises(bad_lambda):
    assume(not (0.0 <= bad_lambda <= 1.0))
    with pytest.raises(ValueError, match="residual_lambda"):
        predict_masked_latent("probe", 0, 0, residual_lambda=bad_lambda)


def test_non_production_coding_systems_are_rejected():
    not_ready = tuple(system for system in CODING_SYSTEMS if not system.production_ready)
    assert not_ready, "catalog must include at least one non-production-ready system"
    with pytest.raises(ValueError, match="non-production-ready"):
        build_poly_embedding("probe", coding_systems=not_ready[:1])


def test_default_coding_systems_are_all_production_ready():
    selected = production_ready_coding_systems()
    assert selected, "production-ready set must be non-empty"
    for system in selected:
        assert system.production_ready


@PROP_SETTINGS
@given(st.lists(st.tuples(CONCEPTS, ROWS, COLS), min_size=1, max_size=4))
def test_batch_verify_reports_zero_failures_for_clean_inputs(specs):
    embeddings = [build_poly_embedding(concept, masked_row=row, masked_col=col) for concept, row, col in specs]
    report = batch_verify(embeddings)
    assert report["count"] == len(specs)
    assert report["failed_count"] == 0
    assert report["ok"] is True
