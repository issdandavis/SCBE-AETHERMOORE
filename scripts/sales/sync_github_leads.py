#!/usr/bin/env python3
"""
Collect automation-service leads from GitHub issues and build outreach drafts.

Current source:
    AinurMaxinum/Upwork-proposals (public issue feed used as lead intake)

Usage:
    python scripts/sales/sync_github_leads.py
    python scripts/sales/sync_github_leads.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "sales"
SOURCE_REPO = "AinurMaxinum/Upwork-proposals"
KEYWORDS = (
    "automation",
    "n8n",
    "zapier",
    "make.com",
    "api",
    "integration",
    "crm",
    "workflow",
    "shopify",
    "ai agent",
)


def run_gh_json(path: str, params: dict[str, str]) -> list[dict]:
    cmd = ["gh", "api", "-X", "GET", path]
    for key, value in params.items():
        cmd.extend(["-f", f"{key}={value}"])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh api failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def score_issue(issue: dict) -> int:
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    return sum(1 for key in KEYWORDS if key in text)


def make_offer(issue: dict) -> str:
    title = issue.get("title", "").lower()
    if "linkedin" in title:
        wedge = "repair LinkedIn lead-flow reliability and dedupe bad records"
    elif "shopify" in title:
        wedge = "stabilize Shopify workflow automation with governed retries and alerts"
    elif "crm" in title:
        wedge = "connect CRM attribution end-to-end with weekly AI audit reporting"
    else:
        wedge = "ship production-safe n8n/Make/Zapier automations with governance checks"

    return (
        f"I can {wedge}. If useful, I can deliver a 48-hour stabilization plan, "
        "then implement in a one-week sprint with handoff docs."
    )


def to_markdown(rows: list[dict], generated_at: str) -> str:
    lines = [
        f"# GitHub Lead Backlog ({generated_at})",
        "",
        f"Source: `{SOURCE_REPO}` issue feed via `gh api`.",
        "",
        "| Issue | Lead Signal | Offer Draft |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| [#{row['number']}]({row['html_url']}) | {row['title'].replace('|', '/')} | {row['offer'].replace('|', '/')} |"
        )
    lines.append("")
    lines.append("## Next action")
    lines.append("1. Send top 5 offers with strongest keyword score first.")
    lines.append("2. Track response state in your CRM or Notion board.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync automation-service leads from GitHub issues.")
    parser.add_argument("--limit", type=int, default=15, help="Number of leads to keep after scoring.")
    args = parser.parse_args()

    issues = run_gh_json(
        f"repos/{SOURCE_REPO}/issues",
        {"state": "open", "per_page": "100"},
    )

    candidates = []
    for issue in issues:
        if issue.get("pull_request"):
            continue
        score = score_issue(issue)
        if score == 0:
            continue
        candidates.append(
            {
                "number": issue["number"],
                "title": issue.get("title", "").strip(),
                "html_url": issue.get("html_url", ""),
                "created_at": issue.get("created_at", ""),
                "score": score,
                "offer": make_offer(issue),
            }
        )

    candidates.sort(key=lambda row: (row["score"], row["created_at"]), reverse=True)
    selected = candidates[: max(1, args.limit)]

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = ARTIFACT_DIR / f"github_leads_{stamp}.json"
    md_path = ARTIFACT_DIR / f"github_leads_{stamp}.md"

    json_path.write_text(json.dumps(selected, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(selected, generated_at=stamp), encoding="utf-8")

    print(f"[leads] selected={len(selected)}")
    print(f"[leads] json={json_path}")
    print(f"[leads] markdown={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
