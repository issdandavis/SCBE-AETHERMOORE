"""Binary/decimal/hex columns across three trit sheets and dual routes."""

from copy import deepcopy

import pytest

from python.scbe.hex_trit_cross_router import (
    ROOT_ROUTES,
    build_256_bit_traversal_stack,
    build_hex_trit_cross_router,
    hex_trit_cross_cell,
    invert_hex_root,
    quantized_helix_state,
    reconstruct_256_bit_traversal_stack,
    route_byte_rook_graph,
)
from python.scbe.intermodel_token_ledger import build_binary_token_atlas


def test_every_hex_root_is_a_bijective_16_by_16_byte_view() -> None:
    receipt = build_hex_trit_cross_router()
    assert receipt["base_shape"] == [16, 16]
    assert receipt["trit_sheet_count"] == 3
    assert receipt["dual_routes_per_sheet"] == 2
    assert receipt["root_unique_cell_counts"] == {root: 256 for root, *_ in ROOT_ROUTES}
    assert receipt["contract"]["deterministic_views_add_shannon_information"] is False


def test_cell_routes_preserve_binary_decimal_and_hex_identity() -> None:
    for value in range(256):
        cell = hex_trit_cross_cell(value)
        assert cell["decimal"] == value
        assert int(cell["hex"], 16) == value
        assert sum(bit << (7 - index) for index, bit in enumerate(cell["bits_msb_first"])) == value
        assert sum(row["bit"] << (7 - row["bit_plane"]) for row in cell["phi_precision_ladder"]) == value
        assert all(
            left["phi_radius"] > right["phi_radius"]
            for left, right in zip(
                cell["phi_precision_ladder"][:-1],
                cell["phi_precision_ladder"][1:],
                strict=True,
            )
        )
        for layer in cell["phi_precision_ladder"]:
            positive = layer["positive_strand_xyz"]
            negative = layer["negative_strand_xyz"]
            assert positive[0] == -negative[0]
            assert positive[1] == -negative[1]
            assert positive[2] == negative[2]
        assert len(cell["routes"]) == 6
        for route in cell["routes"]:
            assert invert_hex_root(route["root"], route["routed_row"], route["routed_column"]) == value


def test_binary_atlas_attaches_hex_trit_routes_to_the_same_byte_root() -> None:
    atlas = build_binary_token_atlas(bytes((0x00, 0xAF, 0xFF)))
    rows = {row["byte_value"]: row for row in atlas["byte_types"]}
    assert rows[0xAF]["hex_trit_cross_column"]["hex"] == "af"
    assert rows[0xAF]["hex_trit_cross_column"]["base_row_high_nibble"] == 10
    assert rows[0xAF]["hex_trit_cross_column"]["base_column_low_nibble"] == 15


def test_quantized_trit_weight_preserves_inverts_or_neutralizes_binary_pole() -> None:
    preserve = quantized_helix_state(0x80, root="F", bit_plane=0, weight_trit=1)
    invert = quantized_helix_state(0x80, root="F", bit_plane=0, weight_trit=-1)
    neutral = quantized_helix_state(0x80, root="F", bit_plane=0, weight_trit=0)
    assert preserve["settled_binary_bit"] == 1
    assert preserve["effective_polarity"] == 1
    assert invert["effective_polarity"] == -1
    assert neutral["effective_polarity"] == 0
    assert neutral["neutral_well"] is True
    for state in (preserve, invert, neutral):
        active = state["active_pole_xyz"]
        negative = state["negative_space_embedding_xyz"]
        assert active[0] == -negative[0]
        assert active[1] == -negative[1]
        assert active[2] == negative[2]
        assert state["byte_identity_unchanged"] is True


def test_256_bit_block_becomes_256_lazy_planes_and_round_trips() -> None:
    payload = bytes(range(32))
    stack = build_256_bit_traversal_stack(payload)
    assert stack["sheet_count"] == 256
    assert stack["shared_root_shape"] == [16, 16]
    assert stack["materialized_root_copy_count"] == 0
    assert len(stack["sheets"]) == 256
    assert reconstruct_256_bit_traversal_stack(stack) == payload
    assert [row["route_root"] for row in stack["sheets"][:6]] == list("ABCDEF")
    assert stack["one_bit_count"] + stack["zero_bit_count"] == 256


def test_256_bit_plane_stack_rejects_wrong_width_and_tampering() -> None:
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        build_256_bit_traversal_stack(b"too short")
    stack = build_256_bit_traversal_stack(bytes(range(32)))
    changed = deepcopy(stack)
    changed["sheets"][17]["bit"] ^= 1
    with pytest.raises(ValueError, match="topology is inconsistent"):
        reconstruct_256_bit_traversal_stack(changed)


def test_16_by_16_byte_root_has_exact_diameter_two() -> None:
    hop_counts = {0: 0, 1: 0, 2: 0}
    for source in range(256):
        for target in range(256):
            route = route_byte_rook_graph(source, target, root="A")
            hop_counts[route["minimum_hop_count"]] += 1
            assert route["minimum_hop_count"] <= 2
            for path in route["shortest_paths"]:
                assert path[0] == source
                assert path[-1] == target
    assert hop_counts == {0: 256, 1: 7680, 2: 57600}


def test_all_six_roots_preserve_the_same_two_hop_property() -> None:
    for root, *_ in ROOT_ROUTES:
        route = route_byte_rook_graph(0x12, 0xA7, root=root)
        assert route["minimum_hop_count"] == 2
        assert route["shortest_path_count"] == 2
        assert route["nested_token_local_hops_not_included"] is True
