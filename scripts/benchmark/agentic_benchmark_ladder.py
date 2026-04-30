#!/usr/bin/env python3
"""SCBE agentic benchmark ladder — multi-level evaluation, not a single score.

Maps conceptual ladder levels to runnable harness steps. Levels 0–1, **6**, and **7** are
implemented in-repo; levels 2–5 record deferred targets (SWE-bench, Terminal-Bench,
GAIA, governance) until adapters are wired.

Level **6** is CLI / GeoSeal *surface readiness* (not model IQ): focused pytest on
`cli_competitive_benchmark` + npm `geoseal` bin smoke. Full scoring refresh:
`npm run benchmark:cli`.

Level **7** is SCBE's deployable coding-agent surface readiness: the
`scripts/agents/scbe_code.py` no-GPU paths plus sandboxed apply tests.

See benchmarks/scbe_agentic_v1/ for the repo-native task format (includes
`representation_consistency`: pytest for the representation kaleidoscope, not
artifact regeneration).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = REPO_ROOT / "benchmarks" / "scbe_agentic_v1" / "tasks"
SCHEMA_VERSION = "scbe_agentic_benchmark_ladder_v1"

# Heuristic secret-like patterns in captured command output (count only; not exhaustive).
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-(?:live|test|ant|proj)-[A-Za-z0-9]{10,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_max_level(query: str) -> int:
    """Accept bare integer, max_level=N, or JSON {\"max_level\": N}."""
    raw = (query or "").strip()
    if not raw:
        return 1
    if raw.isdigit():
        return max(0, min(7, int(raw)))
    if "max_level" in raw:
        m = re.search(r"max_level\s*=\s*(\d+)", raw)
        if m:
            return max(0, min(7, int(m.group(1))))
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "max_level" in obj:
                return max(0, min(7, int(obj["max_level"])))
        except json.JSONDecodeError:
            pass
    return 1


def _secret_leak_count(text: str) -> int:
    if not text:
        return 0
    n = 0
    for pat in _SECRET_PATTERNS:
        n += len(pat.findall(text))
    return n


@dataclass
class MetricRecord:
    task_success: bool
    test_pass: bool
    time_to_success_sec: float
    commands_used: int
    human_interventions: int
    cost_usd: float
    secret_leak_count: int
    rollback_safety: str
    evidence_quality: str


def _default_metrics(
    ok: bool, elapsed: float, commands_used: int, text: str, evidence: str = "log"
) -> dict[str, Any]:
    return asdict(
        MetricRecord(
            task_success=ok,
            test_pass=ok,
            time_to_success_sec=round(elapsed, 3),
            commands_used=commands_used,
            human_interventions=0,
            cost_usd=0.0,
            secret_leak_count=_secret_leak_count(text),
            rollback_safety="ok" if ok else "warn",
            evidence_quality=evidence,
        )
    )


def _env_with_repo_pythonpath() -> dict[str, str]:
    """Ensure repo root is on PYTHONPATH for pytest imports (matches CI)."""
    env = dict(os.environ)
    root = str(REPO_ROOT)
    prev = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = root if not prev else f"{root}{os.pathsep}{prev}"
    return env


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    timeout: int,
    *,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str, float]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=env,
    )
    elapsed = time.perf_counter() - t0
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def run_level0_smoke() -> dict[str, Any]:
    """Level 0: existing coding + system_build smokes."""
    out: dict[str, Any] = {
        "level": 0,
        "label": "local_smoke",
        "ok": True,
        "subtasks": [],
    }
    for name in ("coding", "system_build"):
        cmd = [sys.executable, "scripts/system/agent_router_smoke.py", name]
        code, so, se, elapsed = _run_cmd(cmd, REPO_ROOT, timeout=240)
        text = (so or "") + (se or "")
        ok = code == 0
        if not ok:
            out["ok"] = False
        payload_txt = (so or "")[-8000:]
        try:
            parsed = json.loads(so) if so.strip() else {}
        except json.JSONDecodeError:
            parsed = {}
        out["subtasks"].append(
            {
                "name": name,
                "ok": ok,
                "metrics": _default_metrics(ok, elapsed, 1, text),
                "summary": (
                    parsed if isinstance(parsed, dict) else {"raw": payload_txt[:500]}
                ),
            }
        )
    return out


