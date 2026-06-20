"""Merkle checkpointing locks for the reaction ledger (RFC 6962 tree shape)."""

from __future__ import annotations

import hashlib

from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionLedger,
    ReactionRecalculation,
    merkle_audit_path,
    merkle_tree_head,
    verify_checkpoint,
    verify_merkle_inclusion,
)


def _kwargs(**overrides):
    base = dict(
        domain="code",
        step=1,
        bounded_operation="op",
        source=ReactionEndpoint(identity="a", representation="x", tongue="KO"),
        target=ReactionEndpoint(identity="b", representation="y", tongue="DR"),
        semantic_engravings=["e"],
        loss_notes=[],
        recalculation=ReactionRecalculation(identity_ok=True),
        identity_preserved=True,
        generated_at_utc="2026-06-12T00:00:00Z",
    )
    base.update(overrides)
    return base


def _fake_hashes(n: int) -> list[str]:
    return [hashlib.sha256(f"packet-{i}".encode()).hexdigest() for i in range(n)]


def test_merkle_inclusion_proofs_verify_for_every_leaf_at_every_size():
    """Property lock: RFC 6962 head + audit path + RFC 9162 verify agree for
    every leaf index at every tree size 1..16 (covers perfect and ragged trees)."""
    for size in range(1, 17):
        hashes = _fake_hashes(size)
        root = merkle_tree_head(hashes)
        for index in range(size):
            path = merkle_audit_path(hashes, index)
            assert verify_merkle_inclusion(hashes[index], index, size, path, root), (size, index)
            # A tampered leaf must fail against the same path + root.
            tampered = _fake_hashes(size + 1)[size]
            assert not verify_merkle_inclusion(tampered, index, size, path, root)
            # A wrong index must fail.
            if size > 1:
                assert not verify_merkle_inclusion(hashes[index], (index + 1) % size, size, path, root)


def test_merkle_root_changes_on_omission_and_reorder():
    hashes = _fake_hashes(5)
    full = merkle_tree_head(hashes)
    assert merkle_tree_head(hashes[:-1]) != full
    assert merkle_tree_head(hashes[1:]) != full
    swapped = [hashes[1], hashes[0], *hashes[2:]]
    assert merkle_tree_head(swapped) != full


def test_ledger_checkpoint_commits_count_root_and_chain():
    ledger = ReactionLedger(agent_id="test-checkpoint")
    for i in range(4):
        ledger.append(**_kwargs(step=i + 1, generated_at_utc=f"2026-06-12T00:00:0{i}Z"))
    cp = ledger.checkpoint()
    assert cp["schema_version"] == "scbe_reaction_ledger_checkpoint_v1"
    assert cp["tree_size"] == 4
    assert cp["merkle_root"] == ledger.merkle_root()
    assert cp["chain_verified"] is True
    assert cp["last_packet_hash"] == ledger.packets[-1].packet_hash
    for i in range(4):
        proof = ledger.inclusion_proof(i)
        assert proof["merkle_root"] == cp["merkle_root"]
        assert verify_merkle_inclusion(
            proof["packet_hash"], proof["leaf_index"], proof["tree_size"], proof["audit_path"], cp["merkle_root"]
        )
    # Signature mirrors the packets: True (asymmetric) or None (no signer backend),
    # never False for an honest checkpoint.
    assert verify_checkpoint(cp) in (True, None)
    if cp["signature"]:
        forged = dict(cp)
        forged["tree_size"] = 5
        assert verify_checkpoint(forged) is False


def test_checkpoint_detects_truncated_ledger():
    """The omission attack the linear chain cannot see: re-checkpointing a
    truncated ledger yields a different root and size than the original."""
    ledger = ReactionLedger(agent_id="test-truncate", sign=False)
    for i in range(5):
        ledger.append(**_kwargs(step=i + 1))
    before = ledger.checkpoint()
    ledger.packets.pop()
    ledger._last_hash = ledger.packets[-1].packet_hash
    assert ledger.verify() is True  # linear chain is blind to the omission
    after = ledger.checkpoint()
    assert after["tree_size"] != before["tree_size"]
    assert after["merkle_root"] != before["merkle_root"]
