#!/usr/bin/env python3
"""Route IDE/Codespaces work packets based on a 2D/3D platform matrix.

This script extends the existing GitHub dual-tentacle model by selecting an IDE
profile first (for example, Firebase Studio, Codespaces, PlayCanvas), then
routing the work packet into the appropriate operational lane.

Usage:
    python scripts/system/github_ide_mesh_router.py --task "ship firebase prototype" --mode 2d
    python scripts/system/github_ide_mesh_router.py --task "build 3d web scene" --mode 3d --prefer playcanvas_editor
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.github_dual_tentacle_router import (  # noqa: E402
    CROSSTALK_LOG,
    append_jsonl,
    lane_path,
)

IDE_MATRIX_PATH = REPO_ROOT / "config" / "governance" / "ide_platform_matrix.json"
IDE_ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "ide_mesh"
IDE_DECISIONS = IDE_ARTIFACT_ROOT / "ide_decisions.jsonl"


@dataclass
class PlatformDecision:
    profile_id: str
    label: str
    mode: str
    codespaces_integration: str
    github_integration: str
    score: int
    reason: list[str]
    lane: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "mode": self.mode,
            "codespaces_integration": self.codespaces_integration,
            "github_integration": self.github_integration,
            "score": self.score,
            "reason": self.reason,
            "lane": self.lane,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_matrix() -> dict[str, Any]:
    try:
        return json.loads(IDE_MATRIX_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Failed to read IDE matrix: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid IDE matrix JSON: {exc}") from exc


def choose_lane(profile: dict[str, Any], task: str) -> str:
    t = task.lower()
    codespaces_mode = str(profile.get("codespaces_integration", "none")).lower()

    if codespaces_mode in {"native", "bridge"}:
        return "codespaces_lane"
    if any(k in t for k in ["webhook", "event", "workflow", "issue", "pull request", "pr"]):
        return "webhook_lane"
    return "cli_lane"


def score_profile(
    profile: dict[str, Any],
    task: str,
    mode: str,
    prefer: str,
    require_codespaces: bool,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    task_l = task.lower()
    prefer_l = prefer.lower().strip()

    profile_mode = str(profile.get("mode", "")).lower()
    profile_id = str(profile.get("id", "")).lower()
    profile_label = str(profile.get("label", "")).lower()
    codespaces_integration = str(profile.get("codespaces_integration", "none")).lower()

    if mode != "auto" and profile_mode == mode:
        score += 6
        reasons.append(f"mode match: {mode}")
    elif mode == "auto":
        score += 2
        reasons.append("auto mode baseline")

    if prefer_l and (prefer_l == profile_id or prefer_l in profile_label):
        score += 8
        reasons.append(f"preferred profile: {prefer}")

    for kw in profile.get("task_keywords", []):
        kw_l = str(kw).lower()
        if kw_l and kw_l in task_l:
            score += 2
            reasons.append(f"keyword: {kw_l}")

    if require_codespaces:
        if codespaces_integration in {"native", "bridge"}:
            score += 5
            reasons.append(f"codespaces integration: {codespaces_integration}")
        else:
            score -= 10
            reasons.append("codespaces requirement not satisfied")
    elif codespaces_integration == "native":
        score += 1
        reasons.append("native codespaces bonus")

    if profile.get("firebase_like", False):
        if any(k in task_l for k in ["firebase", "backend", "hosting", "auth", "prototype"]):
            score += 3
            reasons.append("firebase-like fit")

    return score, reasons


def choose_platform(
    platforms: list[dict[str, Any]],
    task: str,
    mode: str,
    prefer: str,
    require_codespaces: bool,
) -> PlatformDecision:
    best_score = -10_000
    best_profile: dict[str, Any] | None = None
    best_reasons: list[str] = []

    for profile in platforms:
        score, reasons = score_profile(profile, task, mode, prefer, require_codespaces)
        if score > best_score:
            best_score = score
            best_profile = profile
            best_reasons = reasons

    if best_profile is None:
        raise RuntimeError("IDE matrix has no profiles.")

    lane = choose_lane(best_profile, task)
    return PlatformDecision(
        profile_id=str(best_profile.get("id", "")),
        label=str(best_profile.get("label", "")),
        mode=str(best_profile.get("mode", "")),
        codespaces_integration=str(best_profile.get("codespaces_integration", "none")),
        github_integration=str(best_profile.get("github_integration", "none")),
        score=best_score,
        reason=best_reasons,
        lane=lane,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick IDE profile + route GitHub packet.")
    parser.add_argument("--repo", default="SCBE-AETHERMOORE", help="Repo context label.")
    parser.add_argument("--sender", default="agent.ide-orchestrator", help="Sender label.")
    parser.add_argument("--event-type", default="ide_task", help="Event type label.")
    parser.add_argument("--task", required=True, help="Task summary used for profile scoring.")
    parser.add_argument("--mode", default="auto", choices=["auto", "2d", "3d"], help="Workspace mode.")
    parser.add_argument("--prefer", default="", help="Preferred IDE profile id or label.")
    parser.add_argument(
        "--require-codespaces",
        action="store_true",
        help="Require native/bridge Codespaces compatibility.",
    )
    parser.add_argument(
        "--risk",
        default="medium",
        choices=["low", "medium", "high"],
        help="Risk label for packet metadata.",
    )
    args = parser.parse_args()

    matrix = load_matrix()
    platforms = matrix.get("platforms", [])
    if not isinstance(platforms, list) or not platforms:
        raise RuntimeError("IDE matrix missing 'platforms' list.")

    decision = choose_platform(
        platforms=platforms,
        task=args.task,
        mode=args.mode,
        prefer=args.prefer,
        require_codespaces=args.require_codespaces,
    )

    packet_id = f"ide-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    packet = {
        "packet_id": packet_id,
        "created_at": utc_now(),
        "sender": args.sender,
        "recipient_lane": decision.lane,
        "intent": "ide_workspace_selection",
        "status": "selected",
        "repo": args.repo,
        "event_type": args.event_type,
        "task": args.task,
        "payload": {
            "mode": args.mode,
            "prefer": args.prefer,
            "require_codespaces": args.require_codespaces,
            "selection_policy_version": matrix.get("version"),
            "decision": decision.to_dict(),
        },
        "next_action": f"Open {decision.profile_id} and execute task in {decision.lane}.",
        "risk": args.risk,
    }

    append_jsonl(lane_path(decision.lane), packet)
    append_jsonl(
        CROSSTALK_LOG,
        {
            "created_at": packet["created_at"],
            "packet_id": packet_id,
            "from": args.sender,
            "to": decision.lane,
            "repo": args.repo,
            "event_type": args.event_type,
            "task": args.task,
            "status": "selected",
            "risk": args.risk,
            "ide_profile": decision.profile_id,
            "ide_mode": decision.mode,
        },
    )

    IDE_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    append_jsonl(IDE_DECISIONS, packet)

    print(
        json.dumps(
            {
                "ok": True,
                "packet_id": packet_id,
                "lane": decision.lane,
                "profile": decision.profile_id,
                "mode": decision.mode,
                "decision_score": decision.score,
                "decision_reason": decision.reason,
                "decision_log": str(IDE_DECISIONS),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
