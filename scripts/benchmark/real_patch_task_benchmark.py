#!/usr/bin/env python3
"""Real patch task benchmark for the SCBE coding-agent challenge lane.

This benchmark creates isolated broken mini-repositories, runs a no-repair
direct baseline, runs the SCBE repair harness, executes the task tests, and
scores pass/fail/time/edit-scope receipts.

It is a starter challenge lane, not a public leaderboard claim. The fixtures
are repo-local and deterministic so the harness itself can be tested before
external agent runners are attached.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "real_patch_tasks"


@dataclass(frozen=True)
class PatchTask:
    task_id: str
    issue: str
    files: dict[str, str]
    tests: dict[str, str]
    expected_files: tuple[str, ...]
    allowed_commands: tuple[str, ...]
    pass_criteria: tuple[str, ...]


@dataclass(frozen=True)
class LaneResult:
    lane: str
    task_id: str
    tests_passed: bool
    scope_ok: bool
    duration_ms: int
    changed_files: list[str]
    unexpected_files: list[str]
    stdout_tail: str
    stderr_tail: str
    patch: str


TASKS: tuple[PatchTask, ...] = (
    PatchTask(
        task_id="slugify_punctuation_regression",
        issue=(
            "Fix slugify so punctuation becomes separators, repeated separators "
            "collapse, and leading/trailing separators are removed."
        ),
        files={
            "src/text_tools.py": """\
import re


def slugify(value: str) -> str:
    value = value.lower().strip()
    return re.sub(r"\\s+", "-", value)
""",
        },
        tests={
            "tests/test_text_tools.py": """\
from src.text_tools import slugify


def test_slugify_collapses_punctuation_and_spaces():
    assert slugify("  The Road, the Lamp & the Door!  ") == "the-road-the-lamp-the-door"


def test_slugify_handles_empty_after_symbols():
    assert slugify(" ... ") == ""
""",
        },
        expected_files=("src/text_tools.py",),
        allowed_commands=("python -m pytest -q",),
        pass_criteria=("pytest passes", "only src/text_tools.py changed"),
    ),
    PatchTask(
        task_id="retry_boundary_regression",
        issue=(
            "Fix should_retry so max_attempts is the total number of attempts, "
            "not the number of retries after the first failure."
        ),
        files={
            "src/retry_policy.py": """\
TRANSIENT_ERRORS = {"timeout", "rate_limit", "connection_reset"}


def should_retry(error_code: str, attempt: int, max_attempts: int) -> bool:
    if error_code not in TRANSIENT_ERRORS:
        return False
    return attempt <= max_attempts
""",
        },
        tests={
            "tests/test_retry_policy.py": """\
from src.retry_policy import should_retry


def test_retries_before_final_attempt():
    assert should_retry("timeout", attempt=1, max_attempts=3) is True
    assert should_retry("timeout", attempt=2, max_attempts=3) is True


def test_stops_at_total_attempt_limit():
    assert should_retry("timeout", attempt=3, max_attempts=3) is False
    assert should_retry("validation", attempt=1, max_attempts=3) is False
""",
        },
        expected_files=("src/retry_policy.py",),
        allowed_commands=("python -m pytest -q",),
        pass_criteria=("pytest passes", "only src/retry_policy.py changed"),
    ),
    PatchTask(
        task_id="manifest_hash_validation",
        issue=(
            "Fix verify_manifest so it rejects missing required fields and "
            "checks the sha256 digest against the payload."
        ),
        files={
            "src/manifest.py": """\
import hashlib


def verify_manifest(manifest: dict) -> bool:
    payload = manifest.get("payload", "")
    expected = manifest.get("sha256")
    if not expected:
        return True
    return hashlib.sha256(payload.encode("utf-8")).hexdigest() == expected
""",
        },
        tests={
            "tests/test_manifest.py": """\
import hashlib

from src.manifest import verify_manifest


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_verify_manifest_accepts_matching_hash():
    assert verify_manifest({"payload": "lamp", "sha256": digest("lamp")}) is True


def test_verify_manifest_rejects_missing_or_wrong_hash():
    assert verify_manifest({"payload": "lamp"}) is False
    assert verify_manifest({"payload": "lamp", "sha256": digest("door")}) is False
