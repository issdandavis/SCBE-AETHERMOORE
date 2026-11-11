"""Exact case/grammar route mechanics and parity with existing authorities."""

from __future__ import annotations

from itertools import product
from pathlib import Path
import re

import pytest

from python.scbe.algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    RadialTableSpec,
    TokenCarrier,
)
from python.scbe.token_surface_routes import (
    TONGUE_ORDERS,
    TONGUE_ORDER_SEQUENCE,
    case_variant,
    decode_route,
    encode_route,
    grammar_route,
    projection_weights,
    surface_case_profile,
    typed_feature_keys,
)


def test_case_profile_keeps_exact_surface_and_binary_upper_lower_root():
    profile = surface_case_profile("Clay-2")

    assert profile.normalized == "clay-2"
    assert profile.signed_trits == (1, -1, -1, -1, 0, 0)
    assert profile.binary_positions == (0, 1, 2, 3)
    assert profile.binary_bits == (1, 0, 0, 0)
    assert profile.case_index == 8
    assert profile.variant_count == 16
    assert profile.kind == "title"


def test_case_table_is_addressed_without_materializing_it():
    variants = [case_variant("aB", index) for index in range(4)]

    assert variants == ["ab", "aB", "Ab", "AB"]
    assert [surface_case_profile(value).case_index for value in variants] == list(range(4))
    assert case_variant("ß!", 0) == "ß!"
    with pytest.raises(ValueError, match="case_index"):
        case_variant("aB", 4)


def test_six_orders_are_exact_permutations_and_roles_keep_identity():
    assert set(TONGUE_ORDERS.values()) == {
        "SOV",
        "SVO",
        "VSO",
        "OVS",
        "VOS",
        "OSV",
    }
    for tongue, role in product(TONGUE_ORDER_SEQUENCE, "SVO"):
        route = grammar_route(role, tongue)
        assert route.order[route.slot] == role

    with pytest.raises(ValueError, match="explicitly observed"):
        grammar_route("unknown", "KO")


def test_runtime_mapping_matches_existing_typescript_authority():
    source = (Path(__file__).resolve().parents[2] / "src" / "harmonic" / "linguisticCrossTalk.ts").read_text(
        encoding="utf-8"
    )
    section = source.split("export const DOMAIN_PROFILES:", 1)[1].split("\n};", 1)[0]
    observed = dict(
        re.findall(
            r"\b(KO|AV|RU|CA|UM|DR):\s*\{[^}]*?grammar:\s*'([SVO]{3})'",
            section,
        )
    )

    assert observed == TONGUE_ORDERS


def test_combined_address_round_trips_case_and_grammar_sector():
    encoded = encode_route("Clay", "V", "RU")
    decoded = decode_route("clay", "V", encoded.address)

    assert encoded.address_count == 16 * 6
    assert decoded == encoded
    assert encoded.order == "VSO"
    assert encoded.slot == 0

    all_addresses = [
        decode_route("aB", "O", address) for address in range(surface_case_profile("aB").variant_count * 6)
    ]
    assert len({(row.surface, row.tongue) for row in all_addresses}) == 24


def test_projection_reuses_radial_table_without_adding_a_tokenizer_view():
    route = encode_route("Clay", "S", "KO")
    weights = projection_weights(route)
    features = typed_feature_keys(route)
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=64,
            sector_count=8,
            dimensions=8,
            depth_count=2,
            neighbor_count=2,
            portal_count=1,
            seed=17,
        )
    )
    assignment = table.assign([TokenCarrier(route.normalized, weights)])

    assert len(weights) == 8
    assert all(-1.0 <= value <= 1.0 for value in weights)
    assert set(features) == {"lexical", "speech"}
    assert assignment[0].canonical_id == "clay"
    assert assignment[0].cell_id is not None
