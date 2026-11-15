"""Six hex-root views over three 16x16 trit routing sheets.

Every byte keeps one identity in binary, decimal, and hexadecimal form.  Its
high and low nibbles select a cell in a 16x16 sheet.  Three balanced-trit
channels each expose two reversible routes, giving six optional A--F roots.
The routes are toroidal coordinate offsets; they add no Shannon information
and carry no opcode or execution semantics.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any

HEX_TRIT_CROSS_ROUTER_SCHEMA = "scbe.hex-trit-cross-router.v1"
BIT_PLANE_TRAVERSAL_STACK_SCHEMA = "scbe.bit-plane-traversal-stack.v1"
GOLDEN_PHI = (1.0 + math.sqrt(5.0)) / 2.0
GOLDEN_ANGLE_DEGREES = 360.0 * (1.0 - 1.0 / GOLDEN_PHI)
TRIT_CHANNELS = (-1, 0, 1)
ROOT_ROUTES = (
    ("A", 10, -1, 0, -1, 0),
    ("B", 11, -1, 1, 0, -1),
    ("C", 12, 0, 0, -1, 1),
    ("D", 13, 0, 1, 1, -1),
    ("E", 14, 1, 0, 0, 1),
    ("F", 15, 1, 1, 1, 0),
)
_BY_ROOT = {row[0]: row for row in ROOT_ROUTES}
INVERSE_ROOTS = {"A": "F", "F": "A", "B": "E", "E": "B", "C": "D", "D": "C"}


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _phi_precision_ladder(byte_value: int, high: int, low: int) -> list[dict[str, Any]]:
    local_offset_degrees = (high - low) * (360.0 / 16.0)
    rows = []
    for index, bit in enumerate(f"{byte_value:08b}"):
        radius = GOLDEN_PHI ** -(index + 1)
        global_angle = (index * GOLDEN_ANGLE_DEGREES) % 360.0
        local_angle = (global_angle + local_offset_degrees) % 360.0
        radians = math.radians(local_angle)
        x = radius * math.cos(radians)
        y = radius * math.sin(radians)
        z = index / 7.0
        rows.append(
            {
                "bit_plane": index,
                "bit": int(bit),
                "phi_radius": radius,
                "global_angle_degrees": global_angle,
                "local_offset_degrees": local_offset_degrees,
                "local_angle_degrees": local_angle,
                "positive_strand_xyz": [x, y, z],
                "negative_strand_xyz": [-x, -y, z],
            }
        )
    return rows


def invert_hex_root(root: str, routed_row: int, routed_column: int) -> int:
    """Recover the original byte from one A--F routed 16x16 coordinate."""

    route = _BY_ROOT.get(root)
    if route is None:
        raise ValueError("root must be one of A, B, C, D, E, F")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 16
        for value in (routed_row, routed_column)
    ):
        raise ValueError("routed row and column must be integers in 0..15")
    delta_row, delta_column = route[4], route[5]
    high = (routed_row - delta_row) % 16
    low = (routed_column - delta_column) % 16
    return (high << 4) | low


def route_byte_rook_graph(
    source_byte: int, target_byte: int, *, root: str
) -> dict[str, Any]:
    """Return every canonical shortest route between two byte-root cells.

    A 16x16 rook graph has diameter two.  Translating the board through any
    A--F root preserves rows, columns, and therefore shortest-path length.
    """

    for name, value in (("source_byte", source_byte), ("target_byte", target_byte)):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value < 256
        ):
            raise ValueError(f"{name} must be an integer in 0..255")
    if root not in _BY_ROOT:
        raise ValueError("root must be one of A, B, C, D, E, F")
    delta_row, delta_column = _BY_ROOT[root][4], _BY_ROOT[root][5]

    def coordinate(byte_value: int) -> tuple[int, int]:
        return (
            ((byte_value >> 4) + delta_row) % 16,
            ((byte_value & 0x0F) + delta_column) % 16,
        )

    source_coord = coordinate(source_byte)
    target_coord = coordinate(target_byte)
    if source_byte == target_byte:
        paths = [[source_byte]]
    elif source_coord[0] == target_coord[0] or source_coord[1] == target_coord[1]:
        paths = [[source_byte, target_byte]]
    else:
        crossover_coordinates = (
            (source_coord[0], target_coord[1]),
            (target_coord[0], source_coord[1]),
        )
        paths = [
            [source_byte, invert_hex_root(root, row, column), target_byte]
            for row, column in crossover_coordinates
        ]
    for path in paths:
        for left, right in zip(path, path[1:]):
            left_route = coordinate(left)
            right_route = coordinate(right)
            if not (left_route[0] == right_route[0] or left_route[1] == right_route[1]):
                raise AssertionError("rook route contains a non-adjacent hop")
    body = {
        "source_byte": source_byte,
        "target_byte": target_byte,
        "root": root,
        "source_routed_coordinate": list(source_coord),
        "target_routed_coordinate": list(target_coord),
        "minimum_hop_count": len(paths[0]) - 1,
        "shortest_path_count": len(paths),
        "shortest_paths": paths,
        "byte_root_graph_diameter_upper_bound": 2,
        "nested_token_local_hops_not_included": True,
    }
    return {**body, "route_receipt_sha256": _digest(body)}


def hex_trit_cross_cell(byte_value: int) -> dict[str, Any]:
    """Return six reversible route views for one byte cell."""

    if isinstance(byte_value, bool) or not isinstance(byte_value, int):
        raise ValueError("byte_value must be an integer")
    if not 0 <= byte_value < 256:
        raise ValueError("byte_value must be in 0..255")
    high, low = byte_value >> 4, byte_value & 0x0F
    routes = []
    for root, root_value, trit, dual_lane, delta_row, delta_column in ROOT_ROUTES:
        routed_row = (high + delta_row) % 16
        routed_column = (low + delta_column) % 16
        recovered = invert_hex_root(root, routed_row, routed_column)
        if recovered != byte_value:
            raise AssertionError("hex-root route failed byte round trip")
        route_body = {
            "root": root,
            "inverse_root": INVERSE_ROOTS[root],
            "root_hex_value": root_value,
            "trit_channel": trit,
            "dual_trit_lane": dual_lane,
            "sheet_index": trit + 1,
            "delta": [delta_row, delta_column],
            "routed_row": routed_row,
            "routed_column": routed_column,
            "routed_cell": routed_row * 16 + routed_column,
            "inverse_byte": recovered,
        }
        routes.append({**route_body, "route_sha256": _digest(route_body)})
    body = {
        "byte_value": byte_value,
        "decimal": byte_value,
        "hex": f"{byte_value:02x}",
        "bits_msb_first": [int(bit) for bit in f"{byte_value:08b}"],
        "base_row_high_nibble": high,
        "base_column_low_nibble": low,
        "base_cell": high * 16 + low,
        "phi_precision_ladder": _phi_precision_ladder(byte_value, high, low),
        "routes": routes,
    }
    return {**body, "cell_sha256": _digest(body)}


def quantized_helix_state(
    byte_value: int,
    *,
    root: str,
    bit_plane: int,
    weight_trit: int,
) -> dict[str, Any]:
    """Apply one quantized {-1,0,+1} weight to a six-phase binary pole."""

    if root not in _BY_ROOT:
        raise ValueError("root must be one of A, B, C, D, E, F")
    if (
        isinstance(bit_plane, bool)
        or not isinstance(bit_plane, int)
        or not 0 <= bit_plane < 8
    ):
        raise ValueError("bit_plane must be an integer in 0..7")
    if weight_trit not in TRIT_CHANNELS or isinstance(weight_trit, bool):
        raise ValueError("weight_trit must be -1, 0, or +1")
    cell = hex_trit_cross_cell(byte_value)
    route = next(row for row in cell["routes"] if row["root"] == root)
    layer = cell["phi_precision_ladder"][bit_plane]
    binary_pole = 1 if layer["bit"] else -1
    effective_polarity = binary_pole * weight_trit
    root_phase = (ord(root) - ord("A")) * 60.0
    phase = (layer["local_angle_degrees"] + root_phase) % 360.0
    radians = math.radians(phase)
    radius = layer["phi_radius"]
    axial_x = effective_polarity * radius * math.cos(radians)
    axial_y = effective_polarity * radius * math.sin(radians)
    lateral_strength = route["trit_channel"] * radius if weight_trit != 0 else 0.0
    lateral_x = -lateral_strength * math.sin(radians)
    lateral_y = lateral_strength * math.cos(radians)
    x = axial_x + lateral_x
    y = axial_y + lateral_y
    z = layer["positive_strand_xyz"][2]
    body = {
        "byte_value": byte_value,
        "byte_hex": f"{byte_value:02x}",
        "root": root,
        "six_phase_degrees": root_phase,
        "bit_plane": bit_plane,
        "settled_binary_bit": layer["bit"],
        "binary_pole": binary_pole,
        "quantized_weight_trit": weight_trit,
        "effective_polarity": effective_polarity,
        "route_trit_channel": route["trit_channel"],
        "dual_trit_lane": route["dual_trit_lane"],
        "phi_radius": radius,
        "combined_local_global_phase_degrees": phase,
        "lateral_push": [lateral_x, lateral_y],
        "active_pole_xyz": [x, y, z],
        "negative_space_embedding_xyz": [-x, -y, z],
        "neutral_well": weight_trit == 0,
        "byte_identity_unchanged": True,
    }
    return {**body, "state_sha256": _digest(body)}


def build_256_bit_traversal_stack(payload: bytes) -> dict[str, Any]:
    """Project one exact 32-byte block into 256 lazy traversal sheets.

    Each sheet describes one bit position over the shared 16x16 byte root.  It
    does not materialize another copy of that root or create another fact.
    """

    if not isinstance(payload, bytes):
        raise ValueError("payload must be bytes")
    if len(payload) != 32:
        raise ValueError("a 256-bit traversal stack requires exactly 32 bytes")
    sheets = []
    for sheet_index in range(256):
        byte_index, bit_plane = divmod(sheet_index, 8)
        byte_value = payload[byte_index]
        bit = (byte_value >> (7 - bit_plane)) & 1
        cell = hex_trit_cross_cell(byte_value)
        root = ROOT_ROUTES[sheet_index % len(ROOT_ROUTES)][0]
        route = next(row for row in cell["routes"] if row["root"] == root)
        layer = cell["phi_precision_ladder"][bit_plane]
        sheets.append(
            {
                "sheet_index": sheet_index,
                "previous_sheet": sheet_index - 1 if sheet_index else None,
                "next_sheet": sheet_index + 1 if sheet_index < 255 else None,
                "byte_index": byte_index,
                "bit_plane_msb_first": bit_plane,
                "bit": bit,
                "polarity": 1 if bit else -1,
                "source_byte": byte_value,
                "source_byte_hex": f"{byte_value:02x}",
                "shared_root_cell": cell["base_cell"],
                "route_root": root,
                "routed_cell": route["routed_cell"],
                "routed_row": route["routed_row"],
                "routed_column": route["routed_column"],
                "route_trit_channel": route["trit_channel"],
                "dual_trit_lane": route["dual_trit_lane"],
                "phi_radius": layer["phi_radius"],
                "local_angle_degrees": layer["local_angle_degrees"],
            }
        )
    body = {
        "schema": BIT_PLANE_TRAVERSAL_STACK_SCHEMA,
        "payload_hex": payload.hex(),
        "payload_byte_count": 32,
        "sheet_count": 256,
        "shared_root_shape": [16, 16],
        "materialized_root_copy_count": 0,
        "one_bit_count": sum(sheet["bit"] for sheet in sheets),
        "zero_bit_count": 256 - sum(sheet["bit"] for sheet in sheets),
        "sheets": sheets,
        "contract": {
            "one_ordered_sheet_per_bit": True,
            "sheets_reference_one_shared_byte_root": True,
            "sheet_sequence_reconstructs_exact_payload": True,
            "route_views_do_not_rewrite_bits": True,
            "deterministic_planes_add_shannon_information": False,
        },
        "receipt_security": "unkeyed-corruption-detection-only",
    }
    stack = {**body, "receipt_sha256": _digest(body)}
    if reconstruct_256_bit_traversal_stack(stack) != payload:
        raise AssertionError("256-bit traversal stack failed exact reconstruction")
    return stack


def reconstruct_256_bit_traversal_stack(stack: dict[str, Any]) -> bytes:
    """Validate a traversal stack and recover its exact 32-byte payload."""

    if not isinstance(stack, dict):
        raise ValueError("stack must be a dictionary")
    if stack.get("schema") != BIT_PLANE_TRAVERSAL_STACK_SCHEMA:
        raise ValueError("unsupported traversal-stack schema")
    sheets = stack.get("sheets")
    if not isinstance(sheets, list) or len(sheets) != 256:
        raise ValueError("traversal stack must contain exactly 256 sheets")
    output = bytearray(32)
    for expected_index, sheet in enumerate(sheets):
        if not isinstance(sheet, dict) or sheet.get("sheet_index") != expected_index:
            raise ValueError("traversal sheets must be in canonical index order")
        byte_index, bit_plane = divmod(expected_index, 8)
        bit = sheet.get("bit")
        if isinstance(bit, bool) or bit not in (0, 1):
            raise ValueError("sheet bit must be the integer 0 or 1")
        source_byte = sheet.get("source_byte")
        if (
            isinstance(source_byte, bool)
            or not isinstance(source_byte, int)
            or not 0 <= source_byte < 256
        ):
            raise ValueError("sheet source_byte must be an integer in 0..255")
        root = ROOT_ROUTES[expected_index % len(ROOT_ROUTES)][0]
        if (
            sheet.get("byte_index") != byte_index
            or sheet.get("bit_plane_msb_first") != bit_plane
            or sheet.get("previous_sheet")
            != (expected_index - 1 if expected_index else None)
            or sheet.get("next_sheet")
            != (expected_index + 1 if expected_index < 255 else None)
            or sheet.get("route_root") != root
            or sheet.get("polarity") != (1 if bit else -1)
        ):
            raise ValueError("traversal-sheet topology is inconsistent")
        recovered_byte = invert_hex_root(
            root, sheet.get("routed_row"), sheet.get("routed_column")
        )
        if recovered_byte != source_byte:
            raise ValueError("traversal sheet does not invert to its source byte")
        if bit != ((source_byte >> (7 - bit_plane)) & 1):
            raise ValueError("sheet bit does not match its source byte")
        output[byte_index] |= bit << (7 - bit_plane)
    payload = bytes(output)
    if stack.get("payload_hex") != payload.hex():
        raise ValueError("reconstructed payload does not match payload_hex")
    claimed = stack.get("receipt_sha256")
    body = {key: value for key, value in stack.items() if key != "receipt_sha256"}
    if claimed != _digest(body):
        raise ValueError("traversal-stack receipt hash mismatch")
    return payload


def build_hex_trit_cross_router() -> dict[str, Any]:
    """Build and exhaustively verify all 256 cells across all six roots."""

    cells = [hex_trit_cross_cell(value) for value in range(256)]
    root_unique_counts = {
        root: len(
            {
                (route["routed_row"], route["routed_column"])
                for cell in cells
                for route in cell["routes"]
                if route["root"] == root
            }
        )
        for root, *_ in ROOT_ROUTES
    }
    if any(count != 256 for count in root_unique_counts.values()):
        raise AssertionError("a hex-root view is not bijective over the byte table")
    body = {
        "schema": HEX_TRIT_CROSS_ROUTER_SCHEMA,
        "base_shape": [16, 16],
        "trit_sheet_count": 3,
        "dual_routes_per_sheet": 2,
        "golden_phi": GOLDEN_PHI,
        "golden_angle_degrees": GOLDEN_ANGLE_DEGREES,
        "hex_roots": [row[0] for row in ROOT_ROUTES],
        "inverse_root_pairs": [["A", "F"], ["B", "E"], ["C", "D"]],
        "root_unique_cell_counts": root_unique_counts,
        "rook_graph": {
            "vertex_count": 256,
            "degree": 30,
            "diameter": 2,
            "ordered_same_cell_pair_count": 256,
            "ordered_one_hop_pair_count": 7680,
            "ordered_two_hop_pair_count": 57600,
            "two_canonical_crossovers_for_each_two_hop_pair": True,
        },
        "cells": cells,
        "contract": {
            "same_byte_identity_in_binary_decimal_hex": True,
            "all_six_routes_are_reversible": True,
            "routes_are_optional_views": True,
            "unused_routes_remain_inert": True,
            "inverse_offsets_cross_at_zero_plane": True,
            "phi_ladder_terminates_in_exact_binary_bits": True,
            "global_phi_turn_and_byte_local_phase_are_separate": True,
            "positive_and_negative_strands_are_antipodal": True,
            "quantized_trit_weights_shift_binary_polarity_without_rewriting_byte": True,
            "every_byte_root_reaches_every_other_in_at_most_two_rook_hops": True,
            "dna_helix_is_a_routing_analogy_not_a_biophysical_model": True,
            "deterministic_views_add_shannon_information": False,
            "opcode_or_execution_semantics": False,
        },
        "receipt_security": "unkeyed-corruption-detection-only",
    }
    return {**body, "receipt_sha256": _digest(body)}


__all__ = [
    "BIT_PLANE_TRAVERSAL_STACK_SCHEMA",
    "HEX_TRIT_CROSS_ROUTER_SCHEMA",
    "ROOT_ROUTES",
    "TRIT_CHANNELS",
    "build_256_bit_traversal_stack",
    "build_hex_trit_cross_router",
    "hex_trit_cross_cell",
    "invert_hex_root",
    "quantized_helix_state",
    "reconstruct_256_bit_traversal_stack",
    "route_byte_rook_graph",
]
