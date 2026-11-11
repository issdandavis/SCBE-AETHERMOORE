"""Fail-closed join between Clay's portable cross-token grid and SCBE routes.

The producer supplies one canonical action-packet byte plus deterministic bit,
trit, and six-tongue views. This module verifies the portable grid, requires an
external exact pin for its codec authorities, attaches only explicitly observed
S/V/O roles, and projects the resulting language branches into the existing
algebraic radial table.

Every branch retains one canonical origin ID. Six tongue surfaces are six
correlated presentations of one byte, not six observations. The result is
training/planning material only; it carries no execution or promotion authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from python.scbe.algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    RadialTableSpec,
    TokenCarrier,
)
from python.scbe.token_surface_routes import (
    GRAMMAR_MAPPING_ID,
    TONGUE_ORDER_SEQUENCE,
    encode_route,
    projection_weights,
)

SCHEMA = "scbe.cross-token-language-family-join.v1"
GRID_SCHEMA = "clay.layr-cross-token-grid.v2"
CODEC_SCHEMA = "clay.cross-token-codec-authorities.v1"
BIT_CONVENTION = "unsigned-byte-msb-first-8"
TRIT_CONVENTION = "six-digit-base3-residue-0-plus-minus"
LANGUAGE_AXIS = ("EN", *TONGUE_ORDER_SEQUENCE)


class CrossTokenJoinError(ValueError):
    """A portable grid or explicit route failed its bounded contract."""


@dataclass(frozen=True, slots=True)
class ObservedRole:
    """One externally observed grammar role at a valid packet coordinate."""

    frame_index: int
    packet_offset: int
    role: str

    def __post_init__(self) -> None:
        if not isinstance(self.frame_index, int) or isinstance(self.frame_index, bool):
            raise TypeError("frame_index must be an integer")
        if not isinstance(self.packet_offset, int) or isinstance(self.packet_offset, bool):
            raise TypeError("packet_offset must be an integer")
        normalized = str(self.role).upper()
        if normalized not in {"S", "V", "O"}:
            raise ValueError("role must be an explicitly observed S, V, or O")
        object.__setattr__(self, "role", normalized)


def _canonical_json(value: object, *, ensure_ascii: bool = False) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=ensure_ascii,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_json(value: object, *, ensure_ascii: bool = False) -> str:
    return sha256(_canonical_json(value, ensure_ascii=ensure_ascii)).hexdigest()


def _decode_trits(value: str) -> int:
    if not isinstance(value, str) or len(value) != 6 or any(char not in "0+-" for char in value):
        raise CrossTokenJoinError("trit view must be six characters over {0,+,-}")
    digits = {"0": 0, "+": 1, "-": 2}
    result = 0
    for character in value:
        result = result * 3 + digits[character]
    if result > 255:
        raise CrossTokenJoinError("trit view is outside the byte range")
    return result


def _verify_codec_authorities(
    observed: object, expected: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(observed, dict) or observed != dict(expected):
        raise CrossTokenJoinError("codec authorities do not match the external pin")
    body = dict(observed)
    mapping_id = body.pop("mapping_id", None)
    required = {
        "schema",
        "layr_adapter_source_sha256",
        "action_packet_codec_source_sha256",
        "trit_codec_source_sha256",
        "tongue_renderer_source_sha256",
        "tongue_order",
        "bit_convention",
        "trit_convention",
    }
    if set(body) != required or body.get("schema") != CODEC_SCHEMA:
        raise CrossTokenJoinError("codec authority schema or fields are invalid")
    if body.get("tongue_order") != list(TONGUE_ORDER_SEQUENCE):
        raise CrossTokenJoinError("codec tongue order does not match SCBE")
    if body.get("bit_convention") != BIT_CONVENTION:
        raise CrossTokenJoinError("bit convention does not match SCBE")
    if body.get("trit_convention") != TRIT_CONVENTION:
        raise CrossTokenJoinError("trit convention does not match SCBE")
    hash_fields = (
        "layr_adapter_source_sha256",
        "action_packet_codec_source_sha256",
        "trit_codec_source_sha256",
        "tongue_renderer_source_sha256",
    )
    if any(
        not isinstance(body.get(name), str)
        or len(body[name]) != 64
        or any(character not in "0123456789abcdef" for character in body[name])
        for name in hash_fields
    ):
        raise CrossTokenJoinError("codec source hashes must be lowercase SHA-256")
    if mapping_id != _sha256_json(body, ensure_ascii=True):
        raise CrossTokenJoinError("codec mapping_id is invalid")
    return dict(observed)


def _verify_grid(
    grid: Mapping[str, Any], expected_codec_authorities: Mapping[str, Any]
) -> tuple[int, int, dict[str, Any]]:
    if not isinstance(grid, dict) or grid.get("schema") != GRID_SCHEMA:
        raise CrossTokenJoinError(f"grid schema must be {GRID_SCHEMA}")
    body = dict(grid)
    claimed_hash = body.pop("grid_sha256", None)
    if claimed_hash != _sha256_json(body, ensure_ascii=True):
        raise CrossTokenJoinError("grid_sha256 does not match the portable grid")
    authorities = _verify_codec_authorities(
        grid.get("codec_authorities"), expected_codec_authorities
    )
    shape = grid.get("shape")
    if (
        not isinstance(shape, list)
        or len(shape) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in shape)
    ):
        raise CrossTokenJoinError("grid shape must contain positive row and width integers")
    rows, width = shape
    matrix_names = ("valid_mask", "byte_grid", "bit_grid", "trit_grid")
    for name in matrix_names:
        matrix = grid.get(name)
        if (
            not isinstance(matrix, list)
            or len(matrix) != rows
            or any(not isinstance(row, list) or len(row) != width for row in matrix)
        ):
            raise CrossTokenJoinError(f"{name} does not match grid shape")
    tongues = grid.get("tongue_grids")
    if not isinstance(tongues, dict) or set(tongues) != set(TONGUE_ORDER_SEQUENCE):
        raise CrossTokenJoinError("tongue_grids must contain exactly the six SCBE tongues")
    for tongue, matrix in tongues.items():
        if (
            not isinstance(matrix, list)
            or len(matrix) != rows
            or any(not isinstance(row, list) or len(row) != width for row in matrix)
        ):
            raise CrossTokenJoinError(f"tongue grid {tongue} does not match grid shape")

    valid_count = 0
    for frame_index in range(rows):
        for packet_offset in range(width):
            valid = grid["valid_mask"][frame_index][packet_offset]
            if type(valid) is not bool:
                raise CrossTokenJoinError("valid_mask values must be booleans")
            byte = grid["byte_grid"][frame_index][packet_offset]
            bit_view = grid["bit_grid"][frame_index][packet_offset]
            trit_view = grid["trit_grid"][frame_index][packet_offset]
            surfaces = [tongues[tongue][frame_index][packet_offset] for tongue in TONGUE_ORDER_SEQUENCE]
            if valid:
                valid_count += 1
                if not isinstance(byte, int) or isinstance(byte, bool) or not 0 <= byte <= 255:
                    raise CrossTokenJoinError("a valid byte cell must contain an integer byte")
                if (
                    not isinstance(bit_view, str)
                    or len(bit_view) != 8
                    or any(character not in "01" for character in bit_view)
                    or int(bit_view, 2) != byte
                ):
                    raise CrossTokenJoinError("bit view does not reconstruct its byte")
                if _decode_trits(trit_view) != byte:
                    raise CrossTokenJoinError("trit view does not reconstruct its byte")
                if any(not isinstance(surface, str) or not surface for surface in surfaces):
                    raise CrossTokenJoinError("valid tongue surfaces must be nonempty strings")
            elif byte != 0 or bit_view is not None or trit_view is not None or any(
                surface is not None for surface in surfaces
            ):
                raise CrossTokenJoinError("masked padding must use byte zero and absent derived views")
    if valid_count == 0:
        raise CrossTokenJoinError("grid contains no valid canonical bytes")

    if grid.get("language_axis") != list(LANGUAGE_AXIS):
        raise CrossTokenJoinError("language_axis does not match the declared source-tongue axis")
    one_hot = grid.get("source_tongue_one_hot")
    if (
        not isinstance(one_hot, list)
        or len(one_hot) != rows
        or any(
            not isinstance(row, list)
            or len(row) != len(LANGUAGE_AXIS)
            or any(value not in (0, 1) or isinstance(value, bool) for value in row)
            or sum(row) != 1
            for row in one_hot
        )
    ):
        raise CrossTokenJoinError("source_tongue_one_hot is not a one-hot row per frame")
    if grid.get("view_contract") != {
        "projection_origin": "action_packets_hex",
        "deterministic_correlated_views": True,
        "independent_evidence_count": 1,
        "similarity_geometry_learned": False,
        "geoseal_transport_ready": True,
    }:
        raise CrossTokenJoinError("grid view contract is invalid or overclaims evidence")
    plan_receipt = grid.get("plan_receipt_sha256")
    if not isinstance(plan_receipt, str) or len(plan_receipt) != 64:
        raise CrossTokenJoinError("plan_receipt_sha256 is invalid")
    return rows, width, authorities


def _origin(
    plan_receipt_sha256: str, frame_index: int, packet_offset: int, byte_value: int
) -> dict[str, Any]:
    body = {
        "plan_receipt_sha256": plan_receipt_sha256,
        "frame_index": frame_index,
        "packet_offset": packet_offset,
        "byte_value": byte_value,
    }
    return {**body, "origin_id": _sha256_json(body)}


def build_join_receipt(
    grid: Mapping[str, Any],
    observed_roles: Sequence[ObservedRole],
    *,
    expected_codec_authorities: Mapping[str, Any],
    table_spec: RadialTableSpec | None = None,
    sector_parameters: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Bind explicit grammar observations to all six correlated language views."""

    rows, width, authorities = _verify_grid(grid, expected_codec_authorities)
    if not observed_roles:
        raise CrossTokenJoinError("at least one explicit role observation is required")
    coordinates = [(row.frame_index, row.packet_offset) for row in observed_roles]
    if len(set(coordinates)) != len(coordinates):
        raise CrossTokenJoinError("each packet coordinate may have only one observed role")

    spec = table_spec or RadialTableSpec(
        cell_count=64,
        sector_count=8,
        dimensions=8,
        depth_count=2,
        neighbor_count=2,
        portal_count=1,
        seed=0,
    )
    if spec.dimensions != 8:
        raise CrossTokenJoinError("the case/grammar projection requires eight dimensions")
    parameters = tuple(sector_parameters or (0.0,) * spec.sector_count)
    table = AlgebraicRadialTokenTable(spec)
    cells = table.move(parameters)

    staged: list[tuple[dict[str, Any], list[tuple[str, dict[str, Any], tuple[float, ...]]]]] = []
    carriers: list[TokenCarrier] = []
    for observation in observed_roles:
        if not 0 <= observation.frame_index < rows or not 0 <= observation.packet_offset < width:
            raise CrossTokenJoinError("observed role coordinate is outside the grid")
        if not grid["valid_mask"][observation.frame_index][observation.packet_offset]:
            raise CrossTokenJoinError("observed role coordinate points to masked padding")
        byte_value = grid["byte_grid"][observation.frame_index][observation.packet_offset]
        origin = _origin(
            grid["plan_receipt_sha256"],
            observation.frame_index,
            observation.packet_offset,
            byte_value,
        )
        branches: list[tuple[str, dict[str, Any], tuple[float, ...]]] = []
        for tongue in TONGUE_ORDER_SEQUENCE:
            surface = grid["tongue_grids"][tongue][observation.frame_index][observation.packet_offset]
            route = encode_route(surface, observation.role, tongue)
            weights = projection_weights(route)
            carrier_id = f"{origin['origin_id']}:{tongue}"
            route_record = {
                **asdict(route),
                "surface": surface,
                "carrier_id": carrier_id,
            }
            carriers.append(TokenCarrier(carrier_id, weights))
            branches.append((carrier_id, route_record, weights))
        staged.append((origin, branches))

    occupancies = table.assign(carriers, cells)
    occupancy_by_id = {row.canonical_id: row for row in occupancies}
    origins: list[dict[str, Any]] = []
    for (origin, branches), observation in zip(staged, observed_roles, strict=True):
        language_branches = []
        for carrier_id, route, weights in branches:
            occupancy = occupancy_by_id[carrier_id]
            language_branches.append(
                {
                    "tongue": route["tongue"],
                    "surface": route["surface"],
                    "route": route,
                    "projection_weights": list(weights),
                    "occupancy": asdict(occupancy),
                }
            )
        origins.append(
            {
                **origin,
                "observed_role": observation.role,
                "bit_view": grid["bit_grid"][observation.frame_index][observation.packet_offset],
                "trit_view": grid["trit_grid"][observation.frame_index][observation.packet_offset],
                "independent_evidence_count": 1,
                "language_branches": language_branches,
            }
        )

    relays = table.build_relays(cells)
    radial_receipt = table.receipt(
        cells=cells,
        occupancies=occupancies,
        relays=relays,
        sector_parameters=parameters,
    )
    body = {
        "schema": SCHEMA,
        "source": {
            "grid_schema": grid["schema"],
            "grid_sha256": grid["grid_sha256"],
            "plan_receipt_sha256": grid["plan_receipt_sha256"],
            "codec_authorities": authorities,
            "grammar_mapping_id": GRAMMAR_MAPPING_ID,
        },
        "observed_origin_count": len(origins),
        "language_branch_count": len(origins) * len(TONGUE_ORDER_SEQUENCE),
        "origins": origins,
        "radial_table": radial_receipt,
        "claim_boundary": {
            "deterministic_views_are_correlated": True,
            "independent_evidence_per_origin": 1,
            "roles_are_explicit_not_inferred": True,
            "similarity_geometry_learned": False,
        },
        "authority": {
            "training_intake": "NOT_AUTHORIZED",
            "execution": "NOT_AUTHORIZED",
            "partial_unfreeze": "NOT_AUTHORIZED",
            "serving": "NOT_AUTHORIZED",
            "merge": "NOT_AUTHORIZED",
            "promotion": "NOT_AUTHORIZED",
        },
    }
    return {**body, "receipt_sha256": _sha256_json(body)}


def verify_join_receipt(
    grid: Mapping[str, Any],
    observed_roles: Sequence[ObservedRole],
    receipt: Mapping[str, Any],
    *,
    expected_codec_authorities: Mapping[str, Any],
    table_spec: RadialTableSpec | None = None,
    sector_parameters: Sequence[float] | None = None,
) -> bool:
    """Rebuild the deterministic join and require exact canonical equality."""

    try:
        rebuilt = build_join_receipt(
            grid,
            observed_roles,
            expected_codec_authorities=expected_codec_authorities,
            table_spec=table_spec,
            sector_parameters=sector_parameters,
        )
    except (CrossTokenJoinError, TypeError, ValueError, KeyError):
        return False
    return dict(receipt) == rebuilt


__all__ = [
    "BIT_CONVENTION",
    "CODEC_SCHEMA",
    "CrossTokenJoinError",
    "GRID_SCHEMA",
    "ObservedRole",
    "SCHEMA",
    "TRIT_CONVENTION",
    "build_join_receipt",
    "verify_join_receipt",
]
