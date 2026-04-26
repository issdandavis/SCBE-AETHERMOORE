#!/usr/bin/env python3
"""Tamper-evident triplet ledger for SCBE message routing.

Each record carries a blockchain-style triplet and two tokenizer views:
- previous_hash: prior committed record hash, or GENESIS for the first record
- current_hash: canonical hash of the message envelope plus previous_hash
- ack_hash: optional hash of acknowledgement/next-hop material
- tokenizer_a / tokenizer_b: two independent encodings of the same envelope

This is intentionally local-first. It provides audit integrity for routing
receipts without requiring paid blockchain infrastructure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = ROOT / "artifacts" / "message_bus" / "triplet_ledger.jsonl"
GENESIS_HASH = "0" * 64


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(payload: Any) -> str:
    data = payload if isinstance(payload, str) else canonical_json(payload)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def tokenizer_views(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return two deterministic tokenizer views over the same envelope.

    View A is byte/hex oriented. View B is word/shape oriented. They are simple
    today, but the ledger enforces the two-view contract so richer tokenizers can
    replace either side without changing the audit surface.
    """

    canonical = canonical_json(envelope)
    encoded = canonical.encode("utf-8")
    word_tokens = [item for item in canonical.replace("{", " ").replace("}", " ").replace(",", " ").split() if item]
    return {
        "tokenizer_a": {
            "name": "utf8_hex_bytes_v1",
            "token_count": len(encoded),
            "digest": hashlib.sha256(encoded.hex().encode("ascii")).hexdigest(),
        },
        "tokenizer_b": {
            "name": "canonical_word_shape_v1",
            "token_count": len(word_tokens),
            "digest": hashlib.sha256("|".join(word_tokens).encode("utf-8")).hexdigest(),
        },
    }


def load_json_payload(value: str, *, from_file: bool = False) -> dict[str, Any]:
    if from_file:
        return json.loads(Path(value).read_text(encoding="utf-8"))
    return json.loads(value)


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def build_triplet_record(
    envelope: dict[str, Any],
    *,
    previous_hash: str,
    ack_payload: dict[str, Any] | None = None,
    channel: str = "local",
) -> dict[str, Any]:
    envelope_hash = sha256_hex(envelope)
    tokenizers = tokenizer_views(envelope)
    tokenizer_pair_hash = sha256_hex(tokenizers)
    ack_hash = sha256_hex(ack_payload) if ack_payload else ""
    current_hash = sha256_hex(
        {
            "previous_hash": previous_hash,
            "envelope_hash": envelope_hash,
            "tokenizer_pair_hash": tokenizer_pair_hash,
            "ack_hash": ack_hash,
            "channel": channel,
        }
    )
    return {
        "schema_version": "scbe_message_triplet_ledger_v1",
        "created_at": now_iso(),
        "channel": channel,
        "triplet": {
            "previous_hash": previous_hash,
            "current_hash": current_hash,
            "ack_hash": ack_hash,
        },
        "envelope_hash": envelope_hash,
        "tokenizers": tokenizers,
        "tokenizer_pair_hash": tokenizer_pair_hash,
        "envelope": envelope,
    }


def append_record(
    path: Path,
    envelope: dict[str, Any],
    *,
    ack_payload: dict[str, Any] | None = None,
    channel: str = "local",
) -> dict[str, Any]:
    records = read_records(path)
    previous_hash = records[-1]["triplet"]["current_hash"] if records else GENESIS_HASH
    record = build_triplet_record(envelope, previous_hash=previous_hash, ack_payload=ack_payload, channel=channel)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(record) + "\n")
    return record


def verify_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    previous_hash = GENESIS_HASH
    failures: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        triplet = record.get("triplet") or {}
        envelope = record.get("envelope")
        channel = record.get("channel", "local")
        expected_envelope_hash = sha256_hex(envelope)
        expected_tokenizers = tokenizer_views(envelope)
        expected_tokenizer_pair_hash = sha256_hex(expected_tokenizers)
        expected_current_hash = sha256_hex(
            {
                "previous_hash": previous_hash,
                "envelope_hash": expected_envelope_hash,
                "tokenizer_pair_hash": expected_tokenizer_pair_hash,
                "ack_hash": triplet.get("ack_hash", ""),
                "channel": channel,
            }
        )
        if triplet.get("previous_hash") != previous_hash:
            failures.append({"index": idx, "reason": "previous_hash_mismatch"})
        if record.get("envelope_hash") != expected_envelope_hash:
            failures.append({"index": idx, "reason": "envelope_hash_mismatch"})
        if record.get("tokenizers") != expected_tokenizers:
            failures.append({"index": idx, "reason": "tokenizer_views_mismatch"})
        if record.get("tokenizer_pair_hash") != expected_tokenizer_pair_hash:
            failures.append({"index": idx, "reason": "tokenizer_pair_hash_mismatch"})
        if triplet.get("current_hash") != expected_current_hash:
            failures.append({"index": idx, "reason": "current_hash_mismatch"})
        previous_hash = str(triplet.get("current_hash", ""))
    return {
        "schema_version": "scbe_message_triplet_ledger_verify_v1",
        "record_count": len(records),
        "ok": not failures,
        "failures": failures,
        "head_hash": previous_hash if records else GENESIS_HASH,
    }


def cmd_append(args: argparse.Namespace) -> int:
    envelope = load_json_payload(args.envelope_file if args.envelope_file else args.envelope, from_file=bool(args.envelope_file))
    ack_payload = None
    if args.ack_file:
        ack_payload = load_json_payload(args.ack_file, from_file=True)
    elif args.ack:
        ack_payload = load_json_payload(args.ack)
    record = append_record(Path(args.ledger), envelope, ack_payload=ack_payload, channel=args.channel)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    result = verify_records(read_records(Path(args.ledger)))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="SCBE message triplet ledger.")
    sub = parser.add_subparsers(dest="command", required=True)

    append = sub.add_parser("append", help="Append a message envelope to the triplet ledger.")
    append.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    append.add_argument("--envelope", default="")
    append.add_argument("--envelope-file", default="")
    append.add_argument("--ack", default="")
    append.add_argument("--ack-file", default="")
    append.add_argument("--channel", default="local")
    append.set_defaults(func=cmd_append)

    verify = sub.add_parser("verify", help="Verify a triplet ledger.")
    verify.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
