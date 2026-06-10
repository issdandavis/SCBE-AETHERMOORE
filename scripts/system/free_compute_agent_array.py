#!/usr/bin/env python3
"""Build a governed free-compute agent array plan for coding work.

This planner does not spawn remote machines directly. It turns a project goal
into bounded task packets that can be claimed by the existing dispatch spine and
run on local, GitHub Actions, Colab, Kaggle, or Hugging Face lanes.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crypto.sacred_tongue_payload_bijection import prove_dict  # noqa: E402

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "free_compute_agent_array"
CAPABILITY_REGISTRY = (
    REPO_ROOT / "config" / "system" / "advanced_ai_dispatch_capabilities.json"
)
HOST_COMPUTE_ROUTES = REPO_ROOT / "config" / "system" / "host_compute_routes.json"

SENSITIVE_PATH_MARKERS = (
    ".env",
    "connector_oauth",
    "secrets",
    "private",
    "tax",
    "credential",
    "key",
    "token",
)

DEFAULT_WORKSTREAMS: list[dict[str, Any]] = [
    {
        "lane": "inventory",
        "capability": "relay.sync",
        "owner_role": "agent.sync",
        "target_paths": [
            "package.json",
            "pyproject.toml",
            "pytest.ini",
            "tsconfig.json",
        ],
        "goal_suffix": "map entrypoints, test commands, and current build shape before edits",
        "compute_target": "github_actions",
        "quest_state": "DISCOVERED",
        "verification": 'python scripts/system/free_compute_agent_array.py --goal "{goal}" --workers {workers} --check',
        "risk": "low",
    },
    {
        "lane": "repo_shape",
        "capability": "relay.sync",
        "owner_role": "agent.sync",
        "target_paths": ["src/", "api/", "python/", "agents/", "scripts/"],
        "goal_suffix": "convert repository shape into bounded agent work slots",
        "compute_target": "github_actions",
        "quest_state": "MAPPED",
        "verification": "npm run repo:shape",
        "risk": "low",
    },
    {
        "lane": "tests",
        "capability": "code.patch",
        "owner_role": "agent.code",
        "target_paths": ["tests/"],
        "goal_suffix": "add or repair focused regression tests for the next coding change",
        "compute_target": "github_actions",
        "quest_state": "TESTED",
        "verification": "pytest tests/ -q",
        "risk": "medium",
    },
    {
        "lane": "cli",
        "capability": "code.patch",
        "owner_role": "agent.code",
        "target_paths": ["bin/", "src/geoseal_cli.py", "scripts/system/"],
        "goal_suffix": "improve command-line and operator entrypoints without changing unrelated APIs",
        "compute_target": "github_actions",
        "quest_state": "PATCHED",
        "verification": "npm run benchmark:cli",
        "risk": "medium",
    },
    {
        "lane": "api_bridge",
        "capability": "code.patch",
        "owner_role": "agent.code",
        "target_paths": ["api/", "src/api/"],
        "goal_suffix": "patch API or bridge surfaces behind existing request boundaries",
        "compute_target": "github_actions",
        "quest_state": "PATCHED",
        "verification": "npm run typecheck",
        "risk": "medium",
    },
    {
        "lane": "training_bucket",
        "capability": "code.patch",
        "owner_role": "agent.code",
        "target_paths": ["training-data/", "scripts/training/", "scripts/eval/"],
        "goal_suffix": "bucket training data and emit small verifiable SFT/eval artifacts",
        "compute_target": "colab",
        "quest_state": "BUCKETED",
        "verification": "npm run training:run-ledger",
        "risk": "medium",
    },
    {
        "lane": "dataset_compute",
        "capability": "code.patch",
        "owner_role": "agent.code",
        "target_paths": ["notebooks/", "scripts/kaggle_auto/", "scripts/hf_jobs/"],
        "goal_suffix": "prepare notebook or remote dataset job that can run outside the local disk pressure zone",
        "compute_target": "kaggle",
        "quest_state": "STAGED",
        "verification": "npm run training:preflight:zero-cost",
        "risk": "medium",
    },
    {
        "lane": "demo_surface",
        "capability": "website.surface",
        "owner_role": "agent.website",
        "target_paths": ["docs/", "api/", "scripts/system/"],
        "goal_suffix": "surface the working result as a website or bridge demo with minimal deployment risk",
        "compute_target": "huggingface_spaces",
        "quest_state": "SURFACED",
        "verification": "npm run docs:check",
        "risk": "medium",
    },
    {
        "lane": "workflow_ci",
        "capability": "code.patch",
        "owner_role": "agent.code",
        "target_paths": [".github/workflows/", "scripts/system/"],
        "goal_suffix": "wire a remote validation lane that reports artifacts and does not require local disk space",
        "compute_target": "github_actions",
        "quest_state": "ROUTED",
        "verification": "gh workflow list",
        "risk": "medium",
    },
    {
        "lane": "integration_review",
        "capability": "relay.sync",
        "owner_role": "agent.sync",
        "target_paths": [
            "artifacts/free_compute_agent_array/",
            "artifacts/dispatch_spine/",
        ],
        "goal_suffix": "review claimed work, merge evidence, and decide promote/rework/scrap",
        "compute_target": "local",
        "quest_state": "MERGED",
        "verification": "python scripts/system/advanced_ai_dispatch.py status --limit 20",
        "risk": "high",
    },
]

COMPUTE_TARGETS: dict[str, dict[str, Any]] = {
    "local": {
        "cost_model": "local energy and local disk only",
        "best_for": ["secrets", "integration", "final review", "dirty worktree"],
        "remote_ok": False,
        "notes": "Use for sensitive or merge authority work.",
    },
    "github_actions": {
        "cost_model": "free for public standard runners; private repos use included monthly minutes",
        "best_for": ["lint", "tests", "build", "matrix jobs", "artifact reports"],
        "remote_ok": True,
        "notes": "Good default for counting, test, and CI shape work.",
    },
    "colab": {
        "cost_model": "free tier exists, but resources are dynamic and not guaranteed",
        "best_for": ["notebooks", "small training", "GPU experiments"],
        "remote_ok": True,
        "notes": "Do not send confidential prompts, secrets, or private code snippets.",
    },
    "kaggle": {
        "cost_model": "free notebook compute with usage quotas and account limits",
        "best_for": ["dataset notebooks", "GPU/TPU experiments", "published kernels"],
        "remote_ok": True,
        "notes": "Keep kernels deterministic and small enough to rerun.",
    },
    "huggingface_spaces": {
        "cost_model": "free CPU Basic Space by default; paid hardware requires explicit upgrade",
        "best_for": ["demo UI", "light API", "artifact viewer", "task scheduler demo"],
        "remote_ok": True,
        "notes": "Use secrets through Space settings, not committed files.",
    },
}

ACHIEVEMENT_CHAIN = [
    "QUEST_CREATED",
    "DISCOVERED",
    "MAPPED",
    "STAGED",
    "PATCHED",
    "TESTED",
    "SURFACED",
    "MERGED",
]


@dataclass(frozen=True)
class WorkPacket:
    task_id: str
    row: int
    lane: str
    title: str
    goal: str
    capability: str
    owner_role: str
    compute_target: str
    remote_ok: bool
    risk: str
    priority: int
    target_paths: list[str]
    blocked_paths: list[str]
    dependencies: list[str]
    quest_state: str
    achievements: list[str]
    matrix_query: str
    claim_command: str
    verify_command: str
    acceptance: list[str]
    training_signal: dict[str, Any]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_slug(value: str) -> str:
    chars = []
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "-":
            chars.append("-")
    return "".join(chars).strip("-")[:42] or "agent-array"


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def compute_remote_ok(target: str, paths: list[str], risk: str) -> bool:
    if target == "local" or risk == "high":
        return False
    lowered = " ".join(paths).lower()
    return not any(marker in lowered for marker in SENSITIVE_PATH_MARKERS)


def build_acceptance(lane: str, verify_command: str) -> list[str]:
    return [
        f"{lane} packet only changes its declared target paths",
        "worker records changed files, commands run, and blockers",
        f"verification command succeeds or failure evidence names the blocker: {verify_command}",
    ]


def build_training_signal(
    goal: str, lane: str, state: str, target_paths: list[str]
) -> dict[str, Any]:
    return {
        "record_type": "agentic_quest_marker",
        "input_command": goal,
        "lane": lane,
        "expected_state": state,
        "target_paths": target_paths,
        "feedback_fields": [
            "result_summary",
            "changed_files",
            "tests",
            "blockers",
            "next_state",
        ],
    }


def build_packets(goal: str, workers: int) -> list[WorkPacket]:
    if workers < 1:
        raise ValueError("--workers must be at least 1")
    selected = [
        DEFAULT_WORKSTREAMS[index % len(DEFAULT_WORKSTREAMS)]
        for index in range(workers)
    ]
    packets: list[WorkPacket] = []
    goal_slug = safe_slug(goal)
    for index, stream in enumerate(selected, start=1):
        row = index
        lane = str(stream["lane"])
        task_id = f"array-{goal_slug}-{row:02d}"
        target_paths = list(stream["target_paths"])
        compute_target = str(stream["compute_target"])
        risk = str(stream["risk"])
        remote_ok = compute_remote_ok(compute_target, target_paths, risk)
        if not remote_ok:
            compute_target = "local"
        dependencies = [] if row <= 2 else [packets[0].task_id]
        if lane == "integration_review":
            dependencies = [packet.task_id for packet in packets]
        verify_command = str(stream["verification"]).format(goal=goal, workers=workers)
        worker_id = f"{lane}-{row:02d}"
        claim_command = (
            "python scripts/system/advanced_ai_dispatch.py claim "
            f"--worker-id {worker_id} --capability {stream['capability']}"
        )
        achievements = ["QUEST_CREATED", str(stream["quest_state"])]
        if stream["quest_state"] not in ACHIEVEMENT_CHAIN:
            achievements.append("CUSTOM_STATE")
        matrix_query = (
            "SELECT * FROM agent_array "
            f"WHERE status = 'queued' AND lane = '{lane}' "
            f"AND compute_target = '{compute_target}' ORDER BY priority DESC, row ASC;"
        )
        packets.append(
            WorkPacket(
                task_id=task_id,
                row=row,
                lane=lane,
                title=f"{lane.replace('_', ' ').title()} - {goal[:72]}",
                goal=f"{goal}: {stream['goal_suffix']}",
                capability=str(stream["capability"]),
                owner_role=str(stream["owner_role"]),
                compute_target=compute_target,
                remote_ok=remote_ok,
                risk=risk,
                priority=max(10, 100 - (row * 3)),
                target_paths=target_paths,
                blocked_paths=[
                    "config/connector_oauth/",
                    ".env",
                    "*.pem",
                    "*.key",
                    "personal/tax/",
                ],
                dependencies=dependencies,
                quest_state=str(stream["quest_state"]),
                achievements=achievements,
                matrix_query=matrix_query,
                claim_command=claim_command,
                verify_command=verify_command,
                acceptance=build_acceptance(lane, verify_command),
                training_signal=build_training_signal(
                    goal, lane, str(stream["quest_state"]), target_paths
                ),
            )
        )
    return packets


def dispatch_payload(packet: WorkPacket) -> dict[str, Any]:
    return {
        "task_id": packet.task_id,
        "lane": packet.lane,
        "compute_target": packet.compute_target,
        "remote_ok": packet.remote_ok,
        "quest_state": packet.quest_state,
        "achievements": packet.achievements,
        "matrix_query": packet.matrix_query,
        "verify_command": packet.verify_command,
        "acceptance": packet.acceptance,
        "training_signal": packet.training_signal,
    }


def enqueue_command(packet: WorkPacket) -> str:
    deps = " ".join(f"--dependency {shell_quote(dep)}" for dep in packet.dependencies)
    payload = json.dumps(
        dispatch_payload(packet), sort_keys=True, separators=(",", ":")
    )
    return (
        "python scripts/system/advanced_ai_dispatch.py enqueue "
        f"--title {shell_quote(packet.title)} "
        f"--goal {shell_quote(packet.goal)} "
        f"--capability {shell_quote(packet.capability)} "
        f"--priority {packet.priority} "
        f"--owner-role {shell_quote(packet.owner_role)} "
        "--requested-by agent.free_compute_array "
        f"--write-scope {shell_quote(','.join(packet.target_paths))} "
        f"{deps} "
        f"--payload {shell_quote(payload)} "
        f"--notes {shell_quote('Generated by free_compute_agent_array.py')} "
        "--evidence-required"
    ).strip()


def plan_summary(goal: str, workers: int, packets: list[WorkPacket]) -> dict[str, Any]:
    capabilities = load_json(CAPABILITY_REGISTRY)
    host_routes = load_json(HOST_COMPUTE_ROUTES)
    return {
        "ok": True,
        "generated_at": utc_stamp(),
        "goal": goal,
        "workers": workers,
        "packet_count": len(packets),
        "compute_targets": COMPUTE_TARGETS,
        "achievement_chain": ACHIEVEMENT_CHAIN,
        "capability_registry_found": bool(capabilities),
        "host_compute_routes_found": bool(host_routes),
        "host_compute_connected": (
            host_routes.get("summary", {})
            if isinstance(host_routes.get("summary"), dict)
            else {}
        ),
        "packets": [asdict(packet) for packet in packets],
    }


def write_outputs(
    goal: str, workers: int, out_dir: Path, packets: list[WorkPacket]
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = plan_summary(goal, workers, packets)
    plan["sacred_tongue_bijection"] = prove_dict(plan)

    plan_path = out_dir / "latest_plan.json"
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    jsonl_path = out_dir / "latest_task_queue.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for packet in packets:
            handle.write(json.dumps(asdict(packet), sort_keys=True) + "\n")

    training_path = out_dir / "latest_training_markers.jsonl"
    with training_path.open("w", encoding="utf-8") as handle:
        for packet in packets:
            marker = {
                "task_id": packet.task_id,
                "record_type": "choicescript_agentic_loop",
                "input": packet.goal,
                "choice": packet.lane,
                "state": packet.quest_state,
                "achievements": packet.achievements,
                "expected_output": {
                    "changed_paths": packet.target_paths,
                    "verification": packet.verify_command,
                    "evidence_required": True,
                },
            }
            handle.write(json.dumps(marker, sort_keys=True) + "\n")

    csv_path = out_dir / "latest_matrix.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "row",
                "task_id",
                "lane",
                "compute_target",
                "remote_ok",
                "risk",
                "capability",
                "priority",
                "target_paths",
                "dependencies",
                "quest_state",
                "verify_command",
                "matrix_query",
            ],
        )
        writer.writeheader()
        for packet in packets:
            writer.writerow(
                {
                    "row": packet.row,
                    "task_id": packet.task_id,
                    "lane": packet.lane,
                    "compute_target": packet.compute_target,
                    "remote_ok": packet.remote_ok,
                    "risk": packet.risk,
                    "capability": packet.capability,
                    "priority": packet.priority,
                    "target_paths": ";".join(packet.target_paths),
                    "dependencies": ";".join(packet.dependencies),
                    "quest_state": packet.quest_state,
                    "verify_command": packet.verify_command,
                    "matrix_query": packet.matrix_query,
                }
            )

    commands_path = out_dir / "enqueue_dispatch_commands.ps1"
    command_lines = ["python scripts/system/advanced_ai_dispatch.py init"]
    command_lines.extend(enqueue_command(packet) for packet in packets)
    commands_path.write_text("\n".join(command_lines) + "\n", encoding="utf-8")

    readme_path = out_dir / "README.md"
    lines = [
        "# Free Compute Agent Array",
        "",
        f"Goal: {goal}",
        f"Workers: {workers}",
        "",
        "This is a governed dispatch matrix. It does not spawn remote machines by itself.",
        "Run `enqueue_dispatch_commands.ps1` only when the task list looks right.",
        "",
        "## Loop Markers",
        "",
        ", ".join(ACHIEVEMENT_CHAIN),
        "",
        "## Files",
        "",
        "- `latest_plan.json` - complete machine-readable plan",
        "- `latest_matrix.csv` - spreadsheet view",
        "- `latest_task_queue.jsonl` - packet queue export",
        "- `latest_training_markers.jsonl` - ChoiceScript-style training markers",
        "- `enqueue_dispatch_commands.ps1` - commands for the SQLite dispatch spine",
        "",
    ]
    readme_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "plan": str(plan_path),
        "matrix": str(csv_path),
        "task_queue": str(jsonl_path),
        "training_markers": str(training_path),
        "enqueue_commands": str(commands_path),
        "readme": str(readme_path),
    }


def check_plan(packets: list[WorkPacket]) -> dict[str, Any]:
    problems: list[str] = []
    seen_ids: set[str] = set()
    for packet in packets:
        if packet.task_id in seen_ids:
            problems.append(f"duplicate task_id: {packet.task_id}")
        seen_ids.add(packet.task_id)
        if packet.compute_target not in COMPUTE_TARGETS:
            problems.append(
                f"unknown compute target for {packet.task_id}: {packet.compute_target}"
            )
        if packet.remote_ok and packet.risk == "high":
            problems.append(f"high-risk packet marked remote_ok: {packet.task_id}")
        if not packet.target_paths:
            problems.append(f"missing target paths: {packet.task_id}")
        for dependency in packet.dependencies:
            if dependency not in seen_ids and packet.lane != "integration_review":
                problems.append(
                    f"dependency not emitted before packet {packet.task_id}: {dependency}"
                )
    return {"ok": not problems, "problems": problems, "packet_count": len(packets)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--goal", required=True, help="Project goal to split into agent work packets."
    )
    parser.add_argument(
        "--workers", type=int, default=10, help="Number of agent packets to create."
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--check", action="store_true", help="Only validate the generated plan."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    packets = build_packets(args.goal, args.workers)
    check = check_plan(packets)
    if args.check:
        print(json.dumps(check, indent=2, sort_keys=True))
        return 0 if check["ok"] else 1
    if not check["ok"]:
        print(json.dumps(check, indent=2, sort_keys=True))
        return 1
    outputs = write_outputs(args.goal, args.workers, args.out_dir, packets)
    result = {"ok": True, "outputs": outputs, "packet_count": len(packets)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
