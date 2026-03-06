#!/usr/bin/env python3
"""Safe repo hygiene cleanup for local artifacts + remote ref pruning."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def remove_old_entries(base: Path, cutoff: datetime, dry_run: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not base.exists():
        return results

    for path in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime):
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified >= cutoff:
            continue
        row = {
            "path": str(path.resolve()),
            "modified_at_utc": modified.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "deleted": False,
            "error": "",
        }
        if not dry_run:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                row["deleted"] = True
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
        results.append(row)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe local/github hygiene cleanup.")
    parser.add_argument("--repo-root", default="", help="Repository root path.")
    parser.add_argument("--days", type=int, default=7, help="Delete artifacts older than N days.")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not delete.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve() if args.repo_root else REPO_ROOT
    cutoff = utc_now() - timedelta(days=max(0, int(args.days)))

    targets = [
        repo_root / "artifacts" / "publish_browser",
        repo_root / "artifacts" / "pilot_demo",
    ]
    removed: list[dict[str, Any]] = []
    for target in targets:
        removed.extend(remove_old_entries(target, cutoff=cutoff, dry_run=bool(args.dry_run)))

    fetch_rc, fetch_out, fetch_err = run_cmd(["git", "fetch", "--prune"], cwd=repo_root)
    merged_rc, merged_out, merged_err = run_cmd(["git", "branch", "--merged", "origin/main"], cwd=repo_root)
    merged_candidates = []
    if merged_rc == 0 and merged_out:
        for line in merged_out.splitlines():
            name = line.replace("*", "").strip()
            if name and name not in {"main", "master"}:
                merged_candidates.append(name)

    summary = {
        "ok": fetch_rc == 0 and merged_rc == 0,
        "generated_at_utc": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": str(repo_root),
        "dry_run": bool(args.dry_run),
        "cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "removed_entries": removed,
        "git_fetch_prune": {
            "return_code": fetch_rc,
            "stdout": fetch_out[-1200:],
            "stderr": fetch_err[-1200:],
        },
        "merged_branch_candidates": merged_candidates,
        "merged_branch_command_error": merged_err[-600:] if merged_rc != 0 else "",
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"[cleanup] dry_run={summary['dry_run']} cutoff={summary['cutoff_utc']}")
        print(f"[cleanup] removed_entries={len(removed)}")
        print(f"[cleanup] git_fetch_prune_rc={fetch_rc}")
        print(f"[cleanup] merged_branch_candidates={len(merged_candidates)}")

    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
