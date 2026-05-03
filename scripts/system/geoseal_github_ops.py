#!/usr/bin/env python3
"""GeoSeal GitHub CLI router.

The router is intentionally conservative: it turns a repo goal into lane-tagged
GitHub or local-assessment commands, dry-runs by default, and only executes an
allowlisted read-only surface when the caller passes --execute.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO = "issdandavis/SCBE-AETHERMOORE"
SCHEMA_VERSION = "scbe_geoseal_github_ops_v1"

GH_READ_ONLY_ALLOWLIST = {
    ("auth", "status"),
    ("status",),
    ("repo", "view"),
    ("workflow", "list"),
    ("run", "list"),
    ("run", "view"),
    ("pr", "list"),
    ("pr", "view"),
    ("pr", "diff"),
}

LOCAL_READ_ONLY_ALLOWLIST = {
    ("git", "status"),
    ("python", "scripts/ci/harness_release_readiness.py"),
}


@dataclass(frozen=True)
class RoutedCommand:
    lane: str
    purpose: str
    argv: list[str]
    mutates: bool = False
    cwd: str = str(PROJECT_ROOT)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _with_repo(argv: list[str], repo: str) -> list[str]:
    if "--repo" in argv:
        return argv
    return [*argv, "--repo", repo]


def _normalize_mode(mode: str, goal: str) -> str:
    if mode != "auto":
        return mode
    text = goal.lower()
    if "workflow" in text:
        return "workflow-list"
    if "run" in text or "ci" in text:
        return "runs"
    if "pull request" in text or " pr" in f" {text}":
        return "pr-list"
    if "assess" in text or "review" in text or "code" in text:
        return "assess-code"
    if "fix" in text or "repair" in text:
        return "fix-plan"
    return "status"


def build_github_plan(
    *,
    goal: str = "repo status",
    mode: str = "auto",
    repo: str = DEFAULT_REPO,
    run_id: str | None = None,
    pr: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Build a lane-tagged plan for GitHub and local repo operations."""

    selected = _normalize_mode(mode, goal)
    commands: list[RoutedCommand] = []
    notes: list[str] = []

    if selected == "status":
        commands.append(RoutedCommand("KO", "Check GitHub CLI authentication and repo state", ["gh", "auth", "status"]))
        commands.append(
            RoutedCommand(
                "KO",
                "Check target repository metadata",
                [
                    "gh",
                    "repo",
                    "view",
                    repo,
                    "--json",
                    "nameWithOwner,defaultBranchRef,isPrivate,viewerPermission",
                ],
            )
        )
    elif selected == "workflow-list":
        commands.append(RoutedCommand("CA", "List GitHub Actions workflows", _with_repo(["gh", "workflow", "list"], repo)))
    elif selected == "runs":
        commands.append(
            RoutedCommand(
                "CA",
                "List recent GitHub Actions runs",
                _with_repo(["gh", "run", "list", "--limit", str(max(1, limit))], repo),
            )
        )
    elif selected == "run-view":
        if not run_id:
            notes.append("run-view needs --run-id before it can execute.")
        else:
            commands.append(
                RoutedCommand("CA", "Inspect one GitHub Actions run", _with_repo(["gh", "run", "view", run_id, "--log"], repo))
            )
    elif selected == "pr-list":
        commands.append(
            RoutedCommand("RU", "List open pull requests for review routing", _with_repo(["gh", "pr", "list", "--limit", str(max(1, limit))], repo))
        )
    elif selected == "pr-view":
        if not pr:
            notes.append("pr-view needs --pr before it can execute.")
        else:
            commands.append(RoutedCommand("RU", "View pull request metadata", _with_repo(["gh", "pr", "view", pr], repo)))
    elif selected == "pr-diff":
        if not pr:
            notes.append("pr-diff needs --pr before it can execute.")
        else:
            commands.append(RoutedCommand("RU", "Inspect pull request diff", _with_repo(["gh", "pr", "diff", pr], repo)))
    elif selected == "assess-code":
        commands.append(RoutedCommand("RU", "Inspect local dirty tree before any fix", ["git", "status", "--short"]))
        commands.append(
            RoutedCommand(
                "DR",
                "Run release-readiness assessment gate",
                [sys.executable, "scripts/ci/harness_release_readiness.py", "--json"],
            )
        )
    elif selected == "fix-plan":
        commands.append(RoutedCommand("RU", "Inspect local dirty tree before repair planning", ["git", "status", "--short"]))
        commands.append(RoutedCommand("CA", "List recent failing workflow candidates", _with_repo(["gh", "run", "list", "--limit", str(max(1, limit))], repo)))
        notes.append("Fix execution is intentionally separate: assess first, patch with focused tests, then commit.")
    else:
        raise ValueError(f"unknown github mode: {mode}")

    return {
        "schema_version": SCHEMA_VERSION,
        "goal": goal,
        "mode": selected,
        "repo": repo,
        "commands": [command.to_dict() for command in commands],
        "notes": notes,
        "lane_policy": {
            "KO": "repo intent, auth, and queue status",
            "RU": "risk review, pull request inspection, and code assessment",
            "CA": "GitHub Actions workflow and run routing",
            "DR": "release gate synthesis and final operator report",
        },
        "execute_default": "dry-run",
        "mutating_commands_enabled": False,
    }


