#!/usr/bin/env python3
"""One-command SCBE agent task planner.

This is the operator entrypoint that ties together the free-compute matrix,
dispatch spine, sandbox choice, and trajectory scaling knobs. It intentionally
plans and records controlled work packets; it does not let remote workers write
to sensitive paths or execute arbitrary code without an explicit flag.

Each written run also emits ``tool_bridge`` (``scbe_agent_tool_bridge_v1``):
ready-made GeoSeal CLI commands, local service URLs, n8n bridge routes, and
MCP lane hints so agents can reach external tools through SCBE surfaces first.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.coding_spine.agent_tool_bridge import build_agent_tool_bridge_v1  # noqa: E402
from src.crypto.sacred_tongue_payload_bijection import prove_dict  # noqa: E402

FREE_COMPUTE_PLANNER = REPO_ROOT / "scripts" / "system" / "free_compute_agent_array.py"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_task_runs"
SANDBOX_MODES = (
    "host",
    "docker",
    "github_actions",
    "colab",
    "kaggle",
    "huggingface_spaces",
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_free_compute_module():
    spec = importlib.util.spec_from_file_location(
        "_scbe_free_compute_agent_array", FREE_COMPUTE_PLANNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {FREE_COMPUTE_PLANNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_trajectory(
    packet: Any, max_attempts: int, critic: bool, rerank: bool
) -> list[dict[str, Any]]:
    """Build inference-time scaling steps for a packet.

    This is deliberately model-agnostic: any agent can fill in the attempt
    outputs, but the harness records generator/critic/rerank evidence in the
    same shape.
    """
    steps: list[dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        steps.append(
            {
                "attempt": attempt,
                "role": "generator",
                "state": "candidate_patch",
                "expected_evidence": [
                    "changed_files",
                    "diff_summary",
                    "verify_command",
                ],
                "packet_id": packet.task_id,
            }
        )
        if critic:
            steps.append(
                {
                    "attempt": attempt,
                    "role": "critic",
                    "state": "candidate_review",
                    "expected_evidence": ["bugs_found", "missing_tests", "risk_notes"],
                    "packet_id": packet.task_id,
                }
            )
    if rerank and max_attempts > 1:
        steps.append(
            {
                "attempt": "final",
                "role": "reranker",
                "state": "select_best_candidate",
                "expected_evidence": [
                    "selected_attempt",
                    "reason",
                    "verification_result",
                ],
                "packet_id": packet.task_id,
            }
        )
    return steps


def sandbox_policy(packet: Any, requested: str) -> dict[str, Any]:
    if not packet.remote_ok or packet.risk == "high":
        effective = "host"
        reason = "high-risk or non-remote packet stays local for review authority"
    elif requested == "auto":
        effective = packet.compute_target
        reason = "selected from packet compute target"
    else:
        effective = requested
        reason = "operator requested sandbox mode"
    if effective == "host":
        isolation = "subprocess_on_current_checkout"
    elif effective == "docker":
        isolation = "ephemeral_container_expected"
    else:
        isolation = "remote_free_compute_lane"
    return {
        "requested": requested,
        "effective": effective,
        "isolation": isolation,
        "reason": reason,
    }


def build_task_run(
    *,
    goal: str,
    workers: int,
    sandbox: str,
    max_attempts: int,
    critic: bool,
    rerank: bool,
) -> dict[str, Any]:
    planner = _load_free_compute_module()
    packets = planner.build_packets(goal, workers)
    check = planner.check_plan(packets)
    if not check["ok"]:
        raise ValueError(f"generated packet plan is invalid: {check['problems']}")
    core = {
        "schema_version": "scbe_agent_task_run_v1",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "goal": goal,
        "workers": workers,
        "trajectory_scaling": {
            "max_attempts": max_attempts,
            "critic_enabled": critic,
            "rerank_enabled": rerank,
            "selection_rule": "highest verified acceptance score; ties prefer lower risk and smaller diff",
        },
        "operator_commands": {
            "matrix": f"npm run agent:free-compute-array -- --goal {json.dumps(goal)} --workers {workers}",
            "enqueue": "powershell -ExecutionPolicy Bypass -File artifacts/free_compute_agent_array/enqueue_dispatch_commands.ps1",
            "status": "python scripts/system/advanced_ai_dispatch.py status --limit 20",
        },
        "packets": [
            {
                **asdict(packet),
                "sandbox_policy": sandbox_policy(packet, sandbox),
                "trajectory": build_trajectory(packet, max_attempts, critic, rerank),
            }
            for packet in packets
        ],
    }
    return core


def attach_build_bijection(payload: dict[str, Any]) -> None:
    """Mutates payload with SS1 round-trip proof over canonical JSON (all six tongues)."""
    core = {k: v for k, v in payload.items() if k != "build_bijection"}
    payload["build_bijection"] = prove_dict(core)


def write_task_run(
    payload: dict[str, Any], output_root: Path, *, attach_bijection: bool = True
) -> dict[str, str]:
    run_dir = output_root / _utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    intent_path = run_dir / "task_intent.txt"
    intent_path.write_text(payload["goal"].rstrip() + "\n", encoding="utf-8")
    rel = intent_path.relative_to(REPO_ROOT).as_posix()
    payload["tool_bridge"] = build_agent_tool_bridge_v1(intent_relative_posix=rel)
    if attach_bijection:
        attach_build_bijection(payload)
    report_path = run_dir / "agent_task_run.json"
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# SCBE Agent Task Run",
        "",
        f"Goal: {payload['goal']}",
        f"Workers: {payload['workers']}",
        "",
        "| Row | Lane | Compute | Sandbox | Attempts | State | Verify |",
        "| ---: | --- | --- | --- | ---: | --- | --- |",
    ]
    for packet in payload["packets"]:
        md_lines.append(
            "| {row} | `{lane}` | `{compute}` | `{sandbox}` | {attempts} | `{state}` | `{verify}` |".format(
                row=packet["row"],
                lane=packet["lane"],
                compute=packet["compute_target"],
                sandbox=packet["sandbox_policy"]["effective"],
                attempts=payload["trajectory_scaling"]["max_attempts"],
                state=packet["quest_state"],
                verify=packet["verify_command"].replace("|", "\\|"),
            )
        )
    bij = payload.get("build_bijection") or {}
    if bij.get("ok") is not None:
        md_lines.extend(
            [
                "",
                "## Sacred Tongue build bijection",
                "",
                f"- **ok**: `{bij.get('ok')}`",
                f"- **canonical_sha256**: `{bij.get('canonical_sha256', '')}`",
                f"- **tongues**: {', '.join(bij.get('tongue_order', []))}",
                "",
            ]
        )
    md_path = run_dir / "agent_task_run.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    latest = output_root / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "agent_task_run.json").write_text(
        report_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (latest / "agent_task_run.md").write_text(
        md_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return {"json": str(report_path), "markdown": str(md_path), "latest": str(latest)}


def execute_verify(payload: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    """Run low-risk host verification commands for planned packets.

    This is opt-in because verification commands may be expensive. Only packets
    whose effective sandbox is host and whose risk is not high are eligible.
    """
    results: list[dict[str, Any]] = []
    for packet in payload["packets"][:limit]:
        if packet["sandbox_policy"]["effective"] != "host" or packet["risk"] == "high":
            results.append(
                {
                    "task_id": packet["task_id"],
                    "skipped": True,
                    "reason": "not eligible for host verify",
                }
            )
            continue
        cmd = packet["verify_command"]
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            text=True,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=240,
            check=False,
        )
        results.append(
            {
                "task_id": packet["task_id"],
                "command": cmd,
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-1500:],
                "stderr_tail": proc.stderr[-1500:],
            }
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--sandbox", choices=("auto",) + SANDBOX_MODES, default="auto")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--no-critic", action="store_true")
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--execute-verify", action="store_true")
    parser.add_argument("--verify-limit", type=int, default=2)
    parser.add_argument(
        "--no-build-bijection",
        action="store_true",
        help="Skip SS1 round-trip proof over canonical task JSON (all six tongues).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.max_attempts < 1:
        raise SystemExit("--max-attempts must be at least 1")
    payload = build_task_run(
        goal=args.goal,
        workers=args.workers,
        sandbox=args.sandbox,
        max_attempts=args.max_attempts,
        critic=not args.no_critic,
        rerank=not args.no_rerank,
    )
    if args.execute_verify:
        payload["verify_results"] = execute_verify(payload, args.verify_limit)
    outputs = write_task_run(
        payload, args.output_root, attach_bijection=not args.no_build_bijection
    )
    print(
        json.dumps(
            {"ok": True, "outputs": outputs, "packets": len(payload["packets"])},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
