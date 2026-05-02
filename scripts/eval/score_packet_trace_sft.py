#!/usr/bin/env python3
"""Score the executable packet-trace SFT lane.

This is a small local eval gate for the agentic packet trace corpus. It does
not score a model. It proves the corpus on disk is still the deterministic
output of ``scripts/training/generate_packet_traces_sft.py`` and still obeys
the SCBE packet contracts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CORPUS = PROJECT_ROOT / "training-data" / "agentic_coding" / "packet_traces.jsonl"
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "training" / "generate_packet_traces_sft.py"
EXPECTED_CATEGORIES = {"agentic-merge-verdict", "agentic-packet-trace"}
EXPECTED_TONGUES = {"KO", "AV", "RU", "CA", "UM", "DR"}
FORBIDDEN_PROSE_TOKENS = (
    "<tool_call>",
    "<tool_result>",
    "<apply_diff>",
    "<verify>",
    "<read_file>",
    "Success: operation completed.",
    '"param": "value"',
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_packet_traces_sft", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator: {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return rows, [f"corpus not found: {path}"]
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_no} invalid JSONL: {exc.msg}")
            continue
        row["_line_no"] = line_no
        rows.append(row)
    return rows, errors


def _stable_jsonl(rows: list[dict[str, Any]]) -> bytes:
    cleaned = [{k: v for k, v in row.items() if not str(k).startswith("_")} for row in rows]
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in cleaned).encode("utf-8")


def score_packet_trace_corpus(path: Path = DEFAULT_CORPUS) -> dict[str, Any]:
    generator = _load_generator()
    rows, errors = _load_jsonl(path)
    categories: dict[str, int] = {}
    tongues: set[str] = set()
    ids: set[str] = set()
    duplicate_ids: list[str] = []
    verdict_fingerprint_failures = 0
    response_json_failures = 0
    forbidden_token_failures = 0

    for row in rows:
        row_id = str(row.get("id", ""))
        if not row_id:
            errors.append(f"line {row.get('_line_no')} missing id")
        elif row_id in ids:
            duplicate_ids.append(row_id)
        ids.add(row_id)

        category = str(row.get("category", ""))
        categories[category] = categories.get(category, 0) + 1
        if category not in EXPECTED_CATEGORIES:
            errors.append(f"{row_id or row.get('_line_no')} unexpected category {category!r}")

        meta = row.get("metadata")
        if not isinstance(meta, dict):
            errors.append(f"{row_id or row.get('_line_no')} missing metadata object")
            meta = {}
        tongue = str(meta.get("tongue", ""))
        if tongue:
            tongues.add(tongue)

        response = str(row.get("response", ""))
        instruction = str(row.get("instruction", ""))
        try:
            json.loads(response)
        except json.JSONDecodeError:
            response_json_failures += 1
            errors.append(f"{row_id or row.get('_line_no')} response is not JSON")

        for token in FORBIDDEN_PROSE_TOKENS:
            if token in response or token in instruction:
                forbidden_token_failures += 1
                errors.append(f"{row_id or row.get('_line_no')} contains forbidden prose token {token!r}")

        if category == "agentic-merge-verdict":
            recomputed = generator.recompute_fingerprint_from_metadata(meta)
            if recomputed != meta.get("packet_fingerprint"):
                verdict_fingerprint_failures += 1
                errors.append(f"{row_id or row.get('_line_no')} packet fingerprint does not recompute")

    if duplicate_ids:
        errors.append(f"duplicate ids: {sorted(duplicate_ids)}")

    missing_categories = EXPECTED_CATEGORIES - set(categories)
    if missing_categories:
        errors.append(f"missing categories: {sorted(missing_categories)}")

    missing_tongues = EXPECTED_TONGUES - tongues
    if missing_tongues:
        errors.append(f"missing tongues: {sorted(missing_tongues)}")

    expected_rows = generator.generate_pairs()
    expected_bytes = _stable_jsonl(expected_rows)
    actual_bytes = path.read_bytes() if path.is_file() else b""
    byte_deterministic = actual_bytes == expected_bytes
    if not byte_deterministic:
        errors.append("corpus bytes do not match deterministic generator output")

    trace_count = categories.get("agentic-packet-trace", 0)
    verdict_count = categories.get("agentic-merge-verdict", 0)
    expected_pair_count = len(expected_rows)
    if len(rows) != expected_pair_count:
        errors.append(f"expected {expected_pair_count} rows, found {len(rows)}")

    report = {
        "gate": "packet_trace_sft_v1",
        "pass": not errors,
        "corpus": str(path),
        "rows": len(rows),
        "expected_rows": expected_pair_count,
        "categories": dict(sorted(categories.items())),
        "trace_count": trace_count,
        "verdict_count": verdict_count,
        "tongues": sorted(tongues),
        "byte_deterministic": byte_deterministic,
        "response_json_failures": response_json_failures,
        "forbidden_token_failures": forbidden_token_failures,
        "verdict_fingerprint_failures": verdict_fingerprint_failures,
        "errors": errors,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = score_packet_trace_corpus(args.corpus)
    print(json.dumps(report, indent=2 if args.json else None, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
