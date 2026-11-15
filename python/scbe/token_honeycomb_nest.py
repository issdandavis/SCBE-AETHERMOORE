"""Typed token nests over exact byte roots and weight-derived radial cells.

The canonical identity of a token remains its declared ID plus its exact byte
path.  An 18-coordinate carrier (eight bit occupancies, six balanced-trit
occupancies, length, byte mean, first byte, and last byte) determines a radial
cell without consulting token text.  Tokens that land in the same radial cell
are not overwritten: they receive unique axial coordinates in a honeycomb
sub-lattice.

Each token is compared only with a bounded window of earlier tokens carrying
the same declared family.  The resulting scores are deterministic routing
hints, not learned semantic evidence or execution authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

from python.scbe.algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    RadialTableSpec,
)
from python.scbe.bit_spine import BitSpine

TOKEN_NEST_SCHEMA = "scbe.typed-token-honeycomb-nest.v1"
B256_NEST_SCHEMA = "scbe.b256-token-honeycomb-nest.v1"
B256_TABLE_SCHEMA = "clay.b256-token-table.v1"
CARRIER_PROFILE = "scbe.byte-root-bit8-trit6-sequence4.v1"
CARRIER_DIMENSIONS = 18
MAX_CANDIDATE_WINDOW = 256
HEX_DIRECTIONS = (
    (+1, 0),
    (+1, -1),
    (0, -1),
    (-1, 0),
    (-1, +1),
    (0, +1),
)


class TokenNestError(ValueError):
    """A token, table, or nest violated its deterministic contract."""


@dataclass(frozen=True, slots=True)
class TokenNestSpec:
    """Bounded mechanics for the radial table and same-family sieve."""

    cell_count: int = 64
    sector_count: int = 8
    candidate_window: int = 24
    neighbor_count: int = 3
    seed: int = 0
    tie_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        for name, value in (
            ("cell_count", self.cell_count),
            ("sector_count", self.sector_count),
            ("candidate_window", self.candidate_window),
            ("neighbor_count", self.neighbor_count),
            ("seed", self.seed),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if self.cell_count < 2 or self.sector_count < 1:
            raise ValueError("the token nest needs cells and sectors")
        if self.cell_count % self.sector_count:
            raise ValueError("cell_count must be divisible by sector_count")
        if self.cell_count // self.sector_count < 2:
            raise ValueError("each sector needs at least two radial cells")
        if self.candidate_window < 1 or self.neighbor_count < 1:
            raise ValueError("candidate and neighbor counts must be positive")
        if self.candidate_window > MAX_CANDIDATE_WINDOW:
            raise ValueError(f"candidate_window cannot exceed {MAX_CANDIDATE_WINDOW}")
        if self.neighbor_count > self.candidate_window:
            raise ValueError("neighbor_count cannot exceed candidate_window")
        if not math.isfinite(self.tie_tolerance) or self.tie_tolerance < 0:
            raise ValueError("tie_tolerance must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class TokenNestInput:
    """One typed token with an exact, nonempty byte path."""

    canonical_id: str
    family: str
    byte_hex: str
    sequence_index: int
    label: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        if not self.canonical_id or not self.family:
            raise ValueError("canonical_id and family must be nonempty")
        if (
            isinstance(self.sequence_index, bool)
            or not isinstance(self.sequence_index, int)
            or self.sequence_index < 0
        ):
            raise ValueError("sequence_index must be a non-negative integer")
        try:
            raw = bytes.fromhex(self.byte_hex)
        except ValueError as exc:
            raise ValueError("byte_hex must be valid hexadecimal") from exc
        if not raw or raw.hex() != self.byte_hex:
            raise ValueError("byte_hex must be canonical, lowercase, and nonempty")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _json_sha256(value: object) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _unit(values: Sequence[float]) -> tuple[float, ...]:
    norm = math.sqrt(math.fsum(value * value for value in values))
    if not math.isfinite(norm) or norm == 0.0:
        raise TokenNestError("token carrier cannot be zero or non-finite")
    return tuple(float(value) / norm for value in values)


def byte_weight_vector(raw: bytes) -> tuple[float, ...]:
    """Derive the weight-only 18-coordinate carrier for one token.

    Coordinates 0..7 are mean signed bit occupancy (MSB first), 8..13 are
    mean balanced-trit occupancy, and 14..17 preserve sequence scale and byte
    endpoints.  The exact bytes remain authoritative; this vector is a routing
    projection only.
    """

    if not isinstance(raw, bytes) or not raw:
        raise TokenNestError("a token carrier needs nonempty bytes")
    bit_coordinates = []
    for shift in range(7, -1, -1):
        occupancy = math.fsum((value >> shift) & 1 for value in raw) / len(raw)
        bit_coordinates.append(2.0 * occupancy - 1.0)

    trit_sums = [0.0] * 6
    for value in raw:
        trits = BitSpine(bytes((value,))).trits()
        if len(trits) != 6 or any(trit not in (-1, 0, 1) for trit in trits):
            raise TokenNestError("balanced-trit byte view drifted")
        for index, trit in enumerate(trits):
            trit_sums[index] += float(trit)
    trit_coordinates = [total / len(raw) for total in trit_sums]

    sequence_coordinates = (
        math.tanh(math.log2(len(raw) + 1.0) / 4.0),
        2.0 * (math.fsum(raw) / len(raw)) / 255.0 - 1.0,
        2.0 * raw[0] / 255.0 - 1.0,
        2.0 * raw[-1] / 255.0 - 1.0,
    )
    vector = (*bit_coordinates, *trit_coordinates, *sequence_coordinates)
    if len(vector) != CARRIER_DIMENSIONS or not all(map(math.isfinite, vector)):
        raise TokenNestError("18-coordinate token carrier drifted")
    return tuple(vector)


def _hex_ring(radius: int) -> tuple[tuple[int, int], ...]:
    if radius < 0:
        raise ValueError("hex radius cannot be negative")
    if radius == 0:
        return ((0, 0),)
    q = HEX_DIRECTIONS[4][0] * radius
    r = HEX_DIRECTIONS[4][1] * radius
    cells: list[tuple[int, int]] = []
    for dq, dr in HEX_DIRECTIONS:
        for _ in range(radius):
            cells.append((q, r))
            q += dq
            r += dr
    return tuple(cells)


def honeycomb_coordinate(slot: int) -> tuple[int, int, int]:
    """Return ``(q, r, radius)`` for a zero-based spiral slot."""

    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
        raise ValueError("honeycomb slot must be a non-negative integer")
    if slot == 0:
        return (0, 0, 0)
    radius = int((3.0 + math.sqrt(12.0 * slot - 3.0)) // 6.0)
    ring_start = 1 + 3 * radius * (radius - 1)
    offset = slot - ring_start
    side, step = divmod(offset, radius)
    q, r = -radius, radius
    for direction_index in range(side):
        dq, dr = HEX_DIRECTIONS[direction_index]
        q += dq * radius
        r += dr * radius
    dq, dr = HEX_DIRECTIONS[side]
    return q + dq * step, r + dr * step, radius


def _shared_prefix(left: bytes, right: bytes) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def _shared_suffix(left: bytes, right: bytes) -> int:
    count = 0
    for a, b in zip(reversed(left), reversed(right)):
        if a != b:
            break
        count += 1
    return count


def _similarity(
    raw: bytes,
    vector: Sequence[float],
    prior_raw: bytes,
    prior_vector: Sequence[float],
) -> tuple[float, dict[str, float]]:
    maximum = max(len(raw), len(prior_raw))
    vector_cosine = math.fsum(
        left * right
        for left, right in zip(_unit(vector), _unit(prior_vector), strict=True)
    )
    vector_agreement = max(0.0, min(1.0, (vector_cosine + 1.0) / 2.0))
    prefix = _shared_prefix(raw, prior_raw) / maximum
    suffix = _shared_suffix(raw, prior_raw) / maximum
    length = min(len(raw), len(prior_raw)) / maximum
    left_set, right_set = set(raw), set(prior_raw)
    root_jaccard = len(left_set & right_set) / len(left_set | right_set)
    components = {
        "carrier_agreement": vector_agreement,
        "prefix_ratio": prefix,
        "suffix_ratio": suffix,
        "length_ratio": length,
        "byte_root_jaccard": root_jaccard,
    }
    score = (
        0.35 * vector_agreement
        + 0.25 * prefix
        + 0.15 * suffix
        + 0.15 * length
        + 0.10 * root_jaccard
    )
    return score, components


def _radial_cells(spec: TokenNestSpec):
    cells_per_sector = spec.cell_count // spec.sector_count
    table = AlgebraicRadialTokenTable(
        RadialTableSpec(
            cell_count=spec.cell_count,
            sector_count=spec.sector_count,
            dimensions=CARRIER_DIMENSIONS,
            depth_count=1,
            neighbor_count=min(3, cells_per_sector - 1),
            portal_count=0,
            seed=spec.seed,
        )
    )
    return table.base_cells


def _assign_cell(
    vector: Sequence[float], cells: Sequence[Any], tolerance: float
) -> tuple[int, float, tuple[int, ...]]:
    normalized = _unit(vector)
    scored = []
    for cell in cells:
        score = math.fsum(
            left * right
            for left, right in zip(normalized, cell.coordinates, strict=True)
        )
        scored.append((score, int(cell.cell_id)))
    best = max(score for score, _ in scored)
    tied = tuple(
        sorted(cell_id for score, cell_id in scored if abs(score - best) <= tolerance)
    )
    selected = tied[0]
    selected_score = next(score for score, cell_id in scored if cell_id == selected)
    return selected, selected_score, tied


def _project_residual_to_hex(
    values: Sequence[float],
) -> tuple[tuple[float, float], tuple[float, ...]]:
    """Project an 18D residual through a declared first-harmonic hex basis."""

    if len(values) != CARRIER_DIMENSIONS:
        raise TokenNestError("hex projection needs the full 18D residual")
    coefficient = 2.0 / CARRIER_DIMENSIONS
    x = coefficient * math.fsum(
        value * math.cos(2.0 * math.pi * index / CARRIER_DIMENSIONS)
        for index, value in enumerate(values)
    )
    y = coefficient * math.fsum(
        value * math.sin(2.0 * math.pi * index / CARRIER_DIMENSIONS)
        for index, value in enumerate(values)
    )
    directional = []
    for q, r in HEX_DIRECTIONS:
        direction_x = q + 0.5 * r
        direction_y = (math.sqrt(3.0) / 2.0) * r
        directional.append(x * direction_x + y * direction_y)
    return (x, y), tuple(directional)


def _node_fill(
    vector: Sequence[float], field: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Insert one carrier into a running cell centroid and retain its residue."""

    carrier = _unit(vector)
    occupancy_before = int(field["occupancy"])
    centroid_before = tuple(float(value) for value in field["centroid"])
    residual = tuple(
        value - center for value, center in zip(carrier, centroid_before, strict=True)
    )
    assimilation_gain = 1.0 / (occupancy_before + 1.0)
    absorbed = tuple(assimilation_gain * value for value in residual)
    centroid_after = tuple(
        center + delta for center, delta in zip(centroid_before, absorbed, strict=True)
    )
    remaining = tuple((1.0 - assimilation_gain) * value for value in residual)
    insertion_energy = math.fsum(value * value for value in residual)
    remaining_energy = math.fsum(value * value for value in remaining)
    consumed_fraction = (
        0.0 if insertion_energy == 0.0 else 1.0 - remaining_energy / insertion_energy
    )
    residual_projection, halo = _project_residual_to_hex(remaining)
    accumulated_halo = tuple(
        old + delta for old, delta in zip(field["halo"], halo, strict=True)
    )
    accumulated_projection = tuple(
        old + delta
        for old, delta in zip(
            field["residual_projection_xy"], residual_projection, strict=True
        )
    )
    residual_m2 = float(field["residual_m2"]) + math.fsum(
        before * after for before, after in zip(residual, remaining, strict=True)
    )
    updated = {
        "occupancy": occupancy_before + 1,
        "centroid": centroid_after,
        "halo": accumulated_halo,
        "residual_projection_xy": accumulated_projection,
        "insertion_energy": float(field["insertion_energy"]) + insertion_energy,
        "post_insertion_residual_energy": float(field["post_insertion_residual_energy"])
        + remaining_energy,
        "residual_m2": residual_m2,
    }
    event = {
        "occupancy_before": occupancy_before,
        "occupancy_after": occupancy_before + 1,
        "pressure_before": math.log1p(occupancy_before),
        "pressure_after": math.log1p(occupancy_before + 1),
        "assimilation_gain": assimilation_gain,
        "carrier_unit_vector": list(carrier),
        "centroid_before": list(centroid_before),
        "insertion_residual": list(residual),
        "absorbed_residual": list(absorbed),
        "remaining_residual": list(remaining),
        "insertion_energy": insertion_energy,
        "remaining_energy": remaining_energy,
        "consumed_energy_fraction": consumed_fraction,
        "residual_projection_xy": list(residual_projection),
        "residual_halo_by_hex_direction": [
            {"direction": list(direction), "value": value}
            for direction, value in zip(HEX_DIRECTIONS, halo, strict=True)
        ],
    }
    return event, updated


