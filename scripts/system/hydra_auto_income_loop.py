#!/usr/bin/env python3
"""Run a HYDRA-driven automated income loop.

This script ties together:
- Sphere-grid skill discovery (monetization-aware skill inventory)
- HYDRA terminal limb execution
- Revenue actions that produce immediate outbound sales motion
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from hydra.limbs import TerminalLimb
from src.sphere_grid.skill_registry import SkillNode, discover_skills


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _select_monetization_skills(nodes: List[SkillNode]) -> List[Dict[str, Any]]:
    keywords = ("monet", "sales", "shopify", "gumroad", "stripe", "cash", "offer", "launch")
    picks: List[Dict[str, Any]] = []
    for node in nodes:
        blob = f"{node.name} {node.description} {node.phase}".lower()
        if any(k in blob for k in keywords):
            picks.append(
                {
                    "name": node.name,
                    "phase": node.phase,
                    "difficulty": round(float(node.difficulty), 3),
                    "path": str(node.path),
                }
            )
    picks.sort(key=lambda x: (x["phase"], x["name"]))
    return picks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HYDRA terminal income loop (research -> leads -> connector push).")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--scbe-url", default="http://127.0.0.1:8080")
    parser.add_argument("--top-leads", type=int, default=12)
    parser.add_argument("--lead-limit", type=int, default=30)
    parser.add_argument("--sender", default="agent.codex")
    parser.add_argument("--recipient", default="agent.claude")
    parser.add_argument("--codename", default="HydraIncomeLoop")
    parser.add_argument("--skip-arxiv", action="store_true")
    parser.add_argument("--skip-lead-sync", action="store_true")
    parser.add_argument("--skip-connector-push", action="store_true")
    return parser.parse_args()


async def _run_limb_command(limb: TerminalLimb, name: str, command: str) -> Dict[str, Any]:
    result = await limb.execute("execute", command, {})
    return {
        "step": name,
        "command": command,
        "success": bool(result.get("success")),
        "decision": result.get("decision", ""),
        "returncode": result.get("returncode"),
        "stdout": str(result.get("stdout", ""))[:2000],
        "stderr": str(result.get("stderr", ""))[:1000],
        "reason": result.get("reason", ""),
        "error": result.get("error", ""),
    }


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    day = _utc_now().strftime("%Y%m%d")
    run_id = f"hydra-income-loop-{_utc_stamp()}"

    skills = discover_skills(extra_dirs=[repo_root / "skills"])
    monetization_skills = _select_monetization_skills(skills)

    steps: List[Dict[str, Any]] = []
    limb = TerminalLimb(scbe_url=args.scbe_url, cwd=str(repo_root))
    await limb.activate()
    try:
        if not args.skip_arxiv:
            cmd = (
                "python scripts/system/arxiv_monetization_spine.py "
                f"--top-leads {max(1, int(args.top_leads))} "
                "--dispatch-monetization-swarm "
                f'--sender "{args.sender}" '
                f'--recipient "{args.recipient}" '
                f'--codename "{args.codename}"'
            )
            steps.append(await _run_limb_command(limb, "arxiv_monetization_spine", cmd))

        if not args.skip_lead_sync:
            cmd = f"python scripts/sales/sync_github_leads.py --limit {max(1, int(args.lead_limit))}"
            steps.append(await _run_limb_command(limb, "github_lead_sync", cmd))

        if not args.skip_connector_push:
            cmd = "python scripts/system/monetization_connector_push.py --top-leads 10 --include-gumroad"
            steps.append(await _run_limb_command(limb, "connector_push", cmd))
    finally:
        await limb.deactivate()

    ok_count = sum(1 for row in steps if row.get("success"))
    artifact = {
        "ok": ok_count == len(steps),
        "run_id": run_id,
        "generated_at": _utc_now().isoformat(),
        "repo_root": str(repo_root),
        "monetization_skills_count": len(monetization_skills),
        "monetization_skills": monetization_skills[:40],
        "steps": steps,
        "summary": {
            "steps_total": len(steps),
            "steps_ok": ok_count,
            "steps_failed": len(steps) - ok_count,
        },
    }

    out_dir = repo_root / "artifacts" / "monetization" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    artifact["artifact_path"] = str(out_path)
    return artifact


def main() -> int:
    args = parse_args()
    result = asyncio.run(run(args))
    print(json.dumps(result, indent=2))
    return 0 if bool(result.get("ok")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
