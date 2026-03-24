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
POST_TO_BUFFER = REPO_ROOT / "scripts" / "publish" / "post_to_buffer.py"
POST_TO_DEVTO = REPO_ROOT / "scripts" / "publish" / "post_to_devto.py"
POST_TO_HUGGINGFACE_DISCUSSION = REPO_ROOT / "scripts" / "publish" / "post_to_huggingface_discussion.py"
POST_TO_GITHUB_DISCUSSIONS = REPO_ROOT / "scripts" / "publish" / "publish_discussions.py"

PLATFORM_PREFIXES: dict[str, tuple[str, ...]] = {
    "x": ("x_thread_", "twitter_thread_"),
    "twitter": ("x_thread_", "twitter_thread_"),
    "buffer": ("x_thread_", "twitter_thread_", "buffer_"),
    "linkedin": ("linkedin_",),
    "medium": ("medium_",),
    "substack": ("substack_",),
    "devto": ("devto_",),
    "huggingface": ("hf_", "huggingface_"),
    "bluesky": ("bluesky_",),
    "mastodon": ("mastodon_",),
    "reddit": ("reddit_",),
    "hackernews": ("hackernews_",),
    "github": ("2026-",),
}

PLATFORM_ORDER = [
    "x",
    "buffer",
    "github",
    "huggingface",
    "linkedin",
    "medium",
    "substack",
    "devto",
    "reddit",
    "bluesky",
    "mastodon",
    "hackernews",
]


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


def _run_buffer_publish(article: Path, dry_run: bool) -> tuple[str, str]:
    if not POST_TO_BUFFER.exists():
        return "error", f"missing publisher: {POST_TO_BUFFER}"

    is_thread = "thread" in article.name.lower()
    if is_thread:
        cmd = [sys.executable, str(POST_TO_BUFFER), "--thread", str(article)]
        if dry_run:
            cmd.append("--dry-run")
    else:
        text = _extract_text_for_single_post(article)
        cmd = [sys.executable, str(POST_TO_BUFFER), "--text", text]
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


def _run_devto_publish(
    article: Path, dry_run: bool, *, tags: list[str] | None = None, series: str = ""
) -> tuple[str, str]:
    if not POST_TO_DEVTO.exists():
        return "error", f"missing publisher: {POST_TO_DEVTO}"
    cmd = [sys.executable, str(POST_TO_DEVTO), "--file", str(article)]
    if tags:
        cmd.extend(["--tags", ",".join(tags)])
    if series:
        cmd.extend(["--series", series])
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


def _run_hf_publish(
    article: Path,
    dry_run: bool,
    *,
    repo_id: str,
    repo_type: str = "model",
    title: str = "",
) -> tuple[str, str]:
    if not POST_TO_HUGGINGFACE_DISCUSSION.exists():
        return "error", f"missing publisher: {POST_TO_HUGGINGFACE_DISCUSSION}"
    cmd = [
        sys.executable,
        str(POST_TO_HUGGINGFACE_DISCUSSION),
        "--file",
        str(article),
        "--repo-id",
        repo_id,
        "--repo-type",
        repo_type,
    ]
    if title:
        cmd.extend(["--title", title])
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


