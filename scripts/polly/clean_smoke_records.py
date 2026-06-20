#!/usr/bin/env python3
"""Delete smoke-test records from the private polly-chat-live dataset.

The capture pipeline writes one JSON file per consented chat turn or lead
submission to issdandavis/polly-chat-live. Smoke tests during development
(2026-05-09 verification round, etc.) leave records that look exactly like
real interactions but are noise for training.

This script lists the dataset, downloads each record, decides whether it
looks like a smoke test based on the heuristic below, and (optionally)
deletes the matched files via the HF commit API.

A record is considered smoke if ANY of these are true (HARD criteria — no
free-text matching, so a real user who happens to type "smoke test" in their
description does not get clobbered):
    - contact ends with '@example.com', '@example.org', '@example.net'
    - contact starts with 'smoke@', 'verify-deploy@', 'goal-complete@'
    - session_id starts with 'goal-complete', 'smoke', 'test-', 'local-smoke'
    - source explicitly equals 'curl-smoke' or starts with 'smoke-'

Usage::

    HF_TOKEN=hf_xxx python scripts/polly/clean_smoke_records.py --dry-run
    HF_TOKEN=hf_xxx python scripts/polly/clean_smoke_records.py --apply

Run with --dry-run first to see what would be deleted. --apply executes the
delete commit. The script never deletes files outside polly-chat-live/ and
polly-leads/ even with --apply.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable

DEFAULT_REPO = "issdandavis/polly-chat-live"
SMOKE_CONTACT_DOMAINS = ("@example.com", "@example.org", "@example.net")
SMOKE_CONTACT_PREFIXES = ("smoke@", "verify-deploy@", "goal-complete@")
SMOKE_SESSION_PREFIXES = ("goal-complete", "smoke", "test-", "local-smoke")
SMOKE_SOURCE_VALUES = ("curl-smoke",)
SMOKE_SOURCE_PREFIXES = ("smoke-",)
ALLOWED_PREFIXES = ("polly-chat-live/", "polly-leads/")


def looks_like_smoke(record: dict) -> bool:
    contact = str(record.get("contact") or "").lower().strip()
    if any(contact.endswith(domain) for domain in SMOKE_CONTACT_DOMAINS):
        return True
    if any(contact.startswith(prefix) for prefix in SMOKE_CONTACT_PREFIXES):
        return True
    session_id = str(record.get("session_id") or "").lower()
    if any(session_id.startswith(prefix) for prefix in SMOKE_SESSION_PREFIXES):
        return True
    source = str(record.get("source") or "").lower()
    if source in SMOKE_SOURCE_VALUES:
        return True
    if any(source.startswith(prefix) for prefix in SMOKE_SOURCE_PREFIXES):
        return True
    return False


def list_dataset_files(api, repo: str) -> Iterable[str]:
    try:
        files = api.list_repo_files(repo_id=repo, repo_type="dataset")
    except Exception as exc:  # noqa: BLE001 — propagate context
        print(f"[error] could not list {repo}: {exc}", file=sys.stderr)
        return
    for path in files:
        if any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            yield path


def download_record(api, repo: str, path: str) -> dict | None:
    try:
        local = api.hf_hub_download(repo_id=repo, repo_type="dataset", filename=path)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] download failed for {path}: {exc}", file=sys.stderr)
        return None
    try:
        with open(local, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] parse failed for {path}: {exc}", file=sys.stderr)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--repo",
        default=os.environ.get("POLLY_HF_DATASET", DEFAULT_REPO),
        help="HF dataset to scan (default: issdandavis/polly-chat-live)",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="list candidates, do not delete")
    mode.add_argument("--apply", action="store_true", help="actually delete matched files")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("[error] HF_TOKEN not set in environment", file=sys.stderr)
        return 2

    try:
        from huggingface_hub import HfApi, CommitOperationDelete
    except ImportError:
        print("[error] huggingface_hub not installed; run `pip install huggingface_hub`", file=sys.stderr)
        return 2

    api = HfApi(token=token)
    candidates: list[str] = []
    skipped: list[str] = []

    for path in list_dataset_files(api, args.repo):
        record = download_record(api, args.repo, path)
        if not isinstance(record, dict):
            skipped.append(path)
            continue
        if looks_like_smoke(record):
            candidates.append(path)
            print(f"[smoke] {path}")
            print(
                f"  contact={record.get('contact') or '-'} "
                f"session={record.get('session_id') or '-'} "
                f"kind={record.get('kind') or 'chat'}"
            )

    if not candidates:
        print("[done] no smoke-test records found")
        return 0

    print(f"[summary] {len(candidates)} smoke-test record(s) flagged, {len(skipped)} unparsable")

    if args.dry_run:
        print("[dry-run] re-run with --apply to actually delete")
        return 0

    operations = [CommitOperationDelete(path_in_repo=p) for p in candidates]
    api.create_commit(
        repo_id=args.repo,
        repo_type="dataset",
        operations=operations,
        commit_message=f"chore(polly): drop {len(candidates)} smoke-test record(s)",
    )
    print(f"[applied] deleted {len(candidates)} record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
