#!/usr/bin/env python3
"""Apply tier/surface topics across GitHub repos from sectioning CSV.

This is a portfolio cleanup utility:
- removes stale `tier-*` and `surface-*` topics
- applies current tier topic + surface topic
- keeps all non-governance topics intact

Usage:
  python scripts/system/github_repo_governance_apply.py --csv artifacts/governance/github_repo_sectioning_*.csv --dry-run
  python scripts/system/github_repo_governance_apply.py --csv artifacts/governance/github_repo_sectioning_*.csv --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "artifacts" / "governance"


@dataclass(frozen=True)
class RepoRow:
    owner: str
    repo: str
    tier: str


TIER_TO_TOPICS = {
    "private_restricted": ("tier-private-restricted", "surface-private"),
    "public_sellable": ("tier-public-sellable", "surface-sellable"),
    "public_open": ("tier-public-open", "surface-open"),
    "public_education": ("tier-public-education", "surface-education"),
}


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return proc.stdout


def _load_rows(csv_path: Path) -> list[RepoRow]:
    rows: list[RepoRow] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(RepoRow(owner=r["owner"], repo=r["repo"], tier=r["tier"]))
    return rows


def _get_topics(owner: str, repo: str) -> list[str]:
    raw = _run(["gh", "api", f"repos/{owner}/{repo}/topics"])
    data = json.loads(raw)
    names = data.get("names", [])
    return [str(t) for t in names]


def _set_topics(owner: str, repo: str, topics: list[str]) -> None:
    cmd = [
        "gh",
        "api",
        "--method",
        "PUT",
        f"repos/{owner}/{repo}/topics",
        "-H",
        "Accept: application/vnd.github+json",
    ]
    for t in topics:
        cmd.extend(["-f", f"names[]={t}"])
    _run(cmd)


def _desired_topics(current: list[str], tier: str) -> list[str]:
    tier_topic, surface_topic = TIER_TO_TOPICS[tier]
    keep = [t for t in current if not (t.startswith("tier-") or t.startswith("surface-"))]
    desired = keep + [tier_topic, surface_topic, "portfolio-managed"]
    dedup: list[str] = []
    seen: set[str] = set()
    for t in desired:
        if t not in seen:
            dedup.append(t)
            seen.add(t)
    return dedup[:20]  # GitHub topic limit


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply governance topics to repos from sectioning CSV.")
    parser.add_argument("--csv", required=True, help="Path to sectioning CSV")
    parser.add_argument("--apply", action="store_true", help="Actually write topics")
    parser.add_argument("--dry-run", action="store_true", help="Show planned topic updates only")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    rows = _load_rows(csv_path)
    dry_run = args.dry_run or not args.apply

    changed = 0
    unchanged = 0
    errors: list[dict[str, str]] = []
    plan_rows: list[dict[str, object]] = []

    for row in rows:
        if row.tier not in TIER_TO_TOPICS:
            errors.append({"repo": f"{row.owner}/{row.repo}", "error": f"unknown tier {row.tier}"})
            continue

        try:
            current = _get_topics(row.owner, row.repo)
            desired = _desired_topics(current, row.tier)
            repo_full = f"{row.owner}/{row.repo}"
            will_change = current != desired

            plan_rows.append(
                {
                    "repo": repo_full,
                    "tier": row.tier,
                    "current_topics": current,
                    "desired_topics": desired,
                    "changed": will_change,
                }
            )

            if not will_change:
                unchanged += 1
                continue

            if not dry_run:
                _set_topics(row.owner, row.repo, desired)
            changed += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"repo": f"{row.owner}/{row.repo}", "error": str(exc)})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mode = "dryrun" if dry_run else "apply"
    out = OUTPUT_DIR / f"github_governance_topic_apply_{mode}.json"
    out.write_text(
        json.dumps(
            {
                "source_csv": str(csv_path),
                "dry_run": dry_run,
                "total_repos": len(rows),
                "changed": changed,
                "unchanged": unchanged,
                "errors": errors,
                "plan": plan_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": len(errors) == 0,
                "dry_run": dry_run,
                "total_repos": len(rows),
                "changed": changed,
                "unchanged": unchanged,
                "errors": len(errors),
                "report": str(out),
            }
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

