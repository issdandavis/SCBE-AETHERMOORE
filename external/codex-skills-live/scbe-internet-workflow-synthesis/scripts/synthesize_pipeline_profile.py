#!/usr/bin/env python3
"""Synthesize a repo-local SCBE internet workflow profile."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCAL_TEMPLATE_FILES = [
    "workflows/scbe_ai_kernel/manager_agent_prompt.md",
    "scripts/web_research_training_pipeline.py",
    "docs/WEB_RESEARCH_TRAINING_PIPELINE.md",
    "workflows/n8n/scbe_n8n_bridge.py",
    "workflows/n8n/scbe_web_agent_tasks.workflow.json",
    "scripts/workflow_audit.py",
    ".github/workflows/workflow-audit.yml",
    "training/cloud_kernel_pipeline.json",
    "src/ai_orchestration/autonomous_workflows.py",
]

GITHUB_TEMPLATE_FILES = [
    "https://github.com/issdandavis/AI-Workflow-Architect/blob/main/README.md",
    "https://github.com/issdandavis/AI-Workflow-Architect/blob/main/docs/PROJECT_DOCUMENTATION.md",
    "https://github.com/issdandavis/AI-Workflow-Architect/blob/main/server/services/orchestrator.ts",
    "https://github.com/issdandavis/AI-Workflow-Architect/blob/main/.github/workflows/deploy.yml",
]

DEFAULT_TOPICS = [
    "agentic web automation",
    "browser orchestration reliability",
    "workflow governance for ai agents",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create training/internet_workflow_profile.json")
    parser.add_argument("--repo-root", default=".", help="Path to SCBE repo root")
    parser.add_argument(
        "--output",
        default="training/internet_workflow_profile.json",
        help="Relative path in repo for synthesized profile",
    )
    parser.add_argument(
        "--topic",
        action="append",
        default=[],
        help="Optional topic override (repeat flag to add multiple topics)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite output file if it exists")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    if not repo_root.exists():
        raise SystemExit(f"repo root not found: {repo_root}")

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = repo_root / out_path

    if out_path.exists() and not args.force:
        raise SystemExit(f"output exists: {out_path} (use --force to overwrite)")

    topics = [t.strip() for t in args.topic if t.strip()] or list(DEFAULT_TOPICS)

    profile = {
        "schema_version": "1.0.0",
        "generated_at_utc": utc_now(),
        "template_sources": {
            "local": LOCAL_TEMPLATE_FILES,
            "github": GITHUB_TEMPLATE_FILES,
            "selection_policy": "local-first, github-fallback",
        },
        "web_research": {
            "topics": topics,
            "max_per_topic": 6,
            "backend": "playwright",
            "max_tabs": 6,
            "query": "",
            "run_root": "training/runs/web_research",
            "intake_dir": "training/intake/web_research",
            "skip_core_check": False,
        },
        "governance_tuning": {
            "cloud_kernel_config": "training/cloud_kernel_pipeline.json",
            "output_cloud_kernel_config": "training/cloud_kernel_pipeline.tuned.json",
            "output_report": "artifacts/internet_workflow_tuning_report.json",
            "output_runtime_profile": "training/internet_workflow_profile.tuned.json",
            "target_quarantine_ratio": 0.08,
        },
    }

    write_json(out_path, profile)
    print(json.dumps({"status": "ok", "profile": str(out_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
