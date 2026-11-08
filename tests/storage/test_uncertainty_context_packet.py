from __future__ import annotations

import pytest

from src.storage.uncertainty_context_packet import (
    build_uncertainty_context_packet,
    make_context_tangent,
)


def _source_hash(character: str) -> str:
    return character * 64


def _tangent(
    *,
    claim: str,
    source: str,
    group: str,
    support: int = 0,
    contradiction: int = 0,
    uncertainty: int = 0,
):
    return make_context_tangent(
        focus_id="word:bank",
        relation="possible-sense",
        claim=claim,
        evidence_kind="observed",
        source_hash=_source_hash(source),
        source_uri=f"local://{source}",
        provenance_group=group,
        support=support,
        contradiction=contradiction,
        uncertainty=uncertainty,
    )


def test_packet_keeps_exact_real_and_imaginary_axes() -> None:
    first = _tangent(claim="financial sense", source="a", group="source-a", support=3, uncertainty=1)
    duplicate_view = _tangent(
        claim="financial sense from another excerpt",
        source="a",
        group="source-a",
        support=3,
        uncertainty=1,
    )
    second = _tangent(
        claim="river edge sense",
        source="b",
        group="source-b",
        contradiction=1,
        uncertainty=1,
    )

    packet = build_uncertainty_context_packet("word:bank", [first, duplicate_view, second])

    assert packet["independent_provenance_group_count"] == 2
    assert packet["axes"]["support"]["numerator"] == 3
    assert packet["axes"]["support"]["denominator"] == 8
    assert packet["axes"]["contradiction"]["numerator"] == 1
    assert packet["axes"]["contradiction"]["denominator"] == 4
    assert packet["axes"]["real_net_support"]["numerator"] == 1
    assert packet["axes"]["real_net_support"]["denominator"] == 8
    assert packet["axes"]["imaginary_unresolved_uncertainty"]["numerator"] == 3
    assert packet["axes"]["imaginary_unresolved_uncertainty"]["denominator"] == 8


def test_repeated_views_from_one_source_do_not_add_independent_mass() -> None:
    one = _tangent(claim="one", source="a", group="same", support=3, uncertainty=1)
    two = _tangent(claim="two", source="a", group="same", support=3, uncertainty=1)

    single = build_uncertainty_context_packet("word:bank", [one])
    repeated = build_uncertainty_context_packet("word:bank", [one, two])

    assert single["axes"] == repeated["axes"]
    assert repeated["active_tangent_count"] == 2
    assert repeated["independent_provenance_group_count"] == 1


def test_absent_is_explicit_and_not_a_zero_weight_observation() -> None:
    absent = make_context_tangent(
        focus_id="word:bank",
        relation="visual-evidence",
        claim="",
        evidence_kind="absent",
        source_hash="",
        source_uri="",
    )

    packet = build_uncertainty_context_packet("word:bank", [absent])

    assert packet["active_tangent_count"] == 0
    assert packet["absent_tangent_count"] == 1
    assert packet["axes"]["imaginary_unresolved_uncertainty"] == {
        "numerator": 1,
        "denominator": 1,
        "float": 1.0,
    }


def test_invalid_mass_and_duplicate_identity_fail_closed() -> None:
    with pytest.raises(ValueError, match="positive integer base"):
        _tangent(claim="empty", source="a", group="a")
    tangent = _tangent(claim="one", source="a", group="a", support=1)
    with pytest.raises(ValueError, match="duplicate tangent"):
        build_uncertainty_context_packet("word:bank", [tangent, tangent])


def test_packet_is_order_stable() -> None:
    one = _tangent(claim="one", source="a", group="a", support=2, uncertainty=1)
    two = _tangent(claim="two", source="b", group="b", contradiction=1, uncertainty=2)
    forward = build_uncertainty_context_packet("word:bank", [one, two])
    reverse = build_uncertainty_context_packet("word:bank", [two, one])
    assert forward == reverse
