#!/usr/bin/env python3
"""Publish a markdown note as a Hugging Face Discussion."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ImportError:  # pragma: no cover - handled at runtime
    HfApi = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "publish_browser"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta: dict[str, str] = {}
            for line in parts[1].strip().splitlines():
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip().strip('"').strip("'")
            return meta, parts[2].strip()
    return {}, text


def _extract_title(body: str) -> tuple[str, str]:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            remaining = "\n".join(lines[:index] + lines[index + 1 :]).strip()
            return title, remaining
    return "", body


def _strip_byline(body: str) -> str:
    return re.sub(r"^\*\*By[^*]*\*\*\s*\|[^\n]*\n+---\n*", "", body, count=1).strip()


def publish_discussion(
    file_path: Path,
    repo_id: str,
    repo_type: str | None = None,
    title: str | None = None,
    token: str | None = None,
    dry_run: bool = False,
) -> dict:
    raw = file_path.read_text(encoding="utf-8", errors="replace")
    meta, body = _parse_frontmatter(raw)

    if not title:
        title = meta.get("title", "")
    if not title:
        title, body = _extract_title(body)
    else:
        _, body = _extract_title(body)
    body = _strip_byline(body)

    if not title:
        return {"error": "Could not determine discussion title."}

    payload = {
        "repo_id": repo_id,
        "repo_type": repo_type,
        "title": title,
        "description": body,
    }

    if dry_run:
        print("[hf] DRY RUN — would create discussion:")
        print(f"  Repo: {repo_id} ({repo_type or 'model'})")
        print(f"  Title: {title}")
        print(f"  Body length: {len(body)} chars")
        return {"dry_run": True, "payload": payload}

    if HfApi is None:
        return {"error": "huggingface_hub is not installed."}

    api = HfApi(token=token)
    try:
        created = api.create_discussion(
            repo_id=repo_id,
            repo_type=repo_type,
            title=title,
            description=body,
        )
    except Exception as exc:  # pragma: no cover - depends on remote API
        return {"error": str(exc)}

    return {
        "id": getattr(created, "id", None),
        "num": getattr(created, "num", None),
        "title": getattr(created, "title", title),
        "url": getattr(created, "url", None),
        "status": getattr(created, "status", None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a markdown file as a Hugging Face Discussion.")
    parser.add_argument("--file", required=True, help="Path to the markdown article file")
    parser.add_argument("--repo-id", required=True, help="Hub repo id, e.g. issdandavis/phdm-21d-embedding")
    parser.add_argument("--repo-type", choices=["model", "dataset", "space"], default="model")
    parser.add_argument("--title", default="", help="Override discussion title")
    parser.add_argument("--token", default="", help="Optional Hugging Face token override")
    parser.add_argument("--dry-run", action="store_true", help="Preview without publishing")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        print(f"[hf] File not found: {file_path}", file=sys.stderr)
        return 1

    result = publish_discussion(
        file_path=file_path,
        repo_id=args.repo_id,
        repo_type=args.repo_type,
        title=args.title or None,
        token=args.token or None,
        dry_run=args.dry_run,
    )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = {
        "run_id": run_id,
        "platform": "huggingface_discussion",
        "file": str(file_path),
        "repo_id": args.repo_id,
        "repo_type": args.repo_type,
        "dry_run": args.dry_run,
        "result": result,
    }
    evidence_path = EVIDENCE_DIR / f"huggingface_discussion_{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"[hf] Evidence saved: {evidence_path}")

    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
