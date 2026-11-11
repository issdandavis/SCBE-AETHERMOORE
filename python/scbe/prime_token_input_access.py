"""Frozen-core input access for typed prime-token catalog packets.

The six catalog views are deterministic, correlated descriptions of one
canonical occurrence.  This module preserves that fact in a sealed packet and
offers equal-width controls without granting execution authority.  It is a
mechanics surface: no tool dispatch, promotion, or partial unfreezing lives
here.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Final, Mapping, Sequence

import torch
from torch import Tensor, nn

from .prime_token_catalog import VIEW_NAMES

PACKET_SCHEMA: Final = "scbe.prime-token-input-access.v1"
FULL_SYSTEM_SCHEMA: Final = "scbe.full-system-prime-token-input-access.v1"
CONTROL_MODES: Final = (
    "lexical_only_reader",
    "canonical_six_view_reader",
    "random_fixed_reader",
    "shuffled_binding_reader",
    "single_frame_reader",
)
VIEW_WIDTH: Final = 8
FEATURE_WIDTH: Final = len(VIEW_NAMES) * VIEW_WIDTH
RANDOM_CONTROL_SEED: Final = 20261111


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def tensor_sha256(value: Tensor) -> str:
    tensor = value.detach().cpu().contiguous()
    header = f"{tensor.dtype}|{tuple(tensor.shape)}|".encode("ascii")
    return hashlib.sha256(header + tensor.numpy().tobytes()).hexdigest()


def _feature_items(features: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for key, value in sorted(features.items()):
        if not isinstance(key, str) or not key:
            raise ValueError("view feature keys must be non-empty strings")
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("view feature values must be finite")
            rendered = json.dumps(value, allow_nan=False)
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = json.dumps(value, sort_keys=True, allow_nan=False)
        rows.append((key, rendered))
    return tuple(rows)


def _project_identity(identity: str, *, width: int = VIEW_WIDTH) -> Tensor:
    """Project a typed identity to bounded deterministic coordinates."""

    if not identity or width <= 0:
        raise ValueError("projection requires a non-empty identity and positive width")
    stream = bytearray()
    counter = 0
    encoded = identity.encode("utf-8")
    while len(stream) < width * 2:
        stream.extend(hashlib.sha256(encoded + counter.to_bytes(4, "big")).digest())
        counter += 1
    values = []
    for index in range(width):
        raw = int.from_bytes(stream[index * 2 : index * 2 + 2], "big")
        values.append((raw / 32767.5) - 1.0)
    vector = torch.tensor(values, dtype=torch.float32)
    return vector / vector.norm().clamp_min(1e-12)


@dataclass(frozen=True, slots=True)
class PrimeTokenRecord:
    """One canonical occurrence and its six correlated catalog views."""

    canonical_id: str
    section_id: str
    source_family: str
    views: Mapping[str, Mapping[str, object]]

    def validate(self) -> None:
        if not self.canonical_id or not self.section_id or not self.source_family:
            raise ValueError("prime-token identity fields must be non-empty")
        if set(self.views) != set(VIEW_NAMES):
            raise ValueError(
                "prime-token record must contain exactly the six named views"
            )
        for view_name in VIEW_NAMES:
            _feature_items(self.views[view_name])

    def receipt(self) -> str:
        self.validate()
        return _sha256_json(
            {
                "canonical_id": self.canonical_id,
                "section_id": self.section_id,
                "source_family": self.source_family,
                "views": {
                    name: list(_feature_items(self.views[name])) for name in VIEW_NAMES
                },
            }
        )


def _canonical_record_vector(record: PrimeTokenRecord) -> Tensor:
    segments = []
    for view_name in VIEW_NAMES:
        identity = json.dumps(
            {
                "canonical_id": record.canonical_id,
                "view": view_name,
                "features": _feature_items(record.views[view_name]),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        segments.append(_project_identity(identity))
    return torch.cat(segments)


def _random_fixed_vector(record: PrimeTokenRecord) -> Tensor:
    return torch.cat(
        [
            _project_identity(
                f"random-fixed:{RANDOM_CONTROL_SEED}:{record.canonical_id}:"
                f"{record.section_id}:{view_index}"
            )
            for view_index in range(len(VIEW_NAMES))
        ]
    )


def _single_frame_vector(record: PrimeTokenRecord, frame: str) -> Tensor:
    if frame not in VIEW_NAMES:
        raise ValueError(f"unknown single frame: {frame}")
    segments = []
    for view_name in VIEW_NAMES:
        identity = json.dumps(
            {
                "canonical_id": record.canonical_id,
                "frame": frame,
                "source_view": view_name,
                "features": _feature_items(record.views[view_name]),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        segments.append(_project_identity(identity))
    return torch.cat(segments)


@dataclass(frozen=True, slots=True)
class SealedPrimeTokenBatch:
    """Fixed features bound to explicit processor-owned token positions."""

    features: Tensor
    owner_mask: Tensor
    view_mask: Tensor
    mode: str
    frame: str | None
    record_receipts: tuple[tuple[str, ...], ...]
    features_sha256: str
    owner_mask_sha256: str
    view_mask_sha256: str
    seal_sha256: str

    def metadata(self) -> dict[str, object]:
        return {
            "schema": PACKET_SCHEMA,
            "mode": self.mode,
            "frame": self.frame,
            "feature_shape": list(self.features.shape),
            "owner_shape": list(self.owner_mask.shape),
            "view_shape": list(self.view_mask.shape),
            "record_receipts": [list(row) for row in self.record_receipts],
            "features_sha256": self.features_sha256,
            "owner_mask_sha256": self.owner_mask_sha256,
            "view_mask_sha256": self.view_mask_sha256,
        }

    def validate(self) -> None:
        if self.mode not in CONTROL_MODES:
            raise ValueError("sealed prime-token mode is invalid")
        if self.features.ndim != 3 or self.features.shape[-1] != FEATURE_WIDTH:
            raise ValueError("prime-token features have invalid shape")
        if self.owner_mask.ndim != 2 or self.owner_mask.dtype != torch.bool:
            raise ValueError("prime-token owner mask must be boolean [batch,time]")
        expected_view_shape = (*self.owner_mask.shape, len(VIEW_NAMES))
        if tuple(self.view_mask.shape) != expected_view_shape:
            raise ValueError("prime-token view mask has invalid shape")
        if self.view_mask.dtype != torch.bool:
            raise ValueError("prime-token view mask must be boolean")
        if self.features.shape[:2] != self.owner_mask.shape:
            raise ValueError("prime-token features and owner mask differ")
        if len(self.record_receipts) != self.features.shape[0]:
            raise ValueError("prime-token receipt batch differs")
        for receipts, owner in zip(self.record_receipts, self.owner_mask, strict=True):
            if len(receipts) != int(owner.sum().item()):
                raise ValueError("prime-token receipt count differs from owner count")
        if tensor_sha256(self.features) != self.features_sha256:
            raise ValueError("sealed prime-token features were mutated")
        if tensor_sha256(self.owner_mask) != self.owner_mask_sha256:
            raise ValueError("sealed prime-token owner mask was mutated")
        if tensor_sha256(self.view_mask) != self.view_mask_sha256:
            raise ValueError("sealed prime-token view mask was mutated")
        if _sha256_json(self.metadata()) != self.seal_sha256:
            raise ValueError("sealed prime-token receipt differs")


def build_prime_token_batch(
    records: Sequence[Sequence[PrimeTokenRecord]],
    owner_positions: Sequence[Sequence[int]],
    *,
    sequence_length: int,
    mode: str,
    frame: str = "lexical",
) -> SealedPrimeTokenBatch:
    """Build one equal-width candidate or control packet."""

    if mode not in CONTROL_MODES:
        raise ValueError(f"unknown prime-token control mode: {mode}")
    if sequence_length <= 0 or not records or len(records) != len(owner_positions):
        raise ValueError(
            "records require matching positions and positive sequence length"
        )
    if mode == "single_frame_reader" and frame not in VIEW_NAMES:
        raise ValueError(f"unknown single frame: {frame}")

    features = torch.zeros((len(records), sequence_length, FEATURE_WIDTH))
    owner_mask = torch.zeros((len(records), sequence_length), dtype=torch.bool)
    view_mask = torch.zeros(
        (len(records), sequence_length, len(VIEW_NAMES)), dtype=torch.bool
    )
    receipts: list[tuple[str, ...]] = []

    flattened = [
        (batch_index, local_index, record)
        for batch_index, row in enumerate(records)
        for local_index, record in enumerate(row)
    ]
    for _, _, record in flattened:
        record.validate()
    shuffled_vectors: dict[tuple[int, int], Tensor] = {}
    if mode == "shuffled_binding_reader":
        ordered = sorted(
            flattened,
            key=lambda item: (
                item[2].canonical_id,
                item[2].section_id,
                item[0],
                item[1],
            ),
        )
        vectors = [_canonical_record_vector(item[2]) for item in ordered]
        if len(vectors) > 1:
            vectors = vectors[1:] + vectors[:1]
        shuffled_vectors = {
            (item[0], item[1]): vector
            for item, vector in zip(ordered, vectors, strict=True)
        }

    for batch_index, (row, raw_positions) in enumerate(
        zip(records, owner_positions, strict=True)
    ):
        positions = tuple(int(position) for position in raw_positions)
        if len(row) != len(positions) or len(set(positions)) != len(positions):
            raise ValueError("each unique owner position requires exactly one record")
        if any(position < 0 or position >= sequence_length for position in positions):
            raise ValueError("prime-token owner position is out of bounds")
        row_receipts: list[str] = []
        for local_index, (record, position) in enumerate(
            zip(row, positions, strict=True)
        ):
            if mode == "canonical_six_view_reader":
                vector = _canonical_record_vector(record)
                active_views = range(len(VIEW_NAMES))
            elif mode == "lexical_only_reader":
                vector = torch.zeros(FEATURE_WIDTH)
                vector[:VIEW_WIDTH] = _canonical_record_vector(record)[:VIEW_WIDTH]
                active_views = (0,)
            elif mode == "random_fixed_reader":
                vector = _random_fixed_vector(record)
                active_views = range(len(VIEW_NAMES))
            elif mode == "shuffled_binding_reader":
                vector = shuffled_vectors[(batch_index, local_index)]
                active_views = range(len(VIEW_NAMES))
            else:
                vector = _single_frame_vector(record, frame)
                active_views = range(len(VIEW_NAMES))
            features[batch_index, position] = vector
            owner_mask[batch_index, position] = True
            view_mask[batch_index, position, list(active_views)] = True
            row_receipts.append(record.receipt())
        receipts.append(tuple(row_receipts))

    metadata = {
        "schema": PACKET_SCHEMA,
        "mode": mode,
        "frame": frame if mode == "single_frame_reader" else None,
        "feature_shape": list(features.shape),
        "owner_shape": list(owner_mask.shape),
        "view_shape": list(view_mask.shape),
        "record_receipts": [list(row) for row in receipts],
        "features_sha256": tensor_sha256(features),
        "owner_mask_sha256": tensor_sha256(owner_mask),
        "view_mask_sha256": tensor_sha256(view_mask),
    }
    return SealedPrimeTokenBatch(
        features=features,
        owner_mask=owner_mask,
        view_mask=view_mask,
        mode=mode,
        frame=metadata["frame"],
        record_receipts=tuple(receipts),
        features_sha256=str(metadata["features_sha256"]),
        owner_mask_sha256=str(metadata["owner_mask_sha256"]),
        view_mask_sha256=str(metadata["view_mask_sha256"]),
        seal_sha256=_sha256_json(metadata),
    )


class PrimeTokenInputReader(nn.Module):
    """Equal-shape low-rank reader for every learned arm."""

    def __init__(self, width: int, rank: int = 32) -> None:
        super().__init__()
        if width <= 0 or rank <= 0 or rank > width:
            raise ValueError("prime-token reader requires 0 < rank <= width")
        self.width = width
        self.rank = rank
        self.down = nn.Linear(FEATURE_WIDTH, rank, bias=False)
        self.up = nn.Linear(rank, width, bias=False)
        self.activation = nn.GELU()
        nn.init.zeros_(self.up.weight)

    def forward(self, language_values: Tensor, packet: SealedPrimeTokenBatch) -> Tensor:
        packet.validate()
        if (
            language_values.ndim != 3
            or language_values.shape[:2] != packet.owner_mask.shape
        ):
            raise ValueError("language values and prime-token packet shapes differ")
        if language_values.shape[-1] != self.width:
            raise ValueError("language width differs from prime-token reader")
        features = packet.features.to(language_values.device, language_values.dtype)
        owner = packet.owner_mask.to(language_values.device)
        projected = self.up(self.activation(self.down(features)))
        return torch.where(owner.unsqueeze(-1), projected, language_values)


def _append_meta(result, meta: dict[str, object]):
    if isinstance(result, tuple):
        return (*result, meta)
    return result, meta


class FullSystemPrimeTokenInputAccessLM(nn.Module):
    """Attach a typed pre-block-0 reader to a frozen FullSystemLM-compatible core."""

    def __init__(self, core: nn.Module, *, reader_rank: int = 32) -> None:
        super().__init__()
        required = (
            "config",
            "input",
            "position",
            "blocks",
            "tilts",
            "route",
            "lane_decoders",
            "final_norm",
            "head",
        )
        missing = [name for name in required if not hasattr(core, name)]
        if missing:
            raise TypeError(f"full-system core is missing required members: {missing}")
        self.core = core
        self.reader = PrimeTokenInputReader(int(core.config.d_model), reader_rank)
        self.freeze_core()

    def freeze_core(self) -> None:
        for parameter in self.core.parameters():
            parameter.requires_grad_(False)
        for parameter in self.reader.parameters():
            parameter.requires_grad_(True)

    def adapter_state_dict(self) -> dict[str, Tensor]:
        return {
            name: tensor.detach().cpu().clone()
            for name, tensor in self.reader.state_dict().items()
        }

    def load_adapter_state_dict(self, state: Mapping[str, Tensor]) -> None:
        self.reader.load_state_dict(dict(state), strict=True)

    def parameter_receipt(self) -> dict[str, object]:
        trainable = {
            name: parameter.numel()
            for name, parameter in self.named_parameters()
            if parameter.requires_grad
        }
        return {
            "schema": FULL_SYSTEM_SCHEMA,
            "input_access": "before_block_0",
            "feature_width": FEATURE_WIDTH,
            "trainable_parameters": sum(trainable.values()),
            "trainable_tensors": trainable,
            "frozen_core_parameters": sum(p.numel() for p in self.core.parameters()),
            "token_derived_owned_paths_masked": ("hidden", "route_lanes", "raw_lanes"),
            "tool_dispatch": False,
            "promotion_authorized": False,
            "partial_unfreeze_authorized": False,
        }

    def forward(
        self,
        token_ids: Tensor,
        *,
        prime_packet: SealedPrimeTokenBatch | None = None,
        return_diagnostics: bool = False,
        return_aux: bool = False,
        return_prime_meta: bool = False,
    ):
        if prime_packet is None:
            result = self.core(
                token_ids,
                return_diagnostics=return_diagnostics,
                return_aux=return_aux,
            )
            if return_prime_meta:
                return _append_meta(
                    result,
                    {
                        "schema": FULL_SYSTEM_SCHEMA,
                        "prime_packet_used": False,
                        "owner_positions": 0,
                        "false_activation": False,
                        "tool_dispatch": False,
                    },
                )
            return result

        prime_packet.validate()
        if token_ids.ndim != 2 or token_ids.dtype != torch.long:
            raise ValueError("token_ids must be a torch.long [batch,time] tensor")
        if tuple(token_ids.shape) != tuple(prime_packet.owner_mask.shape):
            raise ValueError("token IDs and prime-token owner mask differ")
        if token_ids.shape[1] > int(self.core.config.block_size):
            raise ValueError("token sequence exceeds the frozen core block size")

        hidden, route_lanes, raw_lanes = self.core.input(token_ids)
        positions = torch.arange(token_ids.shape[1], device=token_ids.device)
        hidden = hidden + self.core.position(positions)[None, :, :]
        hidden = self.reader(hidden, prime_packet)
        owner = prime_packet.owner_mask.to(token_ids.device)[..., None, None]
        route_lanes = torch.where(owner, torch.zeros_like(route_lanes), route_lanes)
        raw_lanes = torch.where(owner, torch.zeros_like(raw_lanes), raw_lanes)

        route_state = self.core.route.initial_state(route_lanes)
        traces = []
        for index, (block, tilt) in enumerate(
            zip(self.core.blocks, self.core.tilts, strict=True)
        ):
            hidden = tilt(block(hidden))
            if self.core.config.route_mode != "off":
                hidden, route_state, trace = self.core.route.step(
                    hidden, route_state, index
                )
                if return_diagnostics:
                    traces.append(trace)
        logits = self.core.head(self.core.final_norm(hidden))

        aux = None
        if return_aux:
            lane_logits = torch.stack(
                [
                    decoder(raw_lanes[:, :, index])
                    for index, decoder in enumerate(self.core.lane_decoders)
                ],
                dim=2,
            )
            aux = {"lane_logits": lane_logits}
        if return_diagnostics and return_aux:
            result = (logits, traces, aux)
        elif return_diagnostics:
            result = (logits, traces)
        elif return_aux:
            result = (logits, aux)
        else:
            result = logits
        if return_prime_meta:
            result = _append_meta(
                result,
                {
                    "schema": FULL_SYSTEM_SCHEMA,
                    "prime_packet_used": True,
                    "owner_positions": int(prime_packet.owner_mask.sum().item()),
                    "mode": prime_packet.mode,
                    "seal_sha256": prime_packet.seal_sha256,
                    "false_activation": False,
                    "token_derived_owned_paths_masked": True,
                    "tool_dispatch": False,
                },
            )
        return result


__all__ = [
    "CONTROL_MODES",
    "FEATURE_WIDTH",
    "FULL_SYSTEM_SCHEMA",
    "FullSystemPrimeTokenInputAccessLM",
    "PACKET_SCHEMA",
    "PrimeTokenInputReader",
    "PrimeTokenRecord",
    "SealedPrimeTokenBatch",
    "VIEW_WIDTH",
    "build_prime_token_batch",
    "tensor_sha256",
]
