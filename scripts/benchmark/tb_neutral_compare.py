#!/usr/bin/env python3
"""tb_neutral_compare.py — SCBE vs baseline on neutral terminal-bench tasks.

Two modes:
  governance   (default, no Docker) — score each task's instruction through
               the SCBE L12 harmonic wall and show what the agent would
               ALLOW / QUARANTINE / DENY before touching the shell.
               Proves governance delta without requiring Docker.

  run          (requires WSL2 + Podman) — invoke the actual tb harness for
               both oracle and SCBE agent on the selected task set.

Usage:
    python scripts/benchmark/tb_neutral_compare.py
    python scripts/benchmark/tb_neutral_compare.py --mode governance
    python scripts/benchmark/tb_neutral_compare.py --mode run --tasks hello-world,fibonacci-server
    python scripts/benchmark/tb_neutral_compare.py --json

Claim boundary:
    governance mode is static analysis — it shows what the governance layer
    would do to the LLM's planned commands.  It is NOT a task completion score.
    run mode produces real task completion data through the official tb harness.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TB_DATASET_ROOT = REPO_ROOT / "artifacts" / "benchmarks" / "tb-datasets" / "terminal-bench-core-0.1.1" / "tasks"
OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "tb-neutral-compare"
SCBE_AGENT_MODULE = "scripts.benchmark.terminal_bench_scbe_agent:ScbeGovernedAgent"

# ─────────────────────────────────────────────────────────────────────────────
# Neutral task selection — zero SCBE-specific framing; drawn from tb categories
# ─────────────────────────────────────────────────────────────────────────────

NEUTRAL_TASKS = [
    # file-operations (easy)
    "hello-world",
    "fix-permissions",
    # software-engineering
    "fibonacci-server",
    "broken-python",
    "fix-pandas-version",
    # data processing
    "csv-to-parquet",
    "heterogeneous-dates",
    # git / version control
    "fix-git",
    "sanitize-git-repo",
    # environment / networking
    "openssl-selfsigned-cert",
    "nginx-request-logging",
    # coding challenges
    "polyglot-c-py",
    "grid-pattern-transform",
]

# ─────────────────────────────────────────────────────────────────────────────
# Governance pre-screen (no Docker required)
# ─────────────────────────────────────────────────────────────────────────────

_gov_root = str(Path(__file__).parent)
if _gov_root not in sys.path:
    sys.path.insert(0, _gov_root)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark.scbe_governance_core import (  # noqa: E402
    danger_drift,
    harmonic_score,
    risk_tier,
    semantic_distance,
)

PHI = (1 + math.sqrt(5)) / 2


@dataclass
class TaskGovResult:
    task_id: str
    instruction: str
    representative_commands: list[str]
    scores: list[dict[str, Any]]
    overall_tier: str
    deny_count: int
    quarantine_count: int
    allow_count: int


def _load_instruction(task_id: str) -> str:
    task_yaml = TB_DATASET_ROOT / task_id / "task.yaml"
    if not task_yaml.exists():
        return f"(task.yaml not found for {task_id})"
    text = task_yaml.read_text(encoding="utf-8")
    m = re.search(r"^instruction:\s*\|-?\n((?:  .+\n?)+)", text, re.MULTILINE)
    if m:
        return re.sub(r"^  ", "", m.group(1), flags=re.MULTILINE).strip()
    m = re.search(r"^instruction:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "(parse-error)"


def _representative_commands(task_id: str, instruction: str) -> list[str]:
    """Generate a small set of plausible shell commands for the task.

    These represent what a naive agent would typically attempt first.
    Used to evaluate the governance layer, not to solve the task.
    """
    cmd_map: dict[str, list[str]] = {
        "hello-world": ['echo "Hello, world!" > hello.txt'],
        "fix-permissions": ["ls -la", "chmod 644 *.txt"],
        "fibonacci-server": ["cat > server.py << 'EOF'", "python server.py &"],
        "broken-python": ["python broken.py", "pip install -r requirements.txt"],
        "fix-pandas-version": ["pip install pandas==1.5.3", "python check.py"],
        "csv-to-parquet": ["pip install pyarrow", "python convert.py"],
        "heterogeneous-dates": ["python parse_dates.py"],
        "fix-git": ["git status", "git log --oneline -5"],
        "sanitize-git-repo": ["git log --all --oneline", "git filter-branch"],
        "openssl-selfsigned-cert": [
            "openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes"
        ],
        "nginx-request-logging": ["nginx -t", "cat /etc/nginx/nginx.conf"],
        "polyglot-c-py": ["cat polyglot.c", "gcc polyglot.c -o polyglot"],
        "grid-pattern-transform": ["python transform.py"],
    }
    return cmd_map.get(task_id, ["cat task.yaml", "python solution.py"])


def score_governance(task_id: str) -> TaskGovResult:
    instruction = _load_instruction(task_id)
    cmds = _representative_commands(task_id, instruction)
    scores: list[dict[str, Any]] = []
    deny = quarantine = allow = 0
    for cmd in cmds:
        d = semantic_distance(cmd)
        pd = danger_drift(cmd)
        score = harmonic_score(d, pd)
        tier = risk_tier(score)
        scores.append({"cmd": cmd, "d_H": round(d, 4), "pd": round(pd, 4), "score": round(score, 4), "tier": tier})
        if tier == "DENY":
            deny += 1
        elif tier == "QUARANTINE":
            quarantine += 1
        else:
            allow += 1

    if deny > 0:
        overall = "DENY"
    elif quarantine > 0:
        overall = "QUARANTINE"
    else:
        overall = "ALLOW"

    return TaskGovResult(
        task_id=task_id,
        instruction=instruction[:200] + ("…" if len(instruction) > 200 else ""),
        representative_commands=cmds,
        scores=scores,
        overall_tier=overall,
        deny_count=deny,
        quarantine_count=quarantine,
        allow_count=allow,
    )


def run_governance_mode(tasks: list[str]) -> dict[str, Any]:
    results = [score_governance(t) for t in tasks]
    allow = sum(1 for r in results if r.overall_tier == "ALLOW")
    quarantine = sum(1 for r in results if r.overall_tier == "QUARANTINE")
    deny = sum(1 for r in results if r.overall_tier == "DENY")
    return {
        "mode": "governance",
        "generated_at_utc": _utc_now(),
        "claim_boundary": (
            "Static governance pre-screen only. "
            "This is NOT a task completion score. "
            "Use --mode run for actual tb harness results."
        ),
        "task_count": len(results),
        "summary": {
            "allow": allow,
            "quarantine": quarantine,
            "deny": deny,
            "allow_rate": round(allow / len(results), 4) if results else 0,
        },
        "tasks": [asdict(r) for r in results],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full run mode (WSL2 + Podman required)
# ─────────────────────────────────────────────────────────────────────────────


def _wsl_path(win_path: Path) -> str:
    drive = win_path.drive.rstrip(":").lower()
    rest = str(win_path).replace("\\", "/")[len(win_path.drive) :]
    return f"/mnt/{drive}{rest}"


def run_tb_agent(
    agent: str,
    tasks: list[str],
    model: str,
    max_turns: int,
    dataset_root: Path,
    out_root: Path,
) -> dict[str, Any]:
    """Invoke tb runs create via WSL2 bash for one agent on all tasks."""
    wsl_dataset = _wsl_path(dataset_root)
    wsl_out = _wsl_path(out_root / agent)
    wsl_repo = _wsl_path(REPO_ROOT)
    task_flags = " ".join(f"--task-id {t}" for t in tasks)

    if agent == "oracle":
        cmd_parts = [
            "export DOCKER_HOST=unix:///run/podman/podman.sock",
            f"export PYTHONPATH={wsl_repo}",
            f"tb runs create --agent oracle --dataset-path {wsl_dataset} "
            f"--output-path {wsl_out} --n-concurrent 1 {task_flags}",
        ]
    else:
        cmd_parts = [
            "export DOCKER_HOST=unix:///run/podman/podman.sock",
            f"export PYTHONPATH={wsl_repo}",
            f"tb runs create --agent-import-path {SCBE_AGENT_MODULE} "
            f"--dataset-path {wsl_dataset} --output-path {wsl_out} "
            f"--n-concurrent 1 --agent-kwarg model={model} "
            f"--agent-kwarg max_turns={max_turns} {task_flags}",
        ]

    bash_cmd = " && ".join(cmd_parts)
    print(f"\n[tb_neutral_compare] Running {agent} on {len(tasks)} tasks…")
    result = subprocess.run(
        ["wsl", "--", "bash", "-c", bash_cmd],
        capture_output=False,  # stream to stdout so user sees progress
        text=True,
        timeout=3600,
    )
    return {
        "agent": agent,
        "returncode": result.returncode,
        "out_path": str(out_root / agent),
    }


def _score_tb_run(out_dir: Path) -> dict[str, Any]:
    """Walk tb output directory and aggregate pass/fail counts."""
    passed = failed = total = 0
    task_results: list[dict[str, Any]] = []
    if not out_dir.exists():
        return {"passed": 0, "failed": 0, "total": 0, "tasks": []}
    for result_file in out_dir.rglob("results.json"):
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows = data.get("results", [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            total += 1
            ok = row.get("is_resolved") is True
            if ok:
                passed += 1
            else:
                failed += 1
            task_results.append(
                {
                    "task_id": row.get("task_id") or result_file.parent.name,
                    "passed": ok,
                    "failure_mode": row.get("failure_mode"),
                    "results_path": str(result_file),
                }
            )
    for result_file in out_dir.rglob("result.json"):
        if result_file.name == "results.json":
            continue
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        total += 1
        ok = bool(data.get("passed", False))
        if ok:
            passed += 1
        else:
            failed += 1
        task_results.append(
            {
                "task_id": result_file.parent.name,
                "passed": ok,
                "score": data.get("score"),
            }
        )
    return {"passed": passed, "failed": failed, "total": total, "tasks": task_results}


def run_full_mode(
    tasks: list[str],
    model: str,
    max_turns: int,
) -> dict[str, Any]:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = OUT_DIR / run_ts
    dataset_path = TB_DATASET_ROOT

    oracle_meta = run_tb_agent("oracle", tasks, model, max_turns, dataset_path, out_root)
    scbe_meta = run_tb_agent("scbe", tasks, model, max_turns, dataset_path, out_root)

    oracle_score = _score_tb_run(out_root / "oracle")
    scbe_score = _score_tb_run(out_root / "scbe")

    delta = scbe_score["passed"] - oracle_score["passed"]
    return {
        "mode": "run",
        "generated_at_utc": _utc_now(),
        "run_id": run_ts,
        "claim_boundary": (
            "Official terminal-bench task execution. "
            "Oracle = reference agent shipped with tb. "
            "SCBE = ScbeGovernedAgent with L12 harmonic wall + polymerization."
        ),
        "task_count": len(tasks),
        "oracle": oracle_score,
        "scbe": scbe_score,
        "delta_pass": delta,
        "meta": [oracle_meta, scbe_meta],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_TIER_ACTION = {
    "ALLOW": "execute freely     (H≥0.60)",
    "QUARANTINE": "execute + audit    (0.30≤H<0.60)",
    "DENY": "BLOCK entirely     (H<0.30)",
}


def _print_governance_report(report: dict[str, Any]) -> None:
    s = report["summary"]
    blocked = s["deny"]
    executed = s["allow"] + s["quarantine"]
    print(f"\n{'=' * 68}")
    print(f"SCBE Governance Pre-Screen — {report['task_count']} neutral terminal-bench tasks")
    print(f"{'=' * 68}")
    print("\n  Tier breakdown (H = harmonic wall score):")
    print(f"    ALLOW      {s['allow']:>3}  — {_TIER_ACTION['ALLOW']}")
    print(f"    QUARANTINE {s['quarantine']:>3}  — {_TIER_ACTION['QUARANTINE']}")
    print(f"    DENY       {s['deny']:>3}  — {_TIER_ACTION['DENY']}")
    print(f"\n  Execution outcome: {executed}/{report['task_count']} tasks proceed (ALLOW + QUARANTINE)")
    print(f"  Blocked entirely:  {blocked}/{report['task_count']} tasks")
    print(f"  Audit coverage:    {s['quarantine']}/{report['task_count']} tasks logged to JSONL receipt")
    print("\n  Interpretation: QUARANTINE is NOT a rejection. The agent executes the")
    print("  command and records a governance receipt. DENY is the only blocking tier.")
    print(f"\n{'Task':<38} {'Tier':<12} {'Action'}")
    print(f"{'-' * 68}")
    for t in report["tasks"]:
        action = _TIER_ACTION[t["overall_tier"]]
        print(f"  {t['task_id']:<36} {t['overall_tier']:<12} {action}")
    print(f"\nClaim boundary: {report['claim_boundary']}")


def _print_run_report(report: dict[str, Any]) -> None:
    o = report["oracle"]
    s = report["scbe"]
    print(f"\n{'=' * 60}")
    print(f"Terminal-Bench Run — {report['task_count']} neutral tasks")
    print(f"{'=' * 60}")
    print(f"  Oracle: {o['passed']}/{o['total']} passed")
    print(f"  SCBE:   {s['passed']}/{s['total']} passed")
    print(f"  Delta:  {report['delta_pass']:+d}")
    print(f"\nClaim boundary: {report['claim_boundary']}")


def _write_report(report: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mode = report["mode"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"tb_neutral_{mode}_{ts}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT_DIR / f"latest_{mode}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--mode",
        choices=["governance", "run"],
        default="governance",
        help="governance: static pre-screen (no Docker); run: real tb execution (WSL2 required)",
    )
    parser.add_argument(
        "--tasks", default=",".join(NEUTRAL_TASKS), help="Comma-separated task IDs (default: full neutral suite)"
    )
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model for SCBE agent (default: qwen2.5:7b)")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    args = parser.parse_args()

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]

    if args.mode == "governance":
        report = run_governance_mode(tasks)
        path = _write_report(report)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            _print_governance_report(report)
            print(f"\nFull report: {path}")
        return 0

    # run mode
    report = run_full_mode(tasks, args.model, args.max_turns)
    path = _write_report(report)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_run_report(report)
        print(f"\nFull report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
