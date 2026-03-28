"""Tests for governance flux parameters — quorum-gated parameter updates."""

from __future__ import annotations

import pytest

from src.governance.flux_parameters import (
    FluxParams,
    ConsensusEngine,
    create_voxel_header,
)


@pytest.fixture
def current_params() -> FluxParams:
    return FluxParams(
        epoch_id="NK-2026.02-SEASON-0",
        lang_weights={"KO": 1.0, "AV": 1.0, "RU": 1.0, "CA": 1.0, "UM": 1.0, "DR": 1.0},
        curvature_kappa=0.25,
        phase_coupling_eta=0.05,
        entropy_noise_floor=0.01,
        layer12_R=1.0,
        layer12_gamma=1.0,
        quarantine_cost=2500.0,
    )


@pytest.fixture
def engine(current_params: FluxParams) -> ConsensusEngine:
    return ConsensusEngine(current_params=current_params)


def _safe_update_from(base: FluxParams, **overrides) -> FluxParams:
    data = {
        "epoch_id": "NK-2026.02-SEASON-1",
        "lang_weights": dict(base.lang_weights),
        "curvature_kappa": base.curvature_kappa,
        "phase_coupling_eta": base.phase_coupling_eta,
        "entropy_noise_floor": base.entropy_noise_floor,
        "layer12_R": base.layer12_R,
        "layer12_gamma": base.layer12_gamma,
        "quarantine_cost": base.quarantine_cost,
    }
    data.update(overrides)
    return FluxParams(**data)


def test_illegal_layer12_radius_rejected(
    engine: ConsensusEngine, current_params: FluxParams
):
    bad = _safe_update_from(current_params, layer12_R=5.0)  # out of [0.8, 1.2]
    with pytest.raises(ValueError, match="Layer 12 Radius"):
        engine.propose_update(bad, proposer="KO")

    assert engine.pending_proposal is None
    assert engine.current_params.epoch_id == current_params.epoch_id


def test_negative_curvature_rejected(
    engine: ConsensusEngine, current_params: FluxParams
):
    bad = _safe_update_from(current_params, curvature_kappa=-0.01)
    with pytest.raises(ValueError, match="Negative curvature"):
        engine.propose_update(bad, proposer="KO")

    assert engine.pending_proposal is None


def test_unauthorized_proposer_rejected(
    engine: ConsensusEngine, current_params: FluxParams
):
    newp = _safe_update_from(current_params, epoch_id="NK-2026.02-SEASON-X")
    with pytest.raises(PermissionError, match="Unauthorized proposer"):
        engine.propose_update(newp, proposer="ZZ")  # not in AGENTS

    assert engine.pending_proposal is None


def test_quorum_commit_requires_four_signatures(
    engine: ConsensusEngine, current_params: FluxParams
):
    newp = _safe_update_from(current_params, epoch_id="NK-2026.02-SEASON-1")
    engine.propose_update(newp, proposer="KO")
    assert engine.pending_proposal is not None
    assert engine.current_params.epoch_id == "NK-2026.02-SEASON-0"

    # 3/6 votes: should NOT commit
    engine.vote("AV", True, "sig-av")
    engine.vote("RU", True, "sig-ru")
    engine.vote("CA", True, "sig-ca")

    assert engine.current_params.epoch_id == "NK-2026.02-SEASON-0"
    assert engine.pending_proposal is not None
    assert len(engine.signatures) == 3

    # 4th vote: should commit
    engine.vote("UM", True, "sig-um")

    assert engine.current_params.epoch_id == "NK-2026.02-SEASON-1"
    assert engine.pending_proposal is None
    assert engine.signatures == {}


def test_vote_ignores_unknown_agent(
    engine: ConsensusEngine, current_params: FluxParams
):
    newp = _safe_update_from(current_params, epoch_id="NK-2026.02-SEASON-1")
    engine.propose_update(newp, proposer="KO")

    engine.vote("ZZ", True, "sig-zz")  # ignored
    assert engine.signatures == {}
    assert engine.current_params.epoch_id == "NK-2026.02-SEASON-0"
    assert engine.pending_proposal is not None


def test_manifest_hash_deterministic_for_same_values(current_params: FluxParams):
    p1 = _safe_update_from(
        current_params,
        lang_weights={"KO": 2.0, "RU": 0.5, "DR": 0.5, "CA": 1.0, "AV": 0.8, "UM": 0.8},
    )
    # same content, different insertion order
    p2 = _safe_update_from(
        current_params,
        lang_weights={"UM": 0.8, "AV": 0.8, "CA": 1.0, "DR": 0.5, "RU": 0.5, "KO": 2.0},
    )

    assert p1.canonical_json() == p2.canonical_json()
    assert p1.compute_hash() == p2.compute_hash()


def test_create_voxel_header_binds_epoch_and_param_hash(
    monkeypatch, current_params: FluxParams
):
    monkeypatch.setattr("time.time", lambda: 123.456)

    hdr = create_voxel_header("vox-001", current_params)
    assert hdr["vid"] == "vox-001"
    assert hdr["ts"] == 123.456
    assert hdr["epoch"] == current_params.epoch_id
    assert hdr["param_hash"] == current_params.compute_hash()
