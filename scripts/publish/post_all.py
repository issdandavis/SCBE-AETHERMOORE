#!/usr/bin/env python3
"""Multi-platform article publisher with dry-run evidence output.

This is a lightweight orchestrator for existing platform publishers.
Current API posting implementation is wired for X/Twitter via post_to_x.py.
Other platforms are tracked and reported with clear status.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = REPO_ROOT / "content" / "articles"
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "publish_browser"
POST_TO_X = REPO_ROOT / "scripts" / "publish" / "post_to_x.py"
POST_TO_GITHUB_DISCUSSIONS = REPO_ROOT / "scripts" / "publish" / "publish_discussions.py"

PLATFORM_PREFIXES: dict[str, tuple[str, ...]] = {
    "x": ("x_thread_", "twitter_thread_"),
    "twitter": ("x_thread_", "twitter_thread_"),
    "linkedin": ("linkedin_",),
    "medium": ("medium_",),
    "devto": ("devto_",),
    "reddit": ("reddit_",),
    "hackernews": ("hackernews_",),
    "github": ("2026-",),
}

PLATFORM_ORDER = ["x", "github", "linkedin", "medium", "devto", "reddit", "hackernews"]


def _normalize_platforms(raw_only: str | None) -> list[str]:
    if not raw_only:
        return list(PLATFORM_ORDER)
    values = [p.strip().lower() for p in raw_only.split(",") if p.strip()]
    normalized: list[str] = []
    for value in values:
        platform = "x" if value == "twitter" else value
        if platform in PLATFORM_PREFIXES and platform not in normalized:
            normalized.append(platform)
    return normalized


def _pick_article(platform: str) -> Path | None:
    prefixes = PLATFORM_PREFIXES.get(platform, ())
    candidates = []
    for file in ARTICLES_DIR.glob("*.md"):
        if any(file.name.startswith(prefix) for prefix in prefixes):
            candidates.append(file)
    if not candidates:
        return None
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0]


def _extract_text_for_single_post(path: Path, limit: int = 260) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _run_x_publish(article: Path, dry_run: bool) -> tuple[str, str]:
    if not POST_TO_X.exists():
        return "error", f"missing publisher: {POST_TO_X}"

    is_thread = "thread" in article.name.lower()
    if is_thread:
        cmd = [sys.executable, str(POST_TO_X), "--thread", str(article)]
        if dry_run:
            cmd.append("--dry-run")
    else:
        text = _extract_text_for_single_post(article)
        cmd = [sys.executable, str(POST_TO_X), "--text", text]
        if dry_run:
            cmd.append("--dry-run")

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", ".")},
    )
    output = (proc.stdout or "").strip()
    if proc.returncode == 0:
        return ("dry_run_ready" if dry_run else "posted"), output[-4000:]
    return "error", ((proc.stderr or output) or "unknown error")[-4000:]


def _run_github_publish(dry_run: bool, glob_pattern: str, limit: int) -> tuple[str, str]:
    if not POST_TO_GITHUB_DISCUSSIONS.exists():
        return "error", f"missing publisher: {POST_TO_GITHUB_DISCUSSIONS}"
    cmd = [
        sys.executable,
        str(POST_TO_GITHUB_DISCUSSIONS),
        "--glob",
        glob_pattern,
        "--limit",
        str(limit),
        "--skip-existing",
    ]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", ".")},
    )
    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode == 0:
        return ("dry_run_ready" if dry_run else "posted"), output[-4000:]
    return "error", output[-4000:] or "unknown error"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish SCBE articles across supported platforms.")
    parser.add_argument("--dry-run", action="store_true", help="Do not publish; report what would be posted.")
    parser.add_argument("--only", default="", help="Comma-separated platforms (x,linkedin,medium,devto,reddit,hackernews).")
    parser.add_argument("--browser-fallback", action="store_true", help="Record browser fallback mode in evidence.")
    parser.add_argument("--browser-publish", action="store_true", help="Record browser publish intent in evidence.")
    parser.add_argument(
        "--github-glob",
        default="",
        help="Glob for GitHub Discussions article files in content/articles (default: UTC YYYY-MM-DD-*.md).",
    )
    parser.add_argument("--github-limit", type=int, default=3, help="Max GitHub Discussion posts per run.")
    parser.add_argument("--x-article", default="", help="Explicit article path for X posting.")
    parser.add_argument("--linkedin-article", default="", help="Explicit article path for LinkedIn status reporting.")
    args = parser.parse_args()

    platforms = _normalize_platforms(args.only)
    if not platforms:
        print("No valid platforms selected.")
        return 1

    github_glob = args.github_glob.strip() if args.github_glob else ""
    if not github_glob:
        github_glob = os.environ.get("SCBE_GITHUB_DISCUSSIONS_GLOB", "").strip()
    if not github_glob:
        github_glob = datetime.now(timezone.utc).strftime("%Y-%m-%d-*.md")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    statuses: list[dict] = []
    explicit_articles: dict[str, Path] = {}
    if args.x_article.strip():
        explicit_articles["x"] = Path(args.x_article).expanduser().resolve()
    if args.linkedin_article.strip():
        explicit_articles["linkedin"] = Path(args.linkedin_article).expanduser().resolve()

    for platform in platforms:
        article = explicit_articles.get(platform) or _pick_article(platform)
        row = {
            "platform": platform,
            "article": str(article) if article else None,
            "status": "skipped",
            "mode": "dry-run" if args.dry_run else "live",
            "browser_fallback": bool(args.browser_fallback),
            "browser_publish": bool(args.browser_publish),
            "detail": "",
        }

        if platform == "github":
            status, detail = _run_github_publish(
                dry_run=args.dry_run,
                glob_pattern=github_glob,
                limit=max(1, int(args.github_limit)),
            )
            row["status"] = status
            row["article"] = f"content/articles/{github_glob} (limit={max(1, int(args.github_limit))})"
            row["detail"] = detail
            statuses.append(row)
            continue

        if article is None:
            row["status"] = "no_article"
            row["detail"] = f"No article file found with prefixes: {PLATFORM_PREFIXES.get(platform, ())}"
            statuses.append(row)
            continue
        if platform in explicit_articles and not article.exists():
            row["status"] = "no_article"
            row["detail"] = f"Explicit article path does not exist: {article}"
            statuses.append(row)
            continue

        if platform == "x":
            status, detail = _run_x_publish(article, dry_run=args.dry_run)
            row["status"] = status
            row["detail"] = detail
        else:
            row["status"] = "not_implemented"
            row["detail"] = "API publisher not implemented for this platform in this repo."
        statuses.append(row)

    summary = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run),
        "platforms": platforms,
        "github_glob": github_glob,
        "github_limit": max(1, int(args.github_limit)),
        "statuses": statuses,
    }

    evidence_path = EVIDENCE_DIR / f"post_all_{run_id}.json"
    evidence_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"[post_all] run_id={run_id}")
    for row in statuses:
        print(f"- {row['platform']}: {row['status']} :: {row['article'] or '(none)'}")
    print(f"[post_all] evidence={evidence_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
