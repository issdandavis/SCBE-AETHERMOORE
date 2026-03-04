"""
HYDRA Remote Coding Worker
==========================

Headless coding worker for Switchboard roles (planner/coder/reviewer/memory).
Designed for local or remote/virtual compute so coding work can run outside
the primary workstation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .switchboard import Switchboard
from .turnstile import resolve_turnstile


def _worker_id(cli_worker_id: str | None) -> str:
    if cli_worker_id and cli_worker_id.strip():
        return cli_worker_id.strip()
    return f"{socket.gethostname()}-{int(time.time())}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_path(workspace: Path, target: str) -> Path:
    if not target or not str(target).strip():
        raise ValueError("target path is required")
    candidate = Path(target)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
    workspace_resolved = workspace.resolve()
    if resolved != workspace_resolved and workspace_resolved not in resolved.parents:
        raise ValueError(f"target escapes workspace: {target}")
    return resolved


def _risk_score(payload: Dict[str, Any]) -> float:
    action = str(payload.get("action", "")).strip().lower()
    params = payload.get("params", {}) if isinstance(payload.get("params"), dict) else {}
    score = 0.15

    if action == "run_cmd":
        score = 0.6
        cmd = str(payload.get("target", "")).lower()
        banned_fragments = [
            "rm -rf",
            "del /f",
            "format ",
            "shutdown",
            "sc stop",
            "powershell -enc",
            "curl ",
            "invoke-webrequest",
        ]
        if any(token in cmd for token in banned_fragments):
            score = 0.99

    if action in {"write_file", "append_file"}:
        score = max(score, 0.35)

    if params.get("safe_mode"):
        score = max(score, 0.5)

    return min(1.0, score)


def _state_vector(task: Dict[str, Any], worker_id: str, status: str, role: str, turnstile_action: str) -> Dict[str, Any]:
    return {
        "worker_id": worker_id,
        "task_id": str(task.get("task_id", "")),
        "role": role,
        "status": status,
        "turnstile_action": turnstile_action,
        "attempts": int(task.get("attempts", 0)),
        "timestamp": _utc_now(),
    }


def _decision_record(
    task: Dict[str, Any],
    worker_id: str,
    action: str,
    reason: str,
    confidence: float,
) -> Dict[str, Any]:
    signature = f"{worker_id}:{task.get('task_id', '')}:{int(time.time())}"
    return {
        "action": action,
        "signature": signature,
        "timestamp": _utc_now(),
        "reason": reason,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
    }


def _render_plan(title: str, prompt: str) -> str:
    return (
        f"# {title}\n\n"
        "## Objective\n"
        f"{prompt}\n\n"
        "## Work Breakdown\n"
        "1. Define scope and guardrails.\n"
        "2. Implement baseline artifacts.\n"
        "3. Validate execution path.\n"
        "4. Capture memory notes and next actions.\n\n"
        "## Governance\n"
        "- Role separation: planner -> coder -> reviewer -> memory.\n"
        "- Turnstile decisions enforced per task.\n"
        "- Outputs are logged through HYDRA Switchboard.\n"
    )


def _execute_payload(
    payload: Dict[str, Any],
    workspace: Path,
    allowed_prefixes: List[str],
) -> Dict[str, Any]:
    action = str(payload.get("action", "")).strip().lower()
    target = str(payload.get("target", "")).strip()
    params = payload.get("params", {}) if isinstance(payload.get("params"), dict) else {}

    if action == "plan_doc":
        path = _safe_path(workspace, target)
        path.parent.mkdir(parents=True, exist_ok=True)
        prompt = str(params.get("prompt", "Generate implementation plan")).strip()
        title = str(params.get("title", "SCBE Headless IDE Plan")).strip()
        content = _render_plan(title=title, prompt=prompt)
        path.write_text(content, encoding="utf-8")
        return {"success": True, "written": str(path), "bytes": len(content.encode("utf-8"))}

    if action == "write_file":
        path = _safe_path(workspace, target)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(params.get("content", ""))
        path.write_text(content, encoding="utf-8")
        return {"success": True, "written": str(path), "bytes": len(content.encode("utf-8"))}

    if action == "append_file":
        path = _safe_path(workspace, target)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(params.get("content", ""))
        with path.open("a", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "appended": str(path), "bytes": len(content.encode("utf-8"))}

    if action == "read_file":
        path = _safe_path(workspace, target)
        text = path.read_text(encoding="utf-8")
        return {"success": True, "read": str(path), "preview": text[:1200], "bytes": len(text.encode("utf-8"))}

    if action == "run_cmd":
        command = target
        if not command:
            raise ValueError("run_cmd requires command in target")
        parts = shlex.split(command, posix=False)
        if not parts:
            raise ValueError("empty command")
        prefix = parts[0].lower()
        if prefix not in allowed_prefixes:
            raise ValueError(f"command prefix '{prefix}' is not allowed")

        timeout_sec = int(params.get("timeout_sec", 60))
        completed = subprocess.run(
            parts,
            cwd=str(workspace),
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, timeout_sec),
        )
        return {
            "success": completed.returncode == 0,
            "returncode": int(completed.returncode),
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "command": command,
        }

    raise ValueError(f"unsupported action: {action}")


async def run_worker(args: argparse.Namespace) -> int:
    roles: List[str] = [r.strip().lower() for r in args.roles.split(",") if r.strip()]
    if not roles:
        raise ValueError("At least one role is required")

    worker_id = _worker_id(args.worker_id)
    board = Switchboard(args.db)
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    allowed_prefixes = [p.strip().lower() for p in args.allowed_cmd_prefixes.split(",") if p.strip()]
    if not allowed_prefixes:
        allowed_prefixes = ["python"]

    processed = 0
    print(
        json.dumps(
            {
                "event": "coding_worker_start",
                "worker_id": worker_id,
                "roles": roles,
                "db": args.db,
                "workspace": str(workspace),
                "domain": args.domain,
            }
        )
    )

    while True:
        task = board.claim_task(worker_id, roles, lease_seconds=args.lease_sec)
        if not task:
            if args.once:
                break
            await asyncio.sleep(args.poll_sec)
            continue

        role = str(task.get("role", "default")).strip().lower() or "default"
        payload = task.get("payload", {}) if isinstance(task.get("payload"), dict) else {}
        decision = "ALLOW"
        risk = _risk_score(payload)
        if risk >= 0.95:
            decision = "QUARANTINE"
        elif risk >= 0.7:
            decision = "ESCALATE"

        turnstile = resolve_turnstile(
            decision=decision,
            domain=args.domain,
            suspicion=risk,
            geometry_norm=min(0.999, max(0.0, risk)),
            previous_antibody_load=float(args.previous_antibody_load),
            quorum_ok=bool(args.quorum_ok),
        )

        task_id = str(task.get("task_id", ""))
        t0 = time.time()
        try:
            if turnstile.action in {"HOLD", "STOP"}:
                reason = f"turnstile={turnstile.action.lower()} reason={turnstile.reason}"
                board.fail_task(task_id, worker_id, reason, result={"turnstile_action": turnstile.action})
                status = "failed"
                result: Dict[str, Any] = {"success": False, "error": reason}
            elif turnstile.action in {"ISOLATE", "HONEYPOT"}:
                result = {
                    "success": True,
                    "mode": turnstile.action.lower(),
                    "reason": turnstile.reason,
                    "executed": False,
                }
                board.complete_task(task_id, worker_id, result)
                status = "done"
            else:
                result = _execute_payload(payload, workspace=workspace, allowed_prefixes=allowed_prefixes)
                result["elapsed_ms"] = round((time.time() - t0) * 1000.0, 2)
                result["worker_id"] = worker_id
                result["task_role"] = role
                if result.get("success"):
                    board.complete_task(task_id, worker_id, result)
                    status = "done"
                else:
                    err = str(result.get("error") or "execution failed")
                    board.fail_task(task_id, worker_id, err, result=result)
                    status = "failed"

            state = _state_vector(task, worker_id, status, role, turnstile.action)
            decision_record = _decision_record(
                task=task,
                worker_id=worker_id,
                action=turnstile.action,
                reason=turnstile.reason,
                confidence=1.0 - risk,
            )
            board.post_role_message(
                channel=role,
                sender=worker_id,
                message={
                    "task_id": task_id,
                    "status": status,
                    "StateVector": state,
                    "DecisionRecord": decision_record,
                },
            )
        except Exception as exc:  # noqa: BLE001
            board.fail_task(task_id, worker_id, str(exc), result={"worker_id": worker_id})
            status = "failed"
            result = {"success": False, "error": str(exc)}
            state = _state_vector(task, worker_id, status, role, "STOP")
            decision_record = _decision_record(
                task=task,
                worker_id=worker_id,
                action="STOP",
                reason=str(exc),
                confidence=0.0,
            )
            board.post_role_message(
                channel=role,
                sender=worker_id,
                message={
                    "task_id": task_id,
                    "status": status,
                    "StateVector": state,
                    "DecisionRecord": decision_record,
                },
            )

        processed += 1
        print(
            json.dumps(
                {
                    "event": "coding_task_processed",
                    "worker_id": worker_id,
                    "task_id": task_id,
                    "role": role,
                    "status": status,
                    "result_preview": str(result)[:320],
                }
            )
        )

        if args.max_tasks > 0 and processed >= args.max_tasks:
            break

    print(json.dumps({"event": "coding_worker_stop", "worker_id": worker_id, "processed": processed}))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HYDRA remote coding worker")
    parser.add_argument("--db", default="artifacts/hydra/headless_ide/switchboard.db")
    parser.add_argument("--roles", default="planner,coder,reviewer,memory")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--domain", default="fleet", choices=["browser", "vehicle", "fleet", "antivirus", "default"])
    parser.add_argument("--poll-sec", type=float, default=1.0)
    parser.add_argument("--lease-sec", type=int, default=60)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--quorum-ok", dest="quorum_ok", action="store_true")
    parser.add_argument("--no-quorum-ok", dest="quorum_ok", action="store_false")
    parser.set_defaults(quorum_ok=True)
    parser.add_argument("--previous-antibody-load", type=float, default=0.0)
    parser.add_argument(
        "--allowed-cmd-prefixes",
        default="python,pytest",
        help="comma-separated safe command prefixes for run_cmd action",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_worker(args))


if __name__ == "__main__":
    main()
