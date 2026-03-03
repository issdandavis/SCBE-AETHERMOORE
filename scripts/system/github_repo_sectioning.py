#!/usr/bin/env python3
"""Section GitHub repos into sell/public/private governance tiers.

Usage:
    python scripts/system/github_repo_sectioning.py
    python scripts/system/github_repo_sectioning.py --owner issdandavis --limit 200
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "config" / "governance" / "repo_sectioning_policy.json"
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "governance"


@dataclass
class RepoTier:
    owner: str
    name: str
    visibility: str
    url: str
    tier: str
    rationale: str


def run_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return proc.stdout


def get_authenticated_owner() -> str:
    raw = run_cmd(["gh", "api", "user", "--jq", ".login"])
    return raw.strip()


def list_repos(owner: str, limit: int) -> list[dict[str, Any]]:
    cmd = [
        "gh",
        "repo",
        "list",
        owner,
        "--limit",
        str(limit),
        "--json",
        "name,nameWithOwner,visibility,url,description,isPrivate,isFork,isArchived",
    ]
    raw = run_cmd(cmd)
    return json.loads(raw)


def load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def contains_any(value: str, keywords: list[str]) -> bool:
    low = value.lower()
    return any(k in low for k in keywords)


def classify_repo(repo: dict[str, Any], policy: dict[str, Any]) -> RepoTier:
    owner, name = repo["nameWithOwner"].split("/", 1)
    visibility = (repo.get("visibility") or ("PRIVATE" if repo.get("isPrivate") else "PUBLIC")).lower()
    text = " ".join([repo.get("name", ""), repo.get("description", "")]).strip()

    private_keywords = policy["private_keywords"]
    sellable_keywords = policy["sellable_keywords"]
    education_keywords = policy["public_education_keywords"]

    if visibility == "private" or contains_any(text, private_keywords):
        tier = "private_restricted"
        rationale = "Visibility/private keywords indicate sensitive surface."
    elif contains_any(text, sellable_keywords):
        tier = "public_sellable"
        rationale = "Repo looks product/service oriented and should be monetization-facing."
    elif contains_any(text, education_keywords):
        tier = "public_education"
        rationale = "Repo appears education/research oriented and works as top-of-funnel."
    else:
        tier = "public_open"
        rationale = "General public credibility/open-source surface."

    return RepoTier(
        owner=owner,
        name=name,
        visibility=visibility,
        url=repo.get("url", ""),
        tier=tier,
        rationale=rationale,
    )


def write_outputs(rows: list[RepoTier], owner: str) -> tuple[Path, Path]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = ARTIFACT_DIR / f"github_repo_sectioning_{owner}_{stamp}.csv"
    md_path = ARTIFACT_DIR / f"github_repo_sectioning_{owner}_{stamp}.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["owner", "repo", "visibility", "tier", "url", "rationale"])
        for row in rows:
            writer.writerow([row.owner, row.name, row.visibility, row.tier, row.url, row.rationale])

    lines = [
        f"# GitHub Repo Sectioning ({owner})",
        "",
        "| Repo | Visibility | Tier | Rationale |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| [{row.name}]({row.url}) | {row.visibility} | {row.tier} | {row.rationale} |"
        )

    lines.extend(
        [
            "",
            "## Tier Meaning",
            "- `private_restricted`: keep private, no public automation exposure.",
            "- `public_sellable`: public product surface with pricing and lead routing.",
            "- `public_open`: public credibility/research/open-source surface.",
            "- `public_education`: public education/tutorial funnel surface.",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Section GitHub repos into governance tiers.")
    parser.add_argument("--owner", default="", help="GitHub owner login. Defaults to authenticated user.")
    parser.add_argument("--limit", type=int, default=200, help="Max repos to analyze.")
    args = parser.parse_args()

    owner = args.owner.strip() or get_authenticated_owner()
    policy = load_policy()
    repos = list_repos(owner, args.limit)

    rows = [classify_repo(repo, policy) for repo in repos]
    rows.sort(key=lambda r: (r.tier, r.name))
    csv_path, md_path = write_outputs(rows, owner)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.tier] = counts.get(row.tier, 0) + 1

    print(json.dumps({"owner": owner, "count": len(rows), "counts": counts, "csv": str(csv_path), "md": str(md_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