def _run_github_publish_file(
    article: Path,
    dry_run: bool,
    *,
    owner: str,
    repo: str,
    category: str,
) -> tuple[str, str]:
    if not POST_TO_GITHUB_DISCUSSIONS.exists():
        return "error", f"missing publisher: {POST_TO_GITHUB_DISCUSSIONS}"
    cmd = [
        sys.executable,
        str(POST_TO_GITHUB_DISCUSSIONS),
        "--file",
        str(article),
        "--owner",
        owner,
        "--repo",
        repo,
        "--category",
        category,
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


def _load_campaign_posts(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        posts = payload.get("posts", [])
        if isinstance(posts, list):
            return [row for row in posts if isinstance(row, dict)]
    return []


def _route_campaign_post(post: dict, *, dry_run: bool, browser_fallback: bool, browser_publish: bool) -> dict:
    platform = str(post.get("platform", "")).strip().lower()
    content_file = Path(str(post.get("content_file", "")).strip())
    article = content_file if content_file.is_absolute() else (REPO_ROOT / content_file)
    row = {
        "platform": platform,
        "site": str(post.get("site", "")).strip(),
        "post_id": str(post.get("id", "")).strip(),
        "article": str(article),
        "status": "skipped",
        "mode": "dry-run" if dry_run else "live",
        "browser_fallback": browser_fallback,
        "browser_publish": browser_publish,
        "detail": "",
        "title": str(post.get("title", "")).strip(),
    }
    if not article.exists():
        row["status"] = "no_article"
        row["detail"] = f"Content file does not exist: {article}"
        return row

    target = post.get("target", {}) if isinstance(post.get("target"), dict) else {}
    if platform == "github":
        status, detail = _run_github_publish_file(
            article,
            dry_run=dry_run,
            owner=str(target.get("owner", "issdandavis")),
            repo=str(target.get("repo", "SCBE-AETHERMOORE")),
            category=str(target.get("category", "General")),
        )
        row["status"] = status
        row["detail"] = detail
        return row
    if platform == "huggingface":
        status, detail = _run_hf_publish(
            article,
            dry_run=dry_run,
            repo_id=str(target.get("repo_id", "")),
            repo_type=str(target.get("repo_type", "model")),
            title=str(post.get("title", "")),
        )
        row["status"] = status
        row["detail"] = detail
        return row
    if platform == "devto":
        tags = [str(tag).strip() for tag in post.get("tags", []) if str(tag).strip()]
        status, detail = _run_devto_publish(
            article,
            dry_run=dry_run,
            tags=tags,
            series=str(post.get("series", "")),
        )
        row["status"] = status
        row["detail"] = detail
        return row
    if platform == "x":
        status, detail = _run_x_publish(article, dry_run=dry_run)
        row["status"] = status
        row["detail"] = detail
        return row
    if platform == "buffer":
        status, detail = _run_buffer_publish(article, dry_run=dry_run)
        row["status"] = status
        row["detail"] = detail
        return row

    row["status"] = "staged_manual"
    row["detail"] = (
        "API publisher not implemented for this platform; staged package is ready for browser/manual posting."
    )
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish SCBE articles across supported platforms.")
    parser.add_argument("--dry-run", action="store_true", help="Do not publish; report what would be posted.")
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated platforms (x,buffer,github,huggingface,linkedin,medium,devto,reddit,hackernews).",
    )
    parser.add_argument(
        "--campaign-posts", default="", help="Path to campaign posts JSON built by build_research_campaign.py"
    )
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
    campaign_posts_path = Path(args.campaign_posts).expanduser().resolve() if args.campaign_posts.strip() else None
    if campaign_posts_path:
        posts = _load_campaign_posts(campaign_posts_path)
        for post in posts:
            platform = str(post.get("platform", "")).strip().lower()
            if platform and platform in platforms:
                statuses.append(
                    _route_campaign_post(
                        post,
                        dry_run=args.dry_run,
                        browser_fallback=bool(args.browser_fallback),
                        browser_publish=bool(args.browser_publish),
                    )
                )

        summary = {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": bool(args.dry_run),
            "platforms": platforms,
            "campaign_posts": str(campaign_posts_path),
            "statuses": statuses,
        }
        evidence_path = EVIDENCE_DIR / f"post_all_{run_id}.json"
        evidence_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[post_all] run_id={run_id}")
        for row in statuses:
            label = row.get("site") or row["platform"]
            print(f"- {label}: {row['status']} :: {row['article'] or '(none)'}")
        print(f"[post_all] evidence={evidence_path}")
        return 0

    explicit_articles: dict[str, Path] = {}
    if args.x_article.strip():
        resolved_x = Path(args.x_article).expanduser().resolve()
        explicit_articles["x"] = resolved_x
        explicit_articles["buffer"] = resolved_x
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
        elif platform == "buffer":
            status, detail = _run_buffer_publish(article, dry_run=args.dry_run)
            row["status"] = status
            row["detail"] = detail
        elif platform == "devto":
            status, detail = _run_devto_publish(article, dry_run=args.dry_run)
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
