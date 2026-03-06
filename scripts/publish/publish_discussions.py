#!/usr/bin/env python3
"""Publish markdown articles as GitHub Discussions via gh CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = REPO_ROOT / "content" / "articles"
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "publish_browser"


def _run_gh_graphql(payload: dict) -> tuple[int, str, str]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as fh:
        fh.write(json.dumps(payload))
        temp_path = fh.name
    try:
        proc = subprocess.run(
            ["gh", "api", "graphql", "--input", temp_path],
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _fetch_repo_and_categories(owner: str, repo: str) -> tuple[str, dict[str, str]]:
    query = {
        "query": (
            "query($owner:String!,$repo:String!){"
            "repository(owner:$owner,name:$repo){id discussionCategories(first:50){nodes{id name}}}"
            "}"
        ),
        "variables": {"owner": owner, "repo": repo},
    }
    rc, out, err = _run_gh_graphql(query)
    if rc != 0:
        raise RuntimeError(f"GitHub API error: {(err or out)[:500]}")
    data = json.loads(out)
    repo_node = data.get("data", {}).get("repository") or {}
    repo_id = repo_node.get("id")
    if not repo_id:
        raise RuntimeError("Repository not found or discussions unavailable.")
    categories = {
        node.get("name", ""): node.get("id", "")
        for node in repo_node.get("discussionCategories", {}).get("nodes", [])
        if node.get("name") and node.get("id")
    }
    return repo_id, categories


def _fetch_existing_titles(owner: str, repo: str, first: int = 100) -> set[str]:
    payload = {
        "query": (
            "query($owner:String!,$repo:String!,$first:Int!){"
            "repository(owner:$owner,name:$repo){"
            "discussions(first:$first,orderBy:{field:CREATED_AT,direction:DESC}){nodes{title}}"
            "}"
            "}"
        ),
        "variables": {"owner": owner, "repo": repo, "first": first},
    }
    rc, out, err = _run_gh_graphql(payload)
    if rc != 0:
        raise RuntimeError(f"GitHub API error while reading discussions: {(err or out)[:500]}")
    data = json.loads(out)
    nodes = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
    return {str(node.get("title", "")).strip() for node in nodes if node.get("title")}


def _pick_articles(glob_pattern: str, limit: int) -> list[Path]:
    files = sorted(ARTICLES_DIR.glob(glob_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[: max(0, limit)]


def _derive_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").strip()


def _create_discussion(repo_id: str, category_id: str, title: str, body: str) -> dict:
    payload = {
        "query": (
            "mutation($title:String!,$body:String!,$repoId:ID!,$catId:ID!){"
            "createDiscussion(input:{repositoryId:$repoId,categoryId:$catId,title:$title,body:$body})"
            "{discussion{id url number}}}"
        ),
        "variables": {
            "title": title,
            "body": body,
            "repoId": repo_id,
            "catId": category_id,
        },
    }
    rc, out, err = _run_gh_graphql(payload)
    if rc != 0:
        return {"ok": False, "error": (err or out)[-2000:]}
    data = json.loads(out)
    disc = data.get("data", {}).get("createDiscussion", {}).get("discussion", {})
    if not disc.get("url"):
        return {"ok": False, "error": out[-2000:]}
    return {"ok": True, "url": disc.get("url"), "number": disc.get("number"), "id": disc.get("id")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish markdown articles as GitHub Discussions.")
    parser.add_argument("--owner", default="issdandavis")
    parser.add_argument("--repo", default="SCBE-AETHERMOORE")
    parser.add_argument("--category", default="General", help="Discussion category name")
    parser.add_argument("--glob", default="2026-*.md", help="Glob inside content/articles/")
    parser.add_argument("--limit", type=int, default=5, help="Max number of articles to publish")
    parser.add_argument("--skip-existing", action="store_true", help="Skip titles that already exist in Discussions")
    parser.add_argument("--dry-run", action="store_true", help="Only prepare and report, do not publish")
    args = parser.parse_args()

    repo_id, categories = _fetch_repo_and_categories(args.owner, args.repo)
    category_id = categories.get(args.category)
    if not category_id:
        available = ", ".join(sorted(categories.keys())) or "(none)"
        raise SystemExit(f"Category '{args.category}' not found. Available: {available}")

    selected = _pick_articles(args.glob, args.limit)
    existing_titles: set[str] = set()
    if args.skip_existing:
        existing_titles = _fetch_existing_titles(args.owner, args.repo, first=100)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results: list[dict] = []

    for path in selected:
        title = _derive_title(path)
        body = path.read_text(encoding="utf-8", errors="replace")
        row = {"file": str(path), "title": title, "status": "skipped"}
        if title in existing_titles:
            row["status"] = "exists"
            row["detail"] = "discussion with same title already exists"
            results.append(row)
            print(f"SKIP (exists): {title}")
            continue
        if args.dry_run:
            row["status"] = "dry_run_ready"
            results.append(row)
            print(f"DRY-RUN: {title}")
            continue
        created = _create_discussion(repo_id, category_id, title, body)
        if created.get("ok"):
            row["status"] = "posted"
            row["url"] = created["url"]
            row["number"] = created["number"]
            print(f"POSTED: {title}")
            print(f"  {created['url']}")
        else:
            row["status"] = "error"
            row["error"] = created.get("error", "unknown")
            print(f"ERROR: {title}")
            print(f"  {row['error'][:240]}")
        results.append(row)

    summary = {
        "run_id": run_id,
        "owner": args.owner,
        "repo": args.repo,
        "category": args.category,
        "glob": args.glob,
        "limit": args.limit,
        "dry_run": bool(args.dry_run),
        "results": results,
    }
    out_path = EVIDENCE_DIR / f"github_discussions_{run_id}.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"evidence={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
