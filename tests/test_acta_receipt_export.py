"""ACTA (draft-farley-acta-signed-receipts-01) export locks.

The receipt envelope is {payload, signature}; signatures are computed over the
exact JCS bytes of the payload and hex-encoded; chains link via
previousReceiptHash = SHA-256(JCS(entire signed receipt)).
"""

from __future__ import annotations

import hashlib

from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionLedger,
    ReactionRecalculation,
    acta_receipt_hash,
    jcs_dumps,
    packet_to_acta_receipt,
    rekor_hashedrekord_entry,
    verify_acta_chain,
    verify_acta_receipt,
)


def _kwargs(**overrides):
    base = dict(
        domain="chem",
        step=1,
        bounded_operation="balance_reaction",
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


def test_acta_receipt_envelope_shape_and_action_ref():
    ledger = ReactionLedger(agent_id="test-acta")
    packet = ledger.append(**_kwargs())
    receipt = packet_to_acta_receipt(packet, issuer_id="test-acta")
    payload = receipt["payload"]
    assert payload["type"] == "scbe:reaction-state"
    assert payload["issued_at"].endswith("Z")  # RFC 3339 with timezone designator
    assert payload["issuer_id"] == "test-acta"
    assert payload["packet_hash"] == packet.packet_hash
    assert payload["classification"] == "BIJECTIVE"
    # action_ref is the SHA-256 of the JCS canonicalization of the action.
    expected_ref = hashlib.sha256(jcs_dumps(packet.unsigned_dict()).encode("utf-8")).hexdigest()
    assert payload["action_ref"] == expected_ref
    # First receipt in a chain has no previousReceiptHash key at all.
    assert "previousReceiptHash" not in payload
    # Signature, when present, uses ACTA algorithm identifiers and hex encoding.
    if receipt["signature"] is not None:
        assert receipt["signature"]["alg"] in ("ML-DSA-65", "EdDSA")
        assert receipt["signature"]["kid"] == "test-acta"
        sig = receipt["signature"]["sig"]
        assert sig == sig.lower() and int(sig, 16) >= 0  # lowercase hex


def test_acta_chain_links_by_receipt_hash_and_detects_tamper():
    ledger = ReactionLedger(agent_id="test-acta-chain")
    for i in range(3):
        ledger.append(**_kwargs(step=i + 1, generated_at_utc=f"2026-06-12T00:00:0{i}Z"))
    chain = ledger.acta_chain()
    assert len(chain) == 3
    assert verify_acta_chain(chain) is True
    # Each link is the hash of the ENTIRE previous signed receipt (draft 5.7).
    assert chain[1]["payload"]["previousReceiptHash"] == acta_receipt_hash(chain[0])
    assert chain[2]["payload"]["previousReceiptHash"] == acta_receipt_hash(chain[1])
    # Tampering with any receipt breaks the keyless linkage check.
    tampered = [dict(chain[0]), chain[1], chain[2]]
    tampered[0] = {"payload": dict(chain[0]["payload"]), "signature": chain[0]["signature"]}
    tampered[0]["payload"]["bounded_operation"] = "forged"
    assert verify_acta_chain(tampered) is False
    # Dropping a middle receipt also breaks linkage.
    assert verify_acta_chain([chain[0], chain[2]]) is False


def test_acta_signature_verifies_over_exact_jcs_bytes():
    ledger = ReactionLedger(agent_id="test-acta-sig")
    packet = ledger.append(**_kwargs())
    receipt = packet_to_acta_receipt(packet, issuer_id="test-acta-sig")
    if receipt["signature"] is None:
        import pytest

        pytest.skip("no asymmetric signer backend available")
    from agents.agent_bus_signing import EventSigner

    signer = EventSigner("test-acta-sig")
    assert signer.initialize()
    assert verify_acta_receipt(receipt, signer.public_key_b64) is True
    # A flipped payload field must fail against the same signature.
    forged = {"payload": dict(receipt["payload"]), "signature": receipt["signature"]}
    forged["payload"]["classification"] = "INVALID"
    assert verify_acta_receipt(forged, signer.public_key_b64) is False


def test_rekor_entry_is_anchor_ready_and_offline():
    ledger = ReactionLedger(agent_id="test-rekor", sign=False)
    ledger.append(**_kwargs())
    cp = ledger.checkpoint()
    entry = rekor_hashedrekord_entry(cp)
    assert entry["apiVersion"] == "0.0.1"
    assert entry["kind"] == "hashedrekord"
    digest = entry["spec"]["data"]["hash"]
    assert digest["algorithm"] == "sha256"
    assert digest["value"] == hashlib.sha256(jcs_dumps(cp).encode("utf-8")).hexdigest()
    # Dry-run by design: no signature material is invented.
    assert entry["spec"]["signature"]["content"] is None
    assert entry["spec"]["signature"]["publicKey"]["content"] is None
