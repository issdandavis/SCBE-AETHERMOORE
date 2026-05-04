#!/usr/bin/env python3
"""Evaluate a HYDRA challenge-loop report into completion factors."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "artifacts" / "agent_context_vault" / "challenge_loop" / "repo_ladder_validate_latest.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_context_vault" / "challenge_loop" / "eval"
SCHEMA_VERSION = "scbe_hydra_challenge_eval_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _attempt_quality(attempt: dict[str, Any]) -> float:
    result = attempt.get("result") or {}
    parsed = attempt.get("parsed_stdout")
    classification = attempt.get("classification") or {}
    if result.get("ok"):
        base = 1.0
    elif parsed and isinstance(parsed, dict):
        base = 0.55
    elif classification.get("class") in {"manifest_or_schema", "missing_artifact", "timeout"}:
        base = 0.35
    else:
        base = 0.2
    elapsed = float(result.get("elapsed_sec", 0.0) or 0.0)
    time_penalty = min(0.18, elapsed / 1800.0)
    return round(max(0.0, base - time_penalty), 6)


def evaluate_report(report: dict[str, Any]) -> dict[str, Any]:
    attempts = list(report.get("attempts") or [])
    qualities = [_attempt_quality(attempt) for attempt in attempts]
    best_quality = max(qualities) if qualities else 0.0
    ok = bool(report.get("ok"))
    completion_factor = 1.0 if ok else round(min(0.94, best_quality), 6)
    residual = round(max(0.0, 1.0 - completion_factor), 6)
    next_mode = "compact_and_archive" if ok else "reloop_with_compacted_state"
    eval_core = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "source_challenge": report.get("challenge", {}),
        "source_ok": ok,
        "attempt_count": len(attempts),
        "attempt_quality": qualities,
        "completion_factor": completion_factor,
        "residual": residual,
        "next_mode": next_mode,
        "completion_formula": "c = 1.0 on pass else max(attempt_quality); next loop consumes residual 1-c",
        "step_completion": {
            "sense": 1.0 if attempts else 0.0,
            "execute": best_quality,
            "verify": completion_factor,
            "recover": 1.0 if ok or report.get("recovery_events") else (0.35 if attempts else 0.0),
            "compact": 1.0,
        },
    }
    return {**eval_core, "eval_hash": _sha256_json(eval_core)}


def write_eval(report_path: Path = DEFAULT_INPUT, output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    payload = evaluate_report(report)
    output_root.mkdir(parents=True, exist_ok=True)
    safe_id = str(payload["source_challenge"].get("challenge_id", report_path.stem))
    out_path = output_root / f"{safe_id}_eval_latest.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return {**payload, "artifact_path": str(out_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = write_eval(args.report, args.output_root)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
