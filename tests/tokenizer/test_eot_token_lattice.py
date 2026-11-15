"""Exact EOT walls, shared-prefix folds, and bounded path races."""

from __future__ import annotations

from copy import deepcopy
import math

import pytest
import python.scbe.eot_token_lattice as eot_lattice

from python.scbe.eot_token_lattice import (
    EOTLatticeError,
    EOT_SYMBOL,
    CompositeRaceSpec,
    TokenProbability,
    TokenTableDistribution,
    build_interwoven_eot_lattice,
    race_interwoven_token_paths,
    verify_eot_race_receipt,
)


def _table(table_id: str, *, shifted: bool = False) -> TokenTableDistribution:
    probabilities = (0.3, 0.2, 0.1, 0.2, 0.2) if shifted else (0.4, 0.1, 0.1, 0.2, 0.2)
    return TokenTableDistribution(
        table_id,
        tuple(
            TokenProbability(token_id, text.encode().hex(), probability, text)
            for token_id, text, probability in zip(range(5), ("isu", "isk", "is", "m", "n"), probabilities, strict=True)
        ),
    )


def _node(lattice: dict, prefix: bytes) -> dict:
    node = lattice["nodes"][0]
    for byte_value in prefix:
        edge = next(edge for view in node["table_views"] for edge in view["edges"] if edge["symbol"] == byte_value)
        node = lattice["nodes"][edge["child_node_id"]]
    return node


def _view(lattice: dict, prefix: bytes, table_id: str) -> dict:
    node = _node(lattice, prefix)
    return next(row for row in node["table_views"] if row["table_id"] == table_id)


def test_eot_wall_preserves_short_token_mass_exactly() -> None:
    lattice = build_interwoven_eot_lattice((_table("teacher-a"),))
    view = _view(lattice, b"is", "teacher-a")
    distribution = {edge["symbol"]: edge["conditional_probability"] for edge in view["edges"]}
    assert distribution[ord("u")] == pytest.approx(2.0 / 3.0)
    assert distribution[ord("k")] == pytest.approx(1.0 / 6.0)
    assert distribution[EOT_SYMBOL] == pytest.approx(1.0 / 6.0)
    byte_edge = next(edge for edge in view["edges"] if edge["symbol"] == ord("u"))
    assert (byte_edge["root_address"]["orientation"] << 6) | byte_edge["root_address"]["opcode_cell"] == ord("u")
    assert next(edge for edge in view["edges"] if edge["symbol"] == EOT_SYMBOL)["root_address"] is None
    assert view["wall_mass"] == pytest.approx(0.1)
    assert view["continuation_mass"] == pytest.approx(0.5)
    assert view["fold_trit"] == -1
    assert lattice["alphabet"]["eot_is_not_a_byte"] is True
    assert lattice["metrics"]["all_path_masses_exact_within_1e_12"] is True
    assert lattice["receipt_security"] == "unkeyed-corruption-detection-only"
    for path in lattice["token_paths"]:
        assert path["reconstructed_path_mass"] == pytest.approx(path["exact_byte_path_mass"], abs=1e-12)


def test_tables_share_geometry_without_averaging_their_measures() -> None:
    lattice = build_interwoven_eot_lattice((_table("teacher-a"), _table("teacher-b", shifted=True)))
    node = _node(lattice, b"is")
    assert node["is_cross_table_intersection"] is True
    assert node["participating_table_count"] == 2
    assert node["table_pair_relationship_count"] == 1
    left = _view(lattice, b"is", "teacher-a")
    right = _view(lattice, b"is", "teacher-b")
    assert left["wall_mass"] == pytest.approx(0.1)
    assert right["wall_mass"] == pytest.approx(0.1)
    assert left["continuation_mass"] == pytest.approx(0.5)
    assert right["continuation_mass"] == pytest.approx(0.5)
    assert lattice["topology_contract"]["table_measures_remain_independent_at_shared_nodes"]


def test_composite_race_can_start_at_any_existing_prefix_cell() -> None:
    lattice = build_interwoven_eot_lattice((_table("teacher-a"), _table("teacher-b", shifted=True)))
    race = race_interwoven_token_paths(
        lattice,
        start_prefix=b"is",
        spec=CompositeRaceSpec(beam_width=8, max_steps=4, probability_power=1.5),
    )
    assert race["start_prefix_hex"] == b"is".hex()
    assert race["metrics"]["participating_table_count"] == 2
    assert race["metrics"]["multi_table_convergence_count"] == 3
    assert {row["continuation_byte_hex"] for row in race["convergence"]} == {
        "",
        b"u".hex(),
        b"k".hex(),
    }
    assert race["claim_boundary"]["one_next_token_distribution_only"] is True
    assert race["claim_boundary"]["new_distribution_required_after_eot"] is True
    assert race["claim_boundary"]["conditional_and_absolute_mass_are_separate"] is True
    assert race["metrics"]["search_exhaustive_within_lattice"] is True
    assert verify_eot_race_receipt(race, lattice) is True
    teacher_a = [row for row in race["completed_paths"] if row["table_id"] == "teacher-a"]
    by_suffix = {row["continuation_byte_hex"]: row for row in teacher_a}
    assert by_suffix[b"u".hex()]["conditional_probability_from_start"] == pytest.approx(2.0 / 3.0)
    assert by_suffix[b"u".hex()]["absolute_teacher_path_mass"] == pytest.approx(0.4)
    assert sum(row["conditional_probability_from_start"] for row in teacher_a) == pytest.approx(1.0)