def _load_task_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_tasks() -> list[Path]:
    if not TASKS_DIR.is_dir():
        return []
    return sorted(
        p / "task.json"
        for p in TASKS_DIR.iterdir()
        if p.is_dir() and (p / "task.json").is_file()
    )


def run_level1_tasks(max_level: int) -> dict[str, Any]:
    """Level 1: repo-native tasks under benchmarks/scbe_agentic_v1/tasks/."""
    result: dict[str, Any] = {
        "level": 1,
        "label": "repo_native",
        "ok": True,
        "tasks": [],
    }
    if max_level < 1:
        result["skipped"] = True
        return result

    paths = discover_tasks()
    for task_json in paths:
        spec = _load_task_json(task_json)
        level = int(spec.get("level", 1))
        if level > max_level:
            continue
        verify = spec.get("verify") or {}
        cmd = verify.get("command")
        if not cmd or not isinstance(cmd, list):
            result["ok"] = False
            result["tasks"].append(
                {
                    "id": spec.get("id", task_json.parent.name),
                    "ok": False,
                    "error": "task.json missing verify.command list",
                    "path": str(task_json.relative_to(REPO_ROOT)),
                }
            )
            continue

        timeout = int(verify.get("timeout_sec", 120))
        cwd = REPO_ROOT / str(verify.get("cwd", "."))
        code, so, se, elapsed = _run_cmd([str(x) for x in cmd], cwd, timeout=timeout)
        text = (so or "") + (se or "")
        ok = code == 0
        if not ok:
            result["ok"] = False
        evidence = str(spec.get("metrics_hint", {}).get("evidence_quality", "log"))
        entry = {
            "id": spec.get("id", task_json.parent.name),
            "title": spec.get("title", ""),
            "ok": ok,
            "path": str(task_json.relative_to(REPO_ROOT)),
            "metrics": _default_metrics(ok, elapsed, 1, text, evidence),
            "stdout_tail": (so or "")[-2000:],
            "stderr_tail": (se or "")[-2000:],
        }
        result["tasks"].append(entry)
    return result


def run_level6_cli_readiness(max_level: int) -> dict[str, Any]:
    """Level 6: GeoSeal / CLI surface readiness (pytest gates, not merge gates)."""
    out: dict[str, Any] = {
        "level": 6,
        "label": "cli_surface_readiness",
        "summary": (
            "Same question as competitive CLI benchmark: help, version, doctor --json, "
            "JSON stability, bin wiring — not model intelligence."
        ),
        "canonical_scoring_refresh": "npm run benchmark:cli",
        "ok": True,
        "subtasks": [],
    }
    if max_level < 6:
        out["skipped"] = True
        return out

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/benchmark/test_cli_competitive_benchmark.py",
        "tests/smoke/test_npm_geoseal_bin.py",
        "-q",
    ]
    code, so, se, elapsed = _run_cmd(
        cmd, REPO_ROOT, timeout=600, env=_env_with_repo_pythonpath()
    )
    text = (so or "") + (se or "")
    ok = code == 0
    out["ok"] = ok
    out["subtasks"].append(
        {
            "name": "cli_competitive_and_geoseal_bin_tests",
            "ok": ok,
            "metrics": _default_metrics(ok, elapsed, 1, text, "artifact"),
            "command": cmd,
            "stdout_tail": (so or "")[-2500:],
            "stderr_tail": (se or "")[-2500:],
        }
    )
    return out


