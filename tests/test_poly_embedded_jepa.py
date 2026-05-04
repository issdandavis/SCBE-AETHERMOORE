from dataclasses import asdict

import pytest

from python.scbe.atomic_tokenization import TONGUES
from python.scbe.poly_embedded_jepa import (
    CODING_SYSTEMS,
    PHI,
    batch_verify,
    build_poly_embedding,
    coding_system_ids,
    deterministic_masked_tiles,
    jepa_llm_loss_mix,
    normalized_tongue_weights,
    predict_masked_latent,
    predict_masked_latent_unnormalized,
    production_ready_coding_systems,
    row_normalized_edge_weights,
    safe_unnormalized_residual_lambda,
    tongue_phi_weights,
    verify_poly_embedding,
)


def test_phi_weights_follow_six_tongue_order():
    weights = tongue_phi_weights()
    assert tuple(weights) == tuple(TONGUES)
    assert weights[TONGUES[0]] == pytest.approx(1.0)
    assert weights[TONGUES[1]] == pytest.approx(PHI)
    assert weights[TONGUES[5]] == pytest.approx(PHI**5)


def test_normalized_weights_sum_to_one():
    weights = normalized_tongue_weights()
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights[TONGUES[-1]] > weights[TONGUES[0]]


def test_row_normalized_graph_is_stable():
    weights = row_normalized_edge_weights()
    assert sum(weights) == pytest.approx(1.0)
    assert safe_unnormalized_residual_lambda() == pytest.approx(1 / (4 + 1 / PHI**2 + 1 / PHI**3))


def test_mask_ratio_derives_deterministic_masked_tiles():
    masked = deterministic_masked_tiles("matrix", 0.4)
    assert len(masked) == 14  # floor(36 * 0.4)
    assert masked == deterministic_masked_tiles("matrix", 0.4)
    assert masked != deterministic_masked_tiles("matrix", 0.25)


def test_build_poly_embedding_round_trips_all_surfaces():
    embedding = build_poly_embedding("matrix multiply with LSP diagnostic and Vim edit", masked_row=2, masked_col=3)
    report = verify_poly_embedding(embedding)
    assert report["ok"] is True
    assert embedding.schema_version == "scbe_poly_embedded_jepa_v1"
    assert embedding.tile_node.tongue == TONGUES[(2 + 3) % 6]
    assert len(embedding.jepa_latent) == 6
    assert len(embedding.jepa_prediction) == 6
    assert len(embedding.masked_tiles) == 14
    assert embedding.mask_ratio == pytest.approx(0.4)
    assert "matrix" in embedding.llm_token_surface
    assert embedding.sacred_tongue_surface.startswith(f"{embedding.tile_node.tongue}:")


def test_default_embedding_uses_production_ready_coding_systems_only():
    embedding = build_poly_embedding("production ready coding packet", masked_row=2, masked_col=3)
    system_ids = coding_system_ids(embedding.coding_systems)
    assert system_ids == coding_system_ids(production_ready_coding_systems())
    assert "tile_lang" in system_ids
    assert "bijective_reasoning_code_packet" in system_ids
    assert "geoshell_pair_agent" in system_ids
    assert "code_prism" in system_ids
    assert "cassisivadan_opcode_table" in system_ids
    assert "agent_call_switchboard" in system_ids
    assert "lsp_diagnostic" not in system_ids
    assert all(system.production_ready for system in embedding.coding_systems)


def test_non_production_coding_systems_are_blocked_by_default():
    with pytest.raises(ValueError, match="non-production-ready"):
        build_poly_embedding("experimental surface", coding_systems=CODING_SYSTEMS)


def test_tampered_binary_packet_is_rejected():
    embedding = asdict(build_poly_embedding("chemistry valence hidden state", masked_row=1, masked_col=4))
    embedding["binary_packet_sha256"] = "0" * 64
    report = verify_poly_embedding(embedding)
    assert report["ok"] is False
    assert "binary_packet_matches_surfaces" in report["failed"]


def test_tampered_tile_tongue_is_rejected():
    embedding = asdict(build_poly_embedding("Sacred Tongue syntax block", masked_row=0, masked_col=0))
    embedding["tile_node"]["tongue"] = "not-a-tongue"
    report = verify_poly_embedding(embedding)
    assert report["ok"] is False
    assert "tile_tongue_matches_grid" in report["failed"]


def test_tampered_coding_system_readiness_is_rejected():
    embedding = asdict(build_poly_embedding("production system integrity", masked_row=0, masked_col=0))
    embedding["coding_systems"][0]["production_ready"] = False
    report = verify_poly_embedding(embedding)
    assert report["ok"] is False
    assert "coding_systems_are_production_ready" in report["failed"]
    assert "binary_packet_matches_surfaces" in report["failed"]


def test_mask_ratio_gate_blocks_sparse_context():
    with pytest.raises(ValueError, match="mask_ratio"):
        build_poly_embedding("too sparse", mask_ratio=0.75)


def test_prediction_is_deterministic():
    a = predict_masked_latent("same concept", 3, 5)
    b = predict_masked_latent("same concept", 3, 5)
    assert a == b


def test_unnormalized_prediction_uses_safe_lambda_bound():
    prediction = predict_masked_latent_unnormalized("same concept", 3, 5)
    assert len(prediction) == 6
    with pytest.raises(ValueError, match="safe unnormalized"):
        predict_masked_latent_unnormalized("same concept", 3, 5, residual_lambda=0.5)


def test_jepa_llm_schedule_moves_from_latent_to_balanced():
    early = jepa_llm_loss_mix(0.0)
    late = jepa_llm_loss_mix(1.0)
    assert early == {"jepa_latent_weight": 0.75, "llm_decode_weight": 0.25}
    assert late == {"jepa_latent_weight": 0.5, "llm_decode_weight": 0.5}


def test_batch_verify_reports_failure_count():
    embeddings = [
        build_poly_embedding("first", masked_row=0, masked_col=0),
        build_poly_embedding("second", masked_row=1, masked_col=1),
    ]
    report = batch_verify(embeddings)
    assert report["ok"] is True
    assert report["count"] == 2
    assert report["failed_count"] == 0
