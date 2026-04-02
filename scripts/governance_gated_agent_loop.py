#!/usr/bin/env python3
"""SCBE Governance-Gated Agent Loop

Autonomous coding agent that proposes changes, runs them through the
L13 governance gate, and retries until the gate reads ALLOW. Every
rejection becomes a DPO training pair. Every approval becomes SFT data.

Usage:
    python scripts/governance_gated_agent_loop.py --task "add error handling to api/main.py"
    python scripts/governance_gated_agent_loop.py --task "refactor harmonic scaling" --max-retries 10
    python scripts/governance_gated_agent_loop.py --task-file tasks.txt --max-hours 8
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ───────────────────────────────────────────────────────

PHI = (1 + math.sqrt(5)) / 2
PI = math.pi

TONGUE_WEIGHTS = {
    "KO": PHI**0, "AV": PHI**1, "RU": PHI**2,
    "CA": PHI**3, "UM": PHI**4, "DR": PHI**5,
}

# Risk patterns for code governance
RISK_PATTERNS = {
    "critical": [
        (r"os\.system|subprocess\.(run|call|Popen)\(.*shell\s*=\s*True", "shell_injection"),
        (r"eval\(|exec\(", "dynamic_execution"),
        (r"pickle\.load|yaml\.unsafe_load|marshal\.load", "unsafe_deserialization"),
        (r"__import__\(", "dynamic_import"),
    ],
    "high": [
        (r"rm\s+-rf|shutil\.rmtree|os\.remove", "destructive_operation"),
        (r"password|secret|api_key|token.*=\s*['\"]", "hardcoded_credential"),
        (r"requests\.(get|post).*verify\s*=\s*False", "disabled_tls"),
        (r"chmod\s+777|0o777", "permissive_permissions"),
    ],
    "medium": [
        (r"except\s*:", "bare_except"),
        (r"# ?TODO|# ?FIXME|# ?HACK|# ?XXX", "todo_marker"),
        (r"print\(.*password|print\(.*secret|print\(.*token", "credential_leak"),
        (r"assert\s+", "assert_in_production"),
    ],
    "low": [
        (r"import\s+\*", "wildcard_import"),
        (r"type:\s*ignore", "type_ignore"),
        (r"noqa", "linter_suppression"),
    ],
}


# ── Governance Gate (L12-L13) ───────────────────────────────────────

class GovernanceGate:
    """L13 decision gate using canonical harmonic formula."""

    def __init__(self, strict: bool = True):
        self.strict = strict
        self.history: list[dict] = []

    def evaluate(self, code: str, context: dict | None = None) -> dict:
        """Run full governance evaluation on proposed code."""
        risks = self._scan_risks(code)
        tongue_profile = self._compute_tongue_profile(code)
        d_h = self._compute_distance(risks, tongue_profile)
        pd = self._compute_phase_deviation(tongue_profile)

        # Canonical formula: H(d,pd) = 1/(1 + phi*d_H + 2*pd)
        h_score = 1.0 / (1.0 + PHI * d_h + 2.0 * pd)

        # Theoretical cost: pi^(phi*d)
        d_star = min(d_h, 5.0)
        theoretical_cost = PI ** (PHI * d_star)

        # Risk-adjusted score
        risk_adjusted = (1.0 - h_score) * (1.0 + len(risks.get("critical", [])) * 2.0)

        # Decision
        if risk_adjusted < 0.15 and not risks.get("critical"):
            decision = "ALLOW"
        elif risk_adjusted < 0.45 and not risks.get("critical"):
            decision = "QUARANTINE"
        elif risk_adjusted < 0.75:
            decision = "ESCALATE"
        else:
            decision = "DENY"

        # Override: any critical risk = DENY in strict mode
        if self.strict and risks.get("critical"):
            decision = "DENY"

        result = {
            "decision": decision,
            "h_score": round(h_score, 6),
            "theoretical_cost": round(theoretical_cost, 4),
            "risk_adjusted": round(risk_adjusted, 6),
            "distance": round(d_h, 6),
            "phase_deviation": round(pd, 6),
            "risks": risks,
            "tongue_profile": tongue_profile,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.history.append(result)
        return result

    def _scan_risks(self, code: str) -> dict[str, list[tuple[str, int]]]:
        """Scan code for risk patterns by severity."""
        found: dict[str, list] = {}
        for severity, patterns in RISK_PATTERNS.items():
            matches = []
            for pattern, label in patterns:
                for m in re.finditer(pattern, code, re.IGNORECASE):
                    line_num = code[:m.start()].count("\n") + 1
                    matches.append((label, line_num))
            if matches:
                found[severity] = matches
        return found

    def _compute_tongue_profile(self, code: str) -> dict[str, float]:
        """Compute Sacred Tongue activations for code."""
        lower = code.lower()
        n_lines = max(code.count("\n") + 1, 1)

        ko = min(1.0, len(re.findall(r"def |class |return |if |for |while ", code)) / n_lines * 2)
        av = min(1.0, len(re.findall(r"import |from |@\w+|-> |: \w+", code)) / n_lines * 3)
        ru = min(1.0, len(re.findall(r"assert |raise |if not |isinstance|validate", lower)) / n_lines * 4)
        ca = min(1.0, len(re.findall(r"numpy|torch|math\.|sum\(|max\(|min\(|\*\*", lower)) / n_lines * 3)
        um = min(1.0, len(re.findall(r"hash|encrypt|token|auth|permission|sanitize", lower)) / n_lines * 5)
        dr = min(1.0, len(re.findall(r"class \w+|self\.|__init__|@property|abstract", code)) / n_lines * 3)

        return {"KO": round(ko, 4), "AV": round(av, 4), "RU": round(ru, 4),
                "CA": round(ca, 4), "UM": round(um, 4), "DR": round(dr, 4)}

    def _compute_distance(self, risks: dict, profile: dict) -> float:
        """Compute hyperbolic distance from safe center based on risk severity."""
        d = 0.0
        d += len(risks.get("critical", [])) * 1.5
        d += len(risks.get("high", [])) * 0.8
        d += len(risks.get("medium", [])) * 0.3
        d += len(risks.get("low", [])) * 0.1

        # Null tongue penalty (narrow activation = suspicious)
        null_count = sum(1 for v in profile.values() if v < 0.05)
        if null_count >= 4:
            d += 1.0

        return min(d, 5.0)

    def _compute_phase_deviation(self, profile: dict) -> float:
        """Phase deviation = how far the tongue distribution is from expected phi ratio."""
        values = list(profile.values())
        if all(v == 0 for v in values):
            return 1.0

        total = sum(v * TONGUE_WEIGHTS[t] for t, v in profile.items())
        max_possible = sum(TONGUE_WEIGHTS.values())
        return 1.0 - (total / max_possible)

    def rejection_reason(self, result: dict) -> str:
        """Generate human/AI-readable rejection explanation."""
        lines = [f"GOVERNANCE DECISION: {result['decision']}"]
        lines.append(f"Safety score: {result['h_score']:.4f} (1.0 = safe, 0.0 = blocked)")
        lines.append(f"Theoretical cost: {result['theoretical_cost']:.2f}x")
        lines.append(f"Distance from safe center: {result['distance']:.4f}")

        for severity in ["critical", "high", "medium", "low"]:
            risks = result["risks"].get(severity, [])
            if risks:
                lines.append(f"\n{severity.upper()} risks:")
                for label, line_num in risks:
                    lines.append(f"  Line {line_num}: {label}")

        lines.append(f"\nTongue profile: {json.dumps(result['tongue_profile'])}")

        null_count = sum(1 for v in result["tongue_profile"].values() if v < 0.05)
        if null_count >= 4:
            lines.append(f"WARNING: {null_count}/6 tongues silent — narrow activation pattern")

        lines.append(f"\nTo pass: fix all {severity.upper()} risks listed above.")
        return "\n".join(lines)


# ── Code Runner ─────────────────────────────────────────────────────

class CodeRunner:
    """Execute code changes and run tests."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def run_tests(self, test_cmd: str = "python -m pytest tests/ -x -q --tb=short", timeout: int = 120) -> dict:
        """Run test suite and return results."""
        try:
            result = subprocess.run(
                test_cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self.repo_root,
            )
            return {
                "passed": result.returncode == 0,
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "stdout": "", "stderr": "Test timeout", "returncode": -1}
        except Exception as e:
            return {"passed": False, "stdout": "", "stderr": str(e), "returncode": -1}

    def run_lint(self, files: list[str] | None = None) -> dict:
        """Run linting on changed files."""
        cmd = "python -m flake8 --max-line-length=120 --count"
        if files:
            cmd += " " + " ".join(files)
        else:
            cmd += " src/"

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=60, cwd=self.repo_root,
            )
            return {
                "passed": result.returncode == 0,
                "issues": result.stdout.strip().split("\n") if result.stdout.strip() else [],
            }
        except Exception as e:
            return {"passed": False, "issues": [str(e)]}

    def run_typecheck(self, timeout: int = 60) -> dict:
        """Run type checking."""
        try:
            result = subprocess.run(
                "npx tsc --noEmit 2>&1 | tail -5",
                shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=self.repo_root,
            )
            return {"passed": result.returncode == 0, "output": result.stdout[-1000:]}
        except Exception as e:
            return {"passed": False, "output": str(e)}


