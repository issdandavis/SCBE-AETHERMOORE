"""
scbe_shell.py — SCBE-governed local shell.

Replaces raw PowerShell/bash with a governance-checked execution layer:

  1. Accept a natural-language task (or a direct command with --cmd)
  2. Ask the LLM to plan the required shell commands
  3. Run each command through SCBE L12 harmonic governance gate
  4. Execute ALLOW/QUARANTINE commands locally; block DENY
  5. Polymerize follow-up probes when output deviates from intent
  6. Write a governance receipt to stdout (JSON) or a file

Usage:
    # Natural-language task
    python scripts/benchmark/scbe_shell.py "create a python venv and install requests"

    # Direct command bypass (skips LLM planner, still governs)
    python scripts/benchmark/scbe_shell.py --cmd "rm -rf /tmp/test_dir"

    # Quiet mode (only print command output, receipt goes to file)
    python scripts/benchmark/scbe_shell.py --quiet "list all python files recursively"

    # Custom model / Ollama host
    python scripts/benchmark/scbe_shell.py --model qwen2.5:7b --host http://127.0.0.1:11434 "..."

    # Max turns budget
    python scripts/benchmark/scbe_shell.py --max-turns 20 "build the project"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.benchmark.scbe_governance_core import (
    CommandPlan,
    GovRecord as _GovRecord,
    danger_drift,
    harmonic_score,
    output_deviation,
    plan_commands,
    polymerize_probes,
    risk_tier,
    semantic_distance,
)

# ─────────────────────────────────────────────────────────────────────────────
# Local execution
# ─────────────────────────────────────────────────────────────────────────────


def _local_shell_argv(cmd: str) -> list[str]:
    """Return an explicit shell argv so commands run with shell=False."""
    if os.name == "nt":
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh:
            return [pwsh, "-NoProfile", "-NonInteractive", "-Command", cmd]
        comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe") or "cmd.exe"
        return [comspec, "/D", "/C", cmd]

    bash = shutil.which("bash")
    if bash:
        return [bash, "-lc", cmd]
    sh = shutil.which("sh") or "/bin/sh"
    return [sh, "-c", cmd]


def run_local(cmd: str, timeout: int = 30) -> tuple[str, int]:
    """Run a shell command locally. Returns (combined_output, exit_code)."""
    try:
        result = subprocess.run(
            _local_shell_argv(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = result.stdout + result.stderr
        return out, result.returncode
    except subprocess.TimeoutExpired:
        return f"TIMEOUT after {timeout}s", 124
    except Exception as e:
        return f"EXEC ERROR: {e}", 1


# ─────────────────────────────────────────────────────────────────────────────
# Governed execution loop
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ShellSession:
    """Accumulates terminal state like a real shell would."""

    history: list[str] = field(default_factory=list)

    def record(self, cmd: str, output: str) -> None:
        self.history.append(f"$ {cmd}\n{output}")

    def state(self) -> str:
        return "\n".join(self.history[-6:])  # last 6 exchanges


def run_governed_task(
    instruction: str,
    model: str,
    ollama_host: str,
    max_turns: int,
    deviation_threshold: float,
    quiet: bool,
    direct_cmd: Optional[str],
) -> dict:
    session = ShellSession()
    gov: list[_GovRecord] = []

    def emit(msg: str) -> None:
        if not quiet:
            print(msg, flush=True)

    if direct_cmd:
        # Direct-command mode: single-command governance check, no LLM planner
        turns_used = 1
        cmd = direct_cmd
        d = semantic_distance(cmd)
        pd = max(danger_drift(cmd), output_deviation(instruction, ""))
        score = harmonic_score(d, pd)
        tier = risk_tier(score)
        emit(f"[SCBE] cmd={cmd!r}  tier={tier}  score={score:.4f}")
        if tier == "DENY":
            gov.append(_GovRecord(cmd, "DENY", score, d, pd))
            emit(f"[SCBE] DENIED — not executed")
        else:
            out, rc = run_local(cmd)
            emit(out.rstrip())
            session.record(cmd, out)
            dev = output_deviation(instruction, out)
            probes = []
            if dev > deviation_threshold:
                probes = polymerize_probes(cmd, out)
                for probe in probes:
                    p_out, _ = run_local(probe)
                    emit(f"[PROBE] {probe}")
                    emit(p_out.rstrip())
                    session.record(probe, p_out)
            gov.append(_GovRecord(cmd, tier, score, d, pd, polymerized=bool(probes)))
    else:
        # LLM planner mode
        turns_used = 0
        for turn in range(1, max_turns + 1):
            turns_used = turn
            try:
                plan = plan_commands(instruction, session.state(), turn, max_turns, model, ollama_host)
            except Exception as e:
                emit(f"[SCBE] LLM error on turn {turn}: {e}")
                break

            if not plan.commands and plan.done:
                emit(f"[SCBE] Agent signalled done (turn {turn})")
                break

            for cmd in plan.commands:
                d = semantic_distance(cmd)
                pd = max(danger_drift(cmd), output_deviation(instruction, session.state()))
                score = harmonic_score(d, pd)
                tier = risk_tier(score)

                emit(f"[SCBE] turn={turn}  tier={tier}  score={score:.4f}  $ {cmd}")

                if tier == "DENY":
                    gov.append(_GovRecord(cmd, "DENY", score, d, pd))
                    emit(f"  → DENIED — skipped")
                    continue

                out, rc = run_local(cmd)
                emit(out.rstrip() if out.strip() else "  (no output)")
                session.record(cmd, out)
                time.sleep(0.1)

                # Polymerization
                dev = output_deviation(instruction, out)
                probes = []
                if dev > deviation_threshold:
                    probes = polymerize_probes(cmd, out)
                    for probe in probes:
                        emit(f"[PROBE] {probe}")
                        p_out, _ = run_local(probe)
                        emit(p_out.rstrip())
                        session.record(probe, p_out)
                gov.append(_GovRecord(cmd, tier, score, d, pd, polymerized=bool(probes)))

            if plan.done:
                emit(f"[SCBE] Task complete (turn {turn})")
                break

    summary = {
        "allow": sum(1 for r in gov if r.decision == "ALLOW"),
        "quarantine": sum(1 for r in gov if r.decision == "QUARANTINE"),
        "deny": sum(1 for r in gov if r.decision == "DENY"),
        "polymerized_events": sum(1 for r in gov if r.polymerized),
    }
    receipt = {
        "instruction": instruction[:200],
        "model": model,
        "turns": turns_used,
        "governance_summary": summary,
        "commands": [
            {
                "cmd": r.command[:200],
                "decision": r.decision,
                "score": round(r.score, 4),
                "d_H": round(r.d_H, 4),
                "pd": round(r.pd, 4),
                "polymerized": r.polymerized,
            }
            for r in gov
        ],
    }
    return receipt


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SCBE-governed local shell — governed task execution with polymerization"
    )
    parser.add_argument("task", nargs="?", help="Natural-language task description")
    parser.add_argument("--cmd", help="Direct shell command (skips LLM planner, still governed)")
    parser.add_argument("--model", default="qwen2.5:0.5b", help="Ollama model tag")
    parser.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama host URL")
    parser.add_argument("--max-turns", type=int, default=15, help="LLM turn budget")
    parser.add_argument(
        "--deviation-threshold", type=float, default=0.45, help="Deviation score that triggers polymerization probes"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress live output; print JSON receipt only")
    parser.add_argument("--receipt", help="Write JSON receipt to this file path")
    args = parser.parse_args()

    if not args.task and not args.cmd:
        parser.error("Provide a task description or --cmd")

    instruction = args.task or args.cmd

    receipt = run_governed_task(
        instruction=instruction,
        model=args.model,
        ollama_host=args.host,
        max_turns=args.max_turns,
        deviation_threshold=args.deviation_threshold,
        quiet=args.quiet,
        direct_cmd=args.cmd,
    )

    if args.quiet or args.receipt:
        receipt_json = json.dumps(receipt, indent=2)
        if args.receipt:
            Path(args.receipt).write_text(receipt_json)
            if not args.quiet:
                print(f"[SCBE] Receipt written to {args.receipt}")
        else:
            print(receipt_json)
    else:
        print("\n[SCBE] ── Governance Receipt ──")
        s = receipt["governance_summary"]
        print(
            f"  ALLOW={s['allow']}  QUARANTINE={s['quarantine']}  DENY={s['deny']}  polymerized={s['polymerized_events']}"
        )


if __name__ == "__main__":
    main()
