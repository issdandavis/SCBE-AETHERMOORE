#!/usr/bin/env python3
"""Repo-safe audit for SCBE training lanes and recent manifests.

This audit avoids crawling heavy generated paths like ``artifacts/research`` and
notebook JSON payloads. It summarizes the canonical notebooks, host route map,
multi-host registry state, and recent manifests under ``training/runs``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.colab_workflow_catalog import list_notebook_payloads
from scripts.system.multi_host_training_registry import DEFAULT_REGISTRY, load_registry

ROUTE_MAP_PATH = REPO_ROOT / "config" / "system" / "host_compute_routes.json"
NOTEBOOK_DIR = REPO_ROOT / "notebooks"
TRAINING_RUNS_DIR = REPO_ROOT / "training" / "runs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_file_summary(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "size_bytes": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def summarize_recent_notebooks(limit: int = 8) -> list[dict[str, Any]]:
    files = sorted(NOTEBOOK_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    results: list[dict[str, Any]] = []
    for path in files:
        if not path.is_file():
            continue
        results.append(_safe_file_summary(path))
        if len(results) >= limit:
            break
    return results


def summarize_route_map(path: Path = ROUTE_MAP_PATH) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "exists": path.exists(),
    }
    if not path.exists():
        summary["hosts"] = []
        summary["recommended_sequence"] = []
        return summary

    payload = _read_json(path)
    summary["hosts"] = sorted(payload.get("hosts", {}).keys())
    summary["recommended_sequence"] = payload.get("recommended_sequence", [])
    summary["source_of_truth"] = payload.get("summary", {}).get("source_of_truth", [])
    return summary


def summarize_registry(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "run_count": 0,
        "promotion_count": 0,
        "promotions": {},
    }
    if not path.exists():
        return summary

    registry = load_registry(path)
    summary["run_count"] = len(registry.get("runs", []))
    promotions = registry.get("promotions", {})
    summary["promotion_count"] = len(promotions)
    summary["promotions"] = promotions
    return summary


def summarize_recent_manifests(limit: int = 10) -> list[dict[str, Any]]:
    if not TRAINING_RUNS_DIR.exists():
        return []

    files = sorted(TRAINING_RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_safe_file_summary(path) for path in files[:limit]]


def build_training_ops_audit(registry_path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    catalog = list_notebook_payloads()
    priority_names = {
        "spiralverse-generator",
        "canonical-training-lane",
        "aethermoor-finetune",
        "aethermoor-datagen",
    }
    canonical_notebooks = [
        {
            "name": item["name"],
            "category": item["category"],
            "path": item["path"],
            "exists": item["exists"],
            "colab_url": item["colab_url"],
        }
        for item in catalog
        if item["name"] in priority_names
    ]

    warnings: list[str] = []
    if not any(item["name"] == "canonical-training-lane" and item["exists"] for item in canonical_notebooks):
        warnings.append("canonical training notebook missing")
    if not ROUTE_MAP_PATH.exists():
        warnings.append("host route map missing")
    if not registry_path.exists():
        warnings.append("multi-host registry missing; convergence lane has no persisted runs yet")

    next_actions = [
        "Use the canonical Colab lane for primary training and the Kaggle smoke gate before any long Kaggle run.",
        "Register completed runs in the multi-host registry, then promote only after evaluation evidence exists.",
        "Keep audits scoped to canonical notebooks, host routes, and training manifests; avoid broad scans of artifacts/research.",
    ]

    return {
        "schema_version": "training_ops_audit_v1",
        "generated_at": utc_now(),
        "repo_root": str(REPO_ROOT),
        "safe_scope": {
            "included": [
                "config/system/host_compute_routes.json",
                "notebooks/* metadata",
                "training/runs/*.json",
                "scripts/system/colab_workflow_catalog.py",
                "scripts/system/multi_host_training_registry.py",
            ],
            "excluded": [
                "artifacts/research/**",
                "training-data/**",
                "notebook cell payload scans",
            ],
            "reason": "Avoid high-memory recursive scans across generated, binary-heavy, and large JSON surfaces.",
        },
        "canonical_notebooks": sorted(canonical_notebooks, key=lambda item: item["name"]),
        "recent_notebooks": summarize_recent_notebooks(),
        "host_routes": summarize_route_map(),
        "registry": summarize_registry(registry_path),
        "recent_manifests": summarize_recent_manifests(),
        "warnings": warnings,
        "next_actions": next_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo-safe audit for SCBE training operations")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY, help="Registry JSON path")
    parser.add_argument("--json", action="store_true", help="Emit the audit payload as JSON")
    args = parser.parse_args()

    payload = build_training_ops_audit(args.registry)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("# SCBE Training Ops Audit")
    print(f"generated_at: {payload['generated_at']}")
    print(f"registry_runs: {payload['registry']['run_count']} | promotions: {payload['registry']['promotion_count']}")
    print("canonical_notebooks:")
    for item in payload["canonical_notebooks"]:
        status = "yes" if item["exists"] else "no"
        print(f"- {item['name']} [{item['category']}] exists={status} path={item['path']}")
    if payload["warnings"]:
        print("warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
    print("next_actions:")
    for action in payload["next_actions"]:
        print(f"- {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
