"""Independent reconstruction and replay for prime-token reader evidence.

The producer packet builder and producer-written metric aggregates are not used
here.  This module repeats canonicalization, projection, control construction,
checkpoint verification, and per-example scoring through a separate code path.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import torch
from torch import Tensor

from .prime_token_catalog import VIEW_NAMES
from .prime_token_input_access import (
    CONTROL_MODES,
    FEATURE_WIDTH,
    PACKET_SCHEMA,
    RANDOM_CONTROL_SEED,
    VIEW_WIDTH,
    FullSystemPrimeTokenInputAccessLM,
    PrimeTokenRecord,
    SealedPrimeTokenBatch,
    tensor_sha256,
)
from .prime_token_training import (
    CHECKPOINT_SCHEMA,
    POINTER_SCHEMA,
    canonical_sha256,
    module_state_sha256,
    sha256_file,
)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _items(features: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    output = []
    for key in sorted(features):
        value = features[key]
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = json.dumps(value, allow_nan=False)
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = json.dumps(value, sort_keys=True, allow_nan=False)
        output.append((key, rendered))
    return tuple(output)


def _receipt(record: PrimeTokenRecord) -> str:
    body = {
        "canonical_id": record.canonical_id,
        "section_id": record.section_id,
        "source_family": record.source_family,
        "views": {name: list(_items(record.views[name])) for name in VIEW_NAMES},
    }
    return hashlib.sha256(_json_bytes(body)).hexdigest()


def _coordinates(identity: str, width: int) -> Tensor:
    raw = bytearray()
    counter = 0
    payload = identity.encode("utf-8")
    while len(raw) < width * 2:
        raw += hashlib.sha256(payload + counter.to_bytes(4, "big")).digest()
        counter += 1
    values = torch.empty(width, dtype=torch.float32)
    for index in range(width):
        integer = (raw[2 * index] << 8) | raw[2 * index + 1]
        values[index] = integer / 32767.5 - 1.0
    length = torch.sqrt(torch.sum(values * values)).clamp_min(1e-12)
    return values / length


def _canonical_vector(record: PrimeTokenRecord) -> Tensor:
    output = torch.empty(FEATURE_WIDTH, dtype=torch.float32)
    for view_index, view_name in enumerate(VIEW_NAMES):
        identity = json.dumps(
            {
                "canonical_id": record.canonical_id,
                "view": view_name,
                "features": _items(record.views[view_name]),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        start = view_index * VIEW_WIDTH
        output[start : start + VIEW_WIDTH] = _coordinates(identity, VIEW_WIDTH)
    return output


def reconstruct_packet_independently(
    records: Sequence[Sequence[PrimeTokenRecord]],
    owner_positions: Sequence[Sequence[int]],
    *,
    sequence_length: int,
    mode: str,
    frame: str = "lexical",
) -> SealedPrimeTokenBatch:
    """Rebuild a producer packet without calling its packet builder."""

    if mode not in CONTROL_MODES:
        raise ValueError("unknown replay control mode")
    if sequence_length <= 0 or not records or len(records) != len(owner_positions):
        raise ValueError("replay records and owner positions differ")
    if frame not in VIEW_NAMES:
        raise ValueError("unknown replay frame")
    features = torch.zeros((len(records), sequence_length, FEATURE_WIDTH))
    owners = torch.zeros((len(records), sequence_length), dtype=torch.bool)
    views = torch.zeros(
        (len(records), sequence_length, len(VIEW_NAMES)), dtype=torch.bool
    )
    flattened = [
        (batch_index, local_index, record)
        for batch_index, row in enumerate(records)
        for local_index, record in enumerate(row)
    ]
    shuffled: dict[tuple[int, int], Tensor] = {}
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
        source_vectors = [_canonical_vector(item[2]) for item in ordered]
        if len(source_vectors) > 1:
            source_vectors = source_vectors[1:] + source_vectors[:1]
        shuffled = {
            (item[0], item[1]): vector
            for item, vector in zip(ordered, source_vectors, strict=True)
        }
    receipt_rows = []
    for batch_index, (row, positions) in enumerate(
        zip(records, owner_positions, strict=True)
    ):
        if len(row) != len(positions):
            raise ValueError("replay row and positions differ")
        current_receipts = []
        for local_index, (record, raw_position) in enumerate(
            zip(row, positions, strict=True)
        ):
            record.validate()
            position = int(raw_position)
            if (
                position < 0
                or position >= sequence_length
                or owners[batch_index, position]
            ):
                raise ValueError("replay owner position is invalid")
            canonical = _canonical_vector(record)
            if mode == "canonical_six_view_reader":
                vector = canonical
                active = range(len(VIEW_NAMES))
            elif mode == "lexical_only_reader":
                vector = torch.zeros(FEATURE_WIDTH)
                vector[:VIEW_WIDTH] = canonical[:VIEW_WIDTH]
                active = (0,)
            elif mode == "random_fixed_reader":
                vector = torch.cat(
                    [
                        _coordinates(
                            f"random-fixed:{RANDOM_CONTROL_SEED}:"
                            f"{record.canonical_id}:{record.section_id}:{view_index}",
                            VIEW_WIDTH,
                        )
                        for view_index in range(len(VIEW_NAMES))
                    ]
                )
                active = range(len(VIEW_NAMES))
            elif mode == "shuffled_binding_reader":
                vector = shuffled[(batch_index, local_index)]
                active = range(len(VIEW_NAMES))
            else:
                segments = []
                for view_name in VIEW_NAMES:
                    identity = json.dumps(
                        {
                            "canonical_id": record.canonical_id,
                            "frame": frame,
                            "source_view": view_name,
                            "features": _items(record.views[view_name]),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    segments.append(_coordinates(identity, VIEW_WIDTH))
                vector = torch.cat(segments)
                active = range(len(VIEW_NAMES))
            features[batch_index, position] = vector
            owners[batch_index, position] = True
            views[batch_index, position, list(active)] = True
            current_receipts.append(_receipt(record))
        receipt_rows.append(tuple(current_receipts))
    metadata = {
        "schema": PACKET_SCHEMA,
        "mode": mode,
        "frame": frame if mode == "single_frame_reader" else None,
        "feature_shape": list(features.shape),
        "owner_shape": list(owners.shape),
        "view_shape": list(views.shape),
        "record_receipts": [list(row) for row in receipt_rows],
        "features_sha256": tensor_sha256(features),
        "owner_mask_sha256": tensor_sha256(owners),
        "view_mask_sha256": tensor_sha256(views),
    }
    packet = SealedPrimeTokenBatch(
        features=features,
        owner_mask=owners,
        view_mask=views,
        mode=mode,
        frame=metadata["frame"],
        record_receipts=tuple(receipt_rows),
        features_sha256=str(metadata["features_sha256"]),
        owner_mask_sha256=str(metadata["owner_mask_sha256"]),
        view_mask_sha256=str(metadata["view_mask_sha256"]),
        seal_sha256=hashlib.sha256(_json_bytes(metadata)).hexdigest(),
    )
    packet.validate()
    return packet


def load_adapter_read_only(
    checkpoint_dir: str | Path,
    *,
    model: FullSystemPrimeTokenInputAccessLM,
    expected_identity: Mapping[str, str],
) -> dict[str, object]:
    """Verify and load only adapter tensors from a checkpoint lineage."""

    root = Path(checkpoint_dir).resolve(strict=True)
    pointer = json.loads((root / "LATEST.json").read_text(encoding="utf-8"))
    if pointer.get("schema") != POINTER_SCHEMA:
        raise RuntimeError("replay pointer schema differs")
    target = (root / str(pointer.get("file"))).resolve(strict=True)
    if not target.is_relative_to(root) or sha256_file(target) != pointer.get("sha256"):
        raise RuntimeError("replay checkpoint pointer/hash verification failed")
    payload = torch.load(target, map_location="cpu", weights_only=False)
    if payload.get("schema") != CHECKPOINT_SCHEMA:
        raise RuntimeError("replay checkpoint schema differs")
    if payload.get("identity") != dict(expected_identity):
        raise RuntimeError("replay checkpoint identity differs")
    if pointer.get("identity_sha256") != canonical_sha256(dict(expected_identity)):
        raise RuntimeError("replay pointer identity differs")
    if payload.get("parent_sha256") != module_state_sha256(model.core):
        raise RuntimeError("replay parent differs from checkpoint lineage")
    model.load_adapter_state_dict(payload["adapter"])
    return {
        "checkpoint": str(target),
        "checkpoint_sha256": pointer["sha256"],
        "step": int(payload["step"]),
        "identity_sha256": pointer["identity_sha256"],
        "producer_metrics_ignored": True,
    }


@torch.no_grad()
def replay_predictions(
    model: FullSystemPrimeTokenInputAccessLM,
    token_ids: Tensor,
    targets: Tensor,
    packet: SealedPrimeTokenBatch,
) -> dict[str, object]:
    """Recompute per-position outcomes instead of trusting producer aggregates."""

    model.eval()
    logits = model(token_ids, prime_packet=packet)
    predictions = logits.argmax(dim=-1).cpu()
    expected = targets.cpu()
    rows = []
    for batch_index in range(predictions.shape[0]):
        for position in range(predictions.shape[1]):
            rows.append(
                {
                    "batch": batch_index,
                    "position": position,
                    "prediction": int(predictions[batch_index, position]),
                    "target": int(expected[batch_index, position]),
                    "correct": bool(
                        predictions[batch_index, position]
                        == expected[batch_index, position]
                    ),
                    "owned": bool(packet.owner_mask[batch_index, position]),
                }
            )
    correct = sum(int(row["correct"]) for row in rows)
    return {
        "schema": "scbe.prime-token-independent-replay.v1",
        "packet_seal_sha256": packet.seal_sha256,
        "example_count": len(rows),
        "correct_count": correct,
        "accuracy": correct / len(rows) if rows else 0.0,
        "outcomes": rows,
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


def verify_replay_ledger(
    expected_path: str | Path, replay: Mapping[str, object]
) -> None:
    """Fail when a producer ledger differs from independently replayed outcomes."""

    expected = json.loads(Path(expected_path).read_text(encoding="utf-8"))
    compared_fields = (
        "packet_seal_sha256",
        "example_count",
        "correct_count",
        "accuracy",
        "outcomes",
    )
    for field in compared_fields:
        if expected.get(field) != replay.get(field):
            raise RuntimeError(f"producer ledger differs from replay for {field}")


__all__ = [
    "load_adapter_read_only",
    "reconstruct_packet_independently",
    "replay_predictions",
    "verify_replay_ledger",
]
