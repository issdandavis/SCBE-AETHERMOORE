#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from hydra.llm_providers import DEFAULT_LOCAL_BASE_URL, DEFAULT_OLLAMA_BASE_URL

DEFAULT_HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_LOCAL_MODEL = "local-model"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
LANES = {
    "none",
    "octoarmor-triage",
    "hydra-swarm",
    "browse-evidence",
    "colab-bridge-status",
    "colab-bridge-probe",
}
FORMATION_ALIASES: dict[str, str] = {
    "hexagonal": "hexagonal",
    "hexagonal-ring": "hexagonal",
    "tetrahedral": "tetrahedral",
    "concentric": "concentric",
    "ring": "concentric",
    "adaptive-scatter": "adaptive-scatter",
    "scatter": "adaptive-scatter",
}


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slugify(text: str) -> str:
    cleaned = []
    previous_dash = False
    for ch in text.lower():
        if ch.isalnum():
            cleaned.append(ch)
            previous_dash = False
        elif not previous_dash:
            cleaned.append("-")
            previous_dash = True
    slug = "".join(cleaned).strip("-")
    return slug or "task"


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    result = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    return {
        "command": command,
        "command_text": subprocess.list2cmdline(command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_formation(name: str) -> str:
    normalized = FORMATION_ALIASES.get(str(name).strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported formation '{name}'")
    return normalized


def _build_paths(repo_root: Path, task: str) -> dict[str, Path]:
    stamp = _now_stamp()
    slug = _slugify(task)
    base = repo_root / "artifacts" / "octoarms_dispatch"
    base.mkdir(parents=True, exist_ok=True)
    return {
        "plan": base / f"{stamp}-{slug}-plan.json",
        "packets": base / f"{stamp}-{slug}-packets.json",
        "browse": base / f"{stamp}-{slug}-browse.json",
        "summary": base / f"{stamp}-{slug}-summary.json",
        "action_root": repo_root / "training" / "runs" / "action_maps" / f"{stamp}-{slug}-octoarms",
    }


def _octoarmor_triage(repo_root: Path, task: str, provider: str, model: str | None) -> dict[str, Any]:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.aetherbrowser.router import OctoArmorRouter

    router = OctoArmorRouter(local_first=True)
    complexity = router.score_complexity(task).value
    provider_snapshot = router.provider_status_snapshot()
    resolved_provider = provider
    if provider == "auto":
        resolved_provider = "local" if complexity == "low" else "hf"
    if model:
        resolved_model = model
    elif resolved_provider == "ollama":
        resolved_model = DEFAULT_OLLAMA_MODEL
    elif resolved_provider == "local":
        resolved_model = DEFAULT_LOCAL_MODEL
    else:
        resolved_model = DEFAULT_HF_MODEL
    return {
        "complexity": complexity,
        "provider_snapshot": provider_snapshot,
        "recommended_provider": resolved_provider,
        "recommended_model": resolved_model,
        "selection_policy": "low-cost overlay on OctoArmor complexity scoring",
    }


def _flow_plan(
    repo_root: Path,
    task: str,
    formation: str,
    workflow_template: str,
    plan_path: Path,
    action_root: Path,
    emit_action_map: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/scbe-system-cli.py",
        "flow",
        "plan",
        "--task",
        task,
        "--formation",
        formation,
        "--workflow-template",
        workflow_template,
        "--output",
        _relative_to_repo(plan_path, repo_root),
    ]
    if emit_action_map:
        command += ["--action-root", _relative_to_repo(action_root, repo_root)]
    else:
        command.append("--no-action-map")
    return _run(command, repo_root)


def _flow_packetize(
    repo_root: Path,
    plan_path: Path,
    packets_path: Path,
    support_units: int,
    action_root: Path,
    emit_action_map: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/scbe-system-cli.py",
        "flow",
        "packetize",
        "--plan",
        _relative_to_repo(plan_path, repo_root),
        "--support-units",
        str(support_units),
        "--output",
        _relative_to_repo(packets_path, repo_root),
    ]
    if emit_action_map:
        command += ["--action-root", _relative_to_repo(action_root, repo_root)]
    else:
        command.append("--no-action-map")
    return _run(command, repo_root)


def _hydra_swarm_run(
    repo_root: Path,
    task: str,
    provider: str,
    model: str,
    backend: str,
    base_url: str,
    dry_run: bool,
) -> dict[str, Any]:
    if provider == "ollama" and base_url == DEFAULT_LOCAL_BASE_URL:
        base_url = DEFAULT_OLLAMA_BASE_URL
    command = [
        sys.executable,
        "-m",
        "hydra.cli_swarm",
        "--provider",
        provider,
        "--model",
        model,
        "--backend",
        backend,
    ]
    if provider in {"local", "ollama"}:
        command += ["--base-url", base_url]
    if dry_run:
        command.append("--dry-run")
    command.append(task)
    return _run(command, repo_root)


def _browse_evidence_run(repo_root: Path, url: str, browse_path: Path) -> dict[str, Any]:
    skill_script = (
        Path.home()
        / ".codex"
        / "skills"
        / "hydra-node-terminal-browsing"
        / "scripts"
        / "hydra_terminal_browse.mjs"
    )
    if not skill_script.exists():
        return {
            "command": ["node", str(skill_script), "--url", url],
            "command_text": f"node {skill_script} --url {url}",
            "returncode": 2,
            "stdout": "",
            "stderr": f"Missing hydra terminal browsing script: {skill_script}",
        }
    command = [
        "node",
        str(skill_script),
        "--url",
        url,
        "--out",
        _relative_to_repo(browse_path, repo_root),
    ]
    return _run(command, repo_root)


def _colab_bridge_run(repo_root: Path, subcommand: str, bridge_name: str) -> dict[str, Any]:
    command = [sys.executable, "scbe.py", "colab", subcommand, "--name", bridge_name]
    return _run(command, repo_root)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Packetize Octo Arms swarm work and launch a selected execution lane."
    )
    parser.add_argument(
        "--repo-root",
        default="C:/Users/issda/SCBE-AETHERMOORE",
        help="Repo root that contains scbe.py and hydra modules",
    )
    parser.add_argument("--task", required=True, help="Mission or objective to route through the swarm")
    parser.add_argument(
        "--formation",
        default="hexagonal",
        choices=tuple(sorted(FORMATION_ALIASES)),
        help="Swarm geometry to use for packet ordering (canonical and skill-level aliases accepted)",
    )
    parser.add_argument(
        "--workflow-template",
        default="implementation-loop",
        choices=["architecture-enhancement", "implementation-loop", "training-center-loop"],
    )
    parser.add_argument("--support-units", type=int, default=0, help="Extra support units per step during packetization")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "local", "ollama", "hf"],
        help="Execution provider for hydra-swarm runs",
    )
    parser.add_argument("--model", default=None, help="Explicit model name or Hugging Face model id")
    parser.add_argument("--backend", default="playwright", choices=["playwright", "selenium", "cdp"])
    parser.add_argument("--base-url", default=DEFAULT_LOCAL_BASE_URL, help="Base URL for local HYDRA provider")
    parser.add_argument("--lane", default="octoarmor-triage", choices=sorted(LANES))
    parser.add_argument("--bridge-name", default="pivot", help="Colab bridge profile name")
    parser.add_argument("--url", default=None, help="URL for browse-evidence lane")
    parser.add_argument("--dry-run", action="store_true", help="Use dry-run where the selected lane supports it")
    parser.add_argument("--no-action-map", action="store_true", help="Skip action-map emission in flow plan and packetization")
    parser.add_argument("--json", action="store_true", help="Print the final summary JSON to stdout")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    if not repo_root.exists():
        print(f"Repo root not found: {repo_root}", file=sys.stderr)
        return 2

    requested_formation = args.formation
    formation = _normalize_formation(requested_formation)
    paths = _build_paths(repo_root, args.task)
    emit_action_map = not args.no_action_map
    routing = _octoarmor_triage(repo_root, args.task, args.provider, args.model)

    plan_run = _flow_plan(
        repo_root=repo_root,
        task=args.task,
        formation=formation,
        workflow_template=args.workflow_template,
        plan_path=paths["plan"],
        action_root=paths["action_root"],
        emit_action_map=emit_action_map,
    )
    if plan_run["returncode"] != 0:
        print(plan_run["stdout"], end="")
        print(plan_run["stderr"], file=sys.stderr, end="")
        return plan_run["returncode"]

    packet_run = _flow_packetize(
        repo_root=repo_root,
        plan_path=paths["plan"],
        packets_path=paths["packets"],
        support_units=args.support_units,
        action_root=paths["action_root"],
        emit_action_map=emit_action_map,
    )
    if packet_run["returncode"] != 0:
        print(packet_run["stdout"], end="")
        print(packet_run["stderr"], file=sys.stderr, end="")
        return packet_run["returncode"]

    lane_result: dict[str, Any] = {"name": args.lane, "status": "skipped"}
    if args.lane == "octoarmor-triage":
        lane_result = {
            "name": args.lane,
            "status": "completed",
            "routing": routing,
        }
    elif args.lane == "hydra-swarm":
        lane_result = _hydra_swarm_run(
            repo_root=repo_root,
            task=args.task,
            provider=routing["recommended_provider"],
            model=routing["recommended_model"],
            backend=args.backend,
            base_url=args.base_url,
            dry_run=args.dry_run,
        )
        lane_result["name"] = args.lane
        lane_result["routing"] = routing
    elif args.lane == "browse-evidence":
        if not args.url:
            print("--url is required for browse-evidence", file=sys.stderr)
            return 2
        lane_result = _browse_evidence_run(repo_root, args.url, paths["browse"])
        lane_result["name"] = args.lane
        lane_result["routing"] = routing
        lane_result["browse_output"] = _relative_to_repo(paths["browse"], repo_root)
    elif args.lane == "colab-bridge-status":
        lane_result = _colab_bridge_run(repo_root, "bridge-status", args.bridge_name)
        lane_result["name"] = args.lane
        lane_result["routing"] = routing
    elif args.lane == "colab-bridge-probe":
        lane_result = _colab_bridge_run(repo_root, "bridge-probe", args.bridge_name)
        lane_result["name"] = args.lane
        lane_result["routing"] = routing

    plan_payload = _load_json(paths["plan"])
    packet_payload = _load_json(paths["packets"])
    summary = {
        "schema_version": "octoarms_dispatch_v1",
        "generated_at": _now_iso(),
        "repo_root": str(repo_root),
        "task": args.task,
        "routing": routing,
        "flow": {
            "plan_path": _relative_to_repo(paths["plan"], repo_root),
            "packet_path": _relative_to_repo(paths["packets"], repo_root),
            "formation": formation,
            "requested_formation": requested_formation,
            "workflow_template": args.workflow_template,
            "support_units": args.support_units,
            "agent_count": plan_payload.get("formation", {}).get("agent_count"),
            "packet_count": packet_payload.get("packet_count"),
            "action_map_enabled": emit_action_map,
        },
        "intent_packet": {
            "tongue": "KO",
            "status": "planned",
            "gate": "pending external intent-auth execution",
        },
        "lane": lane_result,
    }
    paths["summary"].write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    else:
        print(f"Plan: {_relative_to_repo(paths['plan'], repo_root)}")
        print(f"Packets: {_relative_to_repo(paths['packets'], repo_root)}")
        print(f"Lane: {args.lane}")
        print(f"Recommended provider/model: {routing['recommended_provider']} / {routing['recommended_model']}")
        print(f"Summary: {_relative_to_repo(paths['summary'], repo_root)}")
        if isinstance(lane_result, dict) and lane_result.get("returncode") is not None:
            print(f"Lane return code: {lane_result['returncode']}")

    if isinstance(lane_result, dict) and lane_result.get("returncode") not in (None, 0):
        return int(lane_result["returncode"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
