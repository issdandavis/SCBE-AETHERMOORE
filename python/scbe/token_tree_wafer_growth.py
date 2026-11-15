"""Programmatic token-tree growth over the existing 6D quine wafer.

This experiment keeps byte identity fixed and varies two derived fields:

* a wafer view: depth, signed face, four byte orientations, and micro-rotation;
* a probability field: the input token weights tilted by that wafer view.

Every generated field is rebuilt as an exact EOT lattice. The resulting receipt
answers a bounded capacity question: how many requested trees were distinct
before a view, weight-field, or combined-tree hash repeated? This is not a
claim that deterministic rotations add Shannon information or improve a model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Protocol

from python.scbe.eot_token_lattice import (
    TokenProbability,
    TokenTableDistribution,
    build_interwoven_eot_lattice,
)

TOKEN_TREE_GROWTH_SCHEMA = "scbe.quine-wafer-token-tree-growth.v2"
MAX_GENERATIONS = 4096
MAX_GENERATED_TOKEN_ROWS = 2_000_000


class TokenTreeGrowthError(ValueError):
    """A wafer adapter, growth bound, or generated tree violated its contract."""


class WaferAdapter(Protocol):
    source_file: str
    source_locator: str
    source_sha256: str
    adapter_kind: str
    external_wafer_invoked: bool
    rotor_magnitude: float
    rotor_angle_degrees: float

    def project_byte(
        self,
        byte_value: int,
        *,
        depth: int,
        side: int,
        global_rotation_degrees: float,
        patch_orientation: int,
        patch_rotation_degrees: float,
    ) -> dict[str, float | int]: ...

    def quine_probe(
        self, *, opcode: int, depth: int, side: int, phase: float
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class TokenTreeGrowthSpec:
    """A bounded sequence of wafer reprints."""

    generations: int = 24
    depth_cycle: int = 14
    global_rotation_step_degrees: float = 0.0001
    patch_rotation_step_degrees: float = 0.00001
    modulation_strength: float = 0.25
    seed: int = 0
    coordinate_decimals: int = 12

    def __post_init__(self) -> None:
        if (
            isinstance(self.generations, bool)
            or not isinstance(self.generations, int)
            or not 1 <= self.generations <= MAX_GENERATIONS
        ):
            raise ValueError(f"generations must be in 1..{MAX_GENERATIONS}")
        if (
            isinstance(self.depth_cycle, bool)
            or not isinstance(self.depth_cycle, int)
            or not 1 <= self.depth_cycle <= 256
        ):
            raise ValueError("depth_cycle must be in 1..256")
        for name, value in (
            ("global_rotation_step_degrees", self.global_rotation_step_degrees),
            ("patch_rotation_step_degrees", self.patch_rotation_step_degrees),
            ("modulation_strength", self.modulation_strength),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0.0 <= self.modulation_strength <= 8.0:
            raise ValueError("modulation_strength must be in [0, 8]")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if not 6 <= self.coordinate_decimals <= 15:
            raise ValueError("coordinate_decimals must be in 6..15")


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


def _token_sort_key(row: TokenProbability) -> tuple[str, int, int | str]:
    """Match the EOT lattice's type-preserving canonical token order."""

    if isinstance(row.token_id, int):
        return (row.byte_hex, 0, row.token_id)
    return (row.byte_hex, 1, row.token_id)


