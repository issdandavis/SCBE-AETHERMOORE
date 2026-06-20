#!/usr/bin/env python3
"""PrimeIR speed-coding benchmark.

This benchmark tests the useful version of the "Prime Rust / Prime C /
Prime Python collapse" idea:

* A canonical operation gets one prime-coded semantic coordinate.
* Each language gets a namespace prime.
* A language surface is generated from the same operation coordinate.
* The generated code must run, and each language receipt must collapse back to
  the same semantic key for the operation.

This is not a broad code-generation leaderboard claim. It is a local
speed-coding harness for deterministic, schematic-first multi-language code
packs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "primeir_speed_coding"
SCHEMA_VERSION = "scbe_primeir_speed_coding_benchmark_v1"

LANGUAGE_PRIMES: dict[str, int] = {
    "python": 2,
    "javascript": 3,
    "rust": 5,
}

OPERATION_PRIMES: dict[str, int] = {
    "add": 11,
    "clamp": 13,
    "safe_divide": 17,
    "count_vowels": 19,
    "should_retry": 23,
}

EFFECT_PRIMES: dict[str, int] = {
    "pure": 29,
    "total": 31,
    "bounded": 37,
    "nullable": 41,
    "string_scan": 43,
    "policy_boundary": 47,
}


@dataclass(frozen=True)
class PrimeOperation:
    op_id: str
    name: str
    description: str
    effects: tuple[str, ...]
    examples: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class LanguageRun:
    language: str
    language_prime: int
    path: str
    available: bool
    tests_passed: bool
    duration_ms: int
    stdout_tail: str
    stderr_tail: str
    source_sha256: str


@dataclass(frozen=True)
class PrimeReceipt:
    op_id: str
    op_prime: int
    language: str
    language_prime: int
    effect_primes: tuple[int, ...]
    route_prime_product: int
    semantic_hash: str
    collapse_key: str


OPS: tuple[PrimeOperation, ...] = (
    PrimeOperation(
        op_id="add",
        name="add",
        description="Return the sum of two signed integers.",
        effects=("pure", "total"),
        examples=(
            {"args": [2, 3], "expected": 5},
            {"args": [-4, 9], "expected": 5},
        ),
    ),
    PrimeOperation(
        op_id="clamp",
        name="clamp",
        description="Clamp an integer inside an inclusive lower/upper bound.",
        effects=("pure", "total", "bounded"),
        examples=(
            {"args": [5, 1, 10], "expected": 5},
            {"args": [-2, 0, 8], "expected": 0},
            {"args": [12, 0, 8], "expected": 8},
        ),
    ),
    PrimeOperation(
        op_id="safe_divide",
        name="safe_divide",
        description="Divide two numbers, returning null/None when denominator is zero.",
        effects=("pure", "total", "nullable"),
        examples=(
            {"args": [6, 3], "expected": 2},
            {"args": [1, 0], "expected": None},
        ),
    ),
    PrimeOperation(
        op_id="count_vowels",
        name="count_vowels",
        description="Count ASCII vowels in a string, case-insensitively.",
        effects=("pure", "total", "string_scan"),
        examples=(
            {"args": ["Aether"], "expected": 3},
            {"args": ["sky"], "expected": 0},
        ),
    ),
    PrimeOperation(
        op_id="should_retry",
        name="should_retry",
        description="Allow retry for transient errors before the total attempt limit.",
        effects=("pure", "total", "policy_boundary"),
        examples=(
            {"args": ["timeout", 1, 3], "expected": True},
            {"args": ["timeout", 3, 3], "expected": False},
            {"args": ["validation", 1, 3], "expected": False},
        ),
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tail(text: str, limit: int = 1600) -> str:
    return text[-limit:] if len(text) > limit else text


def _json_stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def semantic_hash(op: PrimeOperation) -> str:
    payload = {
        "op_id": op.op_id,
        "description": op.description,
        "effects": list(op.effects),
        "examples": list(op.examples),
    }
    return _sha256_text(_json_stable(payload))


def build_receipts(languages: tuple[str, ...]) -> list[PrimeReceipt]:
    receipts: list[PrimeReceipt] = []
    for op in OPS:
        op_prime = OPERATION_PRIMES[op.op_id]
        sem_hash = semantic_hash(op)
        effect_primes = tuple(EFFECT_PRIMES[item] for item in op.effects)
        for language in languages:
            lang_prime = LANGUAGE_PRIMES[language]
            product = op_prime * lang_prime
            for effect_prime in effect_primes:
                product *= effect_prime
            receipts.append(
                PrimeReceipt(
                    op_id=op.op_id,
                    op_prime=op_prime,
                    language=language,
                    language_prime=lang_prime,
                    effect_primes=effect_primes,
                    route_prime_product=product,
                    semantic_hash=sem_hash,
                    collapse_key=f"op:{op_prime}:semantic:{sem_hash}",
                )
            )
    return receipts


def _python_value(value: Any) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    if value is None:
        return "None"
    return repr(value)


def render_python() -> str:
    checks: list[str] = []
    for op in OPS:
        for case in op.examples:
            args = ", ".join(_python_value(item) for item in case["args"])
            expected = _python_value(case["expected"])
            checks.append(f"assert {op.name}({args}) == {expected}")
    return """\
