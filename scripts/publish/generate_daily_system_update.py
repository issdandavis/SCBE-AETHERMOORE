#!/usr/bin/env python3
"""Generate daily SCBE system-update posts for social surfaces."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = REPO_ROOT / "content" / "articles"


def run_cmd(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def collect_recent_commits(repo_root: Path, since_hours: int, limit: int) -> list[str]:
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    out = run_cmd(
        ["git", "log", f"--since={since_iso}", "--pretty=format:%s", f"-n{max(1, limit)}"],
        cwd=repo_root,
    )
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if lines:
        return lines
    fallback = run_cmd(["git", "log", "--pretty=format:%s", f"-n{max(1, limit)}"], cwd=repo_root)
    return [line.strip() for line in fallback.splitlines() if line.strip()]


def build_summary_points(commits: list[str], max_points: int) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()
    for msg in commits:
        cleaned = msg.strip().rstrip(".")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        points.append(cleaned)
        if len(points) >= max_points:
            break
    return points


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_github_update(date_iso: str, points: list[str]) -> str:
    lines = [
        f"# SCBE System Update - {date_iso}",
        "",
        "## What shipped",
    ]
    if points:
        for point in points:
            lines.append(f"- {point}")
    else:
        lines.append("- Maintenance day: stability, cleanup, and reliability checks.")
    lines.extend(
        [
            "",
            "## Current focus",
            "- Governed automation quality gates",
            "- Research-to-deployment reliability",
            "- Production-safe multi-agent workflows",
            "",
            "## Contact",
            "- If you want a pilot walkthrough, open a GitHub Discussion or issue in this repo.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_x_thread(date_iso: str, points: list[str]) -> str:
    compact_points = points[:3] if points else ["Maintenance day: reliability and cleanup focus"]
    slots = [
        f"SCBE daily update ({date_iso})\n\nWe shipped governed workflow and reliability improvements.",
        "Highlights:\n" + "\n".join(f"- {point}" for point in compact_points[:2]),
        (
            "Why it matters:\n"
            "Deterministic evidence + safer multi-agent routing means faster deployment decisions."
        ),
        "Next: pilot conversion pipeline + daily system update automation. Follow for build logs.",
    ]
    lines = [f"# SCBE X Thread - {date_iso}", ""]
    total = len(slots)
    for idx, text in enumerate(slots, start=1):
        lines.append(f"## {idx}/{total}")
        lines.append(text.strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_linkedin_update(date_iso: str, points: list[str]) -> str:
    lines = [
        f"# SCBE Daily Build Update ({date_iso})",
        "",
        "We are shipping governed AI workflow infrastructure with deterministic audit trails.",
        "",
        "Today's progress:",
    ]
    if points:
        for point in points:
            lines.append(f"- {point}")
    else:
        lines.append("- Reliability and repo hygiene pass completed.")
    lines.extend(
        [
            "",
            "Why this matters:",
            "- Faster pilot-to-decision cycles",
            "- Safer autonomous workflow operations",
            "- Clear evidence outputs for engineering and procurement teams",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily SCBE social system updates.")
    parser.add_argument("--repo-root", default="", help="Repository root path (optional).")
    parser.add_argument("--since-hours", type=int, default=24, help="Lookback window for commit highlights.")
    parser.add_argument("--commit-limit", type=int, default=8, help="Max commits inspected for summary.")
    parser.add_argument("--point-limit", type=int, default=5, help="Max bullet points in generated updates.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve() if args.repo_root else REPO_ROOT
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_compact = today.replace("-", "_")

    commits = collect_recent_commits(repo_root=repo_root, since_hours=max(1, int(args.since_hours)), limit=max(1, int(args.commit_limit)))
    points = build_summary_points(commits=commits, max_points=max(1, int(args.point_limit)))

    github_path = ARTICLES_DIR / f"{today}-system-update.md"
    x_path = ARTICLES_DIR / f"x_thread_system_update_{today_compact}.md"
    linkedin_path = ARTICLES_DIR / f"linkedin_system_update_{today_compact}.md"

    write_file(github_path, render_github_update(today, points))
    write_file(x_path, render_x_thread(today, points))
    write_file(linkedin_path, render_linkedin_update(today, points))

    result = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": today,
        "points": points,
        "files": {
            "github": str(github_path.resolve()),
            "x_thread": str(x_path.resolve()),
            "linkedin": str(linkedin_path.resolve()),
        },
        "github_glob": f"{today}-system-update.md",
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[daily-update] generated={today}")
        print(f"[daily-update] github={github_path}")
        print(f"[daily-update] x_thread={x_path}")
        print(f"[daily-update] linkedin={linkedin_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
