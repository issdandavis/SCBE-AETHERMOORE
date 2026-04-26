#!/usr/bin/env python3
"""Benchmark the SCBE full coding-system dataset lane.

This is not a public leaderboard runner. It is a local readiness gate that
checks whether the v8 coding-system lane has the minimum properties expected by
standard code-eval practice:

- HumanEval/MBPP style: executable Python functions pass deterministic tests.
- EvalPlus style: edge cases are included for generated primitive tasks.
- SWE-bench/Terminal-Bench style: agent records preserve task evidence,
  reproducible hashes, language/tool lanes, and execution contracts.
- Toolkit comparison: raw code, binary transport, atomic rows, and the full
  SCBE lane are scored separately so we can see what the system adds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAIN = REPO_ROOT / "training-data" / "sft" / "coding_system_full_v1_train.sft.jsonl"
DEFAULT_HOLDOUT = REPO_ROOT / "training-data" / "sft" / "coding_system_full_v1_holdout.sft.jsonl"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "coding_system_full_v1"

REQUIRED_SINGLE_FIELDS = {
    "coding_primary",
    "music_theory",
    "atomic_tokenizer",
    "binary_transport",
    "code_lane_contract",
    "workflow_composition",
    "boundary",
}

EXPECTED_PRIMARIES = {"KO", "AV", "RU", "CA", "UM", "DR"}
EXPECTED_LANGUAGES = {"python", "typescript", "rust", "c", "julia", "haskell"}
EXPECTED_MODES = {"Ionian", "Lydian", "Dorian", "Mixolydian", "Aeolian", "Phrygian"}


@dataclass(frozen=True)
class PythonTaskResult:
    concept_id: str
    passed: bool
    error: str = ""


@dataclass(frozen=True)
class ToolkitScore:
    toolkit: str
    score: float
    passed_checks: int
    total_checks: int
    notes: str


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assistant_payload(row: dict[str, Any]) -> dict[str, Any]:
    messages = row.get("messages") or []
    if not messages:
        raise ValueError("record has no messages")
    payload = json.loads(messages[-1]["content"])
    if not isinstance(payload, dict):
        raise ValueError("assistant payload is not an object")
    return payload


def _single_payloads(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads = [_assistant_payload(row) for row in rows]
    return [item for item in payloads if item.get("schema_version") == "scbe_full_coding_system_answer_v1"]


def _roundabout_payloads(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads = [_assistant_payload(row) for row in rows]
    return [item for item in payloads if item.get("schema_version") == "scbe_full_coding_system_roundabout_v1"]


def _safe_exec_python(source: str, assertions: list[str]) -> tuple[bool, str]:
    scope: dict[str, Any] = {"__builtins__": __builtins__}
    try:
        exec(source, scope, scope)
        for assertion in assertions:
            exec(assertion, scope, scope)
    except Exception as exc:  # pragma: no cover - value is reported
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def _python_assertions(concept_id: str) -> list[str]:
    return {
        "add": ["assert add(2, 3) == 5", "assert add(-1, 1) == 0"],
        "guard_divide": ["assert safe_divide(6, 3) == 2", "assert safe_divide(1, 0) is None"],
        "map_square": ["assert map_square([2, 3]) == [4, 9]", "assert map_square([]) == []"],
        "retry_packet": [
            "assert retry_packet(lambda payload: payload == 'ok', 'ok', 2) is True",
            "assert retry_packet(lambda payload: False, 'x', 2) is False",
        ],
        "budget_fallback": [
            "assert route_or_hold(5, 3) == 'hold'",
            "assert route_or_hold(2, 3) == 'launch'",
        ],
        "hash_route": ["assert len(hash_route('x')) == 64", "assert hash_route('x') == hash_route('x')"],
        "parse_flag": [
            "assert parse_flag(['--json'], '--json') is True",
            "assert parse_flag(['--text'], '--json') is False",
        ],
        "test_assert": ["test_add()"],
    }.get(concept_id, [])


def run_python_code_tasks(single_payloads: list[dict[str, Any]]) -> list[PythonTaskResult]:
    results: list[PythonTaskResult] = []
    ko_payloads = [
        payload
        for payload in single_payloads
        if payload.get("coding_primary", {}).get("tongue") == "KO"
        and payload.get("coding_primary", {}).get("language") == "python"
    ]
    for payload in sorted(ko_payloads, key=lambda item: item["concept"]["concept_id"]):
        concept_id = payload["concept"]["concept_id"]
        assertions = _python_assertions(concept_id)
        if not assertions:
            results.append(PythonTaskResult(concept_id=concept_id, passed=False, error="no assertions"))
            continue
        ok, error = _safe_exec_python(payload["coding_primary"]["sample_code"], assertions)
        results.append(PythonTaskResult(concept_id=concept_id, passed=ok, error=error))
    return results


def validate_lane_integrity(single_payloads: list[dict[str, Any]], roundabouts: list[dict[str, Any]]) -> dict[str, Any]:
    primaries = {payload.get("coding_primary", {}).get("tongue") for payload in single_payloads}
    languages = {payload.get("coding_primary", {}).get("language") for payload in single_payloads}
    modes = {payload.get("music_theory", {}).get("mode") for payload in single_payloads}
    missing_fields = [
        {
            "concept_id": payload.get("concept", {}).get("concept_id"),
            "primary": payload.get("coding_primary", {}).get("tongue"),
            "missing": sorted(REQUIRED_SINGLE_FIELDS - set(payload)),
        }
        for payload in single_payloads
        if not REQUIRED_SINGLE_FIELDS <= set(payload)
    ]
    hash_failures = []
    hex_failures = []
    for payload in single_payloads:
        source = payload["coding_primary"]["sample_code"]
        expected_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        binary = payload["binary_transport"]
        if binary.get("source_sha256") != expected_sha:
            hash_failures.append(payload["concept"]["concept_id"])
        first_16 = [f"{byte:02X}" for byte in source.encode("utf-8")[:16]]
        if binary.get("first_16_hex") != first_16:
            hex_failures.append(payload["concept"]["concept_id"])

    boundary_failures = [
        payload["concept"]["concept_id"]
        for payload in single_payloads
        if "Semantic meaning" not in payload["boundary"].get("semantic_vs_transport", "")
        or "Material chemistry" not in payload["boundary"].get("chemistry_scope", "")
    ]
    return {
        "single_records": len(single_payloads),
        "roundabout_records": len(roundabouts),
        "primary_coverage_ok": primaries == EXPECTED_PRIMARIES,
        "language_coverage_ok": languages == EXPECTED_LANGUAGES,
        "music_mode_coverage_ok": modes == EXPECTED_MODES,
        "missing_fields": missing_fields,
        "hash_failures": hash_failures,
        "hex_failures": hex_failures,
        "boundary_failures": boundary_failures,
        "roundabout_lane_count_ok": all(len(item.get("lanes", [])) == 6 for item in roundabouts),
    }


def toolkit_scores(
    *,
    python_results: list[PythonTaskResult],
    integrity: dict[str, Any],
    single_payloads: list[dict[str, Any]],
) -> list[ToolkitScore]:
    executable_pass = sum(1 for item in python_results if item.passed)
    executable_total = len(python_results)
    binary_ok = len(integrity["hash_failures"]) == 0 and len(integrity["hex_failures"]) == 0
    atomic_ok = all(payload.get("atomic_tokenizer", {}).get("atomic_rows") for payload in single_payloads)
    full_lane_checks = [
        integrity["primary_coverage_ok"],
        integrity["language_coverage_ok"],
        integrity["music_mode_coverage_ok"],
        not integrity["missing_fields"],
        binary_ok,
        atomic_ok,
        not integrity["boundary_failures"],
        integrity["roundabout_lane_count_ok"],
        executable_pass == executable_total,
    ]
    raw_checks = [executable_pass == executable_total]
    binary_checks = [binary_ok, executable_pass == executable_total]
    atomic_checks = [atomic_ok, binary_ok, executable_pass == executable_total]
    music_checks = [integrity["music_mode_coverage_ok"], integrity["roundabout_lane_count_ok"]]
    rows = [
        ToolkitScore(
            "raw_code_only",
            round(sum(raw_checks) / len(raw_checks), 3),
            sum(raw_checks),
            len(raw_checks),
            "Executable Python only; no cross-primary, atomic, or transport evidence.",
        ),
        ToolkitScore(
            "binary_transport_only",
            round(sum(binary_checks) / len(binary_checks), 3),
            sum(binary_checks),
            len(binary_checks),
            "Checks byte/hex/hash transport plus executable Python.",
        ),
        ToolkitScore(
            "atomic_tokenizer_plus_binary",
            round(sum(atomic_checks) / len(atomic_checks), 3),
            sum(atomic_checks),
            len(atomic_checks),
            "Checks atomic rows, binary integrity, and executable Python.",
        ),
        ToolkitScore(
            "music_harmony_primary_map",
            round(sum(music_checks) / len(music_checks), 3),
            sum(music_checks),
            len(music_checks),
            "Checks six modes and cross-primary roundabout lane coverage.",
        ),
        ToolkitScore(
            "scbe_full_coding_system_v1",
            round(sum(full_lane_checks) / len(full_lane_checks), 3),
            sum(full_lane_checks),
            len(full_lane_checks),
            "Checks all aligned lanes plus executable Python readiness.",
        ),
    ]
    return rows


def build_report(train: Path, holdout: Path) -> dict[str, Any]:
    rows = _read_jsonl(train) + _read_jsonl(holdout)
    single = _single_payloads(rows)
    roundabouts = _roundabout_payloads(rows)
    python_results = run_python_code_tasks(single)
    integrity = validate_lane_integrity(single, roundabouts)
    scores = toolkit_scores(python_results=python_results, integrity=integrity, single_payloads=single)
    executable_total = len(python_results)
    executable_pass = sum(1 for item in python_results if item.passed)
    return {
        "schema_version": "scbe_coding_system_industry_benchmark_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {"train": str(train), "holdout": str(holdout)},
        "standard_mapping": {
            "HumanEval_MBPP_style": "Executable function tasks with deterministic assertions.",
            "EvalPlus_style": "Edge-case assertions for empty inputs, zero division, retries, and hash determinism.",
            "SWE_bench_Terminal_Bench_style": "Reproducible evidence lanes, hashes, task contracts, and holdout split. This is readiness, not a public SWE-bench score.",
        },
        "summary": {
            "records_total": len(rows),
            "single_primary_records": len(single),
            "roundabout_records": len(roundabouts),
            "python_executable_pass_rate": round(executable_pass / executable_total, 3) if executable_total else 0.0,
            "python_executable_passed": executable_pass,
            "python_executable_total": executable_total,
            "full_lane_pass": next(item for item in scores if item.toolkit == "scbe_full_coding_system_v1").score == 1.0,
        },
        "python_task_results": [asdict(item) for item in python_results],
        "lane_integrity": integrity,
        "toolkit_comparison": [asdict(item) for item in scores],
        "decision": (
            "PASS"
            if executable_pass == executable_total
            and next(item for item in scores if item.toolkit == "scbe_full_coding_system_v1").score == 1.0
            else "REVIEW"
        ),
        "boundary": "This validates the dataset/system lane. It does not claim public HumanEval, MBPP, or SWE-bench leaderboard performance for the trained adapter.",
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE Full Coding System Industry-Style Benchmark",
        "",
        f"- Decision: `{report['decision']}`",
        f"- Records: `{report['summary']['records_total']}`",
        f"- Python executable pass rate: `{report['summary']['python_executable_pass_rate']}`",
        f"- Full lane pass: `{report['summary']['full_lane_pass']}`",
        "",
        "## Toolkit Comparison",
        "",
        "| Toolkit | Score | Checks | Notes |",
        "|---|---:|---:|---|",
    ]
    for row in report["toolkit_comparison"]:
        lines.append(f"| `{row['toolkit']}` | `{row['score']}` | `{row['passed_checks']}/{row['total_checks']}` | {row['notes']} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["boundary"],
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark SCBE full coding-system dataset lane.")
    parser.add_argument("--train", default=str(DEFAULT_TRAIN))
    parser.add_argument("--holdout", default=str(DEFAULT_HOLDOUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    report = build_report(Path(args.train), Path(args.holdout))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"coding-system-industry-benchmark-{stamp}.json"
    md_path = out_dir / f"coding-system-industry-benchmark-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"decision": report["decision"], "summary": report["summary"], "json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
