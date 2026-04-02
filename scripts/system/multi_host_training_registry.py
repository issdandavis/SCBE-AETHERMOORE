#!/usr/bin/env python3
"""Register, promote, and export multi-host training runs.

This keeps Colab/Kaggle/HF-Jobs runs in one candidate registry and lets one
run per track be promoted as the current winner. Exported provider manifests
remain compatible with ``training/federated_orchestrator.py``.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "training" / "runs" / "multi_host_registry.json"
SUPPORTED_HOSTS = {"colab", "kaggle", "hf_jobs", "local"}
SUPPORTED_PROVIDERS = {"hf", "gcp", "aws"}
SUPPORTED_ROLES = {"textgen", "embed", "runtime"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "multi_host_training_registry_v1",
            "updated_at": utc_now(),
            "runs": [],
            "promotions": {},
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Registry at {path} must be a JSON object")
    data.setdefault("schema_version", "multi_host_training_registry_v1")
    data.setdefault("updated_at", utc_now())
    data.setdefault("runs", [])
    data.setdefault("promotions", {})
    if not isinstance(data["runs"], list):
        raise ValueError(f"Registry at {path} must contain a 'runs' list")
    if not isinstance(data["promotions"], dict):
        raise ValueError(f"Registry at {path} must contain a 'promotions' object")
    return data


def save_registry(path: Path, registry: dict[str, Any]) -> None:
    registry["updated_at"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def _validate_metric(metrics: dict[str, Any], key: str) -> float:
    value = metrics.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Missing numeric metric '{key}'")
    return float(value)


def validate_run_payload(payload: dict[str, Any]) -> None:
    if payload["host"] not in SUPPORTED_HOSTS:
        raise ValueError(f"Unsupported host: {payload['host']}")
    if payload["provider"] not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {payload['provider']}")
    if payload["role"] not in SUPPORTED_ROLES:
        raise ValueError(f"Unsupported role: {payload['role']}")

    metrics = payload["metrics"]
    for key in ("quality", "safety", "latency_ms_p95", "cost_per_1k_tokens"):
        _validate_metric(metrics, key)

    artifact = payload["artifact"]
    if not artifact.get("id") or not artifact.get("uri"):
        raise ValueError("Artifact must include non-empty 'id' and 'uri'")


def upsert_run(registry: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    validate_run_payload(payload)
    runs = registry["runs"]
    for index, existing in enumerate(runs):
        if existing.get("run_id") == payload["run_id"]:
            payload["created_at"] = existing.get("created_at", utc_now())
            runs[index] = payload
            return payload

    runs.append(payload)
    return payload


def find_run(registry: dict[str, Any], run_id: str) -> dict[str, Any]:
    for run in registry["runs"]:
        if run.get("run_id") == run_id:
            return run
    raise ValueError(f"Run '{run_id}' not found")


def promote_run(registry: dict[str, Any], run_id: str) -> dict[str, Any]:
    run = find_run(registry, run_id)
    track = run["role"]

    previous = registry["promotions"].get(track)
    if isinstance(previous, dict):
        previous_run_id = previous.get("run_id")
        if previous_run_id and previous_run_id != run_id:
            old = find_run(registry, previous_run_id)
            if old.get("status") == "promoted":
                old["status"] = "candidate"

    run["status"] = "promoted"
    promotion = {
        "run_id": run_id,
        "provider": run["provider"],
        "host": run["host"],
        "artifact_id": run["artifact"]["id"],
        "artifact_uri": run["artifact"]["uri"],
        "promoted_at": utc_now(),
    }
    registry["promotions"][track] = promotion
    return promotion


def provider_manifest_from_registry(registry: dict[str, Any], provider: str) -> dict[str, Any]:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")

    promoted_run_ids = {
        value["run_id"]
        for value in registry["promotions"].values()
        if isinstance(value, dict) and value.get("provider") == provider and value.get("run_id")
    }
    promoted_runs = [
        run
        for run in registry["runs"]
        if run.get("run_id") in promoted_run_ids and run.get("provider") == provider
    ]
    if not promoted_runs:
        raise ValueError(f"No promoted runs found for provider '{provider}'")

    artifacts = []
    for run in promoted_runs:
        artifacts.append(
            {
                "id": run["artifact"]["id"],
                "role": run["role"],
                "metrics": run["metrics"],
                "uri": run["artifact"]["uri"],
                "metadata": {
                    "host": run["host"],
                    "base_model": run.get("base_model"),
                    "dataset_repo": run.get("dataset_repo"),
                    "dataset_revision": run.get("dataset_revision"),
                    "run_id": run["run_id"],
                },
            }
        )

    return {"provider": provider, "artifacts": artifacts}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage multi-host SCBE training runs")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Registry JSON path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register or update a training run")
    register.add_argument("--run-id", required=True)
    register.add_argument("--host", required=True, choices=sorted(SUPPORTED_HOSTS))
    register.add_argument("--provider", required=True, choices=sorted(SUPPORTED_PROVIDERS))
    register.add_argument("--role", required=True, choices=sorted(SUPPORTED_ROLES))
    register.add_argument("--base-model", required=True)
    register.add_argument("--dataset-repo", required=True)
    register.add_argument("--dataset-revision", required=True)
    register.add_argument("--artifact-id", required=True)
    register.add_argument("--artifact-uri", required=True)
    register.add_argument("--quality", required=True, type=float)
    register.add_argument("--safety", required=True, type=float)
    register.add_argument("--latency-ms-p95", required=True, type=float)
    register.add_argument("--cost-per-1k-tokens", required=True, type=float)
    register.add_argument("--notes", default="")
    register.add_argument("--status", default="candidate", choices=["candidate", "promoted", "rejected"])

    list_runs = subparsers.add_parser("list", help="List registered runs")
    list_runs.add_argument("--provider", choices=sorted(SUPPORTED_PROVIDERS))
    list_runs.add_argument("--host", choices=sorted(SUPPORTED_HOSTS))
    list_runs.add_argument("--role", choices=sorted(SUPPORTED_ROLES))

    promote = subparsers.add_parser("promote", help="Promote a run as the current winner for its track")
    promote.add_argument("--run-id", required=True)

    export_manifest = subparsers.add_parser(
        "export-provider-manifest",
        help="Export promoted runs for a provider in federated_orchestrator-compatible format",
    )
    export_manifest.add_argument("--provider", required=True, choices=sorted(SUPPORTED_PROVIDERS))
    export_manifest.add_argument("--output", required=True, type=Path)

    return parser.parse_args()


def command_register(args: argparse.Namespace, registry: dict[str, Any]) -> int:
    payload = {
        "run_id": args.run_id,
        "host": args.host,
        "provider": args.provider,
        "role": args.role,
        "status": args.status,
        "base_model": args.base_model,
        "dataset_repo": args.dataset_repo,
        "dataset_revision": args.dataset_revision,
        "artifact": {"id": args.artifact_id, "uri": args.artifact_uri},
        "metrics": {
            "quality": args.quality,
            "safety": args.safety,
            "latency_ms_p95": args.latency_ms_p95,
            "cost_per_1k_tokens": args.cost_per_1k_tokens,
        },
        "notes": args.notes,
        "created_at": utc_now(),
    }
    upsert_run(registry, payload)
    save_registry(args.registry, registry)
    print(json.dumps({"registered_run": args.run_id, "registry": str(args.registry)}, indent=2))
    return 0


def command_list(args: argparse.Namespace, registry: dict[str, Any]) -> int:
    runs = registry["runs"]
    if args.provider:
        runs = [run for run in runs if run.get("provider") == args.provider]
    if args.host:
        runs = [run for run in runs if run.get("host") == args.host]
    if args.role:
        runs = [run for run in runs if run.get("role") == args.role]
    print(json.dumps({"runs": runs, "promotions": registry["promotions"]}, indent=2))
    return 0


def command_promote(args: argparse.Namespace, registry: dict[str, Any]) -> int:
    promotion = promote_run(registry, args.run_id)
    save_registry(args.registry, registry)
    print(json.dumps({"promotion": promotion, "registry": str(args.registry)}, indent=2))
    return 0


def command_export_provider_manifest(args: argparse.Namespace, registry: dict[str, Any]) -> int:
    manifest = provider_manifest_from_registry(registry, args.provider)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"provider": args.provider, "output": str(args.output)}, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    registry = load_registry(args.registry)

    if args.command == "register":
        return command_register(args, registry)
    if args.command == "list":
        return command_list(args, registry)
    if args.command == "promote":
        return command_promote(args, registry)
    if args.command == "export-provider-manifest":
        return command_export_provider_manifest(args, registry)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
