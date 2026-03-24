#!/usr/bin/env python3
"""Emit monetization lane assignments onto the SCBE cross-talk bus.

Writes lane packets via src.aethercode.gateway._write_crosstalk_packet so
other agents (Claude/Grok/Gemini/local) can pick up assignments immediately.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from src.aethercode.gateway import CrossTalkRequest, _write_crosstalk_packet  # noqa: E402


@dataclass(frozen=True)
class LaneAssignment:
    recipient: str
    task_id: str
    summary: str
    next_action: str
    proof: List[str]
    where: str
    why: str
    how: str


DEFAULT_LANES: List[LaneAssignment] = [
    LaneAssignment(
        recipient="agent.claude",
        task_id="MONETIZE-SHOPIFY-CONVERSION",
        summary=(
            "Own storefront monetization lane: finalize product copy, pricing clarity, and CTA conversion path "
            "for AetherBrowse + Hydra Armor offers."
        ),
        next_action=(
            "Ship one commit updating Shopify product pages and pricing narrative; emit packet with changed file list "
            "and storefront preview links."
        ),
        proof=[
            "shopify/aethermoore-creator-os/",
            "docs/monetization/2026-03-04-agent-swarm-revenue-sprint.md",
        ],
        where="terminal+shopify",
        why="Increase conversion rate on existing traffic before adding more acquisition spend.",
        how="Update high-intent pages first, then emit done packet with conversion copy proof.",
    ),
    LaneAssignment(
        recipient="agent.grok",
        task_id="MONETIZE-LEADS-30",
        summary=("Own lead-intelligence lane: build first qualified prospect set for automation/workflow services."),
        next_action=(
            "Create 30-lead sheet with persona, pain, channel, and matched offer; emit packet with artifact path."
        ),
        proof=[
            "docs/monetization/2026-03-04-agent-swarm-revenue-sprint.md",
            "scripts/sales/sync_github_leads.py",
        ],
        where="terminal+research",
        why="Revenue requires outbound pipeline, not only product polishing.",
        how="Prioritize buyers with clear workflow pain and near-term budget authority.",
    ),
    LaneAssignment(
        recipient="agent.gemini",
        task_id="MONETIZE-OUTREACH-COPY",
        summary=(
            "Own messaging lane: produce outreach templates and discovery-call script mapped to three paid offers."
        ),
        next_action=(
            "Commit outreach templates and one qualification script; emit packet with exact file paths and send-ready text."
        ),
        proof=[
            "docs/monetization/2026-03-04-agent-swarm-revenue-sprint.md",
            "docs/OFFER_PILOT.md",
        ],
        where="terminal+copy",
        why="Fast follow-up and clear messaging closes deals from the lead lane.",
        how="Build one concise message set per offer tier with strong pain-to-value mapping.",
    ),
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _git_branch(default: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or default
    except Exception:
        return default


def _emit_lane(
    lane: LaneAssignment,
    *,
    sender: str,
    repo: str,
    branch: str,
    session_id: str,
    codename: str,
) -> Dict[str, Any]:
    payload = CrossTalkRequest(
        summary=lane.summary,
        recipient=lane.recipient,
        sender=sender,
        intent="lane_assignment",
        status="in_progress",
        task_id=lane.task_id,
        next_action=lane.next_action,
        risk="low",
        repo=repo,
        branch=branch,
        proof=lane.proof,
        session_id=session_id,
        codename=codename,
        where=lane.where,
        why=lane.why,
        how=lane.how,
    )
    return _write_crosstalk_packet(payload)


def _build_manifest(
    *,
    session_id: str,
    codename: str,
    branch: str,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = _utc_now()
    return {
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": session_id,
        "codename": codename,
        "repo": "SCBE-AETHERMOORE",
        "branch": branch,
        "type": "monetization_swarm_dispatch",
        "packets": [
            {
                "packet_id": item["packet"]["packet_id"],
                "task_id": item["packet"]["task_id"],
                "recipient": item["packet"]["recipient"],
                "packet_path": str(item["packet_path"]),
            }
            for item in results
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch monetization lane assignments to cross-talk bus.")
    parser.add_argument("--sender", default="agent.codex", help="Packet sender identity")
    parser.add_argument("--repo", default="SCBE-AETHERMOORE", help="Repo label for packet metadata")
    parser.add_argument("--branch", default="", help="Branch label (defaults to current git branch)")
    parser.add_argument("--session-id", default="", help="Session ID override")
    parser.add_argument("--codename", default="Revenue-Swarm-01", help="Codename for this dispatch")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = _utc_now()
    day = now.strftime("%Y%m%d")
    branch = args.branch.strip() or _git_branch(default="local")
    session_id = args.session_id.strip() or f"sess-{day}-monetization"
    codename = args.codename.strip() or "Revenue-Swarm-01"

    emitted: List[Dict[str, Any]] = []
    for lane in DEFAULT_LANES:
        emitted.append(
            _emit_lane(
                lane,
                sender=args.sender,
                repo=args.repo,
                branch=branch,
                session_id=session_id,
                codename=codename,
            )
        )

    manifest = _build_manifest(
        session_id=session_id,
        codename=codename,
        branch=branch,
        results=emitted,
    )
    out_dir = REPO_ROOT / "artifacts" / "agent_comm" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"monetization-swarm-dispatch-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "manifest_path": str(out_path), "packets": manifest["packets"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
