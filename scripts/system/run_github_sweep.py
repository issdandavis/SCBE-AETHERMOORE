#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = SCRIPT_REPO_ROOT / "skills" / "codex-mirror" / "scbe-github-sweep-sorter"
CHOOSE_FORMATION = SKILL_ROOT / "scripts" / "choose_formation.py"
BUILD_PACKET = SKILL_ROOT / "scripts" / "build_roundtable_packet.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], cwd: Path) -> SimpleNamespace:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=False, check=False)
    return SimpleNamespace(
        returncode=proc.returncode,
        stdout=proc.stdout.decode("utf-8", errors="replace"),
        stderr=proc.stderr.decode("utf-8", errors="replace"),
    )


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def parse_json_output(raw: str) -> Any:
    return json.loads(raw.strip())


def git_branch(repo_root: Path) -> str:
    proc = run(["git", "branch", "--show-current"], cwd=repo_root)
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def dirty_count_fallback(repo_root: Path) -> int:
    proc = run(["git", "status", "--short", "--untracked-files=all"], cwd=repo_root)
    if proc.returncode != 0:
        return 0
    return len([line for line in proc.stdout.splitlines() if line.strip()])


def risk_from_dirty_count(count: int) -> str:
    if count >= 1000:
        return "high"
    if count >= 100:
        return "medium"
    return "low"


def maybe_run_repo_hygiene(repo_root: Path) -> dict[str, Any]:
    repo_hygiene = repo_root / "scripts" / "system" / "repo_hygiene.py"
    if not repo_hygiene.exists():
        return {
            "mode": "fallback",
            "total_dirty_entries": dirty_count_fallback(repo_root),
            "latest_report": None,
        }

    proc = run(["python", str(repo_hygiene), "report"], cwd=repo_root)
    latest = repo_root / "artifacts" / "repo-hygiene" / "latest_report.json"
    payload: dict[str, Any] = {
        "mode": "repo_hygiene",
        "return_code": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
        "latest_report": str(latest) if latest.exists() else None,
    }
    if latest.exists():
        data = json.loads(latest.read_text(encoding="utf-8"))
        payload["total_dirty_entries"] = int(data.get("total_dirty_entries", 0))
        payload["counts_by_action"] = data.get("counts_by_action", {})
        payload["top_tracked_generated_prefixes"] = data.get("tracked_generated_prefixes", [])[:10]
        payload["top_safe_prune_prefixes"] = data.get("safe_prune_prefixes", [])[:10]
    else:
        payload["total_dirty_entries"] = dirty_count_fallback(repo_root)
    return payload


def maybe_collect_github(owner: str, output_dir: Path) -> dict[str, Any]:
    proc = run(
        [
            "gh",
            "repo",
            "list",
            owner,
            "--limit",
            "100",
            "--json",
            "name,nameWithOwner,isArchived,isPrivate,description,url,updatedAt",
        ],
        cwd=SCRIPT_REPO_ROOT,
    )
    result: dict[str, Any] = {
        "enabled": proc.returncode == 0,
        "return_code": proc.returncode,
        "stderr": proc.stderr[-1200:],
        "inventory_path": None,
    }
    if proc.returncode != 0:
        return result

    inventory_path = output_dir / "github_repo_inventory_latest.json"
    inventory_path.write_text(proc.stdout, encoding="utf-8")
    repos = json.loads(proc.stdout)
    result["inventory_path"] = str(inventory_path)
    result["repo_count"] = len(repos)
    result["active_count"] = sum(1 for repo in repos if not repo.get("isArchived"))
    result["archived_count"] = sum(1 for repo in repos if repo.get("isArchived"))
    result["private_count"] = sum(1 for repo in repos if repo.get("isPrivate"))
    result["public_count"] = sum(1 for repo in repos if not repo.get("isPrivate"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a GitHub/repo sweep using the mirrored SCBE sweep skill.")
    parser.add_argument("--repo-root", default=".", help="Target repo root to sweep.")
    parser.add_argument("--owner", default="issdandavis", help="GitHub owner/org for repo inventory.")
    parser.add_argument("--include-github", action="store_true", help="Also collect GitHub repo inventory with gh.")
    parser.add_argument("--task-id", default="ai-terminal-sweep", help="Task ID for the roundtable packet.")
    args = parser.parse_args()

    require_file(CHOOSE_FORMATION)
    require_file(BUILD_PACKET)

    target_repo_root = Path(args.repo_root).expanduser().resolve()
    output_dir = target_repo_root / "artifacts" / "agent-sweeps"
    output_dir.mkdir(parents=True, exist_ok=True)

    hygiene = maybe_run_repo_hygiene(target_repo_root)
    dirty_entries = int(hygiene.get("total_dirty_entries", 0))
    risk = risk_from_dirty_count(dirty_entries)

    github = {"enabled": False}
    if args.include_github:
        github = maybe_collect_github(args.owner, output_dir)

    choose_proc = run(
        [
            "python",
            str(CHOOSE_FORMATION),
            "--repo-count",
            "1",
            "--item-count",
            str(dirty_entries),
            "--risk",
            risk,
            "--needs-discovery",
        ],
        cwd=SCRIPT_REPO_ROOT,
    )
    if choose_proc.returncode != 0:
        raise RuntimeError(choose_proc.stderr)
    formation = parse_json_output(choose_proc.stdout)

    branch = git_branch(target_repo_root)
    packet_proc = run(
        [
            "python",
            str(BUILD_PACKET),
            "--repo",
            target_repo_root.name,
            "--branch",
            branch,
            "--task-id",
            args.task_id,
            "--formation",
            str(formation["formation"]),
            "--quorum-required",
            str(formation["quorum_required"]),
            "--summary",
            "Classify local repo state and route owned cleanup lanes",
            "--risk",
            risk,
        ],
        cwd=SCRIPT_REPO_ROOT,
    )
    if packet_proc.returncode != 0:
        raise RuntimeError(packet_proc.stderr)
    packet = parse_json_output(packet_proc.stdout)

    summary = {
        "generated_at_utc": utc_now(),
        "target_repo_root": str(target_repo_root),
        "branch": branch,
        "dirty_entries": dirty_entries,
        "risk": risk,
        "formation": formation,
        "packet": packet,
        "repo_hygiene": hygiene,
        "github": github,
    }

    summary_path = output_dir / "github_sweep_latest.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "summary_path": str(summary_path), "dirty_entries": dirty_entries, "formation": formation["formation"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