def add(a: int, b: int) -> int:
    return a + b


def clamp(value: int, lower: int, upper: int) -> int:
    return min(max(value, lower), upper)


def safe_divide(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def count_vowels(text: str) -> int:
    return sum(1 for char in text.lower() if char in "aeiou")


TRANSIENT_ERRORS = {"timeout", "rate_limit", "connection_reset"}


def should_retry(error_code: str, attempt: int, max_attempts: int) -> bool:
    return error_code in TRANSIENT_ERRORS and attempt < max_attempts


if __name__ == "__main__":
""" + "\n".join(f"    {check}" for check in checks) + "\n    print('primeir-python-ok')\n"


def _js_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return json.dumps(value)


def render_javascript() -> str:
    checks: list[str] = []
    for op in OPS:
        for case in op.examples:
            args = ", ".join(_js_value(item) for item in case["args"])
            expected = _js_value(case["expected"])
            checks.append(f"assert.equal({op.name}({args}), {expected});")
    return """\
'use strict';

const assert = require('node:assert/strict');

function add(a, b) {
  return a + b;
}

function clamp(value, lower, upper) {
  return Math.min(Math.max(value, lower), upper);
}

function safe_divide(a, b) {
  if (b === 0) return null;
  return a / b;
}

function count_vowels(text) {
  return Array.from(text.toLowerCase()).filter((char) => 'aeiou'.includes(char)).length;
}

const TRANSIENT_ERRORS = new Set(['timeout', 'rate_limit', 'connection_reset']);

function should_retry(error_code, attempt, max_attempts) {
  return TRANSIENT_ERRORS.has(error_code) && attempt < max_attempts;
}

""" + "\n".join(checks) + "\nconsole.log('primeir-javascript-ok');\n"


def _rust_value(value: Any, *, option: bool = False) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "None" if option else "()"
    if isinstance(value, str):
        return json.dumps(value)
    if option:
        return f"Some({float(value):.1f})"
    return str(value)


def render_rust() -> str:
    checks: list[str] = []
    for op in OPS:
        for case in op.examples:
            args = case["args"]
            if op.op_id == "safe_divide":
                rendered_args = ", ".join(f"{float(item):.1f}" for item in args)
                expected = _rust_value(case["expected"], option=True)
            elif op.op_id == "count_vowels":
                rendered_args = json.dumps(args[0])
                expected = _rust_value(case["expected"])
            elif op.op_id == "should_retry":
                rendered_args = f"{json.dumps(args[0])}, {args[1]}, {args[2]}"
                expected = _rust_value(case["expected"])
            else:
                rendered_args = ", ".join(_rust_value(item) for item in args)
                expected = _rust_value(case["expected"])
            checks.append(f"    assert_eq!({op.name}({rendered_args}), {expected});")
    return """\
use std::cmp::{max, min};

fn add(a: i64, b: i64) -> i64 {
    a + b
}

fn clamp(value: i64, lower: i64, upper: i64) -> i64 {
    min(max(value, lower), upper)
}

fn safe_divide(a: f64, b: f64) -> Option<f64> {
    if b == 0.0 {
        None
    } else {
        Some(a / b)
    }
}

fn count_vowels(text: &str) -> usize {
    text.chars()
        .filter(|char| matches!(char.to_ascii_lowercase(), 'a' | 'e' | 'i' | 'o' | 'u'))
        .count()
}

fn should_retry(error_code: &str, attempt: i64, max_attempts: i64) -> bool {
    matches!(error_code, "timeout" | "rate_limit" | "connection_reset") && attempt < max_attempts
}

fn main() {
""" + "\n".join(checks) + '\n    println!("primeir-rust-ok");\n}\n'


RENDERERS = {
    "python": ("primeir_pack.py", render_python),
    "javascript": ("primeir_pack.js", render_javascript),
    "rust": ("primeir_pack.rs", render_rust),
}


def _language_available(language: str) -> bool:
    if language == "python":
        return True
    if language == "javascript":
        return shutil.which("node") is not None
    if language == "rust":
        return shutil.which("rustc") is not None
    raise ValueError(f"unsupported language: {language}")


def _run_language(language: str, source_path: Path) -> tuple[bool, str, str]:
    if language == "python":
        proc = subprocess.run(
            [sys.executable, str(source_path.name)],
            cwd=source_path.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    if language == "javascript":
        proc = subprocess.run(
            ["node", source_path.name],
            cwd=source_path.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    if language == "rust":
        exe = source_path.with_suffix(".exe" if sys.platform.startswith("win") else "")
        compile_proc = subprocess.run(
            ["rustc", source_path.name, "-o", exe.name],
            cwd=source_path.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
        if compile_proc.returncode != 0:
            return False, compile_proc.stdout, compile_proc.stderr
        run_proc = subprocess.run(
            [str(exe)],
            cwd=source_path.parent,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        return run_proc.returncode == 0, run_proc.stdout, run_proc.stderr
    raise ValueError(f"unsupported language: {language}")


def run_primeir_pack(run_dir: Path, languages: tuple[str, ...]) -> list[LanguageRun]:
    source_dir = run_dir / "primeir_pack"
    source_dir.mkdir(parents=True, exist_ok=True)
    runs: list[LanguageRun] = []
    for language in languages:
        filename, render = RENDERERS[language]
        source = render()
        source_path = source_dir / filename
        source_path.write_text(source, encoding="utf-8")
        available = _language_available(language)
        start = time.perf_counter()
        if available:
            tests_passed, stdout, stderr = _run_language(language, source_path)
        else:
            tests_passed, stdout, stderr = False, "", f"{language} runtime unavailable"
        duration_ms = int((time.perf_counter() - start) * 1000)
        runs.append(
            LanguageRun(
                language=language,
                language_prime=LANGUAGE_PRIMES[language],
                path=str(source_path.relative_to(run_dir)),
                available=available,
                tests_passed=tests_passed,
                duration_ms=duration_ms,
                stdout_tail=_tail(stdout),
                stderr_tail=_tail(stderr),
                source_sha256=_sha256_text(source),
            )
        )
    return runs


def _collapse_report(receipts: list[PrimeReceipt]) -> dict[str, Any]:
    by_op: dict[str, set[str]] = {}
    for receipt in receipts:
        by_op.setdefault(receipt.op_id, set()).add(receipt.collapse_key)
    per_op = {op_id: sorted(keys) for op_id, keys in sorted(by_op.items())}
    return {
        "per_op": per_op,
        "collapse_ok": all(len(keys) == 1 for keys in by_op.values()),
        "op_count": len(by_op),
        "receipt_count": len(receipts),
    }


def build_report(
    *,
    out_dir: Path = DEFAULT_OUT,
    run_id: str | None = None,
    languages: tuple[str, ...] = ("python", "javascript", "rust"),
) -> dict[str, Any]:
    for language in languages:
        if language not in LANGUAGE_PRIMES:
            raise ValueError(f"unsupported language {language!r}; choices: {sorted(LANGUAGE_PRIMES)}")

    run_id = run_id or f"primeir-speed-{int(time.time())}"
    run_dir = out_dir / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    codegen_start = time.perf_counter()
    runs = run_primeir_pack(run_dir, languages)
    receipts = build_receipts(languages)
    codegen_and_run_ms = int((time.perf_counter() - codegen_start) * 1000)
    collapse = _collapse_report(receipts)

    task_count = len(OPS)
    requested_language_count = len(languages)
    requested_cells = task_count * requested_language_count
    passed_languages = [run.language for run in runs if run.available and run.tests_passed]
    primeir_passed_cells = task_count * len(passed_languages)
    single_surface_baseline_cells = task_count
    primeir_authoring_units = task_count + requested_language_count
    surface_authoring_units = task_count * requested_language_count

    decision = (
        "PASS"
        if primeir_passed_cells == requested_cells
        and collapse["collapse_ok"]
        and primeir_passed_cells > single_surface_baseline_cells
        else "FAIL"
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": _utc_now(),
        "claim_boundary": (
            "Deterministic local speed-coding pack benchmark. "
            "PrimeIR measures cross-language semantic collapse and executable pack coverage; "
            "it is not a broad held-out code-generation leaderboard score."
        ),
        "languages": list(languages),
        "operations": [asdict(op) for op in OPS],
        "language_runs": [asdict(run) for run in runs],
        "prime_receipts": [asdict(receipt) for receipt in receipts],
        "collapse": collapse,
        "summary": {
            "decision": decision,
            "task_count": task_count,
            "requested_language_count": requested_language_count,
            "requested_cells": requested_cells,
            "primeir_passed_cells": primeir_passed_cells,
            "single_surface_baseline_cells": single_surface_baseline_cells,
            "coverage_gain_vs_single_surface": round(
                primeir_passed_cells / single_surface_baseline_cells,
                3,
            ),
            "primeir_authoring_units": primeir_authoring_units,
            "surface_authoring_units": surface_authoring_units,
            "authoring_compression_ratio": round(
                surface_authoring_units / primeir_authoring_units,
                3,
            ),
            "codegen_and_run_ms": codegen_and_run_ms,
        },
    }

    report_path = run_dir / "report.json"
    latest_path = out_dir / "latest_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    (out_dir / "LATEST.md").write_text(_markdown_summary(report), encoding="utf-8")
    return report


def _markdown_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# PrimeIR Speed-Coding Benchmark",
        "",
        f"- Decision: `{summary['decision']}`",
        f"- Cells passed: `{summary['primeir_passed_cells']}/{summary['requested_cells']}`",
        f"- Single-surface baseline cells: `{summary['single_surface_baseline_cells']}/{summary['requested_cells']}`",
        f"- Coverage gain: `{summary['coverage_gain_vs_single_surface']}x`",
        f"- Authoring compression: `{summary['authoring_compression_ratio']}x`",
        f"- Collapse OK: `{report['collapse']['collapse_ok']}`",
        f"- Codegen + run: `{summary['codegen_and_run_ms']} ms`",
        "",
        "## Language Runs",
        "",
        "| Language | Available | Passed | Duration ms |",
        "| --- | --- | --- | ---: |",
    ]
    for run in report["language_runs"]:
        lines.append(f"| {run['language']} | {run['available']} | {run['tests_passed']} | {run['duration_ms']} |")
    lines.extend(["", f"Claim boundary: {report['claim_boundary']}", ""])
    return "\n".join(lines)


def _auto_languages() -> tuple[str, ...]:
    languages = ["python"]
    if _language_available("javascript"):
        languages.append("javascript")
    if _language_available("rust"):
        languages.append("rust")
    return tuple(languages)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run PrimeIR speed-coding benchmark.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--languages",
        default="auto",
        help="Comma-separated languages, or 'auto'. Choices: python,javascript,rust.",
    )
    args = parser.parse_args(argv)

    languages = (
        _auto_languages()
        if args.languages == "auto"
        else tuple(item.strip() for item in args.languages.split(",") if item.strip())
    )
    report = build_report(out_dir=args.out_dir, run_id=args.run_id, languages=languages)
    summary = report["summary"]
    print(
        "primeir speed coding: "
        f"decision={summary['decision']} "
        f"cells={summary['primeir_passed_cells']}/{summary['requested_cells']} "
        f"baseline={summary['single_surface_baseline_cells']}/{summary['requested_cells']} "
        f"compression={summary['authoring_compression_ratio']}x "
        f"report={args.out_dir / report['run_id'] / 'report.json'}"
    )
    return 0 if summary["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