def test_alias_tokens_reconstruct_aggregate_byte_path_mass() -> None:
    table = TokenTableDistribution(
        "aliases",
        (
            TokenProbability(1, b"x".hex(), 0.25),
            TokenProbability("1", b"x".hex(), 0.35),
            TokenProbability(2, b"y".hex(), 0.40),
        ),
    )
    lattice = build_interwoven_eot_lattice((table,))
    aliases = [row for row in lattice["token_paths"] if row["byte_hex"] == b"x".hex()]
    assert len(aliases) == 2
    assert all(row["byte_path_alias_count"] == 2 for row in aliases)
    assert all(row["exact_byte_path_mass"] == pytest.approx(0.60) for row in aliases)
    assert aliases[0]["typed_token_id"] != aliases[1]["typed_token_id"]


def test_lattice_receipt_and_probability_contract_fail_closed() -> None:
    lattice = build_interwoven_eot_lattice((_table("teacher-a"),))
    changed = deepcopy(lattice)
    changed["nodes"][0]["table_views"][0]["interior_mass"] = 0.5
    with pytest.raises(EOTLatticeError, match="receipt hash"):
        race_interwoven_token_paths(changed)

    with pytest.raises(ValueError, match="sum to one"):
        TokenTableDistribution(
            "bad",
            (TokenProbability(0, "61", 0.75), TokenProbability(1, "62", 0.20)),
        )


def test_zero_probability_identity_path_is_preserved_without_a_live_edge() -> None:
    table = TokenTableDistribution(
        "zero-path",
        (
            TokenProbability(0, b"a".hex(), 1.0),
            TokenProbability(1, b"z".hex(), 0.0),
        ),
    )
    lattice = build_interwoven_eot_lattice((table,))
    zero_path = next(row for row in lattice["token_paths"] if row["token_id"] == 1)
    assert zero_path["active_probability_path"] is False
    assert zero_path["exact_byte_path_mass"] == 0.0
    assert zero_path["reconstructed_path_mass"] == 0.0
    assert any(not step["positive_mass_edge_present"] for step in zero_path["steps"])
    assert lattice["metrics"]["zero_probability_path_count"] == 1


def test_composite_race_rejects_unbounded_work_product() -> None:
    with pytest.raises(ValueError, match=r"beam_width \* max_steps"):
        CompositeRaceSpec(beam_width=4096, max_steps=4096)


def test_race_reports_when_step_bound_leaves_live_frontier() -> None:
    lattice = build_interwoven_eot_lattice((_table("teacher-a"),))
    race = race_interwoven_token_paths(
        lattice,
        spec=CompositeRaceSpec(beam_width=16, max_steps=1),
    )
    assert race["metrics"]["max_step_limit_reached"] is True
    assert race["metrics"]["unfinished_frontier_count"] > 0
    assert race["metrics"]["search_exhaustive_within_lattice"] is False


def test_near_normalized_input_is_explicitly_normalized_before_telescoping() -> None:
    table = TokenTableDistribution(
        "near",
        (TokenProbability(0, b"a".hex(), 1.0000000005),),
    )
    lattice = build_interwoven_eot_lattice((table,))
    path = lattice["token_paths"][0]
    assert path["teacher_distribution_normalizer"] == pytest.approx(1.0000000005)
    assert path["exact_byte_path_mass"] == pytest.approx(1.0)
    assert path["reconstructed_path_mass"] == pytest.approx(1.0)


def test_input_row_order_does_not_change_lattice_receipt() -> None:
    rows = _table("stable").tokens
    forward = build_interwoven_eot_lattice((TokenTableDistribution("stable", rows),))
    reverse = build_interwoven_eot_lattice((TokenTableDistribution("stable", tuple(reversed(rows))),))
    assert forward["receipt_sha256"] == reverse["receipt_sha256"]


def test_total_decoded_token_work_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(eot_lattice, "MAX_TOTAL_TOKEN_BYTES", 3)
    table = TokenTableDistribution(
        "bounded",
        (
            TokenProbability(0, b"ab".hex(), 0.5),
            TokenProbability(1, b"cd".hex(), 0.5),
        ),
    )
    with pytest.raises(EOTLatticeError, match="total decoded token bytes"):
        build_interwoven_eot_lattice((table,))


def test_fold_trit_is_scale_independent_for_rare_live_paths() -> None:
    table = TokenTableDistribution(
        "tiny",
        (
            TokenProbability(0, b"z".hex(), 1e-20),
            TokenProbability(1, b"bc".hex(), 1.0),
        ),
    )
    lattice = build_interwoven_eot_lattice((table,))
    assert _view(lattice, b"z", "tiny")["fold_trit"] == 1
    assert _view(lattice, b"b", "tiny")["fold_trit"] == -1


def test_probability_rejects_bool_and_normalizes_signed_zero() -> None:
    with pytest.raises(ValueError, match="not bool"):
        TokenProbability(0, "61", True)
    zero = TokenProbability(0, "61", -0.0)
    assert zero.probability == 0.0
    assert math.copysign(1.0, zero.probability) == 1.0
