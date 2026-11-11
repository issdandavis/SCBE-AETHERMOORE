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
    binding_pool: Sequence[PrimeTokenRecord] | None = None,
) -> SealedPrimeTokenBatch:
    """Rebuild a producer packet without calling its packet builder."""

    if mode not in CONTROL_MODES:
        raise ValueError("unknown replay control mode")
    if sequence_length <= 0 or not records or len(records) != len(owner_positions):
        raise ValueError("replay records and owner positions differ")
    if frame not in VIEW_NAMES:
        raise ValueError("unknown replay frame")
    if mode == "shuffled_binding_reader" and binding_pool is None:
        raise ValueError("replay shuffled binding requires an explicit dataset-wide pool")
    if mode != "shuffled_binding_reader" and binding_pool is not None:
        raise ValueError("replay binding pool is valid only for shuffled binding")
    features = torch.zeros((len(records), sequence_length, FEATURE_WIDTH))
    owners = torch.zeros((len(records), sequence_length), dtype=torch.bool)
    views = torch.zeros((len(records), sequence_length, len(VIEW_NAMES)), dtype=torch.bool)
    flattened = [
        (batch_index, local_index, record)
        for batch_index, row in enumerate(records)
        for local_index, record in enumerate(row)
    ]
    shuffled: dict[str, Tensor] = {}
    binding_pool_sha256: str | None = None
    binding_permutation_sha256: str | None = None
    if mode == "shuffled_binding_reader":
        pool = list(binding_pool or ())
        rows: list[tuple[str, str, Tensor]] = []
        for record in pool:
            record.validate()
            receipt = _receipt(record)
            vector = _canonical_vector(record)
            rows.append((receipt, tensor_sha256(vector), vector))
        receipts = [row[0] for row in rows]
        if len(pool) < 2 or len(set(receipts)) != len(receipts):
            raise ValueError("replay shuffled binding pool must be unique and nontrivial")
        rows.sort(key=lambda row: (row[1], row[0]))
        group_counts: dict[str, int] = {}
        for _, vector_sha256, _ in rows:
            group_counts[vector_sha256] = group_counts.get(vector_sha256, 0) + 1
        shift = max(group_counts.values())
        if shift * 2 > len(rows):
            raise ValueError("replay shuffled binding pool cannot form a vector derangement")
        sources = rows[shift:] + rows[:shift]
        if any(target[1] == source[1] for target, source in zip(rows, sources, strict=True)):
            raise RuntimeError("replay shuffled binding derangement construction failed")
        shuffled = {target[0]: source[2] for target, source in zip(rows, sources, strict=True)}
        binding_pool_sha256 = hashlib.sha256(_json_bytes({"record_receipts": sorted(receipts)})).hexdigest()
        binding_permutation_sha256 = hashlib.sha256(
            _json_bytes(
                {
                    "bindings": [
                        {
                            "target_receipt": target[0],
                            "source_receipt": source[0],
                        }
                        for target, source in zip(rows, sources, strict=True)
                    ]
                }
            )
        ).hexdigest()
        if {_receipt(record) for _, _, record in flattened} - set(shuffled):
            raise ValueError("replay shuffled binding pool omits packet occurrences")
    receipt_rows = []
    for batch_index, (row, positions) in enumerate(zip(records, owner_positions, strict=True)):
        if len(row) != len(positions):
            raise ValueError("replay row and positions differ")
        current_receipts = []
        for _local_index, (record, raw_position) in enumerate(zip(row, positions, strict=True)):
            record.validate()
            position = int(raw_position)
            if position < 0 or position >= sequence_length or owners[batch_index, position]:
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
                vector = shuffled[_receipt(record)]
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
        "binding_pool_sha256": binding_pool_sha256,
        "binding_permutation_sha256": binding_permutation_sha256,
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
        binding_pool_sha256=binding_pool_sha256,
        binding_permutation_sha256=binding_permutation_sha256,
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


def verify_no_intervention_parent(
    *,
    model: FullSystemPrimeTokenInputAccessLM,
    expected_identity: Mapping[str, str],
) -> dict[str, object]:
    """Seal the checkpoint-free baseline against its declared frozen parent."""

    if expected_identity.get("arm") != "no_intervention":
        raise ValueError("checkpoint-free replay is valid only for no_intervention")
    expected_parent = str(expected_identity.get("parent_sha256") or "")
    actual_parent = module_state_sha256(model.core)
    if not expected_parent or expected_parent != actual_parent:
        raise RuntimeError("replay parent differs from no-intervention lineage")
    return {
        "checkpoint": None,
        "checkpoint_sha256": None,
        "step": 0,
        "identity_sha256": canonical_sha256(dict(expected_identity)),
        "producer_metrics_ignored": True,
        "checkpoint_free_baseline": True,
    }