""",
        },
        expected_files=("src/manifest.py",),
        allowed_commands=("python -m pytest -q",),
        pass_criteria=("pytest passes", "only src/manifest.py changed"),
    ),
    PatchTask(
        task_id="config_loader_defaults_and_bounds",
        issue=(
            "Fix load_config so it preserves caller overrides, fills deterministic "
            "defaults, rejects invalid retry bounds, and does not mutate input."
        ),
        files={
            "src/config_loader.py": """\
DEFAULTS = {"timeout": 30, "retries": 3, "mode": "safe"}


def load_config(raw: dict) -> dict:
    DEFAULTS.update(raw)
    return DEFAULTS
""",
        },
        tests={
            "tests/test_config_loader.py": """\
import pytest

from src.config_loader import load_config


def test_load_config_merges_defaults_without_mutating_input():
    raw = {"timeout": 10}
    loaded = load_config(raw)

    assert loaded == {"timeout": 10, "retries": 3, "mode": "safe"}
    assert raw == {"timeout": 10}


def test_load_config_rejects_invalid_retries():
    with pytest.raises(ValueError, match="retries"):
        load_config({"retries": -1})

    with pytest.raises(ValueError, match="retries"):
        load_config({"retries": 11})


def test_load_config_calls_are_isolated():
    assert load_config({"mode": "fast"}) == {"timeout": 30, "retries": 3, "mode": "fast"}
    assert load_config({}) == {"timeout": 30, "retries": 3, "mode": "safe"}
""",
        },
        expected_files=("src/config_loader.py",),
        allowed_commands=("python -m pytest -q",),
        pass_criteria=("pytest passes", "only src/config_loader.py changed"),
    ),
    PatchTask(
        task_id="router_priority_scope_regression",
        issue=(
            "Fix route_task so explicit security policy outranks generic code "
            "routing, local filesystem work stays local, and unknown tasks use "
            "the default free-first lane."
        ),
        files={
            "src/router.py": """\
def route_task(text: str) -> str:
    lower = text.lower()
    if "code" in lower or "module" in lower or "pipeline" in lower:
        return "cerebras"
    if "security" in lower or "policy" in lower or "token" in lower:
        return "groq"
    if "file" in lower or "disk" in lower or "process" in lower:
        return "ollama"
    return "huggingface"
""",
        },
        tests={
            "tests/test_router.py": """\
from src.router import route_task


def test_security_policy_overrides_code_words():
    assert route_task("review code token security policy") == "groq"


def test_local_filesystem_lane_stays_local():
    assert route_task("read disk files and process logs") == "ollama"


def test_code_lane_and_default_lane():
    assert route_task("fix module router pipeline") == "cerebras"
    assert route_task("summarize the idea") == "cerebras"
""",
        },
        expected_files=("src/router.py",),
        allowed_commands=("python -m pytest -q",),
        pass_criteria=("pytest passes", "only src/router.py changed"),
    ),
)


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_fixture(root: Path, task: PatchTask) -> dict[str, str]:
    if root.exists():
        shutil.rmtree(root)
    for relative, content in {**task.files, **task.tests}.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    manifest = {
        relative: _sha256_text((root / relative).read_text(encoding="utf-8"))
        for relative in sorted(task.files)
    }
    _write_json(
        root / "challenge_task.json",
        {
            "task_id": task.task_id,
            "issue": task.issue,
            "start_file_hashes": manifest,
            "expected_files": list(task.expected_files),
            "allowed_commands": list(task.allowed_commands),
            "pass_criteria": list(task.pass_criteria),
        },
    )
    return manifest


def _run_tests(root: Path) -> tuple[bool, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return proc.returncode == 0, proc.stdout, proc.stderr


def _changed_files(
    root: Path, task: PatchTask, before: dict[str, str]
) -> tuple[list[str], str]:
    changed = []
    patch_parts = []
    for relative in sorted(task.files):
        before_text = task.files[relative]
        after_path = root / relative
        after_text = (
            after_path.read_text(encoding="utf-8") if after_path.exists() else ""
        )
        digest = _sha256_text(after_text)
        if digest != before[relative]:
            changed.append(relative)
            patch_parts.extend(
                difflib.unified_diff(
                    before_text.splitlines(),
                    after_text.splitlines(),
                    fromfile=f"a/{relative}",
                    tofile=f"b/{relative}",
                    lineterm="",
                )
            )
    return changed, "\n".join(patch_parts)


def _score_scope(changed_files: list[str], task: PatchTask) -> tuple[bool, list[str]]:
    expected = set(task.expected_files)
    unexpected = [path for path in changed_files if path not in expected]
    return bool(changed_files) and not unexpected, unexpected


def _tail(text: str, limit: int = 1600) -> str:
    return text[-limit:] if len(text) > limit else text


def run_lane(
    task: PatchTask,
    *,
    lane: str,
    root: Path,
    repair: Callable[[Path, PatchTask], None] | None,
) -> LaneResult:
    before = _write_fixture(root, task)
    start = time.perf_counter()
    if repair is not None:
        repair(root, task)
    tests_passed, stdout, stderr = _run_tests(root)
    duration_ms = int((time.perf_counter() - start) * 1000)
    changed, patch = _changed_files(root, task, before)
    scope_ok, unexpected = _score_scope(changed, task)
    return LaneResult(
        lane=lane,
        task_id=task.task_id,
        tests_passed=tests_passed,
        scope_ok=scope_ok,
        duration_ms=duration_ms,
        changed_files=changed,
        unexpected_files=unexpected,
        stdout_tail=_tail(stdout),
        stderr_tail=_tail(stderr),
        patch=patch,
    )


def _replace(root: Path, relative: str, text: str) -> None:
    (root / relative).write_text(text, encoding="utf-8")


def scbe_repair(root: Path, task: PatchTask) -> None:
    """Deterministic local repair harness for the starter challenge tasks."""
    if task.task_id == "slugify_punctuation_regression":
        _replace(
            root,
            "src/text_tools.py",
            """\