def _build_prefix_trie(token_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = [
        {
            "node_id": 0,
            "parent_id": None,
            "incoming_byte": None,
            "depth": 0,
            "terminal_token_ids": [],
        }
    ]
    edge_index: dict[tuple[int, int], int] = {}
    for token in token_rows:
        parent = 0
        for depth, value in enumerate(bytes.fromhex(token["byte_hex"]), start=1):
            key = (parent, value)
            node_id = edge_index.get(key)
            if node_id is None:
                node_id = len(nodes)
                edge_index[key] = node_id
                nodes.append(
                    {
                        "node_id": node_id,
                        "parent_id": parent,
                        "incoming_byte": value,
                        "depth": depth,
                        "terminal_token_ids": [],
                    }
                )
            parent = node_id
        nodes[parent]["terminal_token_ids"].append(token["canonical_id"])
        token["trie_terminal_node"] = parent
    return nodes


def build_typed_token_honeycomb(
    inputs: Sequence[TokenNestInput],
    *,
    spec: TokenNestSpec = TokenNestSpec(),
) -> dict[str, Any]:
    """Build a byte-prefix tree plus collision-safe weighted cell nests."""

    if not inputs:
        raise TokenNestError("a token nest needs at least one token")
    ordered = sorted(inputs, key=lambda row: (row.sequence_index, row.canonical_id))
    canonical_ids = [row.canonical_id for row in ordered]
    sequence_indexes = [row.sequence_index for row in ordered]
    if len(set(canonical_ids)) != len(canonical_ids):
        raise TokenNestError("canonical token IDs must be unique")
    if len(set(sequence_indexes)) != len(sequence_indexes):
        raise TokenNestError("sequence indexes must be unique")

    cells = _radial_cells(spec)
    cell_sectors = {int(cell.cell_id): int(cell.sector) for cell in cells}
    occupied: dict[int, int] = {}
    node_fields: dict[int, dict[str, Any]] = {}
    prior_by_family: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    byte_aliases: dict[str, list[str]] = {}

    for item in ordered:
        raw = bytes.fromhex(item.byte_hex)
        vector = byte_weight_vector(raw)
        cell_id, score, tied = _assign_cell(vector, cells, spec.tie_tolerance)
        nest_slot = occupied.get(cell_id, 0)
        occupied[cell_id] = nest_slot + 1
        q, r, radius = honeycomb_coordinate(nest_slot)
        field = node_fields.get(
            cell_id,
            {
                "occupancy": 0,
                "centroid": (0.0,) * CARRIER_DIMENSIONS,
                "halo": (0.0,) * 6,
                "residual_projection_xy": (0.0, 0.0),
                "insertion_energy": 0.0,
                "post_insertion_residual_energy": 0.0,
                "residual_m2": 0.0,
            },
        )
        fill_event, node_fields[cell_id] = _node_fill(vector, field)

        family_prior = prior_by_family.setdefault(item.family, [])
        candidates = family_prior[-spec.candidate_window :]
        scored_neighbors: list[dict[str, Any]] = []
        for prior in candidates:
            relation_score, components = _similarity(
                raw,
                vector,
                prior["raw"],
                prior["vector"],
            )
            scored_neighbors.append(
                {
                    "prior_token_id": prior["canonical_id"],
                    "prior_sequence_index": prior["sequence_index"],
                    "score": relation_score,
                    "components": components,
                    "exact_byte_match": raw == prior["raw"],
                }
            )
        scored_neighbors.sort(key=lambda row: (-row["score"], row["prior_token_id"]))
        neighbors = scored_neighbors[: spec.neighbor_count]

        row = {
            **asdict(item),
            "byte_count": len(raw),
            "byte_root_path": list(raw),
            "weight_vector": list(vector),
            "radial": {
                "cell_id": cell_id,
                "sector": cell_sectors[cell_id],
                "alignment_score": score,
                "tied_cell_ids": list(tied),
                "assignment_uses_token_text": False,
            },
            "nest": {
                "slot": nest_slot,
                "axial_q": q,
                "axial_r": r,
                "radius": radius,
                "address": f"cell:{cell_id}/hex:{q},{r}/slot:{nest_slot}",
            },
            "node_fill": fill_event,
            "same_family_prior_count": len(family_prior),
            "compared_prior_count": len(candidates),
            "prior_neighbors": neighbors,
        }
        rows.append(row)
        family_prior.append(
            {
                "canonical_id": item.canonical_id,
                "sequence_index": item.sequence_index,
                "raw": raw,
                "vector": vector,
            }
        )
        byte_aliases.setdefault(item.byte_hex, []).append(item.canonical_id)

    trie_nodes = _build_prefix_trie(rows)
    addresses = [row["nest"]["address"] for row in rows]
    alias_groups = [
        {"byte_hex": byte_hex, "token_ids": token_ids}
        for byte_hex, token_ids in sorted(byte_aliases.items())
        if len(token_ids) > 1
    ]
    root_values = sorted({value for row in rows for value in row["byte_root_path"]})
    root_dictionary = []
    for value in root_values:
        trits = BitSpine(bytes((value,))).trits()
        root_dictionary.append(
            {
                "root_id": f"b256:{value:02x}",
                "byte_value": value,
                "bits_msb_first": f"{value:08b}",
                "balanced_trits": trits,
            }
        )

    collision_cells = {
        cell_id: count for cell_id, count in sorted(occupied.items()) if count > 1
    }
    final_node_fields = [
        {
            "cell_id": cell_id,
            "occupancy": field["occupancy"],
            "pressure": math.log1p(field["occupancy"]),
            "centroid": list(field["centroid"]),
            "residual_halo_by_hex_direction": [
                {"direction": list(direction), "value": value}
                for direction, value in zip(HEX_DIRECTIONS, field["halo"], strict=True)
            ],
            "residual_projection_xy": list(field["residual_projection_xy"]),
            "cumulative_insertion_energy": field["insertion_energy"],
            "cumulative_post_insertion_residual_energy": field[
                "post_insertion_residual_energy"
            ],
            "current_residual_m2": field["residual_m2"],
        }
        for cell_id, field in sorted(node_fields.items())
    ]
    body = {
        "schema": TOKEN_NEST_SCHEMA,
        "carrier_profile": CARRIER_PROFILE,
        "carrier_dimensions": CARRIER_DIMENSIONS,
        "spec": asdict(spec),
        "root_dictionary": root_dictionary,
        "prefix_trie": trie_nodes,
        "node_fields": final_node_fields,
        "tokens": rows,
        "exact_byte_alias_groups": alias_groups,
        "metrics": {
            "token_count": len(rows),
            "family_count": len(prior_by_family),
            "byte_root_count": len(root_dictionary),
            "prefix_trie_node_count": len(trie_nodes),
            "occupied_radial_cell_count": len(occupied),
            "radial_collision_cell_count": len(collision_cells),
            "radial_collision_token_count": sum(
                count - 1 for count in collision_cells.values()
            ),
            "nested_address_collision_count": len(addresses) - len(set(addresses)),
            "exact_byte_alias_group_count": len(alias_groups),
            "prior_comparison_count": sum(row["compared_prior_count"] for row in rows),
            "cumulative_insertion_energy": math.fsum(
                field["insertion_energy"] for field in node_fields.values()
            ),
            "cumulative_post_insertion_residual_energy": math.fsum(
                field["post_insertion_residual_energy"]
                for field in node_fields.values()
            ),
            "current_residual_m2": math.fsum(
                field["residual_m2"] for field in node_fields.values()
            ),
            "maximum_node_pressure": max(
                math.log1p(field["occupancy"]) for field in node_fields.values()
            ),
        },
        "collision_contract": {
            "radial_cell_collision_is_occupancy_not_identity": True,
            "unique_identity_address": "radial cell plus axial honeycomb slot",
            "exact_byte_aliases_are_retained": True,
            "token_ids_are_never_inferred_from_geometry": True,
            "post_insertion_residual_energy_is_retained": True,
            "current_centroid_residual_m2_is_retained": True,
            "hex_halo_uses_declared_18d_to_2d_projection": True,
        },
        "claim_boundary": {
            "weight_vectors_are_deterministic_correlated_views": True,
            "same_family_scores_are_routing_hints_not_semantic_proof": True,
            "candidate_sieve_is_bounded_not_all_pairs": True,
            "node_fill_is_a_deterministic_running_mean_not_training": True,
            "learned_benefit": False,
            "execution_authority": False,
        },
    }
    if body["metrics"]["nested_address_collision_count"]:
        raise AssertionError("honeycomb nest failed to allocate unique addresses")
    return {**body, "nest_sha256": _json_sha256(body)}


def _validate_b256_table(
    payload: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], set[int]]:
    if not isinstance(payload, dict) or payload.get("schema") != B256_TABLE_SCHEMA:
        raise TokenNestError("invalid B256 token table schema")
    tokens = payload.get("tokens")
    special_ids = payload.get("special_token_ids")
    if not isinstance(tokens, list) or not isinstance(special_ids, list):
        raise TokenNestError("B256 table tokens and special IDs must be lists")
    token_ids: list[int] = []
    for row in tokens:
        if not isinstance(row, dict):
            raise TokenNestError("B256 token row fields are invalid")
        token_id = row.get("id")
        if isinstance(token_id, bool) or not isinstance(token_id, int):
            raise TokenNestError("B256 token IDs must be integers")
        token_ids.append(token_id)
    if token_ids != list(range(len(tokens))):
        raise TokenNestError("B256 token IDs must be contiguous")
    normalized_specials = set()
    for value in special_ids:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value < len(tokens)
        ):
            raise TokenNestError("B256 special token ID is invalid")
        normalized_specials.add(value)
    seen: dict[bytes, int] = {}
    for row in tokens:
        if not isinstance(row, dict) or set(row) != {"id", "hex", "length"}:
            raise TokenNestError("B256 token row fields are invalid")
        if not isinstance(row["hex"], str):
            raise TokenNestError("B256 token hex must be text")
        if isinstance(row["length"], bool) or not isinstance(row["length"], int):
            raise TokenNestError("B256 token length must be an integer")
        try:
            raw = bytes.fromhex(row["hex"])
        except ValueError as exc:
            raise TokenNestError("B256 token hex is invalid") from exc
        if not raw or row["hex"] != raw.hex() or row["length"] != len(raw):
            raise TokenNestError("B256 token byte length or canonical hex drifted")
        if raw in seen:
            raise TokenNestError(
                f"B256 collision between token {seen[raw]} and {row['id']}"
            )
        seen[raw] = row["id"]
    hash_body = {
        "schema": B256_TABLE_SCHEMA,
        "tokens": tokens,
        "special_token_ids": sorted(normalized_specials),
    }
    if payload.get("table_sha256") != _json_sha256(hash_body):
        raise TokenNestError("B256 table SHA-256 is invalid")
    vocab_size = payload.get("vocab_size")
    if vocab_size is not None:
        if isinstance(vocab_size, bool) or not isinstance(vocab_size, int):
            raise TokenNestError("B256 vocabulary size must be an integer")
        if vocab_size != len(tokens):
            raise TokenNestError("B256 vocabulary size drifted")
    return [dict(row) for row in tokens], normalized_specials


