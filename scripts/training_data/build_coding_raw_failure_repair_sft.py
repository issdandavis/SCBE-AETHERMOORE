#!/usr/bin/env python3
"""Build analog repair SFT rows from coding-gate raw failures.

The v6f production-shim gate can pass while the bare model still fails most
prompts. Those raw failures are useful training signal, but the frozen eval
contract must stay clean: this builder does not copy held-out prompt text into
the SFT rows. It maps each raw failure to a neighboring analog task that teaches
the same missing behavior class.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
TRAIN_NAME = "coding_raw_failure_repair_v1_train.sft.jsonl"
EVAL_NAME = "coding_raw_failure_repair_v1_eval.sft.jsonl"
MANIFEST_NAME = "coding_raw_failure_repair_v1_manifest.json"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE coding repair tutor. Teach the model to satisfy "
    "coding-gate contracts directly, without relying on the production prefix shim. "
    "Use neighboring analog examples, preserve code/language boundaries, and do not "
    "copy frozen evaluation prompt text."
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    if payload.get("event") == "gate_report" and isinstance(payload.get("report"), dict):
        return payload["report"]
    return payload


def _extract_gate_report_from_logs(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    latest: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or '"gate_report"' not in line:
            continue
        start = line.find("{")
        if start < 0:
            continue
        try:
            event, _ = decoder.raw_decode(line[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("event") == "gate_report" and isinstance(event.get("report"), dict):
            latest = event["report"]
    if latest is None:
        raise ValueError("No gate_report event found in logs")
    return latest


def _gate_report_from_hf_job(job_id: str) -> dict[str, Any]:
    env = {**os.environ, "HF_HUB_DISABLE_PROGRESS_BARS": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    result = subprocess.run(
        ["hf", "jobs", "logs", job_id],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode != 0 and not combined.strip():
        raise RuntimeError(f"hf jobs logs failed for {job_id}: returncode={result.returncode}")
    return _extract_gate_report_from_logs(combined)


def failure_kind(prompt_id: str) -> str:
    pid = prompt_id.lower()
    if "translate" in pid or "haskell" in pid:
        return "cross_tongue_slot_translation"
    if "zero_guard" in pid or "safe_" in pid:
        return "guarded_python_body"
    if "clamp" in pid:
        return "rust_branch_body"
    if "javascript" in pid or "avali" in pid:
        return "javascript_empty_guard"
    if "identify_algorithm" in pid:
        return "algorithm_slot_identification"
    if "multi_lens" in pid:
        return "multi_lens_consistency"
    if "approval_card" in pid:
        return "approval_card_verdict"
    if "geoseal_pair" in pid:
        return "route_plus_python_body"
    if "lane_boundary" in pid or "no_chem" in pid:
        return "code_chemistry_boundary"
    if "dict_merge" in pid:
        return "dictionary_merge_body"
    if "runethic" in pid or "option" in pid:
        return "rust_option_body"
    if "inventory" in pid or "unique" in pid:
        return "first_seen_unique_body"
    return "generic_coding_contract_body"


ANALOGS: dict[str, list[dict[str, str]]] = {
    "first_seen_unique_body": [
        {
            "instruction": "Implement dedupe_codes(codes) in Kor'aelin/Python. Return first-seen unique codes with a seen-set guard.",
            "answer": (
                "def dedupe_codes(codes):\n"
                "    seen = set()\n"
                "    result = []\n"
                "    for code in codes:\n"
                "        if code not in seen:\n"
                "            seen.add(code)\n"
                "            result.append(code)\n"
                "    return result"
            ),
        },
        {
            "instruction": "Implement first_seen_tags(tags) in Kor'aelin/Python using a set and preserving order.",
            "answer": (
                "def first_seen_tags(tags):\n"
                "    seen = set()\n"
                "    output = []\n"
                "    for tag in tags:\n"
                "        if tag not in seen:\n"
                "            seen.add(tag)\n"
                "            output.append(tag)\n"
                "    return output"
            ),
        },
    ],
    "cross_tongue_slot_translation": [
        {
            "instruction": (
                "Translate a Kor'aelin/Python count_digits routine to Umbroth/Haskell. "
                "Preserve slot labels sig, init, loop_open, loop_body, ret."
            ),
            "answer": (
                "umbroth / haskell\n"
                "sig: count_digits :: String -> Int\n"
                "init: count_digits s = foldl step 0 s\n"
                "loop_open: step acc ch\n"
                "loop_body: | ch >= '0' && ch <= '9' = acc + 1\n"
                "ret: | otherwise = acc"
            ),
        },
        {
            "instruction": "Render an Umbroth slot map for count_spaces over a string.",
            "answer": (
                "umbroth / haskell\n"
                "sig: count_spaces :: String -> Int\n"
                "init: count_spaces xs = foldl step 0 xs\n"
                "loop_open: step acc ch\n"
                "loop_body: if ch == ' ' then acc + 1 else acc\n"
                "ret: final accumulator is returned by foldl"
            ),
        },
    ],
    "guarded_python_body": [
        {
            "instruction": "Implement safe_add(a, b) in Kor'aelin/Python. Return None when either argument is None.",
            "answer": "def safe_add(a, b):\n    if a is None or b is None:\n        return None\n    return a + b",
        },
        {
            "instruction": "Implement safe_multiply(a, b) with explicit None guards.",
            "answer": "def safe_multiply(a, b):\n    if a is None or b is None:\n        return None\n    return a * b",
        },
    ],
    "rust_branch_body": [
        {
            "instruction": "Implement bound_score(x, lo, hi) in Runethic/Rust using i64 branch checks.",
            "answer": (
                "fn bound_score(x: i64, lo: i64, hi: i64) -> i64 {\n"
                "    if x < lo { return lo; }\n"
                "    if x > hi { return hi; }\n"
                "    return x;\n"
                "}"
            ),
        }
    ],
    "javascript_empty_guard": [
        {
            "instruction": "Implement firstToken(text) in Avali/JavaScript with export function syntax and an empty-string guard.",
            "answer": (
                "export function firstToken(text) {\n"
                "  if (!text) return '';\n"
                "  const parts = text.split(' ');\n"
                "  return parts[0];\n"
                "}"
            ),
        }
    ],
    "algorithm_slot_identification": [
        {
            "instruction": "Identify the algorithm and slots for a Haskell snippet named incrementAll using map (+1).",
            "answer": "algorithm: increment all values\ntongue: umbroth phi=6.85\nslots: sig, body\nsig: incrementAll :: [Int] -> [Int]\nbody: map (+1)",
        }
    ],
    "multi_lens_consistency": [
        {
            "instruction": "Provide KO, AV, and RU lenses for double(x), preserving the same multiply-by-two body.",
            "answer": (
                "kor'aelin:\n"
                "def double(x):\n    return x * 2\n\n"
                "avali:\n"
                "export function double(x) {\n  return x * 2;\n}\n\n"
                "runethic:\n"
                "fn double(x: i64) -> i64 {\n    return x * 2;\n}"
            ),
        }
    ],
    "approval_card_verdict": [
        {
            "instruction": "Evaluate a file-processing task card and return verdict, evidence, next action, horizon, and route names.",
            "answer": (
                "verdict: HOLD\n"
                "evidence: require source-tree check and focused test output\n"
                "next: run the smallest safe verification command\n"
                "horizon: medium\n"
                "draumric: task card review\n"
                "kor'aelin: implementation script route"
            ),
        }
    ],
    "route_plus_python_body": [
        {
            "instruction": "Route a request for cumulative_sum(values) and provide the Kor'aelin/Python implementation.",
            "answer": (
                "route: kor'aelin because this is a Python implementation task\n"
                "def cumulative_sum(values):\n"
                "    total = 0\n"
                "    result = []\n"
                "    for value in values:\n"
                "        total += value\n"
                "        result.append(total)\n"
                "    return result"
            ),
        }
    ],
    "code_chemistry_boundary": [
        {
            "instruction": "Verify the code symbol cache_flush_guard using only code-side terms.",
            "answer": (
                "cache_flush_guard is a code identifier.\n"
                "Next action: grep or search for its definition in the source tree.\n"
                "Run the unit test that exercises the symbol before changing behavior."
            ),
        }
    ],
    "dictionary_merge_body": [
        {
            "instruction": "Implement add_counts(left, right) in Kor'aelin/Python with get-default merging.",
            "answer": (
                "def add_counts(left, right):\n"
                "    result = {}\n"
                "    for source in (left, right):\n"
                "        for key, value in source.items():\n"
                "            result[key] = result.get(key, 0) + value\n"
                "    return result"
            ),
        }
    ],
    "rust_option_body": [
        {
            "instruction": "Implement first_even(xs) in Runethic/Rust returning Option<i64>.",
            "answer": (
                "fn first_even(xs: &[i64]) -> Option<i64> {\n"
                "    for x in xs {\n"
                "        if *x % 2 == 0 { return Some(*x); }\n"
                "    }\n"
                "    None\n"
                "}"
            ),
        }
    ],
    "generic_coding_contract_body": [
        {
            "instruction": "Write a compact code answer that includes the requested signature, guard, loop/body evidence, and return.",
            "answer": "Include the exact function signature, initialize state, show branch or loop body, and return the computed value.",
        }
    ],
}


def raw_failures(gate_report: dict[str, Any]) -> list[dict[str, Any]]:
    results = [item for item in gate_report.get("results", []) if isinstance(item, dict)]
    failures = []
    for item in results:
        if item.get("raw_ok") is True:
            continue
        prompt_id = str(item.get("id") or "")
        failures.append(
            {
                "prompt_id": prompt_id,
                "failure_kind": failure_kind(prompt_id),
                "raw_missing_required": [str(x) for x in item.get("raw_missing_required") or []],
                "raw_triggered_forbidden": [str(x) for x in item.get("raw_triggered_forbidden") or []],
                "raw_response_excerpt": str(item.get("raw_response") or "")[:500],
            }
        )
    return failures


def build_rows(
    gate_report: dict[str, Any],
    *,
    repeats: int = 8,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    failures = raw_failures(gate_report)
    rows: list[dict[str, Any]] = []
    for failure_index, failure in enumerate(failures):
        analogs = ANALOGS.get(failure["failure_kind"], ANALOGS["generic_coding_contract_body"])
        for analog_index, analog in enumerate(analogs):
            for repeat_index in range(max(1, repeats)):
                split = "eval" if (len(rows) + 1) % 5 == 0 else "train"
                payload = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Raw gate repair analog. Failure kind: {failure['failure_kind']}. "
                                f"Missing marker count: {len(failure['raw_missing_required'])}. "
                                f"Forbidden hit count: {len(failure['raw_triggered_forbidden'])}. "
                                f"Neighbor task: {analog['instruction']}"
                            ),
                        },
                        {"role": "assistant", "content": analog["answer"]},
                    ],
                    "metadata": {
                        "track": "coding_raw_failure_repair_v1",
                        "split": split,
                        "source_contract_id": gate_report.get("contract_id"),
                        "source_adapter": gate_report.get("adapter"),
                        "source_prompt_id": failure["prompt_id"],
                        "failure_kind": failure["failure_kind"],
                        "failure_index": failure_index,
                        "analog_index": analog_index,
                        "repeat_index": repeat_index,
                        "raw_missing_required": failure["raw_missing_required"],
                        "raw_triggered_forbidden": failure["raw_triggered_forbidden"],
                        "frozen_eval_boundary": "no held-out prompt text copied into messages",
                    },
                }
                payload["id"] = f"coding_raw_failure_repair_v1_{split}_{len(rows):04d}_{_sha(payload)[:16]}"
                rows.append(payload)
    train = [row for row in rows if row["metadata"]["split"] == "train"]
    eval_rows = [row for row in rows if row["metadata"]["split"] == "eval"]
    manifest = {
        "schema_version": "coding_raw_failure_repair_manifest_v1",
        "generated_utc": _utc_stamp(),
        "source_contract_id": gate_report.get("contract_id"),
        "source_adapter": gate_report.get("adapter"),
        "gate_pass_rate": gate_report.get("pass_rate"),
        "raw_pass_rate": gate_report.get("raw_pass_rate"),
        "raw_failures": len(failures),
        "repeats": max(1, repeats),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "failure_kinds": sorted({item["failure_kind"] for item in failures}),
        "source_prompt_ids": [item["prompt_id"] for item in failures],
        "frozen_eval_boundary": {
            "copies_prompt_text": False,
            "copies_raw_response": False,
            "uses_analog_neighbor_tasks": True,
        },
        "next_gate": "retrain or merge this shard, then report raw_pass_rate and shim_pass_rate separately",
    }
    return train, eval_rows, manifest


def write_outputs(gate_report: dict[str, Any], out_dir: Path = DEFAULT_OUT_DIR, *, repeats: int = 8) -> dict[str, Any]:
    train, eval_rows, manifest = build_rows(gate_report, repeats=repeats)
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME
    train_path.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in train) + ("\n" if train else ""), encoding="utf-8")
    eval_path.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in eval_rows) + ("\n" if eval_rows else ""), encoding="utf-8")
    manifest["train_path"] = str(train_path.relative_to(REPO_ROOT))
    manifest["eval_path"] = str(eval_path.relative_to(REPO_ROOT))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "raw_failures": manifest["raw_failures"],
        "repeats": manifest["repeats"],
        "failure_kinds": manifest["failure_kinds"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--gate-report", type=Path, help="Path to a gate report JSON or gate_report event JSON.")
    source.add_argument("--hf-job-id", help="Fetch logs for this HF job and extract the last gate_report event.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--repeats", type=int, default=8, help="Repeat each analog pattern to give the repair shard weight.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gate_report:
        gate_report = _load_json(args.gate_report)
    else:
        gate_report = _gate_report_from_hf_job(str(args.hf_job_id))
    result = write_outputs(gate_report, args.out_dir, repeats=args.repeats)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(f"wrote {result['train_records']} train / {result['eval_records']} eval repair rows")
        print(f"raw failures: {result['raw_failures']}")
        print(f"manifest: {result['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
