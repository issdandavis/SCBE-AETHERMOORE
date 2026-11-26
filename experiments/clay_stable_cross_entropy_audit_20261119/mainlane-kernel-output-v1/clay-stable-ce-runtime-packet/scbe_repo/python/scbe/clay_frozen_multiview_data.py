"""Exact byte-token action rows for a source-disjoint frozen-adapter study.

The physical Clay action state remains a 37-value float32 vector.  Each scalar
is serialized as canonical big-endian IEEE-754 bytes and every byte is mapped
bijectively to one private-use Unicode code point.  The character model therefore
receives one stable token per byte without decimal parsing or lossy rounding.

This module only prepares data and identity receipts.  It cannot execute an
action, mutate the read-only Clay source, or grant compiler authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
import struct
from typing import Any, Mapping, Protocol, Sequence

import torch
from torch import Tensor

from python.scbe.clay_paired_orbit_training import (
    ACTION_COUNT,
    FEATURE_WIDTH,
    sha256_json,
)
from python.scbe.concept_exposure_ledger import ExposureSample

SCHEMA = "clay.frozen-multiview-action-data.v1"
BYTE_TOKEN_BASE = 0xE100
BYTE_TOKEN_LIMIT = BYTE_TOKEN_BASE + 256
STATIC_SOURCE = "clay-action-train-static-v1"
MULTIVIEW_SOURCES = tuple(
    f"clay-action-train-view-{index}-v1" for index in range(3)
)
HOLDOUT_SOURCE = "clay-action-held-diagonal-v1"


class ActionDataProvider(Protocol):
    """Read-only surface supplied by the existing Clay action generator."""

    source_hashes: Mapping[str, str]

    def training_sandboxes(self) -> tuple[Any, ...]: ...

    def holdout_sandbox(self) -> Any: ...

    def sample_state(self, sandbox: Any, rng: random.Random) -> Any: ...

    def materialize(self, sandbox: Any, state: Any) -> tuple[Tensor, int, int]: ...


def feature_bytes(feature: Tensor) -> bytes:
    """Return a platform-independent byte deed for one 37-value state."""

    value = feature.detach().cpu().to(torch.float32).contiguous()
    if value.shape != (FEATURE_WIDTH,) or not bool(torch.isfinite(value).all()):
        raise ValueError("action feature must be one finite 37-value vector")
    return b"".join(struct.pack(">f", float(item)) for item in value.tolist())


def byte_token_text(payload: bytes) -> str:
    """Map bytes bijectively to tokens that cannot collide with control text."""

    return "".join(chr(BYTE_TOKEN_BASE + value) for value in payload)


def decode_byte_token_text(value: str) -> bytes:
    decoded = []
    for token in value:
        code = ord(token)
        if not BYTE_TOKEN_BASE <= code < BYTE_TOKEN_LIMIT:
            raise ValueError("text contains a non-byte token")
        decoded.append(code - BYTE_TOKEN_BASE)
    return bytes(decoded)


def action_prompt(feature: Tensor) -> str:
    """Build the exact byte-token prompt consumed by the frozen core."""

    return "K :" + byte_token_text(feature_bytes(feature)) + " =>"


@dataclass(frozen=True, slots=True)
class ActionTextRow:
    sample: ExposureSample
    prompt: str
    target: str
    label: int
    sector: int

    def pair(self) -> tuple[str, str]:
        return self.prompt, self.target

    def identity_record(self) -> dict[str, Any]:
        return {
            **self.sample.identity_record(),
            "prompt_sha256": hashlib.sha256(
                self.prompt.encode("utf-8")
            ).hexdigest(),
            "target": self.target,
            "label": self.label,
            "sector": self.sector,
        }


@dataclass(frozen=True, slots=True)
class FrozenMultiviewDataset:
    static_rows: tuple[ActionTextRow, ...]
    multiview_rows: tuple[ActionTextRow, ...]
    holdout_rows: tuple[ActionTextRow, ...]
    manifest: Mapping[str, Any]

    def verify(self) -> bool:
        if len(self.static_rows) != len(self.multiview_rows):
            return False
        groups = (self.static_rows, self.multiview_rows, self.holdout_rows)
        if any(not rows for rows in groups):
            return False
        identities = [row.sample.payload_sha256 for rows in groups for row in rows]
        if len(identities) != len(set(identities)):
            return False
        for rows in groups:
            if any(row.label not in range(ACTION_COUNT) for row in rows):
                return False
            if any(int(row.target.strip()) != row.label for row in rows):
                return False
            for row in rows:
                decoded = decode_byte_token_text(row.prompt[3:-3])
                if len(decoded) != FEATURE_WIDTH * 4:
                    return False
                expected = hashlib.sha256(
                    decoded + bytes((row.label, row.sector & 0xFF))
                ).hexdigest()
                if expected != row.sample.payload_sha256:
                    return False
        body = dict(self.manifest)
        expected = body.pop("manifest_sha256", None)
        return expected == sha256_json(body)


def _action_quotas(count: int) -> list[int]:
    if count < ACTION_COUNT:
        raise ValueError("each row bank must be able to cover every action")
    base, remainder = divmod(count, ACTION_COUNT)
    return [base + (index < remainder) for index in range(ACTION_COUNT)]


def _collect_balanced(
    provider: ActionDataProvider,
    sandbox: Any,
    *,
    count: int,
    seed: int,
    view_id: str,
    source_family: str,
    split: str,
    used_payloads: set[str],
) -> tuple[ActionTextRow, ...]:
    quotas = _action_quotas(count)
    accepted = [0] * ACTION_COUNT
    rng = random.Random(seed)
    rows: list[ActionTextRow] = []
    attempts = 0
    while len(rows) < count and attempts < count * 512:
        attempts += 1
        state = provider.sample_state(sandbox, rng)
        feature, raw_label, raw_sector = provider.materialize(sandbox, state)
        label = int(raw_label)
        sector = int(raw_sector)
        if label not in range(ACTION_COUNT) or accepted[label] >= quotas[label]:
            continue
        payload = feature_bytes(feature)
        payload_sha256 = hashlib.sha256(
            payload + bytes((label, sector & 0xFF))
        ).hexdigest()
        if payload_sha256 in used_payloads:
            continue
        used_payloads.add(payload_sha256)
        sample_id = f"{split}-{view_id}-{len(rows):06d}"
        rows.append(
            ActionTextRow(
                sample=ExposureSample(
                    sample_id=sample_id,
                    payload_sha256=payload_sha256,
                    concept_id=f"sector-{sector}",
                    variant_id=f"byte-state-{payload_sha256[:24]}",
                    source_family=source_family,
                    split=split,
                    operation_id=f"action-{label}",
                    view_id=view_id,
                ),
                prompt=action_prompt(feature),
                target=str(label),
                label=label,
                sector=sector,
            )
        )
        accepted[label] += 1
    if len(rows) != count:
        raise RuntimeError(
            f"could not fill {view_id}: {len(rows)}/{count}; action counts={accepted}"
        )
    return tuple(rows)


def _rows_sha256(rows: Sequence[ActionTextRow]) -> str:
    return sha256_json([row.identity_record() for row in rows])


def _action_counts(rows: Sequence[ActionTextRow]) -> dict[str, int]:
    return {
        f"action-{action}": sum(row.label == action for row in rows)
        for action in range(ACTION_COUNT)
    }


def build_frozen_multiview_dataset(
    provider: ActionDataProvider,
    *,
    rows_per_view: int,
    holdout_rows: int,
    seed: int,
) -> FrozenMultiviewDataset:
    """Build equal-row static/multi-view banks and a held source family."""

    if rows_per_view < ACTION_COUNT or holdout_rows < ACTION_COUNT:
        raise ValueError("row counts must cover every action")
    sandboxes = provider.training_sandboxes()
    if len(sandboxes) != 3:
        raise ValueError("the frozen study requires exactly three legal train views")
    used_payloads: set[str] = set()
    static_rows = _collect_balanced(
        provider,
        sandboxes[0],
        count=rows_per_view * 3,
        seed=seed + 11,
        view_id="static-view-0",
        source_family=STATIC_SOURCE,
        split="train",
        used_payloads=used_payloads,
    )
    multiview_parts = []
    for view, sandbox in enumerate(sandboxes):
        multiview_parts.extend(
            _collect_balanced(
                provider,
                sandbox,
                count=rows_per_view,
                seed=seed + 101 + 37 * view,
                view_id=f"train-view-{view}",
                source_family=MULTIVIEW_SOURCES[view],
                split="train",
                used_payloads=used_payloads,
            )
        )
    multiview_rows = tuple(multiview_parts)
    held_rows = _collect_balanced(
        provider,
        provider.holdout_sandbox(),
        count=holdout_rows,
        seed=seed + 1009,
        view_id="held-diagonal",
        source_family=HOLDOUT_SOURCE,
        split="holdout",
        used_payloads=used_payloads,
    )
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "seed": seed,
        "feature_width": FEATURE_WIDTH,
        "feature_bytes_per_row": FEATURE_WIDTH * 4,
        "byte_token_base": BYTE_TOKEN_BASE,
        "byte_token_count": 256,
        "rows_per_view": rows_per_view,
        "static_rows": len(static_rows),
        "multiview_rows": len(multiview_rows),
        "holdout_rows": len(held_rows),
        "static_sha256": _rows_sha256(static_rows),
        "multiview_sha256": _rows_sha256(multiview_rows),
        "holdout_sha256": _rows_sha256(held_rows),
        "static_action_counts": _action_counts(static_rows),
        "multiview_action_counts": _action_counts(multiview_rows),
        "holdout_action_counts": _action_counts(held_rows),
        "source_hashes": dict(sorted(provider.source_hashes.items())),
        "source_families": {
            "static": [STATIC_SOURCE],
            "multiview": list(MULTIVIEW_SOURCES),
            "holdout": [HOLDOUT_SOURCE],
        },
        "source_disjoint": HOLDOUT_SOURCE
        not in {STATIC_SOURCE, *MULTIVIEW_SOURCES},
        "authority": {
            "execution": "NONE",
            "compiler": "DETERMINISTIC_LABEL_AUTHORITY_ONLY",
            "promotion": "NOT_AUTHORIZED",
        },
    }
    manifest = {**body, "manifest_sha256": sha256_json(body)}
    result = FrozenMultiviewDataset(
        static_rows=static_rows,
        multiview_rows=multiview_rows,
        holdout_rows=held_rows,
        manifest=manifest,
    )
    if not result.verify():
        raise RuntimeError("frozen multiview dataset failed its own receipt")
    return result

