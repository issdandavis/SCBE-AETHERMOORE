"""
SCBE Defensive Mesh Kernel (Python wrapper layer)
=================================================

Purpose:
- Wrap browsing/extraction tasks in deterministic SCBE governance gates.
- Reuse existing antivirus + kernel gate logic from `agents/`.
- Provide Hugging Face friendly training rows from governance traces.

This is a user-space "AI kernel" abstraction, not an OS kernel.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse

from agents.antivirus_membrane import scan_text_for_threats, turnstile_action
from agents.kernel_antivirus_gate import evaluate_kernel_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _domain_allowed(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = (urlparse(url).hostname or "").lower()
    for domain in allowed_domains:
        d = (domain or "").strip().lower()
        if not d:
            continue
        if host == d or host.endswith("." + d):
            return True
    return False


def _forbidden_match(url: str, patterns: list[str]) -> str | None:
    for p in patterns:
        if not p:
            continue
        if re.search(p, url, flags=re.IGNORECASE):
            return p
    return None


@dataclass
class GovernedTask:
    task_id: str
    url: str
    selector: str
    fields: dict[str, str]
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernedJob:
    job_id: str
    goal: str
    allowed_domains: list[str]
    forbidden_patterns: list[str]
    allowed_fields: list[str]
    pii_rules: dict[str, str]
    max_depth: int = 2
    rate_limit_per_domain: int = 1
    created_at: str = field(default_factory=_utc_now)


@dataclass
class TaskGateResult:
    task_id: str
    decision: str
    action: str
    risk_score: float
    reasons: list[str]
    antivirus: dict[str, Any]
    kernel_gate: dict[str, Any]
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DefensiveMeshKernel:
    """
    Policy wrapper for manager/worker pipelines.
    """

    @staticmethod
    def from_job_spec(spec: dict[str, Any]) -> tuple[GovernedJob, list[GovernedTask]]:
        job_id = str(spec.get("job_id") or f"job-{_stable_hash(spec)[:10]}")
        goal = str(spec.get("goal") or spec.get("high_level_goal") or "unspecified-goal")
        allowed_domains = [str(x) for x in spec.get("allowed_domains", [])]
        forbidden_patterns = [str(x) for x in spec.get("forbidden_patterns", [])]
        allowed_fields = [str(x) for x in spec.get("allowed_fields", [])]
        pii_rules = {str(k): str(v) for k, v in (spec.get("pii_rules") or {}).items()}

        job = GovernedJob(
            job_id=job_id,
            goal=goal,
            allowed_domains=allowed_domains,
            forbidden_patterns=forbidden_patterns,
            allowed_fields=allowed_fields,
            pii_rules=pii_rules,
            max_depth=int(spec.get("max_depth", 2) or 2),
            rate_limit_per_domain=int(spec.get("rate_limit_per_domain", 1) or 1),
        )

        tasks: list[GovernedTask] = []
        for i, row in enumerate(spec.get("tasks", []), start=1):
            task_id = str(row.get("task_id") or f"{job_id}-task-{i:03d}")
            tasks.append(
                GovernedTask(
                    task_id=task_id,
                    url=str(row.get("url", "")),
                    selector=str(row.get("selector", "")),
                    fields={str(k): str(v) for k, v in (row.get("fields") or {}).items()},
                    actions=[str(x) for x in row.get("actions", [])],
                    metadata=(row.get("metadata") or {}),
                )
            )
        return job, tasks

    @staticmethod
    def gate_task(job: GovernedJob, task: GovernedTask, previous_antibody_load: float = 0.0) -> TaskGateResult:
        reasons: list[str] = []

        if not _domain_allowed(task.url, job.allowed_domains):
            reasons.append("domain not allowed")
            return TaskGateResult(
                task_id=task.task_id,
                decision="DENY",
                action="STOP",
                risk_score=1.0,
                reasons=reasons,
                antivirus={},
                kernel_gate={},
            )

        forbidden_hit = _forbidden_match(task.url, job.forbidden_patterns)
        if forbidden_hit:
            reasons.append(f"forbidden pattern matched: {forbidden_hit}")
            return TaskGateResult(
                task_id=task.task_id,
                decision="DENY",
                action="STOP",
                risk_score=1.0,
                reasons=reasons,
                antivirus={},
                kernel_gate={},
            )

        scan_input = json.dumps(
            {
                "url": task.url,
                "selector": task.selector,
                "fields": task.fields,
                "actions": task.actions,
                "metadata": task.metadata,
            },
            ensure_ascii=False,
        )
        threat = scan_text_for_threats(scan_input)
        browser_turnstile = turnstile_action("browser", threat)

        k_event = {
            "host": "scbe-ai-kernel",
            "pid": 0,
            "process_name": "playwright_worker",
            "operation": "network_connect",
            "target": task.url,
            "command_line": " ".join(task.actions),
            "parent_process": "manager_agent",
            "signer_trusted": True,
            "hash_sha256": hashlib.sha256(scan_input.encode("utf-8")).hexdigest(),
            "geometry_norm": float(threat.risk_score),
            "metadata": {"task_id": task.task_id},
        }
        kernel_gate = evaluate_kernel_event(k_event, previous_antibody_load=previous_antibody_load)
        kernel_gate_dict = kernel_gate.to_dict()

        decision = "ALLOW"
        action = "ALLOW"

        if kernel_gate_dict["kernel_action"] in {"KILL", "QUARANTINE", "HONEYPOT"}:
            decision = "QUARANTINE"
            action = kernel_gate_dict["kernel_action"]
            reasons.append("kernel gate elevated risk")
        elif browser_turnstile in {"HONEYPOT", "ISOLATE"}:
            decision = "QUARANTINE"
            action = browser_turnstile
            reasons.append(f"browser turnstile action={browser_turnstile}")
        elif browser_turnstile == "HOLD":
            decision = "ESCALATE"
            action = "HOLD"
            reasons.append("browser turnstile hold")
        else:
            reasons.append("passed mesh gate")

        reasons.extend(threat.reasons)

        return TaskGateResult(
            task_id=task.task_id,
            decision=decision,
            action=action,
            risk_score=float(threat.risk_score),
            reasons=reasons,
            antivirus={
                **threat.to_dict(),
                "browser_turnstile_action": browser_turnstile,
            },
            kernel_gate=kernel_gate_dict,
        )

    @staticmethod
    def sanitize_items(
        items: list[dict[str, Any]],
        *,
        allowed_fields: list[str],
        pii_rules: dict[str, str],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        allowed = set(allowed_fields) if allowed_fields else set()
        for row in items:
            clean: dict[str, Any] = {}
            for k, v in row.items():
                if allowed and k not in allowed:
                    continue
                clean[k] = v
            for key, rule in pii_rules.items():
                if key not in clean:
                    continue
                if rule == "drop":
                    clean.pop(key, None)
                elif rule == "mask":
                    clean[key] = "***"
            out.append(clean)
        return out

    @staticmethod
    def review_output(job: GovernedJob, items: list[dict[str, Any]]) -> dict[str, Any]:
        disallowed_fields = set()
        allowed = set(job.allowed_fields) if job.allowed_fields else set()
        for item in items:
            for key in item.keys():
                if allowed and key not in allowed:
                    disallowed_fields.add(key)
        if disallowed_fields:
            return {
                "status": "fail",
                "reason": f"disallowed fields present: {sorted(disallowed_fields)}",
            }
        return {"status": "ok", "item_count": len(items)}

    @staticmethod
    def build_hf_training_row(
        *,
        idx: int,
        job: GovernedJob,
        task: GovernedTask,
        gate: TaskGateResult,
    ) -> dict[str, Any]:
        instruction = (
            f"Given SCBE job '{job.job_id}' and browser task '{task.task_id}', "
            f"choose the governance outcome for URL '{task.url}'."
        )
        response = json.dumps(
            {
                "decision": gate.decision,
                "action": gate.action,
                "risk_score": round(gate.risk_score, 4),
                "reasons": gate.reasons,
                "antivirus_verdict": gate.antivirus.get("verdict"),
                "kernel_action": gate.kernel_gate.get("kernel_action"),
            },
            ensure_ascii=False,
        )
        return {
            "id": f"mesh-{idx:04d}",
            "category": "safety",
            "instruction": instruction,
            "response": response,
            "metadata": {
                "source": "scbe_aethermoore",
                "version": "3.3.0",
                "author": "Issac Davis",
                "origin": "defensive_mesh_governance",
                "job_id": job.job_id,
                "task_id": task.task_id,
                "risk_score": round(gate.risk_score, 4),
                "decision": gate.decision,
                "action": gate.action,
            },
        }