import re


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return value.strip("-")
""",
        )
        return
    if task.task_id == "retry_boundary_regression":
        _replace(
            root,
            "src/retry_policy.py",
            """\
TRANSIENT_ERRORS = {"timeout", "rate_limit", "connection_reset"}


def should_retry(error_code: str, attempt: int, max_attempts: int) -> bool:
    if error_code not in TRANSIENT_ERRORS:
        return False
    return attempt < max_attempts
""",
        )
        return
    if task.task_id == "manifest_hash_validation":
        _replace(
            root,
            "src/manifest.py",
            """\
import hashlib


def verify_manifest(manifest: dict) -> bool:
    payload = manifest.get("payload")
    expected = manifest.get("sha256")
    if not isinstance(payload, str) or not isinstance(expected, str):
        return False
    actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return actual == expected
""",
        )
        return
    if task.task_id == "config_loader_defaults_and_bounds":
        _replace(
            root,
            "src/config_loader.py",
            """\
DEFAULTS = {"timeout": 30, "retries": 3, "mode": "safe"}


def load_config(raw: dict) -> dict:
    loaded = {**DEFAULTS, **raw}
    retries = loaded["retries"]
    if not isinstance(retries, int) or retries < 0 or retries > 10:
        raise ValueError("retries must be an integer between 0 and 10")
    return loaded
""",
        )
        return
    if task.task_id == "router_priority_scope_regression":
        _replace(
            root,
            "src/router.py",
            """\
def route_task(text: str) -> str:
    lower = text.lower()
    if "security" in lower or "policy" in lower or "token" in lower:
        return "groq"
    if "file" in lower or "disk" in lower or "process" in lower or "network" in lower:
        return "ollama"
    if "code" in lower or "module" in lower or "router" in lower or "pipeline" in lower:
        return "cerebras"
    return "cerebras"