class ExternalQuineWaferAdapter:
    """Narrow adapter over ``clay_wafer_net.wafer_6d_quine``."""

    def __init__(self, wafer_repo: str | Path) -> None:
        repo = Path(wafer_repo).resolve()
        source = repo / "clay_wafer_net" / "wafer_6d_quine.py"
        if not source.is_file():
            raise TokenTreeGrowthError(f"wafer module not found: {source}")
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        module = importlib.import_module("clay_wafer_net.wafer_6d_quine")
        loaded_source = Path(module.__file__).resolve()
        if loaded_source != source:
            raise TokenTreeGrowthError(
                f"loaded wafer module {loaded_source}, expected {source}"
            )
        required = ("state6", "variable_injection_quine", "QUINE_ROTOR")
        if any(not hasattr(module, name) for name in required):
            raise TokenTreeGrowthError("wafer module is missing required APIs")
        self._module = module
        self.source_file = str(source)
        self.source_locator = "clay_wafer_net/wafer_6d_quine.py"
        self.source_sha256 = sha256(source.read_bytes()).hexdigest()
        self.adapter_kind = "external-quine-wafer"
        self.external_wafer_invoked = True
        rotor = complex(module.QUINE_ROTOR)
        self.rotor_magnitude = abs(rotor)
        self.rotor_angle_degrees = math.degrees(math.atan2(rotor.imag, rotor.real))

    def project_byte(
        self,
        byte_value: int,
        *,
        depth: int,
        side: int,
        global_rotation_degrees: float,
        patch_orientation: int,
        patch_rotation_degrees: float,
    ) -> dict[str, float | int]:
        if not 0 <= byte_value < 256:
            raise TokenTreeGrowthError("byte_value must be in 0..255")
        opcode = byte_value & 63
        orientation = byte_value >> 6
        state = self._module.state6(opcode, depth, side)
        local_patch = (
            patch_rotation_degrees if orientation == patch_orientation else 0.0
        )
        angle_degrees = 90.0 * orientation + global_rotation_degrees + local_patch
        angle = math.radians(angle_degrees)
        turn = complex(math.cos(angle), math.sin(angle))
        point = complex(state.projected) * turn
        return {
            "byte_cell": byte_value,
            "opcode_cell": opcode,
            "orientation": orientation,
            "depth": depth,
            "side": side,
            "angle_degrees": angle_degrees,
            "x": point.real,
            "y": point.imag,
            "z": float(state.height),
            "radius": abs(point),
        }

    def quine_probe(
        self, *, opcode: int, depth: int, side: int, phase: float
    ) -> dict[str, Any]:
        record = self._module.variable_injection_quine(opcode, depth, side, phase)
        return {
            "kind": record["kind"],
            "template_hash": record["template_hash"],
            "rendered_sha256": sha256(record["rendered"].encode("utf-8")).hexdigest(),
            "self_check": bool(record["self_check"]),
            "binary_roundtrip": bool(record["binary_roundtrip"]),
            "primary_consistent": bool(record["primary_consistent"]),
        }


def _empty_token_anchor_byte(row: TokenProbability) -> int:
    raw = bytes.fromhex(row.byte_hex)
    if raw:
        return raw[0]
    identity = f"{type(row.token_id).__name__}:{row.token_id}".encode("utf-8")
    return sha256(identity).digest()[0]


def _token_path_signal(
    row: TokenProbability,
    atlas: Mapping[int, Mapping[str, float | int]],
) -> float:
    """Compose one deterministic wafer signal across the complete byte path."""

    raw = bytes.fromhex(row.byte_hex)
    byte_path = raw or bytes((_empty_token_anchor_byte(row),))
    weighted_signals: list[float] = []
    weights: list[float] = []
    denominator = len(byte_path) + 1
    for position, byte_value in enumerate(byte_path):
        point = atlas[byte_value]
        phase = math.atan2(float(point["y"]), float(point["x"]))
        positional_phase = 2.0 * math.pi * (position + 1) / denominator
        radius = float(point["radius"])
        height = float(point["z"])
        signal = (
            math.cos(phase + positional_phase)
            + 0.5 * math.sin(3.0 * phase - positional_phase)
            + 0.25 * math.tanh(radius)
            + 0.125 * math.tanh(height)
        )
        weight = 1.0 / math.sqrt(position + 1.0)
        weighted_signals.append(weight * signal)
        weights.append(weight)
    return math.fsum(weighted_signals) / math.fsum(weights)


def _atlas(
    adapter: WaferAdapter,
    *,
    depth: int,
    side: int,
    global_rotation_degrees: float,
    patch_orientation: int,
    patch_rotation_degrees: float,
    decimals: int,
) -> tuple[dict[int, dict[str, float | int]], dict[str, Any]]:
    rows: dict[int, dict[str, float | int]] = {}
    coordinate_owners: dict[tuple[float, float, float], list[int]] = {}
    canonical_rows = []
    for byte_value in range(256):
        row = adapter.project_byte(
            byte_value,
            depth=depth,
            side=side,
            global_rotation_degrees=global_rotation_degrees,
            patch_orientation=patch_orientation,
            patch_rotation_degrees=patch_rotation_degrees,
        )
        rows[byte_value] = row
        coordinate = (
            round(float(row["x"]), decimals),
            round(float(row["y"]), decimals),
            round(float(row["z"]), decimals),
        )
        coordinate_owners.setdefault(coordinate, []).append(byte_value)
        canonical_rows.append(
            {
                "byte_cell": byte_value,
                "opcode_cell": int(row["opcode_cell"]),
                "orientation": int(row["orientation"]),
                "xyz": list(coordinate),
            }
        )
    collisions = [owners for owners in coordinate_owners.values() if len(owners) > 1]
    summary = {
        "atlas_sha256": _digest(canonical_rows),
        "root_cells": len(rows),
        "unique_quantized_coordinates": len(coordinate_owners),
        "coordinate_collision_group_count": len(collisions),
        "coordinate_collision_occupant_count": sum(len(group) for group in collisions),
    }
    return rows, summary