def run_level7_scbe_code_agent(max_level: int) -> dict[str, Any]:
    """Level 7: deployable SCBE coding-agent surface readiness."""

    out: dict[str, Any] = {
        "level": 7,
        "label": "scbe_code_agent_readiness",
        "summary": (
            "Measures scripts/agents/scbe_code.py: CA opcode compilation, "
            "lexicon rendering, stage6 manifest fallback, and sandboxed safe_apply."
        ),
        "ok": True,
        "subtasks": [],
    }
    if max_level < 7:
        out["skipped"] = True
        return out

    checks: list[tuple[str, list[str], int]] = [
        (
            "scbe_code_unit_tests",
            [sys.executable, "-m", "pytest", "tests/agents/test_scbe_code.py", "-q"],
            240,
        ),
        (
            "scbe_code_manifest",
            [sys.executable, "scripts/agents/scbe_code.py", "manifest"],
            60,
        ),
        (
            "scbe_code_compile_ca",
            [
                sys.executable,
                "scripts/agents/scbe_code.py",
                "compile-ca",
                "--opcodes",
                "0x00",
                "--target",
                "python",
                "--fn",
                "bench_add",
                "--args",
                "a,b",
                "--json",
            ],
            60,
        ),
        (
            "scbe_code_render_op",
            [
                sys.executable,
                "scripts/agents/scbe_code.py",
                "render-op",
                "--op",
                "add",
                "--target",
                "KO",
                "--a",
                "x",
                "--b",
                "y",
                "--json",
            ],
            60,
        ),
    ]

    for name, cmd, timeout in checks:
        code, so, se, elapsed = _run_cmd(
            cmd, REPO_ROOT, timeout=timeout, env=_env_with_repo_pythonpath()
        )
        text = (so or "") + (se or "")
        ok = code == 0
        if ok and name == "scbe_code_compile_ca":
            try:
                ok = bool(json.loads(so).get("round_trip_ok"))
            except json.JSONDecodeError:
                ok = False
        if ok and name == "scbe_code_render_op":
            try:
                ok = json.loads(so).get("rendered") == "(x + y)"
            except json.JSONDecodeError:
                ok = False
        if not ok:
            out["ok"] = False
        out["subtasks"].append(
            {
                "name": name,
                "ok": ok,
                "metrics": _default_metrics(ok, elapsed, 1, text, "artifact"),
                "command": cmd,
                "stdout_tail": (so or "")[-2500:],
                "stderr_tail": (se or "")[-2500:],
            }
        )
    return out


def deferred_targets() -> dict[str, Any]:
    """Document external ladder rungs not yet wired in CI."""
    return {
        "2": {
            "name": "terminal_bench_style",
            "summary": "Task folder + Docker/sandbox + verifier (Terminal-Bench analog)",
            "status": "adapter_scaffolded",
            "reference": "https://www.tbench.ai/",
            "local_adapter": "python scripts/benchmark/external_agentic_eval_driver.py --manifest config/eval/external_agentic_eval_tasks.sample.json",
        },
        "3": {
            "name": "swe_bench_lite",
            "summary": "Public issue-resolution harness (SWE-bench Lite / Verified)",
            "status": "adapter_scaffolded",
            "reference": "https://www.swebench.com/",
            "local_adapter": "python scripts/benchmark/external_agentic_eval_driver.py --manifest config/eval/external_agentic_eval_tasks.sample.json",
        },
        "4": {
            "name": "web_gaia_style",
            "summary": "Browser search, evidence collection, cited answers",
            "status": "not_wired",
            "reference": "https://huggingface.co/gaia-benchmark",
        },
        "5": {
            "name": "scbe_governance",
            "summary": "Route decision, no secret leak, rollback plan, test evidence, artifact hash",
            "status": "partial",
            "notes": "secret_leak_count and test evidence tracked in ladder metrics; full gate pending",
        },
    }