@torch.no_grad()
def replay_predictions(
    model: FullSystemPrimeTokenInputAccessLM,
    token_ids: Tensor,
    targets: Tensor,
    packet: SealedPrimeTokenBatch,
    *,
    use_prime_packet: bool = True,
    record_ids: Sequence[str],
    splits: Sequence[str],
    source_families: Sequence[str],
    output_positions: Sequence[Sequence[int]],
    allowed_output_token_ids: Sequence[int],
    exact_evaluator_receipt_sha256: str,
) -> dict[str, object]:
    """Recompute only declared bounded outputs from held, receipted examples."""

    packet.validate()
    if token_ids.ndim != 2 or token_ids.dtype != torch.long:
        raise ValueError("replay token IDs must be torch.long [batch,time]")
    if targets.shape != token_ids.shape or targets.dtype != torch.long:
        raise ValueError("replay targets must match token IDs and use torch.long")
    if tuple(packet.owner_mask.shape) != tuple(token_ids.shape):
        raise ValueError("replay packet differs from token IDs")
    batch_size = token_ids.shape[0]
    if not (len(record_ids) == len(splits) == len(source_families) == len(output_positions) == batch_size):
        raise ValueError("replay provenance rows differ from batch size")
    if not all(isinstance(value, str) and value.strip() for value in record_ids) or not all(
        isinstance(value, str) and value.strip() for value in source_families
    ):
        raise ValueError("replay record and source-family identities are required")
    if any(split not in {"validation", "final_test"} for split in splits):
        raise ValueError("replay accepts only validation/final-test rows")
    if len(exact_evaluator_receipt_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in exact_evaluator_receipt_sha256
    ):
        raise ValueError("replay evaluator receipt SHA-256 is invalid")
    allowed = set(allowed_output_token_ids)
    if (
        not allowed
        or len(allowed) != len(tuple(allowed_output_token_ids))
        or any(isinstance(token_id, bool) or not isinstance(token_id, int) or token_id < 0 for token_id in allowed)
    ):
        raise ValueError("replay allowed output token IDs are invalid")
    normalized_positions: list[tuple[int, ...]] = []
    for batch_index, raw_positions in enumerate(output_positions):
        positions = tuple(int(position) for position in raw_positions)
        if not positions or positions != tuple(sorted(set(positions))):
            raise ValueError("replay output positions must be sorted and unique")
        if positions[0] < 0 or positions[-1] >= token_ids.shape[1]:
            raise ValueError("replay output position is out of bounds")
        owner_positions = packet.owner_mask[batch_index].nonzero().flatten().tolist()
        if not owner_positions or max(owner_positions) > positions[0]:
            raise ValueError("replay output precedes a required owner position")
        if any(int(targets[batch_index, position]) not in allowed for position in positions):
            raise ValueError("replay target lies outside the bounded output set")
        normalized_positions.append(positions)

    model.eval()
    logits = model(token_ids, prime_packet=packet if use_prime_packet else None)
    if logits.ndim != 3 or tuple(logits.shape[:2]) != tuple(token_ids.shape):
        raise RuntimeError("replay model returned invalid logits")
    if max(allowed) >= logits.shape[-1]:
        raise ValueError("replay allowed output token exceeds model vocabulary")
    predictions = logits.argmax(dim=-1).cpu()
    expected = targets.cpu()
    rows = []
    for batch_index in range(predictions.shape[0]):
        for position in normalized_positions[batch_index]:
            rows.append(
                {
                    "id": f"{record_ids[batch_index]}:{position}",
                    "record_id": record_ids[batch_index],
                    "split": splits[batch_index],
                    "source_family": source_families[batch_index],
                    "batch": batch_index,
                    "position": position,
                    "prediction": int(predictions[batch_index, position]),
                    "target": int(expected[batch_index, position]),
                    "correct": bool(predictions[batch_index, position] == expected[batch_index, position]),
                    "owned": bool(packet.owner_mask[batch_index, position]),
                }
            )
    correct = sum(int(row["correct"]) for row in rows)
    return {
        "schema": "scbe.prime-token-independent-replay.v1",
        "packet_seal_sha256": packet.seal_sha256,
        "exact_evaluator_receipt_sha256": exact_evaluator_receipt_sha256,
        "allowed_output_token_ids": sorted(allowed),
        "example_count": len(rows),
        "correct_count": correct,
        "accuracy": correct / len(rows) if rows else 0.0,
        "prime_packet_used": use_prime_packet,
        "outcomes": rows,
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


def verify_replay_ledger(expected_path: str | Path, replay: Mapping[str, object]) -> None:
    """Fail when a producer ledger differs from independently replayed outcomes."""

    expected = json.loads(Path(expected_path).read_text(encoding="utf-8"))
    compared_fields = (
        "packet_seal_sha256",
        "exact_evaluator_receipt_sha256",
        "allowed_output_token_ids",
        "example_count",
        "correct_count",
        "accuracy",
        "prime_packet_used",
        "outcomes",
    )
    for field in compared_fields:
        if expected.get(field) != replay.get(field):
            raise RuntimeError(f"producer ledger differs from replay for {field}")


__all__ = [
    "load_adapter_read_only",
    "reconstruct_packet_independently",
    "replay_predictions",
    "verify_no_intervention_parent",
    "verify_replay_ledger",
]