def _allowed_command(argv: list[str]) -> bool:
    if not argv:
        return False
    executable = Path(argv[0]).name.lower()
    if executable == "gh":
        signature = (
            tuple(argv[1:3])
            if len(argv) >= 3 and argv[1] in {"auth", "repo", "workflow", "run", "pr"}
            else tuple(argv[1:2])
        )
        return signature in GH_READ_ONLY_ALLOWLIST
    if executable == "git":
        return tuple(argv[:2]) in LOCAL_READ_ONLY_ALLOWLIST
    if executable in {"python", "python.exe"} or executable == Path(sys.executable).name.lower():
        return len(argv) >= 2 and tuple(["python", argv[1]]) in LOCAL_READ_ONLY_ALLOWLIST
    return False


def _sanitize_output(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- Token:") or stripped.startswith("Token:"):
            lines.append("  - Token: <redacted>")
        else:
            lines.append(line)
    return "\n".join(lines)


def execute_github_plan(plan: dict[str, Any], *, timeout: float = 60.0) -> dict[str, Any]:
    """Execute only read-only allowlisted commands from a plan."""

    results: list[dict[str, Any]] = []
    for command in plan.get("commands", []):
        argv = list(command["argv"])
        if command.get("mutates") or not _allowed_command(argv):
            results.append(
                {
                    "lane": command.get("lane"),
                    "purpose": command.get("purpose"),
                    "argv": argv,
                    "skipped": True,
                    "returncode": None,
                    "stdout": "",
                    "stderr": "command is not on the read-only allowlist",
                }
            )
            continue
        proc = subprocess.run(
            argv,
            cwd=command.get("cwd") or str(PROJECT_ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        results.append(
            {
                "lane": command.get("lane"),
                "purpose": command.get("purpose"),
                "argv": argv,
                "skipped": False,
                "returncode": proc.returncode,
                "stdout": _sanitize_output(proc.stdout)[-4000:],
                "stderr": _sanitize_output(proc.stderr)[-4000:],
            }
        )
    return {**plan, "executed": True, "results": results}


def render_github_plan_text(payload: dict[str, Any]) -> str:
    lines = [
        "GeoSeal GitHub Router",
        "=" * 28,
        f"repo={payload['repo']} mode={payload['mode']} execute={payload.get('executed', False)}",
        "",
        "Lane Commands",
        "-" * 28,
    ]
    for command in payload.get("commands", []):
        lines.append(f"- {command['lane']} {command['purpose']}: {' '.join(command['argv'])}")
    for note in payload.get("notes", []):
        lines.append(f"note: {note}")
    if payload.get("results"):
        lines.extend(["", "Results", "-" * 28])
        for result in payload["results"]:
            status = "skipped" if result["skipped"] else f"rc={result['returncode']}"
            lines.append(f"- {result['lane']} {status}: {' '.join(result['argv'])}")
            if result.get("stdout"):
                lines.append(result["stdout"].strip())
            if result.get("stderr"):
                lines.append(result["stderr"].strip())
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", default="repo status")
    parser.add_argument(
        "--mode",
        default="auto",
        choices=[
            "auto",
            "status",
            "workflow-list",
            "runs",
            "run-view",
            "pr-list",
            "pr-view",
            "pr-diff",
            "assess-code",
            "fix-plan",
        ],
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--pr", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    plan = build_github_plan(
        goal=args.goal,
        mode=args.mode,
        repo=args.repo,
        run_id=args.run_id,
        pr=args.pr,
        limit=args.limit,
    )
    payload = execute_github_plan(plan, timeout=args.timeout) if args.execute else plan
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_github_plan_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
