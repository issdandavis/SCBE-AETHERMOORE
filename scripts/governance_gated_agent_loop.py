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
import difflib
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
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

    def __init__(self, repo_root: Path, strict: bool = True):
        self.repo_root = repo_root
        self.strict = strict
        self.history: list[dict] = []

    def evaluate(self, code: str, context: dict | None = None) -> dict:
        """Run code-derived analysis and route the final decision through canonical governance."""
        risks = self._scan_risks(code)
        tongue_profile = self._compute_tongue_profile(code)
        d_h = self._compute_distance(risks, tongue_profile)
        pd = self._compute_phase_deviation(tongue_profile)

        # Keep the local harmonic diagnostics for explainability and training metadata.
        h_score = 1.0 / (1.0 + PHI * d_h + 2.0 * pd)
        d_star = min(d_h, 5.0)
        theoretical_cost = PI ** (PHI * d_star)
        governance_scalars = self._compute_governance_scalars(risks, tongue_profile, d_h, pd, theoretical_cost)
        canonical = self._canonical_decide(code, governance_scalars, context or {})

        decision = canonical["decision"]
        reason_codes = canonical["reason_codes"]

        # Strict mode still fail-closes on critical local risk signatures.
        if self.strict and risks.get("critical") and decision != "DENY":
            decision = "DENY"
            reason_codes = [*reason_codes, "LOCAL_CRITICAL_RISK"]

        result = {
            "decision": decision,
            "h_score": round(h_score, 6),
            "theoretical_cost": round(theoretical_cost, 4),
            "distance": round(d_h, 6),
            "phase_deviation": round(pd, 6),
            "risks": risks,
            "tongue_profile": tongue_profile,
            "reason_codes": reason_codes,
            "governance_scalars": canonical["governance_scalars"],
            "proof": canonical["proof"],
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

    def _compute_governance_scalars(
        self,
        risks: dict[str, list[tuple[str, int]]],
        profile: dict[str, float],
        d_h: float,
        pd: float,
        theoretical_cost: float,
    ) -> dict[str, float]:
        """Project code heuristics into the canonical scalar space consumed by DECIDE()."""
        critical = len(risks.get("critical", []))
        high = len(risks.get("high", []))
        medium = len(risks.get("medium", []))
        low = len(risks.get("low", []))
        null_count = sum(1 for value in profile.values() if value < 0.05)

        conflict = min(1.0, critical * 0.7 + high * 0.2 + medium * 0.08 + low * 0.02)
        drift = min(1.0, pd * 0.6 + null_count * 0.06 + medium * 0.03 + low * 0.01)
        wall_cost = min(1.0, d_h / 5.0 + (1.0 if theoretical_cost > 25 else theoretical_cost / 25.0) * 0.25)

        coherence_penalty = min(0.95, pd * 0.7 + conflict * 0.5 + drift * 0.25)
        coherence = max(0.0, min(1.0, 1.0 - coherence_penalty))

        return {
            "mm_coherence": round(coherence, 6),
            "mm_conflict": round(conflict, 6),
            "mm_drift": round(drift, 6),
            "wall_cost": round(wall_cost, 6),
        }

    def _canonical_decide(self, code: str, scalars: dict[str, float], context: dict[str, Any]) -> dict[str, Any]:
        """Delegate the final decision to the canonical offline governance engine."""
        npx = shutil.which("npx.cmd" if os.name == "nt" else "npx") or ("npx.cmd" if os.name == "nt" else "npx")
        payload = {
            "action": context.get("action", "code.patch.proposal"),
            "subject": context.get("subject", "governance-gated-agent"),
            "object": context.get("object", context.get("target_file", "candidate")),
            "payload_hash_hex": hashlib.sha512(code.encode("utf-8")).hexdigest(),
            "scalars": scalars,
            "manifest_stale": bool(context.get("manifest_stale", False)),
        }
        try:
            result = subprocess.run(
                [npx, "ts-node", "--transpile-only", "scripts/governance/offline_decide_cli.ts"],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.repo_root,
                check=False,
            )
        except Exception as exc:
            return {
                "decision": "DENY",
                "reason_codes": [f"GOVERNANCE_ADAPTER_ERROR:{type(exc).__name__}"],
                "governance_scalars": {**scalars, "trust_level": "T4"},
                "proof": {"adapter_error": str(exc)},
            }

        if result.returncode != 0:
            stderr = (result.stderr or "unknown error").strip().replace("\n", " ")
            return {
                "decision": "DENY",
                "reason_codes": [f"GOVERNANCE_ADAPTER_FAILED:{stderr[:160]}"],
                "governance_scalars": {**scalars, "trust_level": "T4"},
                "proof": {"adapter_error": stderr[:500]},
            }

        data = json.loads(result.stdout)
        return {
            "decision": data["decision"],
            "reason_codes": data.get("reason_codes", []),
            "governance_scalars": data.get("governance_scalars", {**scalars, "trust_level": "T0"}),
            "proof": data.get("proof", {}),
        }

    def rejection_reason(self, result: dict) -> str:
        """Generate human/AI-readable rejection explanation."""
        lines = [f"GOVERNANCE DECISION: {result['decision']}"]
        lines.append(f"Safety score: {result['h_score']:.4f} (1.0 = safe, 0.0 = blocked)")
        lines.append(f"Theoretical cost: {result['theoretical_cost']:.2f}x")
        lines.append(f"Distance from safe center: {result['distance']:.4f}")
        if result.get("reason_codes"):
            lines.append(f"Canonical reasons: {', '.join(result['reason_codes'])}")

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

        failed_severities = [s.upper() for s in ["critical", "high", "medium", "low"] if result["risks"].get(s)]
        if failed_severities:
            lines.append(f"\nTo pass: fix all {' + '.join(failed_severities)} risks listed above.")
        else:
            lines.append("\nNo pattern-based risks found. Decision based on tongue profile and distance.")
        return "\n".join(lines)


# ── Code Runner ─────────────────────────────────────────────────────

class CodeRunner:
    """Execute code changes and run tests."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def _command_args(self, command: str | list[str]) -> list[str]:
        if isinstance(command, list):
            return command
        return shlex.split(command, posix=False)

    def run_tests(self, test_cmd: str | list[str] = "python -m pytest tests/ -x -q --tb=short", timeout: int = 120) -> dict:
        """Run test suite and return results."""
        try:
            result = subprocess.run(
                self._command_args(test_cmd), capture_output=True, text=True,
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
        cmd: list[str] = ["python", "-m", "flake8", "--max-line-length=120", "--count"]
        if files:
            cmd.extend(files)
        else:
            cmd.append("src/")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
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
                ["npx", "tsc", "--noEmit"],
                capture_output=True, text=True,
                timeout=timeout, cwd=self.repo_root,
            )
            return {"passed": result.returncode == 0, "output": result.stdout[-1000:]}
        except Exception as e:
            return {"passed": False, "output": str(e)}

    def validate_candidate(
        self,
        target_file: str,
        code: str,
        test_cmd: str | list[str] = "python -m pytest tests/ -x -q --tb=short",
        timeout: int = 120,
    ) -> dict:
        """Apply a candidate to the target file, test it, and restore on failure."""
        target_path = self.repo_root / target_file
        original_exists = target_path.exists()
        original_text = target_path.read_text(encoding="utf-8") if original_exists else None
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            target_path.write_text(code, encoding="utf-8")
            test_result = self.run_tests(test_cmd=test_cmd, timeout=timeout)
            if test_result["passed"]:
                return {"applied": True, "restored": False, "test_result": test_result}
        except Exception as exc:
            test_result = {"passed": False, "stdout": "", "stderr": str(exc), "returncode": -1}
        if original_exists and original_text is not None:
            target_path.write_text(original_text, encoding="utf-8")
        elif target_path.exists():
            target_path.unlink()
        return {"applied": False, "restored": True, "test_result": test_result}


# ── Training Data Logger ────────────────────────────────────────────

class TrainingLogger:
    """Log every governance evaluation as training data."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sft_file = output_dir / "governance_sft.jsonl"
        self.dpo_file = output_dir / "governance_dpo.jsonl"
        self.session_log = output_dir / "session_log.jsonl"
        self.attempt_log = output_dir / "governance_loop_attempts.jsonl"
        self.metrics_log = output_dir / "governance_loop_metrics.jsonl"

    def _append_jsonl(self, path: Path, record: dict):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

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
        self._append_jsonl(self.sft_file, record)

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
        self._append_jsonl(self.dpo_file, record)

    def log_session_event(self, event: str, data: dict | None = None):
        """Log session lifecycle events."""
        record = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        self._append_jsonl(self.session_log, record)

    def log_attempt(self, record: dict):
        """Log per-attempt telemetry for UPG loop metrics."""
        self._append_jsonl(self.attempt_log, record)

    def log_metrics(self, record: dict):
        """Log derived per-task loop metrics."""
        self._append_jsonl(self.metrics_log, record)


def make_task_id(task: str, target_file: str | None) -> str:
    """Create a stable identifier for a task/file pair."""
    payload = f"{task}|{target_file or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def hash_candidate(code: str) -> str:
    """Return a stable content hash for a proposal."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def count_risks(risks: dict[str, list[tuple[str, int]]]) -> dict[str, int]:
    """Collapse raw risk findings into severity counts."""
    return {severity: len(items) for severity, items in risks.items()}


def weighted_risk_score(risk_counts: dict[str, int]) -> int:
    """Weighted severity score used by damping/adaptation summaries."""
    weights = {"critical": 8, "high": 4, "medium": 2, "low": 1}
    return sum(weights.get(severity, 0) * count for severity, count in risk_counts.items())


def diff_ratio(previous_code: str | None, current_code: str | None) -> float:
    """Normalized structural delta between two proposals."""
    if previous_code is None or current_code is None:
        return 1.0 if previous_code != current_code else 0.0
    similarity = difflib.SequenceMatcher(a=previous_code, b=current_code).ratio()
    return round(1.0 - similarity, 6)


def summarize_attempts(task_id: str, task: str, target_file: str | None, attempts: list[dict], final_status: str) -> dict:
    """Compute session-level damping/adaptation metrics from attempt telemetry."""
    attempt_count = len(attempts)
    repeated_hashes = 0
    repeated_denials_without_reason_change = 0
    total_denials = 0
    low_delta_repeat_count = 0
    targeted_fix_hits = 0
    targeted_fix_opportunities = 0
    tests_run = 0
    approval_attempt = None
    approval_elapsed_sec = None

    previous_attempt = None
    repeated_reason_streak = 1
    max_reason_persistence = 1 if attempts else 0
    risk_scores = [attempt["weighted_risk_score"] for attempt in attempts]
    risk_gradient = 0 if attempt_count < 2 else risk_scores[-1] - risk_scores[0]
    improvement_gains: list[int] = []
    reason_seen: dict[str, list[int]] = {}
    active_reasons: set[str] = set()
    reintroduced_reason_count = 0

    for attempt in attempts:
        tests_run += 1 if attempt["test_passed"] else 0
        reasons = tuple(sorted(set(attempt["reason_codes"])))
        for reason in reasons:
            history = reason_seen.setdefault(reason, [])
            if history and reason not in active_reasons:
                reintroduced_reason_count += 1
            history.append(attempt["attempt_index"])
        active_reasons = set(reasons)

        if previous_attempt is not None:
            if attempt["candidate_hash"] == previous_attempt["candidate_hash"]:
                repeated_hashes += 1
            if attempt["retry_delta"] < 0.03 and reasons == tuple(sorted(set(previous_attempt["reason_codes"]))):
                low_delta_repeat_count += 1
            if reasons == tuple(sorted(set(previous_attempt["reason_codes"]))):
                repeated_reason_streak += 1
            else:
                repeated_reason_streak = 1
            max_reason_persistence = max(max_reason_persistence, repeated_reason_streak)

            if previous_attempt["decision"] != "ALLOW":
                targeted_fix_opportunities += 1
                if attempt["retry_delta"] >= 0.03 and (
                    attempt["weighted_risk_score"] < previous_attempt["weighted_risk_score"]
                    or len(reasons) < len(set(previous_attempt["reason_codes"]))
                ):
                    targeted_fix_hits += 1

            improvement_gains.append(previous_attempt["weighted_risk_score"] - attempt["weighted_risk_score"])

        if attempt["decision"] != "ALLOW":
            total_denials += 1
            if previous_attempt is not None and previous_attempt["decision"] != "ALLOW":
                if reasons == tuple(sorted(set(previous_attempt["reason_codes"]))):
                    repeated_denials_without_reason_change += 1

        if attempt["approved_after_attempt"] and approval_attempt is None:
            approval_attempt = attempt["attempt_index"]
            approval_elapsed_sec = attempt["elapsed_sec"]

        previous_attempt = attempt

    average_retry_delta = round(
        sum(attempt["retry_delta"] for attempt in attempts[1:]) / max(attempt_count - 1, 1),
        6,
    ) if attempt_count > 1 else 0.0

    improvement_decay = None
    if len(improvement_gains) >= 2:
        gain_deltas = [improvement_gains[idx + 1] - improvement_gains[idx] for idx in range(len(improvement_gains) - 1)]
        improvement_decay = round(sum(gain_deltas) / len(gain_deltas), 6)

    reason_resolution_velocity = {
        reason: indexes[-1] - indexes[0] + 1
        for reason, indexes in reason_seen.items()
        if indexes
    }

    reason_frequency: dict[str, int] = {}
    for attempt in attempts:
        for reason in set(attempt["reason_codes"]):
            reason_frequency[reason] = reason_frequency.get(reason, 0) + 1
    dominant_reason_codes = [
        reason for reason, _count in sorted(reason_frequency.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]

    final_attempt = attempts[-1] if attempts else None
    post_approval_integrity = bool(final_attempt and final_attempt["approved_after_attempt"] and final_attempt["test_passed"])
    reconstruction_quality = bool(
        post_approval_integrity
        and final_attempt is not None
        and not any(reason in set(final_attempt["reason_codes"]) for reason in dominant_reason_codes)
    )

    return {
        "task_id": task_id,
        "task": task,
        "target_file": target_file,
        "attempt_count": attempt_count,
        "final_status": final_status,
        "primary_metrics": {
            "average_retry_delta": average_retry_delta,
            "max_reason_code_persistence": max_reason_persistence,
            "risk_gradient": risk_gradient,
            "approval_efficiency": {
                "attempts_to_approval": approval_attempt,
                "wall_time_to_approval_sec": approval_elapsed_sec,
                "tests_run_to_approval": tests_run if approval_attempt is not None else None,
            },
            "post_approval_integrity": post_approval_integrity,
        },
        "damping_metrics": {
            "structural_repetition_rate": round(repeated_hashes / max(attempt_count - 1, 1), 6) if attempt_count > 1 else 0.0,
            "denial_fatigue_index": round(repeated_denials_without_reason_change / max(total_denials, 1), 6) if total_denials else 0.0,
            "improvement_decay": improvement_decay,
            "context_rot_proxy": {
                "reintroduced_reason_count": reintroduced_reason_count,
                "low_delta_repeat_count": low_delta_repeat_count,
            },
        },
        "adaptation_metrics": {
            "targeted_fix_ratio": round(targeted_fix_hits / max(targeted_fix_opportunities, 1), 6) if targeted_fix_opportunities else 0.0,
            "reason_resolution_velocity": reason_resolution_velocity,
            "cross_task_carryover": None,
            "reconstruction_quality": reconstruction_quality,
        },
    }


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
        self.gate = GovernanceGate(repo_root=repo_root, strict=strict)
        self.runner = CodeRunner(repo_root)
        self.logger = TrainingLogger(repo_root / "training-data" / "governance_agent")
        self.repo_root = repo_root
        self.max_retries = max_retries
        self.max_hours = max_hours
        self.start_time = time.time()

    def run_task(self, task: str, target_file: str | None = None) -> dict:
        """Execute a task through the governance-gated loop."""
        task_id = make_task_id(task, target_file)
        self.logger.log_session_event("task_start", {"task_id": task_id, "task": task, "target": target_file})
        print(f"\n{'='*60}")
        print(f"TASK: {task}")
        print(f"Max retries: {self.max_retries} | Max hours: {self.max_hours}")
        print(f"{'='*60}\n")

        attempt = 0
        last_rejection = None
        attempt_records: list[dict[str, Any]] = []
        baseline_code = None
        if target_file:
            target_path = self.repo_root / target_file
            if target_path.exists():
                baseline_code = target_path.read_text(encoding="utf-8")

        while attempt < self.max_retries:
            # Check time limit
            elapsed_hours = (time.time() - self.start_time) / 3600
            if elapsed_hours > self.max_hours:
                print(f"\nTIME LIMIT: {elapsed_hours:.1f}h exceeded {self.max_hours}h cap")
                self.logger.log_session_event("time_limit", {"task_id": task_id, "hours": elapsed_hours})
                metrics = summarize_attempts(task_id, task, target_file, attempt_records, final_status="time_limit")
                self.logger.log_metrics(metrics)
                return {"success": False, "reason": "time_limit", "attempts": attempt}

            attempt += 1
            print(f"\n--- Attempt {attempt}/{self.max_retries} ---")
            attempt_started = time.time()

            # Generate code (in a real system, this calls the HF model)
            code = self._generate_code(task, target_file, last_rejection)
            if not code:
                print("  No code generated, skipping")
                continue

            # Governance gate evaluation
            gate_result = self.gate.evaluate(code, {"target_file": target_file})
            decision = gate_result["decision"]
            candidate_hash = hash_candidate(code)
            risk_counts = count_risks(gate_result["risks"])
            previous_code = attempt_records[-1]["candidate_code"] if attempt_records else baseline_code
            retry_delta = diff_ratio(previous_code, code)
            attempt_record = {
                "task_id": task_id,
                "attempt_index": attempt,
                "candidate_hash": candidate_hash,
                "decision": decision,
                "reason_codes": gate_result["reason_codes"],
                "risk_counts": risk_counts,
                "test_passed": False,
                "elapsed_sec": round(time.time() - attempt_started, 6),
                "changed_target": baseline_code is None or code != baseline_code,
                "approved_after_attempt": False,
                "retry_delta": retry_delta,
                "weighted_risk_score": weighted_risk_score(risk_counts),
                "candidate_code": code,
            }

            print(f"  H-score: {gate_result['h_score']:.4f}")
            print(f"  Cost: {gate_result['theoretical_cost']:.2f}x")
            print(f"  Decision: {decision}")

            if decision == "ALLOW":
                if not target_file:
                    last_rejection = "Canonical governance approved the proposal, but execution requires --file so the candidate can be applied and tested."
                    self.logger.log_rejection(task, code, last_rejection)
                    print("  ALLOW reached, but no target file was provided for execution")
                    continue

                print(f"\n  APPROVED on attempt {attempt}; applying candidate to {target_file}")
                validation = self.runner.validate_candidate(target_file, code)
                test_result = validation["test_result"]
                attempt_record["test_passed"] = bool(test_result["passed"])
                attempt_record["elapsed_sec"] = round(time.time() - attempt_started, 6)
                if validation["applied"] and test_result["passed"]:
                    print("  Tests PASSED")
                    attempt_record["approved_after_attempt"] = True
                    attempt_records.append(attempt_record)
                    self.logger.log_attempt({key: value for key, value in attempt_record.items() if key != "candidate_code"})
                    self.logger.log_approval(task, code, gate_result)
                    self.logger.log_session_event("approved", {
                        "task_id": task_id,
                        "attempt": attempt,
                        "h_score": gate_result["h_score"],
                        "target_file": target_file,
                    })
                    self.logger.log_session_event("tests_passed", {"task_id": task_id, "attempt": attempt})
                    metrics = summarize_attempts(task_id, task, target_file, attempt_records, final_status="approved")
                    self.logger.log_metrics(metrics)
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
                    attempt_records.append(attempt_record)
                    self.logger.log_attempt({key: value for key, value in attempt_record.items() if key != "candidate_code"})
                    self.logger.log_rejection(task, code, last_rejection)
                    continue

            else:
                # Rejected — log and prepare retry context
                rejection = self.gate.rejection_reason(gate_result)
                print(f"  REJECTED: {decision}")
                for severity in ["critical", "high"]:
                    for label, line in gate_result["risks"].get(severity, []):
                        print(f"    [{severity}] Line {line}: {label}")

                attempt_record["elapsed_sec"] = round(time.time() - attempt_started, 6)
                attempt_records.append(attempt_record)
                self.logger.log_attempt({key: value for key, value in attempt_record.items() if key != "candidate_code"})
                self.logger.log_rejection(task, code, rejection)
                last_rejection = rejection

        print(f"\nFAILED after {attempt} attempts")
        self.logger.log_session_event("max_retries", {"task_id": task_id, "attempts": attempt})
        metrics = summarize_attempts(task_id, task, target_file, attempt_records, final_status="max_retries")
        self.logger.log_metrics(metrics)
        return {"success": False, "reason": "max_retries", "attempts": attempt}

    def _generate_code(self, task: str, target_file: str | None, last_rejection: str | None) -> str | None:
        """Generate code for the task. Uses HF model if available, falls back to file read."""
        target_path = self.repo_root / target_file if target_file else None
        current_code = None
        if target_path and target_path.exists():
            current_code = target_path.read_text(encoding="utf-8")

        # Try HF model via Polly Sandbox API
        try:
            import httpx

            prompt = f"Write Python code for this task: {task}"
            if current_code:
                prompt += f"\n\nCurrent file ({target_file}):\n```python\n{current_code[:4000]}\n```"
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

        # Fallback: use the current file as a baseline candidate.
        return current_code

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
    print(f"  Attempt telemetry: training-data/governance_agent/governance_loop_attempts.jsonl")
    print(f"  Loop metrics: training-data/governance_agent/governance_loop_metrics.jsonl")


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
        gate = GovernanceGate(repo_root=repo_root, strict=args.strict)
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