def validate_b256_table(
    payload: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], set[int]]:
    """Validate and return one hash-pinned canonical B256 table."""

    return _validate_b256_table(payload)


def build_b256_token_honeycomb(
    payload: Mapping[str, Any],
    *,
    spec: TokenNestSpec = TokenNestSpec(),
) -> dict[str, Any]:
    """Place a frozen B256 vocabulary into the collision-safe token nest."""

    tokens, special_ids = _validate_b256_table(payload)
    table_sha256 = str(payload["table_sha256"])
    nest = build_typed_token_honeycomb(
        [
            TokenNestInput(
                canonical_id=f"b256-token:{table_sha256}:{row['id']}",
                family="b256:special" if row["id"] in special_ids else "b256:token",
                byte_hex=str(row["hex"]),
                sequence_index=int(row["id"]),
                label=f"token:{row['id']}",
                source_id=table_sha256,
            )
            for row in tokens
        ],
        spec=spec,
    )
    body = {
        "schema": B256_NEST_SCHEMA,
        "source_table": {
            "schema": payload["schema"],
            "tokenizer_sha256": payload.get("tokenizer_sha256"),
            "table_sha256": table_sha256,
            "vocab_size": len(tokens),
            "special_token_count": len(special_ids),
        },
        "nest": nest,
    }
    return {**body, "receipt_sha256": _json_sha256(body)}


__all__ = [
    "B256_NEST_SCHEMA",
    "B256_TABLE_SCHEMA",
    "CARRIER_DIMENSIONS",
    "CARRIER_PROFILE",
    "MAX_CANDIDATE_WINDOW",
    "TOKEN_NEST_SCHEMA",
    "TokenNestError",
    "TokenNestInput",
    "TokenNestSpec",
    "build_b256_token_honeycomb",
    "build_typed_token_honeycomb",
    "byte_weight_vector",
    "honeycomb_coordinate",
    "validate_b256_table",
]
