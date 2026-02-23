#!/usr/bin/env python3
"""SCBE MIN MCP server stub.

This server implements a minimal MCP contract for:
- task orchestration
- headless browser run stubs
- security scanning gates
- resources and resource templates

The implementation is deterministic and inspectable, intended as a launch point
for real browser workers and antivirus integrations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

WALL_FORMULA = "H(d*,R) = R · pi^(phi · d*)"
PROTOCOL_VERSION = "2024-11-05"


@dataclass
class RpcError(Exception):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class ScbeMinServer:
    def __init__(
        self,
        telemetry_path: Optional[Path] = None,
        enable_telemetry: bool = True,
    ) -> None:
        self.server_name = "scbe-min"
        self.server_version = "0.1.0"
        self.kernel_version = "scbe-min-mcp-0.1.0"
        self.enable_telemetry = enable_telemetry

        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.runs: Dict[str, Dict[str, Any]] = {}
        self.artifacts: Dict[str, Dict[str, Any]] = {}

        self.security_policy = {
            "allow_threshold": 0.35,
            "deny_threshold": 0.75,
            "max_parallel_tasks": 16,
            "antivirus_gate": "enabled",
            "notes": [
                "Deny high-risk targets before execution.",
                "Quarantine medium-risk targets with full logging.",
                "Hook external antivirus scanner before task completion.",
            ],
        }

        self.signatures = {
            "signature_set": "scbe-min-signatures-2026.02",
            "indicators": [
                "phish",
                "malware",
                "trojan",
                "credential-harvest",
                "crypto-drainer",
            ],
            "updated_utc": self._now_iso(),
        }

        repo_root = Path(__file__).resolve().parents[3]
        default_telemetry_path = repo_root / "artifacts" / "scbe_min" / "telemetry" / "events.jsonl"
        self.telemetry_path = telemetry_path or default_telemetry_path
        if self.enable_telemetry:
            self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)

    def _now_iso(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")

    def _queue_summary(self) -> Dict[str, Any]:
        queued = sum(1 for t in self.tasks.values() if t.get("status") == "queued")
        running = sum(1 for r in self.runs.values() if r.get("status") == "running")
        blocked = sum(1 for t in self.tasks.values() if t.get("status") == "blocked")
        completed = sum(1 for r in self.runs.values() if r.get("status") == "completed")
        return {
            "queued": queued,
            "running": running,
            "blocked": blocked,
            "completed": completed,
            "tasks_total": len(self.tasks),
            "runs_total": len(self.runs),
        }

    def _append_telemetry_event(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        state_vector: Dict[str, Any],
        decision_record: Dict[str, Any],
        target_ref: str,
    ) -> None:
        if not self.enable_telemetry:
            return

        event = {
            "dataset": "scbe_min_browser_telemetry",
            "created_at_utc": self._now_iso(),
            "event_type": tool_name,
            "target_ref": target_ref,
            "payload": payload,
            "state_vector": state_vector,
            "decision_record": decision_record,
        }

        try:
            with self.telemetry_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, sort_keys=True) + "\n")
        except Exception:
            # Telemetry write failure should never block governance decisions.
            return

    @staticmethod
    def _percentile(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = (len(ordered) - 1) * p
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            return ordered[lo]
        weight = idx - lo
        return ordered[lo] * (1 - weight) + ordered[hi] * weight

    @staticmethod
    def _coerce_point(value: Any) -> Optional[Tuple[float, float]]:
        if not isinstance(value, dict):
            return None
        x = value.get("x")
        y = value.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        return float(x), float(y)

    def _summarize_action_diagnostics(self, action_diagnostics: Any) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "events_total": 0,
            "click_events": 0,
            "click_metrics": {
                "sample_count": 0,
                "mean_offset_px": 0.0,
                "p95_offset_px": 0.0,
                "max_offset_px": 0.0,
                "high_offset_count": 0,
                "high_offset_threshold_px": 16.0,
            },
            "recommendations": [],
        }

        if not isinstance(action_diagnostics, list):
            summary["recommendations"].append("No action_diagnostics array provided")
            return summary

        summary["events_total"] = len(action_diagnostics)
        click_offsets: List[float] = []
        high_offset_threshold = 16.0

        for item in action_diagnostics:
            if not isinstance(item, dict):
                continue
            action = str(item.get("action", "")).strip().lower()
            if action != "click":
                continue
            summary["click_events"] += 1

            intended = self._coerce_point(item.get("intended"))
            actual = self._coerce_point(item.get("actual"))
            if intended is None or actual is None:
                continue

            dx = actual[0] - intended[0]
            dy = actual[1] - intended[1]
            click_offsets.append(round(math.sqrt((dx * dx) + (dy * dy)), 4))

        if click_offsets:
            mean_offset = round(sum(click_offsets) / len(click_offsets), 4)
            p95_offset = round(self._percentile(click_offsets, 0.95), 4)
            max_offset = round(max(click_offsets), 4)
            high_count = sum(1 for x in click_offsets if x > high_offset_threshold)
            summary["click_metrics"] = {
                "sample_count": len(click_offsets),
                "mean_offset_px": mean_offset,
                "p95_offset_px": p95_offset,
                "max_offset_px": max_offset,
                "high_offset_count": high_count,
                "high_offset_threshold_px": high_offset_threshold,
            }

            if p95_offset > high_offset_threshold:
                summary["recommendations"].append(
                    "High click drift detected: add pre-click stabilize wait and element re-center checks"
                )
                summary["recommendations"].append(
                    "Capture viewport scale/zoom and devicePixelRatio for click correction"
                )
            elif p95_offset > 8.0:
                summary["recommendations"].append(
                    "Moderate click drift: verify selector specificity and scroll-to-center before click"
                )
            else:
                summary["recommendations"].append("Click precision within expected bounds")
        else:
            summary["recommendations"].append(
                "No usable click coordinate pairs; include intended/actual points to learn click calibration"
            )

        return summary

    def _state_vector(self, objective: str, lane: str) -> Dict[str, Any]:
        return {
            "objective": objective,
            "lane": lane,
            "kernel_version": self.kernel_version,
            "canonical_wall_formula": WALL_FORMULA,
            "queue": self._queue_summary(),
            "timestamp_utc": self._now_iso(),
        }

    def _decision_from_risk(self, risk: float) -> str:
        if risk >= self.security_policy["deny_threshold"]:
            return "DENY"
        if risk >= self.security_policy["allow_threshold"]:
            return "QUARANTINE"
        return "ALLOW"

    def _scan_target(self, target: str) -> Dict[str, Any]:
        parsed = urlparse(target if "://" in target else f"https://{target}")
        host = parsed.netloc.lower() or parsed.path.lower()
        scheme = parsed.scheme.lower() or "https"

        risk = 0.10
        reasons: List[str] = ["baseline risk"]

        suspicious_terms = [
            "phish",
            "malware",
            "trojan",
            "drainer",
            "steal",
            "credential",
            "crack",
            "warez",
            "botnet",
        ]

        if any(term in host for term in suspicious_terms):
            risk = max(risk, 0.92)
            reasons.append("host contains known malicious indicators")

        if scheme == "http":
            risk = max(risk, 0.42)
            reasons.append("non-TLS transport")

        host_parts = host.split(".")
        if host and len(host_parts) <= 1:
            risk = max(risk, 0.55)
            reasons.append("non-qualified host")

        if all(part.isdigit() for part in host_parts if part):
            risk = max(risk, 0.64)
            reasons.append("direct IP target")

        decision = self._decision_from_risk(risk)
        return {
            "target": target,
            "normalized_host": host,
            "risk": round(risk, 4),
            "decision": decision,
            "reasons": reasons,
        }

    def _scan_artifact(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(artifact, sort_keys=True).lower()
        risk = 0.08
        reasons = ["artifact baseline scan"]

        indicators = [
            "password",
            "seed phrase",
            "private key",
            "wallet",
            "install this extension",
            "urgent verify account",
        ]
        if any(token in payload for token in indicators):
            risk = max(risk, 0.78)
            reasons.append("sensitive credential or phishing indicator in artifact")

        decision = self._decision_from_risk(risk)
        return {
            "artifact_id": artifact.get("artifact_id"),
            "risk": round(risk, 4),
            "decision": decision,
            "reasons": reasons,
        }

    def _decision_record(
        self,
        decision: str,
        decision_reason: str,
        risk: float,
        target_ref: str,
        profile_id: str = "default",
        job_id: str = "none",
        agent_id: str = "scbe-min-agent",
        session_id: str = "local-session",
    ) -> Dict[str, Any]:
        seed = f"{decision}|{target_ref}|{risk}|{self._now_iso()}"
        trace_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        d_star = round(risk * 2.0, 4)
        coherence = round(max(0.0, 1.0 - risk), 4)
        verification_score = round((coherence + (1.0 - abs(0.5 - risk))) / 2.0, 4)

        return {
            "schema_version": "1.0.0",
            "decision_id": str(uuid.uuid4()),
            "timestamp_utc": self._now_iso(),
            "kernel_version": self.kernel_version,
            "profile_id": profile_id,
            "job_id": job_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "decision": decision,
            "decision_reason": decision_reason,
            "risk_tier": "REFLEX" if risk < 0.7 else "DELIBERATION",
            "metrics": {
                "risk": round(risk, 4),
                "d_star": d_star,
                "coherence": coherence,
                "verification_score": verification_score,
            },
            "capability": {
                "required": True,
                "present": True,
                "valid": decision != "DENY",
                "token_id": None,
                "reason": "antivirus_gate=enabled",
                "expires_at_epoch": None,
            },
            "trace_hash": trace_hash,
            "verification": {
                "score": verification_score,
                "passed_checks": 3 if decision == "ALLOW" else 2 if decision == "QUARANTINE" else 1,
                "total_checks": 3,
                "checks": [
                    {"name": "target_scan", "ok": decision != "DENY"},
                    {"name": "policy_thresholds", "ok": True},
                    {"name": "antivirus_gate", "ok": decision != "DENY"},
                ],
            },
        }

    def _tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "task.submit",
                "description": "Submit a web automation task with security gate.",
                "inputSchema": {
                    "type": "object",
                    "required": ["target"],
                    "properties": {
                        "target": {"type": "string"},
                        "task_type": {"type": "string", "default": "web"},
                        "profile_id": {"type": "string", "default": "default"},
                    },
                },
            },
            {
                "name": "task.status",
                "description": "Fetch status for a submitted task.",
                "inputSchema": {
                    "type": "object",
                    "required": ["task_id"],
                    "properties": {"task_id": {"type": "string"}},
                },
            },
            {
                "name": "browser.run_headless",
                "description": "Execute a headless browser run with policy gating.",
                "inputSchema": {
                    "type": "object",
                    "required": ["target"],
                    "properties": {
                        "target": {"type": "string"},
                        "max_steps": {"type": "integer", "default": 20},
                        "profile_id": {"type": "string", "default": "default"},
                        "action_diagnostics": {
                            "type": "array",
                            "description": "Optional step diagnostics for calibration learning.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string"},
                                    "selector": {"type": "string"},
                                    "intended": {
                                        "type": "object",
                                        "properties": {
                                            "x": {"type": "number"},
                                            "y": {"type": "number"},
                                        },
                                    },
                                    "actual": {
                                        "type": "object",
                                        "properties": {
                                            "x": {"type": "number"},
                                            "y": {"type": "number"},
                                        },
                                    },
                                    "ok": {"type": "boolean"},
                                    "error": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            {
                "name": "browser.capture_artifact",
                "description": "Capture run artifact and register for scanning.",
                "inputSchema": {
                    "type": "object",
                    "required": ["run_id"],
                    "properties": {
                        "run_id": {"type": "string"},
                        "artifact_type": {
                            "type": "string",
                            "enum": ["dom_text", "screenshot_manifest", "network_summary"],
                            "default": "dom_text",
                        },
                    },
                },
            },
            {
                "name": "security.scan_target",
                "description": "Scan target before execution and classify ALLOW/QUARANTINE/DENY.",
                "inputSchema": {
                    "type": "object",
                    "required": ["target"],
                    "properties": {"target": {"type": "string"}},
                },
            },
            {
                "name": "security.scan_artifact",
                "description": "Scan collected artifact content using baseline signatures.",
                "inputSchema": {
                    "type": "object",
                    "required": ["artifact_id"],
                    "properties": {"artifact_id": {"type": "string"}},
                },
            },
        ]

    def _resources(self) -> List[Dict[str, Any]]:
        return [
            {
                "uri": "scbe://queue/summary",
                "name": "Queue Summary",
                "description": "Current queue and run counters.",
                "mimeType": "application/json",
            },
            {
                "uri": "scbe://worker/local-health",
                "name": "Local Worker Health",
                "description": "Runtime and capacity status for local worker.",
                "mimeType": "application/json",
            },
            {
                "uri": "scbe://policy/security-baseline",
                "name": "Security Baseline Policy",
                "description": "Risk thresholds and antivirus gate defaults.",
                "mimeType": "application/json",
            },
            {
                "uri": "scbe://signatures/current",
                "name": "Current Signature Pack",
                "description": "Current malware/phishing indicators.",
                "mimeType": "application/json",
            },
        ]

    def _resource_templates(self) -> List[Dict[str, Any]]:
        return [
            {
                "uriTemplate": "scbe://tasks/{task_id}",
                "name": "Task Record",
                "description": "Task record by task_id.",
                "mimeType": "application/json",
            },
            {
                "uriTemplate": "scbe://runs/{run_id}/logs",
                "name": "Run Logs",
                "description": "Execution logs for a run_id.",
                "mimeType": "application/json",
            },
            {
                "uriTemplate": "scbe://domains/{domain}/risk",
                "name": "Domain Risk",
                "description": "On-demand risk evaluation for a domain.",
                "mimeType": "application/json",
            },
        ]

    def _read_resource(self, uri: str) -> Dict[str, Any]:
        if uri == "scbe://queue/summary":
            return self._queue_summary()

        if uri == "scbe://worker/local-health":
            return {
                "worker_id": "local-worker-01",
                "status": "healthy",
                "capacity": {"parallel_slots": self.security_policy["max_parallel_tasks"], "used_slots": 0},
                "timestamp_utc": self._now_iso(),
            }

        if uri == "scbe://policy/security-baseline":
            return {
                "policy": self.security_policy,
                "decision_actions": ["ALLOW", "QUARANTINE", "DENY"],
                "wall_formula": WALL_FORMULA,
            }

        if uri == "scbe://signatures/current":
            return self.signatures

        if uri.startswith("scbe://tasks/"):
            task_id = uri.split("scbe://tasks/", 1)[1]
            task = self.tasks.get(task_id)
            if task is None:
                raise RpcError(-32004, f"task not found: {task_id}")
            return task

        if uri.startswith("scbe://runs/") and uri.endswith("/logs"):
            run_id = uri[len("scbe://runs/") : -len("/logs")]
            run = self.runs.get(run_id)
            if run is None:
                raise RpcError(-32004, f"run not found: {run_id}")
            return {"run_id": run_id, "logs": run.get("logs", [])}

        if uri.startswith("scbe://domains/") and uri.endswith("/risk"):
            domain = uri[len("scbe://domains/") : -len("/risk")]
            scan = self._scan_target(domain)
            return {"domain": domain, **scan}

        raise RpcError(-32004, f"resource not found: {uri}")

    def _tool_response(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        objective: str,
        lane: str,
        decision: str,
        decision_reason: str,
        risk: float,
        target_ref: str,
        profile_id: str = "default",
        job_id: str = "none",
    ) -> Dict[str, Any]:
        state_vector = self._state_vector(objective=objective, lane=lane)
        decision_record = self._decision_record(
            decision=decision,
            decision_reason=decision_reason,
            risk=risk,
            target_ref=target_ref,
            profile_id=profile_id,
            job_id=job_id,
        )

        response = {
            "tool": tool_name,
            "payload": payload,
            "StateVector": state_vector,
            "DecisionRecord": decision_record,
        }
        self._append_telemetry_event(
            tool_name=tool_name,
            payload=payload,
            state_vector=state_vector,
            decision_record=decision_record,
            target_ref=target_ref,
        )
        return response

    def _call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "security.scan_target":
            target = str(args.get("target", "")).strip()
            if not target:
                raise RpcError(-32602, "target is required")
            scan = self._scan_target(target)
            return self._tool_response(
                tool_name=name,
                payload=scan,
                objective="Pre-flight target risk gate",
                lane="security",
                decision=scan["decision"],
                decision_reason="target scan completed",
                risk=scan["risk"],
                target_ref=target,
            )

        if name == "task.submit":
            target = str(args.get("target", "")).strip()
            if not target:
                raise RpcError(-32602, "target is required")

            profile_id = str(args.get("profile_id", "default"))
            task_type = str(args.get("task_type", "web"))
            scan = self._scan_target(target)

            task_id = str(uuid.uuid4())
            task_status = "blocked" if scan["decision"] == "DENY" else "queued"
            task = {
                "task_id": task_id,
                "task_type": task_type,
                "target": target,
                "profile_id": profile_id,
                "status": task_status,
                "decision": scan["decision"],
                "created_at": self._now_iso(),
                "reasons": scan["reasons"],
            }
            self.tasks[task_id] = task

            return self._tool_response(
                tool_name=name,
                payload=task,
                objective="Submit multi-task web job",
                lane="queue",
                decision=scan["decision"],
                decision_reason="task accepted" if task_status == "queued" else "task blocked by security gate",
                risk=scan["risk"],
                target_ref=target,
                profile_id=profile_id,
                job_id=task_id,
            )

        if name == "task.status":
            task_id = str(args.get("task_id", "")).strip()
            if not task_id:
                raise RpcError(-32602, "task_id is required")

            task = self.tasks.get(task_id)
            if task is None:
                raise RpcError(-32004, f"task not found: {task_id}")

            risk = 0.2 if task["decision"] == "ALLOW" else 0.5 if task["decision"] == "QUARANTINE" else 0.9
            return self._tool_response(
                tool_name=name,
                payload=task,
                objective="Observe queued task state",
                lane="queue",
                decision=task["decision"],
                decision_reason="task status lookup",
                risk=risk,
                target_ref=task["target"],
                profile_id=task.get("profile_id", "default"),
                job_id=task_id,
            )

        if name == "browser.run_headless":
            target = str(args.get("target", "")).strip()
            if not target:
                raise RpcError(-32602, "target is required")

            max_steps = int(args.get("max_steps", 20))
            profile_id = str(args.get("profile_id", "default"))
            action_diagnostics = args.get("action_diagnostics", [])
            diagnostic_summary = self._summarize_action_diagnostics(action_diagnostics)
            scan = self._scan_target(target)

            run_id = str(uuid.uuid4())
            if scan["decision"] == "DENY":
                status = "blocked"
                logs = ["blocked_before_execution"]
            else:
                status = "completed"
                logs = [
                    f"headless session started for {target}",
                    f"steps executed: {min(max_steps, 5)} (stub)",
                    "artifacts available via browser.capture_artifact",
                ]

            click_samples = int(diagnostic_summary.get("click_metrics", {}).get("sample_count", 0))
            if click_samples > 0:
                p95 = diagnostic_summary["click_metrics"]["p95_offset_px"]
                logs.append(f"click drift p95: {p95}px over {click_samples} samples")

            run = {
                "run_id": run_id,
                "target": target,
                "profile_id": profile_id,
                "max_steps": max_steps,
                "status": status,
                "decision": scan["decision"],
                "logs": logs,
                "created_at": self._now_iso(),
                "completed_at": self._now_iso() if status == "completed" else None,
                "diagnostics_ingested": diagnostic_summary.get("events_total", 0),
                "telemetry_summary": diagnostic_summary,
            }
            if isinstance(action_diagnostics, list) and action_diagnostics:
                run["action_diagnostics_preview"] = action_diagnostics[:10]

            self.runs[run_id] = run

            return self._tool_response(
                tool_name=name,
                payload=run,
                objective="Run safe headless browser task",
                lane="browser",
                decision=scan["decision"],
                decision_reason="run executed" if status == "completed" else "execution denied by policy",
                risk=scan["risk"],
                target_ref=target,
                profile_id=profile_id,
                job_id=run_id,
            )

        if name == "browser.capture_artifact":
            run_id = str(args.get("run_id", "")).strip()
            if not run_id:
                raise RpcError(-32602, "run_id is required")

            run = self.runs.get(run_id)
            if run is None:
                raise RpcError(-32004, f"run not found: {run_id}")

            artifact_type = str(args.get("artifact_type", "dom_text"))
            artifact_id = str(uuid.uuid4())
            artifact = {
                "artifact_id": artifact_id,
                "run_id": run_id,
                "artifact_type": artifact_type,
                "content": {
                    "summary": f"Stub artifact for {run['target']}",
                    "status": run["status"],
                },
                "created_at": self._now_iso(),
            }
            self.artifacts[artifact_id] = artifact

            scan = self._scan_artifact(artifact)

            return self._tool_response(
                tool_name=name,
                payload={"artifact": artifact, "artifact_scan": scan},
                objective="Capture and classify run artifacts",
                lane="artifacts",
                decision=scan["decision"],
                decision_reason="artifact capture complete",
                risk=scan["risk"],
                target_ref=run.get("target", run_id),
                profile_id=run.get("profile_id", "default"),
                job_id=run_id,
            )

        if name == "security.scan_artifact":
            artifact_id = str(args.get("artifact_id", "")).strip()
            if not artifact_id:
                raise RpcError(-32602, "artifact_id is required")

            artifact = self.artifacts.get(artifact_id)
            if artifact is None:
                raise RpcError(-32004, f"artifact not found: {artifact_id}")

            scan = self._scan_artifact(artifact)

            return self._tool_response(
                tool_name=name,
                payload=scan,
                objective="Artifact threat scan",
                lane="security",
                decision=scan["decision"],
                decision_reason="artifact scan completed",
                risk=scan["risk"],
                target_ref=artifact_id,
                job_id=artifact_id,
            )

        raise RpcError(-32601, f"tool not found: {name}")

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rpc_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "serverInfo": {"name": self.server_name, "version": self.server_version},
                        "capabilities": {
                            "tools": {},
                            "resources": {"subscribe": False, "listChanged": False},
                        },
                    },
                }

            if method == "notifications/initialized":
                return None

            if method == "ping":
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}

            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": self._tools()}}

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments", {})
                if not name:
                    raise RpcError(-32602, "tools/call requires params.name")
                tool_result = self._call_tool(name=name, args=arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(tool_result, indent=2, sort_keys=True),
                            }
                        ]
                    },
                }

            if method == "resources/list":
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {"resources": self._resources()},
                }

            if method == "resources/templates/list":
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {"resourceTemplates": self._resource_templates()},
                }

            if method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    raise RpcError(-32602, "resources/read requires params.uri")
                body = self._read_resource(uri)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps(body, indent=2, sort_keys=True),
                            }
                        ]
                    },
                }

            raise RpcError(-32601, f"method not found: {method}")

        except RpcError as err:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {
                    "code": err.code,
                    "message": err.message,
                    "data": err.data or {},
                },
            }

    def serve(self) -> None:
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "parse error",
                        "data": {"detail": str(exc)},
                    },
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
                continue

            response = self.handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def run_self_test() -> Tuple[int, str]:
    server = ScbeMinServer(enable_telemetry=False)
    tools = server._tools()
    resources = server._resources()
    templates = server._resource_templates()
    if len(tools) != 6:
        return 1, f"expected 6 tools, found {len(tools)}"
    if len(resources) != 4:
        return 1, f"expected 4 resources, found {len(resources)}"
    if len(templates) != 3:
        return 1, f"expected 3 templates, found {len(templates)}"

    sample = server._call_tool("security.scan_target", {"target": "https://example.com"})
    decision = sample["DecisionRecord"]["decision"]
    if decision not in {"ALLOW", "QUARANTINE", "DENY"}:
        return 1, f"unexpected decision: {decision}"

    diagnostic = server._summarize_action_diagnostics(
        [
            {
                "action": "click",
                "intended": {"x": 100, "y": 100},
                "actual": {"x": 110, "y": 100},
            }
        ]
    )
    if diagnostic["click_metrics"]["sample_count"] != 1:
        return 1, "diagnostic summary failed"

    return 0, "self-test passed"


def main() -> int:
    parser = argparse.ArgumentParser(description="SCBE MIN MCP server stub")
    parser.add_argument("--self-test", action="store_true", help="Run internal contract checks and exit")
    parser.add_argument(
        "--telemetry-path",
        default=None,
        help="Optional path for JSONL telemetry output",
    )
    parser.add_argument(
        "--disable-telemetry",
        action="store_true",
        help="Disable telemetry emission to local JSONL",
    )
    args = parser.parse_args()

    if args.self_test:
        code, msg = run_self_test()
        print(msg)
        return code

    telemetry_path = Path(args.telemetry_path).expanduser().resolve() if args.telemetry_path else None
    server = ScbeMinServer(
        telemetry_path=telemetry_path,
        enable_telemetry=not args.disable_telemetry,
    )
    server.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())