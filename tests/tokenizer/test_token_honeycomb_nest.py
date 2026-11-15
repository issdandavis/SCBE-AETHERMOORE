"""Weight-derived token nest and collision accounting tests."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from python.scbe.token_honeycomb_nest import (
    CARRIER_DIMENSIONS,
    MAX_CANDIDATE_WINDOW,
    TokenNestError,
    TokenNestInput,
    TokenNestSpec,
    _hex_ring,
    build_b256_token_honeycomb,
    build_typed_token_honeycomb,
    byte_weight_vector,
    honeycomb_coordinate,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _table() -> dict[str, object]:
    tokens = [
        {"id": 0, "hex": "3c7061643e", "length": 5},
        {"id": 1, "hex": "61", "length": 1},
        {"id": 2, "hex": "6162", "length": 2},
        {"id": 3, "hex": "6163", "length": 2},
    ]
    hash_body = {
        "schema": "clay.b256-token-table.v1",
        "tokens": tokens,
        "special_token_ids": [0],
    }
    return {
        **hash_body,
        "tokenizer_sha256": "1" * 64,
        "table_sha256": sha256(_canonical(hash_body)).hexdigest(),
        "vocab_size": len(tokens),
        "maximum_token_bytes": 5,
    }


def test_weight_carrier_is_byte_derived_not_label_or_identity_derived() -> None:
    raw = b"same-bytes"
    vector = byte_weight_vector(raw)
    assert len(vector) == CARRIER_DIMENSIONS == 18

    nest = build_typed_token_honeycomb(
        (
            TokenNestInput("left", "identifier", raw.hex(), 0, "alpha", "m1"),
            TokenNestInput("right", "identifier", raw.hex(), 1, "omega", "m2"),
        )
    )
    left, right = nest["tokens"]
    assert left["weight_vector"] == right["weight_vector"]
    assert left["radial"]["cell_id"] == right["radial"]["cell_id"]
    assert left["nest"]["address"] != right["nest"]["address"]
    assert right["prior_neighbors"][0]["score"] == 1.0
    assert right["prior_neighbors"][0]["exact_byte_match"] is True
    assert nest["metrics"]["radial_collision_token_count"] == 1
    assert nest["metrics"]["nested_address_collision_count"] == 0
    assert left["node_fill"]["occupancy_before"] == 0
    assert right["node_fill"]["occupancy_before"] == 1
    assert right["node_fill"]["pressure_after"] > left["node_fill"]["pressure_after"]
    assert sum(field["occupancy"] for field in nest["node_fields"]) == 2


def test_prefix_tree_shares_roots_while_families_restrict_prior_sieve() -> None:
    nest = build_typed_token_honeycomb(
        (
            TokenNestInput("ab", "identifier", b"ab".hex(), 0),
            TokenNestInput("ac", "identifier", b"ac".hex(), 1),
            TokenNestInput("ab-op", "operator", b"ab".hex(), 2),
        )
    )
    ab, ac, ab_operator = nest["tokens"]
    trie = nest["prefix_trie"]
    assert trie[ab["trie_terminal_node"]]["parent_id"] == trie[ac["trie_terminal_node"]]["parent_id"]
    assert ac["same_family_prior_count"] == 1
    assert ac["prior_neighbors"][0]["prior_token_id"] == "ab"
    assert ab_operator["same_family_prior_count"] == 0
    assert ab_operator["prior_neighbors"] == []
    assert nest["metrics"]["exact_byte_alias_group_count"] == 1


def test_honeycomb_spiral_addresses_are_unique_and_ring_sized() -> None:
    coordinates = [honeycomb_coordinate(index) for index in range(19)]
    assert len(set(coordinates)) == 19
    assert coordinates[0] == (0, 0, 0)
    assert sum(radius == 1 for _, _, radius in coordinates) == 6
    assert sum(radius == 2 for _, _, radius in coordinates) == 12
    for radius in range(1, 12):
        start = 1 + 3 * radius * (radius - 1)
        assert [honeycomb_coordinate(start + offset)[:2] for offset in range(6 * radius)] == list(_hex_ring(radius))


def test_node_field_m2_and_projected_hex_halo_are_geometric() -> None:
    nest = build_typed_token_honeycomb(
        tuple(TokenNestInput(f"byte-{value}", "byte", f"{value:02x}", value) for value in range(32, 64)),
        spec=TokenNestSpec(cell_count=2, sector_count=1, candidate_window=4),
    )
    tokens_by_cell: dict[int, list[dict]] = {}
    for token in nest["tokens"]:
        tokens_by_cell.setdefault(token["radial"]["cell_id"], []).append(token)
        halo = [row["value"] for row in token["node_fill"]["residual_halo_by_hex_direction"]]
        assert halo[0] == pytest.approx(-halo[3])
        assert halo[1] == pytest.approx(-halo[4])
        assert halo[2] == pytest.approx(-halo[5])

    for field in nest["node_fields"]:
        centroid = field["centroid"]
        expected_m2 = sum(
            sum(
                (value - center) ** 2
                for value, center in zip(token["node_fill"]["carrier_unit_vector"], centroid, strict=True)
            )
            for token in tokens_by_cell[field["cell_id"]]
        )
        assert field["current_residual_m2"] == pytest.approx(expected_m2)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"cell_count": 64.0},
        {"sector_count": True},
        {"candidate_window": MAX_CANDIDATE_WINDOW + 1},
        {"neighbor_count": 1.0},
        {"seed": 0.0},
    ),
)
def test_token_nest_spec_rejects_non_integer_or_unbounded_counts(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        TokenNestSpec(**kwargs)


def test_b256_table_builds_weighted_nest_and_fails_closed_on_collision() -> None:
    receipt = build_b256_token_honeycomb(_table())
    assert receipt["source_table"]["vocab_size"] == 4
    assert receipt["nest"]["metrics"]["token_count"] == 4
    assert receipt["nest"]["metrics"]["nested_address_collision_count"] == 0
    assert receipt["nest"]["tokens"][0]["family"] == "b256:special"

    changed = deepcopy(_table())
    changed["tokens"][3] = {"id": 3, "hex": "6162", "length": 2}
    body = {
        "schema": changed["schema"],
        "tokens": changed["tokens"],
        "special_token_ids": changed["special_token_ids"],
    }
    changed["table_sha256"] = sha256(_canonical(body)).hexdigest()
    with pytest.raises(TokenNestError, match="B256 collision"):
        build_b256_token_honeycomb(changed)


def test_invalid_duplicate_identity_or_sequence_index_is_rejected() -> None:
    with pytest.raises(TokenNestError, match="canonical token IDs"):
        build_typed_token_honeycomb(
            (
                TokenNestInput("same", "x", "61", 0),
                TokenNestInput("same", "x", "62", 1),
            )
        )
    with pytest.raises(TokenNestError, match="sequence indexes"):
        build_typed_token_honeycomb(
            (
                TokenNestInput("left", "x", "61", 0),
                TokenNestInput("right", "x", "62", 0),
            )
        )


def test_token_hex_must_be_canonical_lowercase() -> None:
    with pytest.raises(ValueError, match="canonical, lowercase"):
        TokenNestInput("upper", "x", "AB", 0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("id", 0.0, "IDs must be integers"),
        ("length", 1.0, "length must be an integer"),
    ),
)
def test_b256_numeric_fields_reject_float_lookalikes(field: str, value: float, message: str) -> None:
    table = _table()
    table["tokens"][0][field] = value
    body = {
        "schema": table["schema"],
        "tokens": table["tokens"],
        "special_token_ids": table["special_token_ids"],
    }
    table["table_sha256"] = sha256(_canonical(body)).hexdigest()
    with pytest.raises(TokenNestError, match=message):
        build_b256_token_honeycomb(table)
