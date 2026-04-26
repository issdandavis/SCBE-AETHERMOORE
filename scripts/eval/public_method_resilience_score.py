#!/usr/bin/env python3
"""Score public-method resilience for SCBE red-team games.

This encodes the Kerckhoffs-style security axiom:
the method may be known, but the system should remain hard to break because
keys, authority, state, consensus/tamper evidence, and gates remain protected.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_POSITIVES = {
    "method_public": 0.15,
    "keys_private": 0.15,
    "authority_checked": 0.15,
    "tamper_evident_ledger": 0.15,
    "dual_tokenizer_verification": 0.10,
    "ack_or_receipt_required": 0.10,
    "replay_or_duplicate_protection": 0.10,
    "red_team_method_exposed_tested": 0.10,
}

PENALTIES = {
    "depends_on_hidden_algorithm": 0.35,
    "direct_execution_from_message": 0.30,
    "raw_secret_forwarding": 0.30,
    "no_receipts": 0.15,
    "no_sender_authority_gate": 0.20,
}


def load_json_payload(value: str, *, from_file: bool = False) -> dict[str, Any]:
    if from_file:
        return json.loads(Path(value).read_text(encoding="utf-8"))
    return json.loads(value)


def score_public_method_resilience(payload: dict[str, Any]) -> dict[str, Any]:
    positives = payload.get("controls", payload)
    risks = payload.get("risks", {})
    earned: dict[str, float] = {}
    penalties: dict[str, float] = {}

    for key, weight in REQUIRED_POSITIVES.items():
        if bool(positives.get(key)):
            earned[key] = weight

    for key, weight in PENALTIES.items():
        if bool(risks.get(key) or positives.get(key)):
            penalties[key] = weight

    raw = sum(earned.values()) - sum(penalties.values())
    score = max(0.0, min(1.0, raw))
    verdict = "pass" if score >= 0.75 and not penalties else "review"
    if score < 0.50 or any(key in penalties for key in ("direct_execution_from_message", "raw_secret_forwarding")):
        verdict = "fail"

    missing = [key for key in REQUIRED_POSITIVES if key not in earned]
    return {
        "schema_version": "scbe_public_method_resilience_score_v1",
        "metric_id": "A8_PUBLIC_METHOD_RESILIENCE",
        "score": round(score, 4),
        "verdict": verdict,
        "earned": earned,
        "penalties": penalties,
        "missing_controls": missing,
        "axiom": "The method may be public; security must still hold through protected keys, authority, state, and tamper-evident verification.",
    }


def cmd_score(args: argparse.Namespace) -> int:
    payload = load_json_payload(args.input_file if args.input_file else args.json, from_file=bool(args.input_file))
    result = score_public_method_resilience(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] != "fail" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Score public-method resilience.")
    parser.add_argument("--json", default="")
    parser.add_argument("--input-file", default="")
    args = parser.parse_args()
    if not args.json and not args.input_file:
        parser.error("Provide --json or --input-file.")
    return cmd_score(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
