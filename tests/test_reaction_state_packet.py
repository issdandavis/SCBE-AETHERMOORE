from __future__ import annotations

from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    build_reaction_state_packet,
    classify_reaction,
)


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