def rollup_metrics(level_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate counts — pass rate is explicit, not the only signal."""
    passed = 0
    failed = 0
    total_secret = 0
    total_time = 0.0
    for block in level_blocks:
        for key in ("subtasks", "tasks"):
            for item in block.get(key) or []:
                m = item.get("metrics") or {}
                total_secret += int(m.get("secret_leak_count", 0))
                total_time += float(m.get("time_to_success_sec", 0))
                if m.get("task_success"):
                    passed += 1
                else:
                    failed += 1
    total = passed + failed
    return {
        "task_success_rate": round(passed / total, 4) if total else 1.0,
        "tasks_evaluated": total,
        "tasks_passed": passed,
        "tasks_failed": failed,
        "total_secret_leak_count": total_secret,
        "total_time_sec": round(total_time, 3),
        "dimensions_tracked": [
            "task_success",
            "test_pass",
            "time_to_success_sec",
            "commands_used",
            "human_interventions",
            "cost_usd",
            "secret_leak_count",
            "rollback_safety",
            "evidence_quality",
        ],
    }


def run_ladder(max_level: int) -> dict[str, Any]:
    max_level = max(0, min(7, max_level))
    blocks: list[dict[str, Any]] = []
    blocks.append(run_level0_smoke())
    blocks.append(run_level1_tasks(max_level))
    blocks.append(run_level6_cli_readiness(max_level))
    blocks.append(run_level7_scbe_code_agent(max_level))

    ok = all(b.get("ok", True) for b in blocks if not b.get("skipped"))
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "lane": "agentic_benchmark_ladder",
        "max_level": max_level,
        "ok": ok,
        "metrics_rollup": rollup_metrics(blocks),
        "levels": {str(b["level"]): b for b in blocks},
        "external_ladder_targets": deferred_targets(),
        "notes": [
            "Pass rate alone is insufficient; use metrics_rollup and per-task metrics.",
            "Levels 2–5 require separate adapters (Terminal-Bench, SWE-bench, GAIA/WebArena, governance).",
            "Level 6 is CLI/GeoSeal surface readiness (pytest); full peer scoring: npm run benchmark:cli.",
            "Level 7 is SCBE deployable coding-agent surface readiness, not frontier-model parity.",
        ],
    }


def cmd_validate(_: argparse.Namespace) -> int:
    errors: list[str] = []
    for task_json in discover_tasks():
        try:
            spec = _load_task_json(task_json)
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f"{task_json}: {e}")
            continue
        if "id" not in spec:
            errors.append(f"{task_json}: missing id")
        if "verify" not in spec or not isinstance(spec["verify"], dict):
            errors.append(f"{task_json}: missing verify object")
        else:
            cmd = spec["verify"].get("command")
            if not isinstance(cmd, list) or not all(isinstance(x, str) for x in cmd):
                errors.append(f"{task_json}: verify.command must be a list of strings")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "tasks": len(discover_tasks())}, indent=2))
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    rows = []
    for task_json in discover_tasks():
        spec = _load_task_json(task_json)
        rows.append(
            {
                "id": spec.get("id", task_json.parent.name),
                "level": spec.get("level", 1),
                "path": str(task_json.relative_to(REPO_ROOT)),
            }
        )
    print(json.dumps({"tasks": rows}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SCBE agentic benchmark ladder")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run ladder up to max_level (0–7)")
    p_run.add_argument(
        "--max-level",
        type=int,
        default=1,
        help="Highest ladder level to execute: 0–1, 6, and 7 are implemented; 2–5 deferred (default 1)",
    )
    p_run.add_argument(
        "--query",
        type=str,
        default="",
        help="Same as workflow query: integer or max_level=N",
    )

    sub.add_parser(
        "validate", help="Validate task.json files under scbe_agentic_v1/tasks"
    )
    sub.add_parser("list", help="List discovered repo-native tasks")

    args = parser.parse_args()
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "run":
        ml = max(0, min(7, args.max_level))
        if args.query:
            ml = _parse_max_level(args.query)
        result = run_ladder(ml)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
