#!/usr/bin/env python3
"""Generate a starter SCBE worker productization packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROFILES = {
    "pilot": {
        "buyer": "Security, ops, or AI platform team evaluating governed agent workflows",
        "problem": "They want automation and agents, but need auditability, recovery paths, and approval gates.",
        "promise": "Deliver a scoped governed worker pilot with flock orchestration, refresh/reassignment, and audit outputs.",
        "delivery_artifacts": [
            "Pilot walkthrough",
            "Worker lane design",
            "API/demo surface",
            "Usage and audit reporting",
        ],
        "next_build_steps": [
            "Expose or refine the flock dashboard API surface.",
            "Add one external connector lane or webhook path.",
            "Package a demo with tenant, flock, task, and audit flow.",
        ],
    },
    "workflow-pack": {
        "buyer": "Operators who want a reusable automation bundle more than a custom platform contract",
        "problem": "They need repeatable content, publishing, or revenue workflows tied to clear triggers.",
        "promise": "Deliver a reusable worker workflow pack that connects content creation, publishing, and tracking lanes.",
        "delivery_artifacts": [
            "Workflow map",
            "Connector list",
            "Trigger and approval design",
            "Runbook",
        ],
        "next_build_steps": [
            "Choose n8n or Zapier as the primary orchestration layer.",
            "Define trigger schemas and approval checkpoints.",
            "Map each lane to repo scripts and external apps.",
        ],
    },
    "saas": {
        "buyer": "Teams paying for software access to governed worker infrastructure",
        "problem": "They need a product surface, not just services or loose scripts.",
        "promise": "Provide an API-first governed worker SaaS surface with tenants, flocks, tasks, governance, and usage reporting.",
        "delivery_artifacts": [
            "Endpoint group summary",
            "Tenant and flock lifecycle",
            "Governance and audit routes",
            "Metering model",
        ],
        "next_build_steps": [
            "Move tenancy state from in-memory to persistent storage.",
            "Add connector registration and webhooks.",
            "Add one buyer-facing dashboard or guided demo flow.",
        ],
    },
    "service": {
        "buyer": "Customers buying managed automation outcomes with software in the background",
        "problem": "They need someone else to operate the workflow, not just hand them tooling.",
        "promise": "Run and maintain governed worker systems as a managed engagement with clear visibility and approval gates.",
        "delivery_artifacts": [
            "Service scope",
            "Ops lane definition",
            "Escalation rules",
            "Weekly proof packet",
        ],
        "next_build_steps": [
            "Define what remains manual vs automated.",
            "Add recurring reporting and status artifacts.",
            "Map ops handoff to admin/autopilot lanes.",
        ],
    },
}

SOURCE_PAGES = [
    "Autonomous AI Workers - Revenue Generation System",
    "AI Business Automation Hub - The Self-Teaching Template",
    "HYDRA AI Automation Templates - Product Strategy",
    "Automation Triggers",
    "SCBE Product Brief - Buyer Guide & Demo Requirements",
]

REPO_PROOF_SURFACES = [
    "src/api/saas_routes.py",
    "src/api/main.py",
    "src/symphonic_cipher/scbe_aethermoore/flock_shepherd.py",
    "tests/test_saas_api.py",
    "tests/test_flock_shepherd.py",
    "scripts/system/dispatch_monetization_swarm.py",
    "scripts/system/monetization_connector_push.py",
    "scripts/system/pilot_demo_to_decision.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a starter SCBE worker product packet")
    parser.add_argument("--repo-root", default=".", help="Path to the SCBE repo root")
    parser.add_argument("--mode", choices=sorted(PROFILES), default="pilot", help="Packaging mode")
    parser.add_argument(
        "--output-json",
        default=None,
        help="JSON output path relative to repo root; defaults to artifacts/worker_productization/<mode>_packet.json",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Markdown output path relative to repo root; defaults to artifacts/worker_productization/<mode>_packet.md",
    )
    return parser.parse_args()


def write_markdown(packet: dict, output_path: Path) -> None:
    lines = [
        f"# SCBE Worker Product Packet: {packet['mode']}",
        "",
        f"- Buyer: {packet['buyer']}",
        f"- Problem: {packet['problem']}",
        f"- Promise: {packet['promise']}",
        "",
        "## Source Pages",
        "",
    ]
    for page in packet["source_pages"]:
        lines.append(f"- {page}")
    lines.extend(["", "## Repo Proof Surfaces", ""])
    for path in packet["repo_proof_surfaces"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Delivery Artifacts", ""])
    for artifact in packet["delivery_artifacts"]:
        lines.append(f"- {artifact}")
    lines.extend(["", "## Next Build Steps", ""])
    for step in packet["next_build_steps"]:
        lines.append(f"- {step}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    profile = PROFILES[args.mode]
    packet = {
        "mode": args.mode,
        "buyer": profile["buyer"],
        "problem": profile["problem"],
        "promise": profile["promise"],
        "source_pages": SOURCE_PAGES,
        "repo_proof_surfaces": REPO_PROOF_SURFACES,
        "delivery_artifacts": profile["delivery_artifacts"],
        "next_build_steps": profile["next_build_steps"],
    }

    output_json = args.output_json or f"artifacts/worker_productization/{args.mode}_packet.json"
    output_md = args.output_md or f"artifacts/worker_productization/{args.mode}_packet.md"

    json_path = repo_root / output_json
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    md_path = repo_root / output_md
    write_markdown(packet, md_path)

    print(f"[worker-product-packet] json={json_path}")
    print(f"[worker-product-packet] md={md_path}")


if __name__ == "__main__":
    main()
