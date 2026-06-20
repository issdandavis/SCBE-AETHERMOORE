from __future__ import annotations

from dataclasses import replace

import pytest

from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionLedger,
    ReactionRecalculation,
    build_reaction_state_packet,
    classify_reaction,
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
        generated_at_utc="2026-06-11T00:00:00Z",
    )
    base.update(overrides)
    return base


def _sample_packet(**overrides):
    return build_reaction_state_packet(**_kwargs(**overrides))


def test_bijective_packet_hash_verifies() -> None:
    source = ReactionEndpoint(identity="is_palindrome", representation="python:function", tongue="KO")
    target = ReactionEndpoint(identity="isPalindrome", representation="javascript:function", tongue="DR")
    recalculation = ReactionRecalculation(syntax_ok=True, tests_ok=True, identity_ok=True)

    packet = build_reaction_state_packet(
        domain="code",
        step=4,
        bounded_operation="translate",
        source=source,
        target=target,
        semantic_engravings=[
            "function behavior preserved",
            "snake_case renamed to camelCase",
        ],
        loss_notes=[],
        recalculation=recalculation,
        identity_preserved=True,
        generated_at_utc="2026-05-31T00:00:00Z",
    )

    assert packet.schema_version == "scbe_reaction_state_packet_v1"
    assert packet.classification == "BIJECTIVE"
    assert packet.packet_hash
    assert packet.verify_hash() is True
    assert packet.tongue_columns["UM"] == "uncertainty_loss"


def test_lossy_recoverable_classification_requires_recovery_evidence() -> None:
    recalculation = ReactionRecalculation(scientific_checks_ok=True, identity_ok=True)

    classification = classify_reaction(
        recalculation=recalculation,
        identity_preserved=True,
        loss_notes=["topology dropped at atom mud step"],
        recovery_evidence=["hydroxyl fragment card restored identity"],
    )

    assert classification == "LOSSY_RECOVERABLE"


def test_ambiguous_atom_bag_stays_ambiguous_without_recovery() -> None:
    recalculation = ReactionRecalculation(scientific_checks_ok=True, identity_ok=None)

    classification = classify_reaction(
        recalculation=recalculation,
        identity_preserved=False,
        loss_notes=["ethanol and dimethyl ether both reduce to C2H6O"],
        recovery_evidence=[],
    )

    assert classification == "LOSSY_AMBIGUOUS"


def test_failed_recalculation_is_invalid() -> None:
    recalculation = ReactionRecalculation(syntax_ok=True, tests_ok=False, identity_ok=True)

    classification = classify_reaction(
        recalculation=recalculation,
        identity_preserved=True,
        loss_notes=[],
        recovery_evidence=[],
    )

    assert classification == "INVALID"


def test_signing_preserves_the_content_hash() -> None:
    # Signing must never invalidate the integrity hash: the hash is computed over
    # content that excludes the signature fields, so an unsigned packet and its
    # signed self carry the identical packet_hash (backward compatibility).
    packet = _sample_packet()
    signed = packet.sign("scbe-test-signing")

    assert signed.packet_hash == packet.packet_hash
    assert signed.verify_hash() is True


def test_packet_signature_verifies_and_tamper_is_caught() -> None:
    signed = _sample_packet().sign("scbe-test-signing")

    if signed.signature_alg in (None, "unsigned", "HMAC-SHA512-sim"):
        pytest.skip(f"no public-key signer available (alg={signed.signature_alg})")

    assert signed.signature
    assert signed.signer_public_key
    # Real public-key signature over the content verifies...
    assert signed.verify_signature() is True
    # ...and any tamper to signed content flips verification to not-True.
    tampered = replace(signed, semantic_engravings=["e", "tampered"])
    assert tampered.verify_signature() is not True


def test_reaction_ledger_anchors_chain_and_verifies() -> None:
    ledger = ReactionLedger("scbe-test-ledger")
    p1 = ledger.append(**_kwargs(step=1, bounded_operation="first"))
    p2 = ledger.append(**_kwargs(step=2, bounded_operation="second"))

    # The chain is hash-linked: each packet anchors the prior packet's hash.
    assert p1.previous_packet_hash is None
    assert p2.previous_packet_hash == p1.packet_hash
    assert p2.packet_hash != p1.packet_hash
    assert ledger.verify() is True


def test_reaction_ledger_chains_prebuilt_packets() -> None:
    # Domain builders return standalone packets (each with previous_packet_hash
    # = None); append_packet re-anchors and signs them into one chain.
    ledger = ReactionLedger("scbe-test-ledger")
    standalone_a = _sample_packet(step=1, bounded_operation="balance")
    standalone_b = _sample_packet(step=2, bounded_operation="geometry")
    assert standalone_a.previous_packet_hash is None
    assert standalone_b.previous_packet_hash is None

    a = ledger.append_packet(standalone_a)
    b = ledger.append_packet(standalone_b)

    assert a.previous_packet_hash is None
    assert b.previous_packet_hash == a.packet_hash
    assert ledger.verify() is True


def test_reaction_ledger_detects_a_broken_link() -> None:
    ledger = ReactionLedger("scbe-test-ledger")
    ledger.append(**_kwargs(step=1, bounded_operation="first"))
    ledger.append(**_kwargs(step=2, bounded_operation="second"))

    # Snap the chain by rewriting the second packet's anchor; verify() must fail.
    ledger.packets[1] = replace(ledger.packets[1], previous_packet_hash="deadbeef")
    assert ledger.verify() is False
