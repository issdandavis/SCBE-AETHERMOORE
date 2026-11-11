"""Portable cross-token grid to exact SCBE route/radial join tests."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from python.scbe.algebraic_radial_token_table import RadialTableSpec
from python.scbe.cross_token_language_grid import (
    CrossTokenJoinError,
    ObservedRole,
    build_join_receipt,
    verify_join_receipt,
)

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _trits(value: int) -> str:
    alphabet = {0: "0", 1: "+", 2: "-"}
    digits = ""
    remaining = value
    while remaining:
        digits = alphabet[remaining % 3] + digits
        remaining //= 3
    return digits.rjust(6, "0")


def _authorities() -> dict[str, object]:
    body = {
        "schema": "clay.cross-token-codec-authorities.v1",
        "layr_adapter_source_sha256": "1" * 64,
        "action_packet_codec_source_sha256": "2" * 64,
        "trit_codec_source_sha256": "3" * 64,
        "tongue_renderer_source_sha256": "4" * 64,
        "tongue_order": list(TONGUES),
        "bit_convention": "unsigned-byte-msb-first-8",
        "trit_convention": "six-digit-base3-residue-0-plus-minus",
    }
    return {**body, "mapping_id": _sha(body)}


def _grid() -> dict[str, object]:
    authorities = _authorities()
    values = ((65, 66), (67, None))
    valid_mask = [[value is not None for value in row] for row in values]
    byte_grid = [[value or 0 for value in row] for row in values]
    bit_grid = [[f"{value:08b}" if value is not None else None for value in row] for row in values]
    trit_grid = [[_trits(value) if value is not None else None for value in row] for row in values]
    tongue_grids = {
        tongue: [[f"{tongue.lower()}-{value}" if value is not None else None for value in row] for row in values]
        for tongue in TONGUES
    }
    body = {
        "schema": "clay.layr-cross-token-grid.v2",
        "plan_receipt_sha256": "a" * 64,
        "codec_authorities": authorities,
        "shape": [2, 2],
        "valid_mask": valid_mask,
        "byte_grid": byte_grid,
        "bit_grid": bit_grid,
        "trit_grid": trit_grid,
        "tongue_grids": tongue_grids,
        "language_axis": ["EN", *TONGUES],
        "source_tongue_one_hot": [[1, 0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0]],
        "view_contract": {
            "projection_origin": "action_packets_hex",
            "deterministic_correlated_views": True,
            "independent_evidence_count": 1,
            "similarity_geometry_learned": False,
            "geoseal_transport_ready": True,
        },
    }
    return {**body, "grid_sha256": _sha(body)}


def _spec() -> RadialTableSpec:
    return RadialTableSpec(
        cell_count=16,
        sector_count=4,
        dimensions=8,
        depth_count=2,
        neighbor_count=2,
        portal_count=1,
        seed=23,
    )


def test_join_keeps_one_origin_and_six_correlated_language_branches() -> None:
    grid = _grid()
    roles = (ObservedRole(0, 0, "S"), ObservedRole(0, 1, "V"))
    receipt = build_join_receipt(
        grid,
        roles,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
    )

    assert receipt["observed_origin_count"] == 2
    assert receipt["language_branch_count"] == 12
    assert receipt["claim_boundary"] == {
        "deterministic_views_are_correlated": True,
        "independent_evidence_per_origin": 1,
        "roles_are_explicit_not_inferred": True,
        "similarity_geometry_learned": False,
    }
    assert all(row["independent_evidence_count"] == 1 for row in receipt["origins"])
    assert all(len(row["language_branches"]) == 6 for row in receipt["origins"])
    assert {branch["tongue"] for origin in receipt["origins"] for branch in origin["language_branches"]} == set(TONGUES)
    assert verify_join_receipt(
        grid,
        roles,
        receipt,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
    )


def test_join_is_deterministic_and_sector_movement_changes_only_derived_receipt() -> None:
    grid = _grid()
    roles = (ObservedRole(0, 0, "O"),)
    zero = build_join_receipt(
        grid,
        roles,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
    )
    repeat = build_join_receipt(
        grid,
        roles,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
    )
    moved = build_join_receipt(
        grid,
        roles,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
        sector_parameters=(0.0, 0.25, -0.5, 1.0),
    )

    assert zero == repeat
    assert zero["origins"][0]["origin_id"] == moved["origins"][0]["origin_id"]
    assert zero["receipt_sha256"] != moved["receipt_sha256"]


@pytest.mark.parametrize(
    "mutation",
    ("bit", "trit", "mask", "authority", "evidence"),
)
def test_join_rejects_tampered_or_overclaiming_grid(mutation: str) -> None:
    grid = _grid()
    if mutation == "bit":
        grid["bit_grid"][0][0] = "00000000"
    elif mutation == "trit":
        grid["trit_grid"][0][0] = "000000"
    elif mutation == "mask":
        grid["valid_mask"][1][1] = True
    elif mutation == "authority":
        grid["codec_authorities"]["mapping_id"] = "f" * 64
    else:
        grid["view_contract"]["independent_evidence_count"] = 7
    body = dict(grid)
    body.pop("grid_sha256")
    grid["grid_sha256"] = _sha(body)

    with pytest.raises(CrossTokenJoinError):
        build_join_receipt(
            grid,
            (ObservedRole(0, 0, "S"),),
            expected_codec_authorities=_authorities(),
            table_spec=_spec(),
        )


def test_join_refuses_unpinned_codec_and_unobserved_or_duplicate_roles() -> None:
    grid = _grid()
    wrong_pin = deepcopy(_authorities())
    wrong_pin["tongue_renderer_source_sha256"] = "9" * 64
    with pytest.raises(CrossTokenJoinError, match="external pin"):
        build_join_receipt(
            grid,
            (ObservedRole(0, 0, "S"),),
            expected_codec_authorities=wrong_pin,
            table_spec=_spec(),
        )
    with pytest.raises(ValueError, match="explicitly observed"):
        ObservedRole(0, 0, "unknown")
    with pytest.raises(CrossTokenJoinError, match="only one observed role"):
        build_join_receipt(
            grid,
            (ObservedRole(0, 0, "S"), ObservedRole(0, 0, "V")),
            expected_codec_authorities=_authorities(),
            table_spec=_spec(),
        )
    with pytest.raises(CrossTokenJoinError, match="masked padding"):
        build_join_receipt(
            grid,
            (ObservedRole(1, 1, "O"),),
            expected_codec_authorities=_authorities(),
            table_spec=_spec(),
        )


def test_receipt_tamper_is_not_independently_verifiable() -> None:
    grid = _grid()
    roles = (ObservedRole(0, 0, "S"),)
    receipt = build_join_receipt(
        grid,
        roles,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
    )
    changed = deepcopy(receipt)
    changed["origins"][0]["language_branches"][0]["occupancy"]["cell_id"] = 7
    body = dict(changed)
    body.pop("receipt_sha256")
    changed["receipt_sha256"] = sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert not verify_join_receipt(
        grid,
        roles,
        changed,
        expected_codec_authorities=_authorities(),
        table_spec=_spec(),
    )
