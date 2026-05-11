#!/usr/bin/env python3
"""Augment an SFT JSONL file with a `dense_bundle` field per record.

Reads OpenAI-chat-format SFT records and writes back the same records
with an added `dense_bundle` key holding the multi-encoding view of
the user-turn payload (the prompt that the model has to answer).

The bundle lets a downstream training loop train on parallel views
of the same input: binary, hex, base64, balanced-ternary plus an
intent-polarity overlay. See src/encoding/dense_bundle.py for the
primitive.

Usage:
    python scripts/encoding/augment_sft_with_dense_bundle.py INPUT.jsonl OUTPUT.jsonl
    python scripts/encoding/augment_sft_with_dense_bundle.py INPUT.jsonl OUTPUT.jsonl --target user

The `--target` flag picks which message turn to encode (default: user).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from src.encoding.dense_bundle import (
    DenseBundle,
    bundle_intent_profile,
    route_lane_for_bundle,
)


def _pick_target_content(record: dict, target: str) -> str | None:
    """Return the content of the first message with role == target.

    Records that don't have the target role are returned unchanged
    by the caller (we just skip augmentation).
    """
    messages = record.get("messages") or []
    for msg in messages:
        if msg.get("role") == target:
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # OpenAI chat with multipart content — concatenate the text parts.
                text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
                return "".join(text_parts)
    return None


def augment_record(record: dict, target: str = "user", default_view: str = "hex") -> dict:
    """Return a new record with `dense_bundle` added.

    Pure: doesn't mutate the input. If the record has no target turn,
    returns the input as-is (no bundle added).
    """
    content = _pick_target_content(record, target)
    if content is None or content == "":
        return record
    bundle = DenseBundle.from_text(content)
    return {
        **record,
        "dense_bundle": {
            "target": target,
            "default_view": default_view,
            "route_lane": route_lane_for_bundle(default_view, bundle),
            "intent_profile": bundle_intent_profile(bundle),
            "byte_length": bundle.byte_length,
            "density_ratio": bundle.density_ratio(),
            "views": {
                "hex": bundle.hex,
                "binary": bundle.binary,
                "base64": bundle.base64,
                "ternary": bundle.ternary,
            },
            "intent": list(bundle.intent),
        },
    }


def augment_stream(records: Iterable[dict], target: str = "user", default_view: str = "hex") -> Iterable[dict]:
    for record in records:
        yield augment_record(record, target=target, default_view=default_view)


def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as fh:
        for line_num, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as err:
                print(f"[warn] line {line_num} of {path}: {err}", file=sys.stderr)
                continue


def _write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False))
            fh.write("\n")
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Augment SFT JSONL with dense_bundle field.")
    parser.add_argument("input", type=Path, help="Input SFT JSONL file (OpenAI chat format).")
    parser.add_argument("output", type=Path, help="Output JSONL with augmented records.")
    parser.add_argument(
        "--target",
        default="user",
        choices=["user", "system", "assistant"],
        help="Which message role to encode (default: user).",
    )
    parser.add_argument(
        "--default-view",
        default="hex",
        choices=["hex", "binary", "base64", "ternary"],
        help="Default view that drives the route_lane hint (default: hex).",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"[error] input not found: {args.input}", file=sys.stderr)
        return 2

    written = _write_jsonl(
        args.output,
        augment_stream(_iter_jsonl(args.input), target=args.target, default_view=args.default_view),
    )
    print(f"[ok] wrote {written} records -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