# ── Training Data Logger ────────────────────────────────────────────

class TrainingLogger:
    """Log every governance evaluation as training data."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sft_file = output_dir / "governance_sft.jsonl"
        self.dpo_file = output_dir / "governance_dpo.jsonl"
        self.session_log = output_dir / "session_log.jsonl"

    def log_approval(self, task: str, code: str, gate_result: dict):
        """Log approved code as SFT training pair."""
        record = {
            "instruction": f"Write code for: {task}",
            "response": code,
            "category": "governance_approved",
            "layer": "L3",
            "meta": {
                "h_score": gate_result["h_score"],
                "decision": gate_result["decision"],
                "timestamp": gate_result["timestamp"],
            },
        }
        with self.sft_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_rejection(self, task: str, bad_code: str, rejection: str, fixed_code: str | None = None):
        """Log rejection as DPO training pair."""
        record = {
            "prompt": f"Write code for: {task}",
            "rejected": bad_code[:2000],
            "rejection_reason": rejection[:1000],
            "chosen": fixed_code[:2000] if fixed_code else None,
            "category": "governance_rejected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self.dpo_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_session_event(self, event: str, data: dict | None = None):
        """Log session lifecycle events."""
        record = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        with self.session_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── Agent Loop ──────────────────────────────────────────────────────

class GovernanceGatedAgent:
    """Autonomous agent that proposes code and retries until governance approves."""

    def __init__(
        self,
        repo_root: Path,
        max_retries: int = 15,
        max_hours: float = 8.0,
        strict: bool = True,
    ):
        self.gate = GovernanceGate(strict=strict)
        self.runner = CodeRunner(repo_root)
        self.logger = TrainingLogger(repo_root / "training-data" / "governance_agent")
        self.repo_root = repo_root
        self.max_retries = max_retries
        self.max_hours = max_hours
        self.start_time = time.time()

    def run_task(self, task: str, target_file: str | None = None) -> dict:
        """Execute a task through the governance-gated loop."""
        self.logger.log_session_event("task_start", {"task": task, "target": target_file})
        print(f"\n{'='*60}")
        print(f"TASK: {task}")
        print(f"Max retries: {self.max_retries} | Max hours: {self.max_hours}")
        print(f"{'='*60}\n")

        attempt = 0
        last_rejection = None

        while attempt < self.max_retries:
            # Check time limit
            elapsed_hours = (time.time() - self.start_time) / 3600
            if elapsed_hours > self.max_hours:
                print(f"\nTIME LIMIT: {elapsed_hours:.1f}h exceeded {self.max_hours}h cap")
                self.logger.log_session_event("time_limit", {"hours": elapsed_hours})
                return {"success": False, "reason": "time_limit", "attempts": attempt}

            attempt += 1
            print(f"\n--- Attempt {attempt}/{self.max_retries} ---")

            # Generate code (in a real system, this calls the HF model)
            code = self._generate_code(task, target_file, last_rejection)
            if not code:
                print("  No code generated, skipping")
                continue

            # Governance gate evaluation
            gate_result = self.gate.evaluate(code)
            decision = gate_result["decision"]

            print(f"  H-score: {gate_result['h_score']:.4f}")
            print(f"  Cost: {gate_result['theoretical_cost']:.2f}x")
            print(f"  Decision: {decision}")

            if decision == "ALLOW":
                print(f"\n  APPROVED on attempt {attempt}")
                self.logger.log_approval(task, code, gate_result)
                self.logger.log_session_event("approved", {
                    "attempt": attempt,
                    "h_score": gate_result["h_score"],
                })

                # Run tests
                print("  Running tests...")
                test_result = self.runner.run_tests()
                if test_result["passed"]:
                    print("  Tests PASSED")
                    self.logger.log_session_event("tests_passed", {"attempt": attempt})
                    return {
                        "success": True,
                        "attempts": attempt,
                        "code": code,
                        "gate_result": gate_result,
                        "test_result": test_result,
                    }
                else:
                    print(f"  Tests FAILED: {test_result['stderr'][:200]}")
                    last_rejection = f"Governance approved but tests failed:\n{test_result['stderr'][:500]}"
                    self.logger.log_rejection(task, code, last_rejection)
                    continue

            else:
                # Rejected — log and prepare retry context
                rejection = self.gate.rejection_reason(gate_result)
                print(f"  REJECTED: {decision}")
                for severity in ["critical", "high"]:
                    for label, line in gate_result["risks"].get(severity, []):
                        print(f"    [{severity}] Line {line}: {label}")

                self.logger.log_rejection(task, code, rejection)
                last_rejection = rejection

        print(f"\nFAILED after {attempt} attempts")
        self.logger.log_session_event("max_retries", {"attempts": attempt})
        return {"success": False, "reason": "max_retries", "attempts": attempt}

    def _generate_code(self, task: str, target_file: str | None, last_rejection: str | None) -> str | None:
        """Generate code for the task. Uses HF model if available, falls back to file read."""

        # If we have a target file, read it as the base
        if target_file:
            target_path = self.repo_root / target_file
            if target_path.exists():
                return target_path.read_text(encoding="utf-8")

        # Try HF model via Polly Sandbox API
        try:
            import httpx

            prompt = f"Write Python code for this task: {task}"
            if last_rejection:
                prompt += f"\n\nPrevious attempt was rejected:\n{last_rejection[:500]}\n\nFix the issues and try again."

            resp = httpx.post(
                "https://issdandavis-polly-sandbox.hf.space/api/predict",
                json={"data": [prompt, []]},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("data", [None])[0]
                if result and len(result) > 20:
                    return result
        except Exception:
            pass

        # Fallback: read from stdin or return None
        return None

    def run_batch(self, tasks: list[dict]) -> list[dict]:
        """Run multiple tasks sequentially through the governance loop."""
        results = []
        for i, task_spec in enumerate(tasks):
            task = task_spec.get("task", "")
            target = task_spec.get("file")
            print(f"\n{'#'*60}")
            print(f"BATCH {i+1}/{len(tasks)}")
            print(f"{'#'*60}")
            result = self.run_task(task, target)
            results.append(result)

            # Check time limit for batch
            elapsed = (time.time() - self.start_time) / 3600
            if elapsed > self.max_hours:
                print(f"\nBatch time limit reached ({elapsed:.1f}h)")
                break

        return results


# ── Session Summary ─────────────────────────────────────────────────

def print_summary(results: list[dict], start_time: float):
    """Print session summary."""
    elapsed = time.time() - start_time
    total = len(results)
    passed = sum(1 for r in results if r.get("success"))
    total_attempts = sum(r.get("attempts", 0) for r in results)

    print(f"\n{'='*60}")
    print(f"SESSION SUMMARY")
    print(f"{'='*60}")
    print(f"Duration: {elapsed/3600:.1f} hours")
    print(f"Tasks: {passed}/{total} passed")
    print(f"Total governance evaluations: {total_attempts}")
    print(f"Average attempts per task: {total_attempts/max(total,1):.1f}")
    print(f"\nTraining data generated:")
    print(f"  SFT pairs (approved): training-data/governance_agent/governance_sft.jsonl")
    print(f"  DPO pairs (rejected): training-data/governance_agent/governance_dpo.jsonl")
    print(f"  Session log: training-data/governance_agent/session_log.jsonl")


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SCBE Governance-Gated Agent Loop")
    parser.add_argument("--task", type=str, help="Single task description")
    parser.add_argument("--file", type=str, help="Target file to evaluate/modify")
    parser.add_argument("--task-file", type=str, help="JSON file with batch tasks")
    parser.add_argument("--max-retries", type=int, default=15, help="Max retries per task")
    parser.add_argument("--max-hours", type=float, default=8.0, help="Max session duration in hours")
    parser.add_argument("--strict", action="store_true", default=True, help="Strict mode (critical = DENY)")
    parser.add_argument("--scan-only", action="store_true", help="Just scan a file, don't loop")
    args = parser.parse_args()

    repo_root = Path(".")
    start = time.time()

    # Scan-only mode: evaluate a file through the gate
    if args.scan_only and args.file:
        gate = GovernanceGate(strict=args.strict)
        code = Path(args.file).read_text(encoding="utf-8")
        result = gate.evaluate(code)
        print(gate.rejection_reason(result) if result["decision"] != "ALLOW" else f"ALLOW (H={result['h_score']:.4f})")
        return

    agent = GovernanceGatedAgent(
        repo_root=repo_root,
        max_retries=args.max_retries,
        max_hours=args.max_hours,
        strict=args.strict,
    )

    if args.task_file:
        with open(args.task_file) as f:
            tasks = json.load(f)
        results = agent.run_batch(tasks)
    elif args.task:
        result = agent.run_task(args.task, args.file)
        results = [result]
    elif args.file:
        result = agent.run_task(f"Evaluate and improve {args.file}", args.file)
        results = [result]
    else:
        parser.print_help()
        return

    print_summary(results, start)


if __name__ == "__main__":
    main()