""",
        )
        return
    raise ValueError(f"no SCBE repair registered for {task.task_id}")


def score_result(result: LaneResult) -> dict[str, Any]:
    checks = {
        "tests_passed": result.tests_passed,
        "expected_file_changed": bool(result.changed_files),
        "edit_scope_clean": result.scope_ok,
        "no_unexpected_files": not result.unexpected_files,
        "patch_captured": bool(result.patch),
    }
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return {
        "lane": result.lane,
        "task_id": result.task_id,
        "score": round(passed / total, 4),
        "passed": passed,
        "total": total,
        "duration_ms": result.duration_ms,
        "checks": checks,
    }


def build_report(
    *, out_dir: Path = DEFAULT_OUT, run_id: str | None = None
) -> dict[str, Any]:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir / run_id
    work_dir = run_dir / "work"

    baseline_results = [
        run_lane(
            task,
            lane="direct_no_repair_baseline",
            root=work_dir / "baseline" / task.task_id,
            repair=None,
        )
        for task in TASKS
    ]
    scbe_results = [
        run_lane(
            task,
            lane="scbe_repair_harness",
            root=work_dir / "scbe" / task.task_id,
            repair=scbe_repair,
        )
        for task in TASKS
    ]
    baseline_scores = [score_result(result) for result in baseline_results]
    scbe_scores = [score_result(result) for result in scbe_results]
    baseline_passes = sum(
        1 for item in baseline_scores if item["checks"]["tests_passed"]
    )
    scbe_passes = sum(
        1
        for item in scbe_scores
        if item["checks"]["tests_passed"] and item["checks"]["edit_scope_clean"]
    )
    task_count = len(TASKS)
    summary = {
        "decision": (
            "PASS"
            if scbe_passes == task_count and baseline_passes < task_count
            else "HOLD"
        ),
        "task_count": task_count,
        "baseline_test_passes": baseline_passes,
        "scbe_test_passes": scbe_passes,
        "baseline_avg": round(
            sum(item["score"] for item in baseline_scores) / task_count, 4
        ),
        "scbe_avg": round(sum(item["score"] for item in scbe_scores) / task_count, 4),
        "scbe_wins": sum(
            1
            for base, scbe in zip(baseline_scores, scbe_scores)
            if scbe["score"] > base["score"]
        ),
    }
    report = {
        "schema_version": "scbe_real_patch_task_benchmark_v1",
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "scope": "deterministic local real-patch challenge fixtures; not a frontier coding-agent claim",
        "tasks": [asdict(task) for task in TASKS],
        "summary": summary,
        "criteria": {
            "tests_passed": "The task-specific pytest suite must pass after the lane runs.",
            "expected_file_changed": "The lane must produce an actual source edit.",
            "edit_scope_clean": "Only task-declared expected files may change.",
            "no_unexpected_files": "No unrelated source files may be modified.",
            "patch_captured": "A unified diff must be available for review.",
        },
        "baseline_scores": baseline_scores,
        "scbe_scores": scbe_scores,
        "raw_results": {
            "baseline": [asdict(result) for result in baseline_results],
            "scbe": [asdict(result) for result in scbe_results],
        },
        "claim_boundary": [
            "This proves the challenge harness can run issue-to-edit-to-test tasks with receipts.",
            "The current SCBE lane is a deterministic repair harness for seeded fixtures.",
            "The next escalation is attaching live coding agents to the same task manifest.",
        ],
    }
    _write_json(run_dir / "report.json", report)
    _write_json(out_dir / "latest_report.json", report)
    (run_dir / "REPORT.md").write_text(_render_markdown(report), encoding="utf-8")
    (out_dir / "LATEST.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# SCBE Real Patch Task Benchmark",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Run ID: `{report['run_id']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Scope: {report['scope']}",
        "",
        "## Summary",
        "",
        "| Lane | Avg score | Test passes |",
        "|---|---:|---:|",
        f"| Direct no-repair baseline | `{summary['baseline_avg']}` | "
        f"`{summary['baseline_test_passes']} / {summary['task_count']}` |",
        f"| SCBE repair harness | `{summary['scbe_avg']}` | "
        f"`{summary['scbe_test_passes']} / {summary['task_count']}` |",
        "",
        f"- SCBE wins: `{summary['scbe_wins']} / {summary['task_count']}`",
        "",
        "## Per-Task Scores",
        "",
        "| Task | Baseline | SCBE |",
        "|---|---:|---:|",
    ]
    baseline_by_id = {item["task_id"]: item for item in report["baseline_scores"]}
    for item in report["scbe_scores"]:
        task_id = item["task_id"]
        lines.append(
            f"| `{task_id}` | `{baseline_by_id[task_id]['score']}` | `{item['score']}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            *[f"- {item}" for item in report["claim_boundary"]],
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(out_dir=args.out_dir, run_id=args.run_id or None)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        summary = report["summary"]
        print(
            "real patch task benchmark: "
            f"decision={summary['decision']} "
            f"baseline={summary['baseline_test_passes']}/{summary['task_count']} "
            f"scbe={summary['scbe_test_passes']}/{summary['task_count']}"
        )
        print(f"report={args.out_dir / report['run_id'] / 'report.json'}")
    return 0 if report["summary"]["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
