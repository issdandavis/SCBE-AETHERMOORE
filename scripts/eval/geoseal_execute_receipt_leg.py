#!/usr/bin/env python3
"""Zone-4 GeoSeal execute-and-receipt bridge.

This deliberately sits outside ``src/geoseal_cli.py`` and the agent-bus rewrite.
It proves the missing leg:

    plan / doctor payload -> governed subprocess execution -> receipt

The script is a drop-in prototype. It consumes a JSON plan or direct command,
fails closed unless the plan decision is ALLOW, runs through the existing
``src.crypto.geoseal_execution_gate`` policy, and emits a receipt that can be
ported into the canonical GeoSeal CLI after the rewrite settles.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

with contextlib.redirect_stdout(io.StringIO()):
    from src.crypto.geoseal_execution_gate import (
        TIER_RANK,
        execute_governed_command,
    )  # noqa: E402

SECRET_PATTERNS = [
    re.compile(r"\b(sk-[A-Za-z0-9_-]{8,})\b"),
    re.compile(r"\b(ghp_[A-Za-z0-9_]{8,})\b"),
    re.compile(r"\b(AKIA[0-9A-Z]{12,})\b"),
    re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{8,})\b"),
    re.compile(r"\b(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact(text: str, limit: int = 800) -> str:
    out = text[:limit]
    for pattern in SECRET_PATTERNS:
        out = pattern.sub(_redact_match, out)
    return out


def _redact_match(match: re.Match[str]) -> str:
    if match.lastindex and match.group(1).lower().startswith("bearer"):
        return f"{match.group(1)}[secret]"
    return "[secret]"


def _load_plan(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _first_present(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        cursor: Any = payload
        ok = True
        for part in key.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                ok = False
                break
            cursor = cursor[part]
        if ok and cursor not in (None, ""):
            return cursor
    return None


def extract_command(payload: dict[str, Any], explicit_command: str = "") -> str:
    """Extract a command from common GeoSeal plan/doctor payload shapes."""

    if explicit_command.strip():
        return explicit_command.strip()

    command = _first_present(
        payload,
        [
            "command",
            "planned_command",
            "plan.command",
            "operation.command",
            "operation_panel.command",
            "route.command",
            "tool_call.command",
            "execution.command",
        ],
    )
    if isinstance(command, str):
        return command.strip()
    argv = _first_present(
        payload,
        [
            "argv",
            "plan.argv",
            "operation.argv",
            "operation_panel.argv",
            "tool_call.argv",
            "execution.argv",
        ],
    )
    if isinstance(argv, list) and all(isinstance(part, str) for part in argv):
        return " ".join(json.dumps(part) for part in argv)
    return ""


def extract_policy_decision(
    payload: dict[str, Any], explicit_decision: str = ""
) -> str:
    if explicit_decision:
        return explicit_decision.upper()
    decision = _first_present(
        payload,
        [
            "decision",
            "policy.decision",
            "gate.decision",
            "route.decision",
            "operation_panel.decision",
            "governance.decision",
        ],
    )
    return str(decision or "ALLOW").upper()


def build_execute_receipt(
    *,
    plan: dict[str, Any],
    command: str,
    policy_decision: str,
    max_tier: str,
    cwd: Path,
    timeout: float,
    claimed_paths: list[str] | None = None,
) -> dict[str, Any]:
    started = time.time()
    plan_hash = (
        _sha256_text(json.dumps(plan, sort_keys=True, separators=(",", ":")))
        if plan
        else ""
    )
    command_hash = _sha256_text(command)

    if not command:
        return {
            "schema_version": "scbe_geoseal_execute_receipt_leg_v1",
            "receipt": "SCBE_GEOSEAL_EXECUTE=0",
            "ok": False,
            "executed": False,
            "reason": "missing command",
            "policy_decision": policy_decision,
            "plan_sha256": plan_hash,
            "command_sha256": command_hash,
        }

    if policy_decision != "ALLOW":
        return {
            "schema_version": "scbe_geoseal_execute_receipt_leg_v1",
            "receipt": "SCBE_GEOSEAL_EXECUTE=0",
            "ok": False,
            "executed": False,
            "reason": f"policy decision {policy_decision} is not ALLOW",
            "policy_decision": policy_decision,
            "plan_sha256": plan_hash,
            "command_sha256": command_hash,
            "command_preview": _redact(command, 300),
        }

    result = execute_governed_command(
        command,
        cwd=cwd,
        timeout=timeout,
        max_tier=max_tier,
        claimed_paths=claimed_paths,
        audit_log=None,
    )
    result_dict = result.to_dict()
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    ok = bool(result.ran and result.returncode == 0)
    return {
        "schema_version": "scbe_geoseal_execute_receipt_leg_v1",
        "receipt": f"SCBE_GEOSEAL_EXECUTE={'1' if ok else '0'}",
        "ok": ok,
        "executed": bool(result.ran),
        "policy_decision": policy_decision,
        "max_tier": max_tier,
        "gate_tier": result.decision.tier,
        "plan_sha256": plan_hash,
        "command_sha256": command_hash,
        "command_preview": _redact(command, 300),
        "cwd": str(cwd),
        "returncode": result.returncode,
        "duration_ms": round((time.time() - started) * 1000.0, 3),
        "stdout_sha256": _sha256_text(stdout),
        "stderr_sha256": _sha256_text(stderr),
        "stdout_preview": _redact(stdout),
        "stderr_preview": _redact(stderr),
        "error": result.error,
        "gate": result_dict["decision"],
        "claim_boundary": (
            "Zone-4 prototype only: proves plan-to-execution receipt shape; "
            "canonical GeoSeal integration must land after dirty rewrite files settle."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, help="JSON plan/doctor payload to execute")
    parser.add_argument(
        "--command", default="", help="Explicit command string; overrides plan command"
    )
    parser.add_argument(
        "--decision",
        default="",
        help="Explicit policy decision; overrides plan decision",
    )
    parser.add_argument("--max-tier", default="ALLOW", choices=sorted(TIER_RANK))
    parser.add_argument("--cwd", type=Path, default=REPO_ROOT)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--claimed-path", action="append", default=[])
    parser.add_argument("--out", type=Path, help="Write receipt JSON to path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = _load_plan(args.plan)
    command = extract_command(plan, args.command)
    policy_decision = extract_policy_decision(plan, args.decision)
    receipt = build_execute_receipt(
        plan=plan,
        command=command,
        policy_decision=policy_decision,
        max_tier=args.max_tier,
        cwd=args.cwd.resolve(),
        timeout=args.timeout,
        claimed_paths=args.claimed_path or None,
    )
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
