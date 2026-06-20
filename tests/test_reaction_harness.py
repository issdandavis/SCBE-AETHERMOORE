from __future__ import annotations

from python.scbe.reaction_harness import evaluate_bijective_reaction
from python.scbe.reaction_state import ReactionEndpoint, ReactionRecalculation
from python.scbe.quasi_integer_recoupling import recouple_bond_order


def endpoint(identity: str, representation: str = "field-map") -> ReactionEndpoint:
    return ReactionEndpoint(identity=identity, representation=representation)


def test_exact_field_round_trip_is_bijective() -> None:
    result = evaluate_bijective_reaction(
        domain="code",
        bounded_operation="python_to_js_behavior_roundtrip",
        source=endpoint("is_palindrome", "python:function"),
        target=endpoint("isPalindrome", "javascript:function"),
        source_fields={
            "behavior_hash": "sha256:abc",
            "test_vector_hash": "sha256:cases",
        },
        target_fields={
            "behavior_hash": "sha256:abc",
            "test_vector_hash": "sha256:cases",
        },
        required_identity_fields=("behavior_hash", "test_vector_hash"),
        generated_at_utc="2026-05-31T00:00:00Z",
    )

    assert result.ok is True
    assert result.packet.classification == "BIJECTIVE"
    assert result.preserved_fields == ["behavior_hash", "test_vector_hash"]
    assert result.packet.verify_hash() is True


def test_atom_bag_without_topology_recovery_stays_ambiguous() -> None:
    result = evaluate_bijective_reaction(
        domain="chem",
        bounded_operation="formula_only_recompose",
        source=endpoint("ethanol", "canonical_smiles"),
        target=endpoint("formula-bag", "formula"),
        source_fields={
            "formula": "C2H6O",
            "canonical_smiles": "CCO",
            "hydroxyl_count": 1,
        },
        target_fields={"formula": "C2H6O"},
        required_identity_fields=("formula", "canonical_smiles"),
        allowed_loss_fields=("hydroxyl_count",),
        claim_boundary=("computational chemistry only",),
        generated_at_utc="2026-05-31T00:00:00Z",
    )

    assert result.ok is False
    assert result.packet.classification == "LOSSY_AMBIGUOUS"
    assert result.preserved_fields == ["formula"]
    assert result.lost_fields == ["canonical_smiles"]
    assert result.ignored_loss_fields == ["hydroxyl_count"]


def test_recovery_lane_restores_identity_after_mud_step() -> None:
    result = evaluate_bijective_reaction(
        domain="chem",
        bounded_operation="atom_mud_recover_with_fragment_cards",
        source=endpoint("ethanol", "canonical_smiles"),
        target=endpoint("formula-bag", "formula"),
        source_fields={
            "formula": "C2H6O",
            "canonical_smiles": "CCO",
            "hydroxyl_count": 1,
            "connectivity": "C-C-O",
        },
        target_fields={"formula": "C2H6O"},
        recoverable_fields={
            "canonical_smiles": "CCO",
            "hydroxyl_count": 1,
        },
        required_identity_fields=("formula", "canonical_smiles", "hydroxyl_count"),
        allowed_loss_fields=("connectivity",),
        semantic_engravings=("fragment cards carried hydroxyl identity",),
        claim_boundary=("computational chemistry only",),
        generated_at_utc="2026-05-31T00:00:00Z",
    )

    assert result.ok is True
    assert result.packet.classification == "LOSSY_RECOVERABLE"
    assert result.preserved_fields == ["formula"]
    assert result.recovered_fields == ["canonical_smiles", "hydroxyl_count"]
    assert result.ignored_loss_fields == ["connectivity"]


def test_failed_recalculation_marks_result_invalid() -> None:
    result = evaluate_bijective_reaction(
        domain="code",
        bounded_operation="translate_with_test_failure",
        source=endpoint("add", "python:function"),
        target=endpoint("add", "javascript:function"),
        source_fields={"behavior_hash": "sha256:abc"},
        target_fields={"behavior_hash": "sha256:abc"},
        required_identity_fields=("behavior_hash",),
        recalculation=ReactionRecalculation(syntax_ok=True, tests_ok=False),
        generated_at_utc="2026-05-31T00:00:00Z",
    )

    assert result.ok is False
    assert result.packet.classification == "INVALID"
    assert result.preserved_fields == ["behavior_hash"]


def test_recoupled_fractional_fields_can_preserve_identity() -> None:
    result = evaluate_bijective_reaction(
        domain="chem",
        bounded_operation="fractional_bond_order_to_symbolic_state",
        source=endpoint("aromatic-fragment", "field-map"),
        target=endpoint("aromatic-fragment", "field-map"),
        source_fields={
            "bond_order_state": recouple_bond_order(1.49, tolerance=0.1),
        },
        target_fields={
            "bond_order_state": 1.5,
        },
        required_identity_fields=("bond_order_state",),
        generated_at_utc="2026-05-31T00:00:00Z",
    )

    assert result.ok is True
    assert result.packet.classification == "BIJECTIVE"
    assert result.field_checks[0].source_value["label"] == "aromatic-or-resonance-like"
