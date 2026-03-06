"""Tests for Sacred Egg Genesis Lifecycle (G0-G4).

Validates the canonical lifecycle: Proposal → Sealing → Ritual → Decision → Spawn.

@pytest.mark.crypto
@pytest.mark.unit
"""

import math
import os
import secrets

import pytest

from src.symphonic_cipher.scbe_aethermoore.sacred_egg_genesis_lifecycle import (
    GENESIS_THRESHOLD,
    PHI,
    TONGUE_WEIGHTS,
    Decision,
    GenesisProof,
    SacredEgg,
    SpawnedEntity,
    ValidatorVote,
    cast_vote,
    check_geometric_admissibility,
    check_payload_integrity,
    compute_quorum_weight,
    evaluate_ritual,
    full_genesis_lifecycle,
    genesis_noise,
    propose_egg,
    seal_egg,
    spawn_entity,
    verify_seal,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_payload():
    return b"agent-init:model=claude-4,role=researcher,max_tokens=4096"


@pytest.fixture
def signer_key():
    return secrets.token_bytes(32)


@pytest.fixture
def sample_egg(sample_payload):
    return propose_egg(
        entity_type="agent",
        proposer_id="proposer-001",
        purpose="research assistant",
        init_payload=sample_payload,
        target_realm="research-lab",
        geometric_anchor=[0.1, 0.2, 0.1],
        d_star_max=2.0,
        epoch=1,
    )


@pytest.fixture
def voted_egg(sample_egg):
    """An egg with sufficient votes to pass quorum."""
    # Need quorum_weight >= phi^3 ~ 4.236
    # CA=4.24, UM=6.85, DR=11.09 — any one of CA+KO or UM or DR suffices
    cast_vote(sample_egg, "v1", "DR", True, secrets.token_bytes(32))
    return sample_egg


# =============================================================================
# G0 — Proposal
# =============================================================================


class TestG0Proposal:
    def test_propose_egg_creates_valid_egg(self, sample_payload):
        egg = propose_egg(
            entity_type="agent",
            proposer_id="proposer-001",
            purpose="test agent",
            init_payload=sample_payload,
        )
        assert egg.egg_id is not None
        assert len(egg.egg_id) == 16
        assert egg.entity_type == "agent"
        assert egg.proposer_id == "proposer-001"
        assert egg.purpose == "test agent"
        assert len(egg.init_payload_ciphertext) > 0
        assert len(egg.init_payload_hash) == 64
        assert egg.votes == []
        assert egg.decision is None
        assert egg.hatch_proof is None

    def test_propose_egg_unique_ids(self, sample_payload):
        egg1 = propose_egg("agent", "p1", "purpose1", sample_payload)
        egg2 = propose_egg("agent", "p1", "purpose2", sample_payload)
        assert egg1.egg_id != egg2.egg_id

    def test_propose_egg_with_geometry(self, sample_payload):
        anchor = [0.1, 0.2, 0.3]
        egg = propose_egg(
            entity_type="realm",
            proposer_id="p1",
            purpose="new realm",
            init_payload=sample_payload,
            geometric_anchor=anchor,
            d_star_max=1.5,
        )
        assert egg.geometric_anchor == anchor
        assert egg.d_star_max == 1.5

    def test_propose_egg_entity_types(self, sample_payload):
        for etype in ("agent", "realm", "subsystem", "service"):
            egg = propose_egg(etype, "p1", "test", sample_payload)
            assert egg.entity_type == etype

    def test_propose_egg_default_threshold(self, sample_payload):
        egg = propose_egg("agent", "p1", "test", sample_payload)
        assert egg.required_phi_weight == pytest.approx(GENESIS_THRESHOLD, rel=1e-6)

    def test_propose_egg_custom_threshold(self, sample_payload):
        egg = propose_egg(
            "agent", "p1", "test", sample_payload, required_phi_weight=2.0
        )
        assert egg.required_phi_weight == 2.0


# =============================================================================
# G1 — Sealing
# =============================================================================


class TestG1Sealing:
    def test_seal_produces_hex_string(self, sample_egg, signer_key):
        seal = seal_egg(sample_egg, signer_key)
        assert isinstance(seal, str)
        assert len(seal) == 64  # SHA-256 hex

    def test_seal_deterministic(self, sample_egg, signer_key):
        seal1 = seal_egg(sample_egg, signer_key)
        seal2 = seal_egg(sample_egg, signer_key)
        assert seal1 == seal2

    def test_seal_changes_with_key(self, sample_egg):
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        seal1 = seal_egg(sample_egg, key1)
        seal2 = seal_egg(sample_egg, key2)
        assert seal1 != seal2

    def test_verify_seal_valid(self, sample_egg, signer_key):
        seal = seal_egg(sample_egg, signer_key)
        assert verify_seal(sample_egg, seal, signer_key) is True

    def test_verify_seal_wrong_key(self, sample_egg, signer_key):
        seal = seal_egg(sample_egg, signer_key)
        wrong_key = secrets.token_bytes(32)
        assert verify_seal(sample_egg, seal, wrong_key) is False


# =============================================================================
# G2 — Ritual Validation
# =============================================================================


class TestG2Ritual:
    def test_cast_vote(self, sample_egg):
        key = secrets.token_bytes(32)
        vote = cast_vote(sample_egg, "validator-1", "KO", True, key)
        assert vote.validator_id == "validator-1"
        assert vote.tongue == "KO"
        assert vote.weight == pytest.approx(1.0)
        assert vote.approved is True
        assert len(vote.signature) == 64
        assert len(sample_egg.votes) == 1

    def test_tongue_weights_phi_scaling(self):
        assert TONGUE_WEIGHTS["KO"] == pytest.approx(1.0)
        assert TONGUE_WEIGHTS["AV"] == pytest.approx(PHI, rel=1e-6)
        assert TONGUE_WEIGHTS["RU"] == pytest.approx(PHI ** 2, rel=1e-6)
        assert TONGUE_WEIGHTS["CA"] == pytest.approx(PHI ** 3, rel=1e-6)
        assert TONGUE_WEIGHTS["UM"] == pytest.approx(PHI ** 4, rel=1e-6)
        assert TONGUE_WEIGHTS["DR"] == pytest.approx(PHI ** 5, rel=1e-6)

    def test_compute_quorum_weight_approved_only(self):
        votes = [
            ValidatorVote("v1", "KO", 1.0, True, "sig1"),
            ValidatorVote("v2", "AV", PHI, False, "sig2"),
            ValidatorVote("v3", "DR", PHI ** 5, True, "sig3"),
        ]
        w = compute_quorum_weight(votes)
        assert w == pytest.approx(1.0 + PHI ** 5, rel=1e-6)

    def test_compute_quorum_weight_none_approved(self):
        votes = [
            ValidatorVote("v1", "KO", 1.0, False, "sig1"),
        ]
        assert compute_quorum_weight(votes) == 0.0

    def test_geometric_admissibility_no_anchor(self, sample_payload):
        egg = propose_egg("agent", "p1", "test", sample_payload)
        ok, d = check_geometric_admissibility(egg, [0.5, 0.5, 0.5])
        assert ok is True
        assert d == 0.0

    def test_geometric_admissibility_same_point(self, sample_payload):
        anchor = [0.1, 0.2, 0.1]
        egg = propose_egg(
            "agent", "p1", "test", sample_payload,
            geometric_anchor=anchor, d_star_max=2.0,
        )
        ok, d = check_geometric_admissibility(egg, anchor)
        assert ok is True
        assert d < 0.001

    def test_geometric_admissibility_far_point(self, sample_payload):
        anchor = [0.0, 0.0, 0.0]
        egg = propose_egg(
            "agent", "p1", "test", sample_payload,
            geometric_anchor=anchor, d_star_max=0.5,
        )
        ok, d = check_geometric_admissibility(egg, [0.9, 0.0, 0.0])
        assert ok is False
        assert d > 0.5

    def test_payload_integrity_valid(self, sample_egg):
        assert check_payload_integrity(sample_egg) is True

    def test_payload_integrity_empty_hash(self, sample_payload):
        egg = propose_egg("agent", "p1", "test", sample_payload)
        egg.init_payload_hash = ""
        assert check_payload_integrity(egg) is False


# =============================================================================
# G3 — Hatching Decision
# =============================================================================


class TestG3Decision:
    def test_hatch_with_sufficient_quorum(self, voted_egg):
        decision, report = evaluate_ritual(voted_egg)
        assert decision == "HATCH"
        assert report["quorum_pass"] is True
        assert report["integrity_pass"] is True

    def test_deny_with_no_votes(self, sample_egg):
        decision, report = evaluate_ritual(sample_egg)
        assert decision == "DENY"
        assert report["quorum_pass"] is False

    def test_deny_with_insufficient_quorum(self, sample_egg):
        cast_vote(sample_egg, "v1", "KO", True, secrets.token_bytes(32))
        decision, report = evaluate_ritual(sample_egg)
        # KO weight = 1.0, threshold = phi^3 ~ 4.236
        assert decision == "DENY"

    def test_quarantine_with_geometry_fail(self, sample_payload):
        egg = propose_egg(
            "agent", "p1", "test", sample_payload,
            geometric_anchor=[0.0, 0.0, 0.0], d_star_max=0.1,
        )
        # Add enough votes to pass quorum
        cast_vote(egg, "v1", "DR", True, secrets.token_bytes(32))
        decision, report = evaluate_ritual(
            egg, current_position=[0.9, 0.0, 0.0]
        )
        assert decision == "QUARANTINE"
        assert report["geometric_pass"] is False

    def test_quarantine_with_governance_risk(self, sample_payload):
        egg = propose_egg("agent", "p1", "test", sample_payload)
        cast_vote(egg, "v1", "DR", True, secrets.token_bytes(32))
        decision, report = evaluate_ritual(
            egg, governance_risk=2.0, max_governance_risk=1.0
        )
        assert decision == "QUARANTINE"
        assert report["governance_pass"] is False

    def test_decision_stored_on_egg(self, voted_egg):
        evaluate_ritual(voted_egg)
        assert voted_egg.decision == "HATCH"

    def test_coherence_computed(self, voted_egg):
        evaluate_ritual(voted_egg)
        assert voted_egg.coherence is not None
        assert voted_egg.coherence > 0

    def test_h_eff_computed(self, voted_egg):
        evaluate_ritual(voted_egg)
        assert voted_egg.h_eff is not None
        assert 0 < voted_egg.h_eff <= 1.0


# =============================================================================
# G4 — Spawn
# =============================================================================


class TestG4Spawn:
    def test_spawn_entity_from_hatched_egg(self, voted_egg, sample_payload):
        evaluate_ritual(voted_egg)
        assert voted_egg.decision == "HATCH"

        entity, proof = spawn_entity(
            voted_egg,
            decryption_key=b"x" * 32,
            governance_envelope={"max_actions": 100},
        )

        # Entity checks
        assert isinstance(entity, SpawnedEntity)
        assert entity.entity_type == "agent"
        assert entity.init_payload == sample_payload
        assert entity.governance_limits == {"max_actions": 100}
        assert entity.origin_egg_id == voted_egg.egg_id
        assert entity.origin_realm == "research-lab"

        # Proof checks
        assert isinstance(proof, GenesisProof)
        assert proof.egg_id == voted_egg.egg_id
        assert proof.entity_id == entity.entity_id
        assert proof.entity_type == "agent"
        assert proof.proposer_id == "proposer-001"
        assert len(proof.validators) > 0
        assert proof.quorum_weight >= GENESIS_THRESHOLD
        assert len(proof.genesis_seal) == 64

    def test_spawn_blocked_for_denied_egg(self, sample_egg):
        evaluate_ritual(sample_egg)
        assert sample_egg.decision == "DENY"

        with pytest.raises(PermissionError, match="DENY"):
            spawn_entity(sample_egg, decryption_key=b"x" * 32)

    def test_spawn_blocked_for_quarantined_egg(self, sample_payload):
        egg = propose_egg(
            "agent", "p1", "test", sample_payload,
            geometric_anchor=[0.0, 0.0, 0.0], d_star_max=0.1,
        )
        cast_vote(egg, "v1", "DR", True, secrets.token_bytes(32))
        evaluate_ritual(egg, current_position=[0.9, 0.0, 0.0])
        assert egg.decision == "QUARANTINE"

        with pytest.raises(PermissionError, match="QUARANTINE"):
            spawn_entity(egg, decryption_key=b"x" * 32)

    def test_hatch_proof_attached_to_egg(self, voted_egg, sample_payload):
        evaluate_ritual(voted_egg)
        spawn_entity(voted_egg, decryption_key=b"x" * 32)
        assert voted_egg.hatch_proof is not None
        assert "entity_id" in voted_egg.hatch_proof
        assert "genesis_seal" in voted_egg.hatch_proof
        assert "validators" in voted_egg.hatch_proof

    def test_payload_roundtrip_integrity(self, sample_payload):
        """The decrypted payload must match the original."""
        egg = propose_egg("agent", "p1", "test", sample_payload)
        cast_vote(egg, "v1", "DR", True, secrets.token_bytes(32))
        evaluate_ritual(egg)
        entity, _ = spawn_entity(egg, decryption_key=b"x" * 32)
        assert entity.init_payload == sample_payload


# =============================================================================
# Fail-to-Noise
# =============================================================================


class TestFailToNoise:
    def test_noise_deterministic(self, sample_egg):
        n1 = genesis_noise(sample_egg)
        n2 = genesis_noise(sample_egg)
        assert n1 == n2

    def test_noise_different_for_different_eggs(self, sample_payload):
        egg1 = propose_egg("agent", "p1", "purpose1", sample_payload)
        egg2 = propose_egg("agent", "p1", "purpose2", sample_payload)
        n1 = genesis_noise(egg1)
        n2 = genesis_noise(egg2)
        assert n1 != n2

    def test_noise_length_consistent(self, sample_egg):
        noise = genesis_noise(sample_egg)
        ct_len = len(sample_egg.init_payload_ciphertext) // 2
        assert len(noise) == ct_len


# =============================================================================
# Full Lifecycle
# =============================================================================


class TestFullLifecycle:
    def test_full_lifecycle_hatch(self, sample_payload):
        signer_key = secrets.token_bytes(32)
        validator_votes = [
            ("v1", "DR", True, secrets.token_bytes(32)),
            ("v2", "UM", True, secrets.token_bytes(32)),
        ]
        entity, proof, decision, report = full_genesis_lifecycle(
            entity_type="agent",
            proposer_id="proposer-001",
            purpose="research bot",
            init_payload=sample_payload,
            validator_votes=validator_votes,
            signer_key=signer_key,
            target_realm="lab",
        )
        assert decision == "HATCH"
        assert entity is not None
        assert proof is not None
        assert entity.init_payload == sample_payload
        assert entity.origin_realm == "lab"
        assert proof.entity_type == "agent"

    def test_full_lifecycle_deny(self, sample_payload):
        signer_key = secrets.token_bytes(32)
        validator_votes = [
            ("v1", "KO", False, secrets.token_bytes(32)),
        ]
        entity, proof, decision, report = full_genesis_lifecycle(
            entity_type="agent",
            proposer_id="p1",
            purpose="test",
            init_payload=sample_payload,
            validator_votes=validator_votes,
            signer_key=signer_key,
        )
        assert decision == "DENY"
        assert entity is None
        assert proof is None

    def test_full_lifecycle_quarantine_geo(self, sample_payload):
        signer_key = secrets.token_bytes(32)
        validator_votes = [
            ("v1", "DR", True, secrets.token_bytes(32)),
        ]
        entity, proof, decision, report = full_genesis_lifecycle(
            entity_type="agent",
            proposer_id="p1",
            purpose="test",
            init_payload=sample_payload,
            validator_votes=validator_votes,
            signer_key=signer_key,
            geometric_anchor=[0.0, 0.0, 0.0],
            current_position=[0.95, 0.0, 0.0],
            d_star_max=0.1,
        )
        assert decision == "QUARANTINE"
        assert entity is None

    def test_genesis_threshold_is_phi_cubed(self):
        assert GENESIS_THRESHOLD == pytest.approx(PHI ** 3, rel=1e-10)
        assert GENESIS_THRESHOLD == pytest.approx(4.23606797749979, rel=1e-6)
