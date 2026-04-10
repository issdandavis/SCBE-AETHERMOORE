#!/usr/bin/env python3
"""Bootstrap and verify the OpenClaw Hugging Face handler lane through the live gateway."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROFILE = "hf-agentic-handler"
DEFAULT_PROVIDER = "hf"
DEFAULT_LANE = "hydra-swarm"
DEFAULT_FORMATION = "hexagonal-ring"
DEFAULT_WORKFLOW_TEMPLATE = "training-center-loop"
DEFAULT_TASK = "Bootstrap the Hugging Face agent handler lane"
DEFAULT_TIMEOUT_MS = 120_000


@dataclass
class BootstrapPlan:
    repo_root: str
    probe_script: str
    node_bin: str
    profile: str
    provider: str
    lane: str
    formation: str
    workflow_template: str
    task: str
    dry_run: bool
    timeout_ms: int
    output_path: str


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def make_stamp(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y%m%dT%H%M%SZ")


def default_output_path(repo_root: Path, profile: str) -> Path:
    slug = profile.replace("_", "-").replace(" ", "-")
    return repo_root / "artifacts" / "openclaw-plugin" / f"{make_stamp()}-{slug}-bootstrap.json"


def build_plan(args: argparse.Namespace) -> BootstrapPlan:
    repo_root = Path(args.repo_root).resolve()
    probe_script = (
        Path(args.probe_script).resolve()
        if args.probe_script
        else repo_root / "scripts" / "system" / "openclaw_gateway_probe.mjs"
    )
    output_path = (
        Path(args.output_path).resolve()
        if args.output_path
        else default_output_path(repo_root, args.profile)
    )
    return BootstrapPlan(
        repo_root=str(repo_root),
        probe_script=str(probe_script),
        node_bin=args.node_bin,
        profile=args.profile,
        provider=args.provider,
        lane=args.lane,
        formation=args.formation,
        workflow_template=args.workflow_template,
        task=args.task,
        dry_run=not args.execute_dispatch,
        timeout_ms=args.timeout_ms,
        output_path=str(output_path),
    )


def _decode_json_blob(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    return json.loads(text)


def _probe(
    repo_root: Path,
    probe_script: Path,
    node_bin: str,
    timeout_ms: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = [
        node_bin,
        str(probe_script),
        "--method",
        method,
        "--params",
        json.dumps(params or {}, ensure_ascii=True),
        "--timeout-ms",
        str(timeout_ms),
    ]
    result = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    stream = result.stdout.strip() or result.stderr.strip()
    payload = _decode_json_blob(stream) if stream else None
    if result.returncode != 0:
        message = stream or f"Probe failed with exit code {result.returncode}"
        raise RuntimeError(message)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Probe returned non-object payload for {method}")
    return payload


def _extract_tool_names(payload: Any) -> list[str]:
    names: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for field in ("name", "id"):
                name = node.get(field)
                if isinstance(name, str) and (
                    name.startswith("scbe_")
                    or name == "browser"
                    or any(key in node for key in ("label", "description", "parameters", "pluginId"))
                ):
                    names.add(name)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return sorted(names)


def _extract_text_content(payload: Any) -> str:
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, list):
            for item in content:
                if (
                    isinstance(item, dict)
                    and item.get("type") == "text"
                    and isinstance(item.get("text"), str)
                ):
                    return item["text"]
        for value in payload.values():
            text = _extract_text_content(value)
            if text:
                return text
    elif isinstance(payload, list):
        for item in payload:
            text = _extract_text_content(item)
            if text:
                return text
    return ""


def _extract_tool_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _extract_text_content(payload)
    if text:
        decoded = _decode_json_blob(text)
        if isinstance(decoded, dict):
            return decoded
    response = payload.get("response")
    if isinstance(response, dict):
        return response
    return {}


def _health_ok(payload: dict[str, Any]) -> bool:
    response = payload.get("response")
    if isinstance(response, dict):
        if isinstance(response.get("ok"), bool):
            return bool(response["ok"])
        status = response.get("status")
        if isinstance(status, str):
            return status.lower() in {"ok", "healthy", "ready"}
    return False


def build_bootstrap_report(
    plan: BootstrapPlan,
    health_payload: dict[str, Any],
    catalog_payload: dict[str, Any],
    model_payload: dict[str, Any],
    dispatch_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tool_names = _extract_tool_names(catalog_payload)
    model_plan = _extract_tool_payload(model_payload)
    dispatch_plan = _extract_tool_payload(dispatch_payload or {}) if dispatch_payload else None
    required_tools = ["browser", "scbe_model_plan", "scbe_octoarms_dispatch"]
    missing_tools = [name for name in required_tools if name not in tool_names]
    return {
        "schema_version": "scbe_openclaw_hf_handler_bootstrap_v1",
        "generated_at": make_stamp(),
        "ready": _health_ok(health_payload) and not missing_tools and bool(model_plan),
        "plan": asdict(plan),
        "health": {
            "ok": _health_ok(health_payload),
            "payload": health_payload,
        },
        "catalog": {
            "tool_count": len(tool_names),
            "required_tools": required_tools,
            "missing_tools": missing_tools,
            "tool_names": tool_names,
        },
        "hf_handler": {
            "profile_id": model_plan.get("profile_id"),
            "base_model": model_plan.get("base_model"),
            "backend": model_plan.get("backend"),
            "ready": bool(model_plan.get("ready")),
            "total_train_rows": model_plan.get("total_train_rows"),
            "total_eval_rows": model_plan.get("total_eval_rows"),
            "missing_files": model_plan.get("missing_files", []),
            "payload": model_plan,
        },
        "dispatch": {
            "executed": dispatch_payload is not None,
            "dry_run": plan.dry_run,
            "payload": dispatch_plan,
        },
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe the live OpenClaw gateway and bootstrap the HF handler lane."
    )
    parser.add_argument("--repo-root", default=str(repo_root_from_script()))
    parser.add_argument("--probe-script", default="")
    parser.add_argument("--node-bin", default="node")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--lane", default=DEFAULT_LANE)
    parser.add_argument("--formation", default=DEFAULT_FORMATION)
    parser.add_argument("--workflow-template", default=DEFAULT_WORKFLOW_TEMPLATE)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--output-path", default="")
    parser.add_argument(
        "--execute-dispatch",
        action="store_true",
        help="Call scbe_octoarms_dispatch instead of stopping at model-plan verification.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(args)
    repo_root = Path(plan.repo_root)
    probe_script = Path(plan.probe_script)

    health_payload = _probe(repo_root, probe_script, plan.node_bin, plan.timeout_ms, "health")
    catalog_payload = _probe(
        repo_root, probe_script, plan.node_bin, plan.timeout_ms, "tools.catalog"
    )
    model_payload = _probe(
        repo_root,
        probe_script,
        plan.node_bin,
        plan.timeout_ms,
        "tools.invoke",
        {"tool": "scbe_model_plan", "args": {"profile": plan.profile}},
    )

    dispatch_payload: dict[str, Any] | None = None
    if args.execute_dispatch:
        dispatch_payload = _probe(
            repo_root,
            probe_script,
            plan.node_bin,
            plan.timeout_ms,
            "tools.invoke",
            {
                "tool": "scbe_octoarms_dispatch",
                "args": {
                    "task": plan.task,
                    "lane": plan.lane,
                    "formation": plan.formation,
                    "workflowTemplate": plan.workflow_template,
                    "provider": plan.provider,
                    "dryRun": False,
                },
            },
        )

    payload = build_bootstrap_report(
        plan, health_payload, catalog_payload, model_payload, dispatch_payload
    )
    output_path = Path(plan.output_path)
    write_report(output_path, payload)

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"OpenClaw health: {'ok' if payload['health']['ok'] else 'not ready'}")
    print(
        f"Required tools present: {'yes' if not payload['catalog']['missing_tools'] else 'no'}"
    )
    print(
        f"HF handler profile: {payload['hf_handler']['profile_id']} ({payload['hf_handler']['base_model']})"
    )
    print(f"HF handler ready: {'yes' if payload['hf_handler']['ready'] else 'no'}")
    print(f"Artifact: {output_path}")
    if payload["catalog"]["missing_tools"]:
        print(f"Missing tools: {', '.join(payload['catalog']['missing_tools'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