def _tilt_distribution(
    base: TokenTableDistribution,
    atlas: Mapping[int, Mapping[str, float | int]],
    *,
    generation: int,
    strength: float,
) -> tuple[TokenTableDistribution, dict[str, Any]]:
    ordered_tokens = tuple(sorted(base.tokens, key=_token_sort_key))
    logits: list[float | None] = []
    signals: list[float] = []
    for row in ordered_tokens:
        signal = _token_path_signal(row, atlas)
        signals.append(signal)
        if row.probability == 0.0:
            logits.append(None)
            continue
        logits.append(math.log(row.probability) + strength * signal)
    maximum = max(value for value in logits if value is not None)
    masses = [0.0 if value is None else math.exp(value - maximum) for value in logits]
    normalizer = math.fsum(masses)
    tokens = tuple(
        TokenProbability(
            token_id=row.token_id,
            byte_hex=row.byte_hex,
            probability=mass / normalizer,
            label=row.label,
        )
        for row, mass in zip(ordered_tokens, masses, strict=True)
    )
    generated_table_id = f"{base.table_id}@wafer-{generation:04d}"
    if len(generated_table_id) > 4096:
        generated_table_id = (
            f"wafer-{generation:04d}-" f"{sha256(base.table_id.encode()).hexdigest()}"
        )
    return (
        TokenTableDistribution(
            table_id=generated_table_id,
            tokens=tokens,
            tokenizer_fingerprint=base.tokenizer_fingerprint,
        ),
        {
            "projection_mode": "ordered-full-decoded-byte-path",
            "token_path_signal_sha256": _digest(signals),
            "unique_quantized_token_path_signals": len(
                {round(value, 15) for value in signals}
            ),
        },
    )


