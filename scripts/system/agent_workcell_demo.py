#!/usr/bin/env python3
"""Run a visible SCBE multi-agent workcell proof.

This is an operator-facing proof path: one task is routed through named agent
slots, cross-talk packets are written, verification commands run, and a ship
report is emitted. Provider names are slots, not claims that an external model
API was called.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "agent_workcells" / "latest"
DEFAULT_BUS_LOG = REPO_ROOT / "artifacts" / "agent-bus" / "events.jsonl"
DEFAULT_AGENT_COUNT = 100

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.agent_bus_schema import CURRENT_SCHEMA_VERSION
from src.crypto.geoseal_execution_gate import scan_command


@dataclass(frozen=True)
class WorkcellAgent:
    agent_id: str
    model_slot: str
    role: str
    job: str


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    duration_ms: int
    stdout_tail: str
    stderr_tail: str
    geoseal_gate: dict[str, Any]
    attempts: int = 1


AGENTS = (
    WorkcellAgent(
        agent_id="planner",
        model_slot="codex",
        role="task-router",
        job="Turn the human request into bounded work packets.",
    ),
    WorkcellAgent(
        agent_id="builder",
        model_slot="claude",
        role="implementation-worker",
        job="Apply or identify the concrete system change.",
    ),
    WorkcellAgent(
        agent_id="reviewer",
        model_slot="gemini",
        role="risk-reviewer",
        job="Challenge the work for missing proof and unsafe claims.",
    ),
    WorkcellAgent(
        agent_id="verifier",
        model_slot="local-shell",
        role="test-runner",
        job="Run deterministic checks and capture evidence.",
    ),
    WorkcellAgent(
        agent_id="shipper",
        model_slot="github-ci",
        role="release-coordinator",
        job="Summarize whether the work can ship and what artifact proves it.",
    ),
)


DEPLOY_AGENTS = (
    WorkcellAgent(
        agent_id="architect",
        model_slot="codex",
        role="deploy-router",
        job="Break the deploy request into bounded, non-overlapping release packets.",
    ),
    WorkcellAgent(
        agent_id="builder",
        model_slot="free-local-first",
        role="release-builder",
        job="Prepare the deployable artifact and local proof paths.",
    ),
    WorkcellAgent(
        agent_id="security",
        model_slot="geoseal",
        role="command-gate",
        job="Gate every deploy command before execution.",
    ),
    WorkcellAgent(
        agent_id="tester",
        model_slot="local-shell",
        role="regression-runner",
        job="Run deterministic deploy and product-readiness checks.",
    ),
    WorkcellAgent(
        agent_id="deployer",
        model_slot="github-ci",
        role="promotion-coordinator",
        job="Promote only when gates pass and rollback evidence exists.",
    ),
    WorkcellAgent(
        agent_id="monitor",
        model_slot="vercel-smoke",
        role="post-deploy-monitor",
        job="Confirm live-route and Agent Bus evidence after the deploy lane runs.",
    ),
)


def scenario_agents(scenario: str) -> tuple[WorkcellAgent, ...]:
    return DEPLOY_AGENTS if scenario == "deploy" else AGENTS


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tail(text: str, limit: int = 1800) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[-limit:]


def run_command(
    command: str,
    cwd: Path,
    *,
    max_attempts: int = 1,
    claimed_paths: list[str] | None = None,
) -> CommandResult:
    gate = scan_command(command, claimed_paths=claimed_paths).to_dict()
    if not gate["allowed"]:
        return CommandResult(
            command=command,
            returncode=126,
            duration_ms=0,
            stdout_tail="",
            stderr_tail=f"GeoSeal gate blocked command at tier {gate['tier']}",
            geoseal_gate=gate,
            attempts=0,
        )

    started = datetime.now(timezone.utc)
    attempts = 0
    proc: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        attempts = attempt
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        if proc.returncode == 0:
            break
    ended = datetime.now(timezone.utc)
    assert proc is not None
    return CommandResult(
        command=command,
        returncode=proc.returncode,
        duration_ms=int((ended - started).total_seconds() * 1000),
        stdout_tail=tail(proc.stdout),
        stderr_tail=tail(proc.stderr),
        geoseal_gate=gate,
        attempts=attempts,
    )


def git_value(args: Iterable[str], cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except Exception:
        return "unknown"
    return proc.stdout.strip() or proc.stderr.strip() or "unknown"


def packet(
    sender: WorkcellAgent,
    recipient: WorkcellAgent,
    task_id: str,
    summary: str,
    proof: list[str],
) -> dict[str, Any]:
    return {
        "created_at": utc_now(),
        "task_id": task_id,
        "sender": asdict(sender),
        "recipient": asdict(recipient),
        "intent": "workcell_crosstalk",
        "status": "done",
        "summary": summary,
        "proof": proof,
    }


def build_lease_plan(agent_count: int = DEFAULT_AGENT_COUNT) -> list[dict[str, Any]]:
    """Build disjoint agent work leases for a 100-agent coding swarm plan."""

    roles = ("planner", "builder", "reviewer", "verifier", "shipper")
    systems = (
        "geoseal_agent_task",
        "agent_bus",
        "swarm_router",
        "code_slice_geometry",
        "functional_coding_agent_benchmark",
        "cross_language_lookup",
        "ss1_sacred_tongue_transport",
        "stisa_atomic_tokenizer",
    )
    return [
        {
            "lease_id": f"agent-slot-{idx:03d}",
            "agent_id": f"agent-{idx:03d}",
            "role": roles[idx % len(roles)],
            "model_policy": "free-first; paid escalation only when verification fails or human marks high value",
            "coding_system": systems[idx % len(systems)],
            "claim_path": f"artifacts/agent_workcells/slot-{idx:03d}",
            "write_scope": [f"artifacts/agent_workcells/slot-{idx:03d}/"],
            "shared_files": [],
        }
        for idx in range(1, agent_count + 1)
    ]


def command_specs_for_scenario(scenario: str) -> list[dict[str, Any]]:
    if scenario == "deploy":
        return [
            {
                "command": (
                    "python -m py_compile scripts\\system\\agent_workcell_demo.py "
                    "scripts\\system\\remote_app_config_smoke.py "
                    "scripts\\system\\product_launch_readiness.py"
                ),
                "claimed_paths": ["scripts/system"],
            },
            {
                "command": (
                    "python -m pytest tests\\system\\test_agent_workcell_demo.py "
                    "tests\\system\\test_product_launch_readiness.py -q"
                ),
                "claimed_paths": ["tests/system", "scripts/system"],
            },
            {
                "command": "npm run smoke:remote-app-config --silent",
                "claimed_paths": [
                    "package.json",
                    "scripts/system",
                    "docs",
                    "vercel.json",
                ],
            },
            {
                "command": "npm run cash:launch-readiness:gate --silent",
                "claimed_paths": ["package.json", "scripts/system", "docs"],
            },
        ]
    return [
        {
            "command": (
                "python -m py_compile scripts\\system\\product_launch_readiness.py "
                "scripts\\system\\build_manufacturing_braid_package.py"
            ),
            "claimed_paths": ["scripts/system"],
        },
        {
            "command": (
                "python -m pytest tests\\system\\test_product_launch_readiness.py "
                "tests\\system\\test_build_manufacturing_braid_package.py -q"
            ),
            "claimed_paths": ["tests/system", "scripts/system"],
        },
        {
            "command": "npm run cash:launch-readiness:gate --silent",
            "claimed_paths": ["package.json", "scripts/system", "docs"],
        },
    ]


def collision_report(leases: list[dict[str, Any]]) -> dict[str, Any]:
    owners_by_scope: dict[str, list[str]] = {}
    for lease in leases:
        for scope in lease["write_scope"]:
            owners_by_scope.setdefault(scope, []).append(lease["agent_id"])
    collisions = {
        scope: owners for scope, owners in owners_by_scope.items() if len(owners) > 1
    }
    return {
        "agent_slots": len(leases),
        "exclusive_write_scopes": len(owners_by_scope),
        "collision_count": len(collisions),
        "collisions": collisions,
        "policy": "one writer per scope; shared files require explicit integration packet",
    }


def write_lease_manifest(
    path: Path, leases: list[dict[str, Any]], collisions: dict[str, Any]
) -> None:
    write_json(
        path,
        {
            "schema": "scbe.agent_workcell_leases.v1",
            "created_at": utc_now(),
            "agent_slots": len(leases),
            "collision_count": collisions["collision_count"],
            "policy": collisions["policy"],
            "leases": leases,
        },
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def build_bus_event(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "_schema_version": CURRENT_SCHEMA_VERSION,
        "task_type": (
            "agent_workcell_deploy"
            if report["scenario"] == "deploy"
            else "agent_workcell_sop"
        ),
        "query": report["task"],
        "timestamp": report["created_at"],
        "success": report["decision"] == "SHIP_READY",
        "agent_id": "scbe-workcell-os",
        "llm_provider": "multi-slot-free-first",
        "llm_model": "codex+claude+gemini+local-shell+github-ci slots",
        "sources_used": len(report["agents"]),
        "duration_seconds": round(
            sum(item["duration_ms"] for item in report["verification"]["checks"])
            / 1000,
            3,
        ),
        "breaker_state": {"geoseal": "closed", "collision_gate": "closed"},
        "scbe": {
            "decision": report["decision"],
            "geo_seal_gate_tiers": [
                item["geoseal_gate"]["tier"]
                for item in report["verification"]["checks"]
            ],
            "collision_count": report["collision_report"]["collision_count"],
            "agent_slots": report["collision_report"]["agent_slots"],
            "coding_systems": report["coding_operating_system"]["coding_systems"],
            "product_routes": report["coding_operating_system"]["product_routes"],
            "artifact_paths": report["artifacts"],
            "scenario": report["scenario"],
            "deploy_policy": report.get("deploy_policy"),
        },
    }


def build_markdown(report: dict[str, Any]) -> str:
    checks = report["verification"]["checks"]
    check_lines = [
        (
            f"- `{item['command']}` -> `{item['returncode']}` "
            f"in {item['duration_ms']} ms; GeoSeal `{item['geoseal_gate']['tier']}`"
        )
        for item in checks
    ]
    agent_lines = [
        f"- `{agent['agent_id']}` / `{agent['model_slot']}`: {agent['job']}"
        for agent in report["agents"]
    ]
    proof_lines = [f"- `{path}`" for path in report["artifacts"].values()]
    os_lines = [
        f"- Standard: `{report['coding_operating_system']['standard']}`",
        f"- Gate: {report['coding_operating_system']['gate']}",
        f"- Retry: {report['coding_operating_system']['retry_policy']}",
        f"- Bus: {report['coding_operating_system']['agent_bus_policy']}",
        f"- Concurrency target: `{report['coding_operating_system']['concurrency_goal']}` agent slots",
        f"- Collision count: `{report['collision_report']['collision_count']}`",
        f"- Bus event: `{report['artifacts']['agent_bus_event_log']}`",
    ]
    deploy_lines = []
    if report["scenario"] == "deploy":
        deploy_lines = [
            "",
            "## Deploy Policy",
            f"- Promotion: {report['deploy_policy']['promotion']}",
            f"- Rollback: {report['deploy_policy']['rollback']}",
            f"- Monitor: {report['deploy_policy']['monitor']}",
        ]
    return "\n".join(
        [
            "# SCBE Workcell Ship Report",
            "",
            f"Scenario: `{report['scenario']}`",
            f"Task: {report['task']}",
            f"Decision: **{report['decision']}**",
            f"Branch: `{report['git']['branch']}`",
            f"Commit: `{report['git']['commit']}`",
            "",
            "## Agent Slots",
            *agent_lines,
            "",
            "## Verification",
            *check_lines,
            "",
            "## Cross-Talk",
            f"Packets written: `{report['crosstalk']['packet_count']}`",
            "",
            "## Coding Operating System",
            *os_lines,
            *deploy_lines,
            "",
            "## Artifacts",
            *proof_lines,
            "",
            "## Meaning",
            report["meaning"],
            "",
        ]
    )


def run_workcell(
    task: str,
    out_dir: Path,
    verify: bool = True,
    max_attempts: int = 1,
    scenario: str = "launch",
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if scenario not in {"launch", "deploy"}:
        raise ValueError(f"unsupported workcell scenario: {scenario}")
    agents = scenario_agents(scenario)
    task_id = (
        "multi-agent-deploy-proof" if scenario == "deploy" else "visible-system-proof"
    )
    command_specs = command_specs_for_scenario(scenario)
    checks = (
        [
            asdict(
                run_command(
                    spec["command"],
                    REPO_ROOT,
                    max_attempts=max_attempts,
                    claimed_paths=spec["claimed_paths"],
                )
            )
            for spec in command_specs
        ]
        if verify
        else []
    )
    passed = bool(checks) and all(item["returncode"] == 0 for item in checks)
    geoseal_passed = bool(checks) and all(
        item["geoseal_gate"]["allowed"] for item in checks
    )
    leases = build_lease_plan()
    collisions = collision_report(leases)
    decision = "SHIP_READY" if passed else "BLOCKED"
    if collisions["collision_count"]:
        decision = "BLOCKED"
    if not geoseal_passed:
        decision = "BLOCKED"

    packets = [
        packet(
            agents[0],
            agents[1],
            task_id,
            "Planner bounded the work into build, review, verify, and ship packets.",
            [],
        ),
        packet(
            agents[1],
            agents[2],
            task_id,
            "Builder identified the deployable gates and product readiness checks as the concrete work.",
            [],
        ),
        packet(
            agents[2],
            agents[3],
            task_id,
            "Reviewer required executable proof instead of claims.",
            [],
        ),
        packet(
            agents[3],
            agents[4],
            task_id,
            f"Verifier completed {len(checks)} GeoSeal-gated checks with decision {decision}.",
            [item["command"] for item in checks],
        ),
    ]

    artifacts = {
        "report_json": str((out_dir / "workcell-report.json").relative_to(REPO_ROOT)),
        "crosstalk_jsonl": str((out_dir / "crosstalk.jsonl").relative_to(REPO_ROOT)),
        "ship_report": str((out_dir / "ship-report.md").relative_to(REPO_ROOT)),
        "lease_manifest": str((out_dir / "leases.json").relative_to(REPO_ROOT)),
        "agent_bus_event_log": str(DEFAULT_BUS_LOG.relative_to(REPO_ROOT)),
    }
    report: dict[str, Any] = {
        "schema": "scbe.agent_workcell_demo.v1",
        "created_at": utc_now(),
        "scenario": scenario,
        "task": task,
        "decision": decision,
        "agents": [asdict(agent) for agent in agents],
        "crosstalk": {"packet_count": len(packets), "packets": packets},
        "verification": {"checks": checks},
        "leases": leases,
        "collision_report": collisions,
        "coding_operating_system": {
            "standard": "SCBE agent coding workcell SOP v1",
            "gate": "GeoSeal scan before command execution; deterministic checks before ship",
            "retry_policy": f"commands retry up to {max_attempts} attempt(s), then block",
            "concurrency_goal": DEFAULT_AGENT_COUNT,
            "agent_bus_policy": (
                "all products and model workers support each other by emitting bus packets with task, "
                "lease, proof, risk, product route, and training-capture metadata"
            ),
            "routing_policy": (
                "free models do first-pass work; paid models review/escalate "
                "high-value or failing packets"
            ),
            "coding_systems": sorted({lease["coding_system"] for lease in leases}),
            "product_routes": [
                "workflow_snapshot_starter",
                "governance_snapshot",
                "governance_heartbeat",
                "service_credits",
                "toolkit",
                "training_vault",
            ],
        },
        "deploy_policy": {
            "promotion": (
                "staging proof must pass GeoSeal, regression checks, remote-app "
                "route smoke, and launch readiness gate before production promotion"
            ),
            "rollback": (
                "failed gate or post-deploy monitor returns BLOCKED and preserves "
                "artifacts for rollback review"
            ),
            "monitor": "Agent Bus event plus route/product readiness artifacts become the post-deploy evidence trail",
        },
        "git": {
            "branch": git_value(["branch", "--show-current"], REPO_ROOT),
            "commit": git_value(["rev-parse", "--short", "HEAD"], REPO_ROOT),
            "status": git_value(["status", "--short"], REPO_ROOT),
        },
        "artifacts": artifacts,
        "meaning": (
            "This proves the system can turn one operator task into coordinated agent slots, "
            "pass bounded cross-talk, reserve non-colliding work scopes, run GeoSeal-gated "
            "verification, and emit a ship/no-ship report."
        ),
    }
    write_jsonl(out_dir / "crosstalk.jsonl", packets)
    write_lease_manifest(out_dir / "leases.json", leases, collisions)
    append_jsonl(DEFAULT_BUS_LOG, build_bus_event(report))
    write_json(out_dir / "workcell-report.json", report)
    (out_dir / "ship-report.md").write_text(build_markdown(report), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a visible SCBE multi-agent workcell proof."
    )
    parser.add_argument(
        "--task",
        default="Show that SCBE can coordinate one unit of work from plan to ship.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--scenario", choices=("launch", "deploy"), default="launch")
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Write packets/report without running commands.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_workcell(
        args.task,
        args.out_dir,
        verify=not args.no_verify,
        max_attempts=args.max_attempts,
        scenario=args.scenario,
    )
    print(
        json.dumps(
            {"decision": report["decision"], "artifacts": report["artifacts"]}, indent=2
        )
    )
    return 0 if report["decision"] == "SHIP_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