def grow_token_trees(
    base: TokenTableDistribution,
    adapter: WaferAdapter,
    spec: TokenTreeGrowthSpec = TokenTreeGrowthSpec(),
    *,
    source_table_sha256: str | None = None,
) -> dict[str, Any]:
    """Grow and verify a bounded family of wafer-projected token trees."""

    total_token_rows = len(base.tokens) * spec.generations
    if total_token_rows > MAX_GENERATED_TOKEN_ROWS:
        raise TokenTreeGrowthError(
            "token_count * generations cannot exceed "
            f"{MAX_GENERATED_TOKEN_ROWS} (got {total_token_rows})"
        )
    if source_table_sha256 is not None and (
        not isinstance(source_table_sha256, str)
        or len(source_table_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_table_sha256)
    ):
        raise TokenTreeGrowthError("source_table_sha256 must be lowercase SHA-256")

    ordered_base_tokens = tuple(sorted(base.tokens, key=_token_sort_key))
    base_identity = [
        {
            "typed_token_id": f"{type(row.token_id).__name__}:{row.token_id}",
            "byte_hex": row.byte_hex,
        }
        for row in ordered_base_tokens
    ]
    base_measure = [
        {**identity, "probability": row.probability}
        for identity, row in zip(base_identity, ordered_base_tokens, strict=True)
    ]

    records: list[dict[str, Any]] = []
    seen_views: dict[str, int] = {}
    seen_measures: dict[str, int] = {}
    seen_trees: dict[str, int] = {}
    first_collision: dict[str, int | str] | None = None

    for generation in range(spec.generations):
        depth = generation % spec.depth_cycle
        shell = generation // spec.depth_cycle
        side = 1 if (generation + spec.seed) % 2 == 0 else -1
        patch_orientation = (generation + spec.seed) % 4
        global_rotation = generation * spec.global_rotation_step_degrees
        patch_rotation = (shell + 1) * spec.patch_rotation_step_degrees
        atlas, atlas_summary = _atlas(
            adapter,
            depth=depth,
            side=side,
            global_rotation_degrees=global_rotation,
            patch_orientation=patch_orientation,
            patch_rotation_degrees=patch_rotation,
            decimals=spec.coordinate_decimals,
        )
        distribution, path_projection = _tilt_distribution(
            base,
            atlas,
            generation=generation,
            strength=spec.modulation_strength,
        )
        lattice = build_interwoven_eot_lattice((distribution,))
        generated_identity = [
            {
                "typed_token_id": f"{type(row.token_id).__name__}:{row.token_id}",
                "byte_hex": row.byte_hex,
            }
            for row in distribution.tokens
        ]
        if generated_identity != base_identity:
            raise AssertionError("wafer growth changed token identity or byte paths")
        measure_body = [
            {
                "typed_token_id": f"{type(row.token_id).__name__}:{row.token_id}",
                "byte_hex": row.byte_hex,
                "probability": row.probability,
            }
            for row in distribution.tokens
        ]
        measure_sha = _digest(measure_body)
        topology_sha = _digest(
            [
                {
                    "node_id": node["node_id"],
                    "parent_node_id": node["parent_node_id"],
                    "incoming_byte": node["incoming_byte"],
                }
                for node in lattice["nodes"]
            ]
        )
        tree_sha = _digest(
            {
                "atlas_sha256": atlas_summary["atlas_sha256"],
                "measure_sha256": measure_sha,
                "topology_sha256": topology_sha,
            }
        )
        quine = adapter.quine_probe(
            opcode=(spec.seed + generation) & 63,
            depth=depth,
            side=side,
            phase=math.radians(global_rotation),
        )
        record = {
            "generation": generation,
            "shell": shell,
            "depth": depth,
            "side": side,
            "global_rotation_degrees": global_rotation,
            "patch_orientation": patch_orientation,
            "patch_rotation_degrees": patch_rotation,
            "atlas": atlas_summary,
            "token_path_projection": path_projection,
            "measure_sha256": measure_sha,
            "topology_sha256": topology_sha,
            "tree_sha256": tree_sha,
            "lattice_sha256": lattice["receipt_sha256"],
            "prefix_node_count": lattice["metrics"]["prefix_node_count"],
            "maximum_reconstruction_error": lattice["metrics"][
                "maximum_path_reconstruction_abs_error"
            ],
            "quine_probe": quine,
        }
        records.append(record)
        for kind, value, seen in (
            ("view", atlas_summary["atlas_sha256"], seen_views),
            ("measure", measure_sha, seen_measures),
            ("tree", tree_sha, seen_trees),
        ):
            if value in seen and first_collision is None:
                first_collision = {
                    "kind": kind,
                    "first_generation": seen[value],
                    "repeated_generation": generation,
                }
            seen.setdefault(value, generation)

    all_quines_pass = all(
        row["quine_probe"]["self_check"]
        and row["quine_probe"]["binary_roundtrip"]
        and row["quine_probe"]["primary_consistent"]
        for row in records
    )
    max_error = max(row["maximum_reconstruction_error"] for row in records)
    body = {
        "schema": TOKEN_TREE_GROWTH_SCHEMA,
        "base_table": {
            "table_id": base.table_id,
            "token_count": len(base.tokens),
            "tokenizer_fingerprint": base.tokenizer_fingerprint,
            "identity_sha256": _digest(base_identity),
            "measure_sha256": _digest(base_measure),
            "source_table_sha256": source_table_sha256,
        },
        "spec": asdict(spec),
        "wafer_adapter": {
            "source_locator": adapter.source_locator,
            "source_sha256": adapter.source_sha256,
            "adapter_kind": adapter.adapter_kind,
            "rotor_magnitude": adapter.rotor_magnitude,
            "rotor_angle_degrees": adapter.rotor_angle_degrees,
            "external_wafer_invoked": adapter.external_wafer_invoked,
            "opcode_cells_are_geometry_keys_not_isa_semantics": True,
        },
        "records": records,
        "metrics": {
            "requested_tree_count": spec.generations,
            "built_tree_count": len(records),
            "generated_token_row_count": total_token_rows,
            "unique_view_count": len(seen_views),
            "unique_measure_count": len(seen_measures),
            "unique_combined_tree_count": len(seen_trees),
            "trees_before_first_collision": (
                len(records)
                if first_collision is None
                else int(first_collision["repeated_generation"])
            ),
            "capacity_is_lower_bound_when_no_collision": first_collision is None,
            "first_collision": first_collision,
            "maximum_path_reconstruction_abs_error": max_error,
            "all_quine_probes_pass": all_quines_pass,
        },
        "claim_boundary": {
            "byte_identity_changed": False,
            "identity_preservation_checked_each_generation": True,
            "token_topology_may_remain_constant_across_weight_fields": True,
            "deterministic_views_add_shannon_information": False,
            "model_quality_gain_proven": False,
            "neural_weights_trained": False,
            "probability_fields_are_not_neural_checkpoint_weights": True,
            "probability_tilt_uses_ordered_full_decoded_byte_path": True,
            "wafer_opcode_cell_is_not_ca_or_vm_execution_semantics": True,
            "versioned_wafer_to_isa_crosswalk_applied": False,
        },
        "receipt_security": "unkeyed-corruption-detection-only",
    }
    return {**body, "receipt_sha256": _digest(body)}


__all__ = [
    "TOKEN_TREE_GROWTH_SCHEMA",
    "ExternalQuineWaferAdapter",
    "TokenTreeGrowthError",
    "TokenTreeGrowthSpec",
    "WaferAdapter",
    "grow_token_trees",
]
