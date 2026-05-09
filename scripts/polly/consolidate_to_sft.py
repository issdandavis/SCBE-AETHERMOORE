#!/usr/bin/env python3
"""Pull per-turn polly records and emit a JSONL ready for SFT fine-tuning.

The capture pipeline (api/polly/chat.js + api/polly/lead.js + api/_polly_hf_upload.js)
writes one JSON file per consented chat turn or lead submission to the private
dataset issdandavis/polly-chat-live. That's great for durability but inconvenient
for training: HF datasets typically expect a single JSONL.

This script reads every record from the dataset (or a local mirror), filters
the chat turns, formats each as a single SFT pair (user message → assistant
reply), and writes the result to either a local file or back to the dataset
under polly-sft/{YYYY-MM}.jsonl.

Output shape (one record per line)::

    {
      "messages": [
        {"role": "system", "content": "<polly system prompt>"},
        {"role": "user", "content": "<user message>"},
        {"role": "assistant", "content": "<assistant reply>"}
      ],
      "metadata": {
        "ts": 1715201652,
        "session_id": "hire-1715201640000",
        "intent": "research",
        "provider": "research",
        "source_path": "polly-chat-live/2026-05-09/20260509T203412-a4f7c2.json"
      }
    }

Usage::

    HF_TOKEN=hf_xxx python scripts/polly/consolidate_to_sft.py \\
        --month 2026-05 --out polly-sft-2026-05.jsonl

    # Same, plus push the result back to the dataset under polly-sft/2026-05.jsonl
    HF_TOKEN=hf_xxx python scripts/polly/consolidate_to_sft.py \\
        --month 2026-05 --upload

    # Drop low-quality records (matches consolidate_smoke_records heuristic)
    HF_TOKEN=hf_xxx python scripts/polly/consolidate_to_sft.py \\
        --month 2026-05 --out out.jsonl --skip-smoke

Use --skip-smoke (default true) to filter the same hard-criteria smoke records
that `clean_smoke_records.py` deletes. Pass --include-smoke to keep them.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from typing import Iterable

DEFAULT_REPO = "issdandavis/polly-chat-live"
CHAT_PREFIX = "polly-chat-live/"

POLLY_SYSTEM_PROMPT = (
    "You are Polly, the AI assistant for AetherMoore — an AI safety and "
    "governance framework using hyperbolic geometry with a 14-layer security "
    "pipeline. Be helpful, concise, and accurate. If asked about SCBE, "
    "explain the core innovation: governed agent behavior with auditable "
    "safety decisions and cheap-first/local-first model routing."
)

SMOKE_CONTACT_DOMAINS = ("@example.com", "@example.org", "@example.net")
SMOKE_CONTACT_PREFIXES = ("smoke@", "verify-deploy@", "goal-complete@")
SMOKE_SESSION_PREFIXES = ("goal-complete", "smoke", "test-", "local-smoke")


def is_smoke(record: dict) -> bool:
    contact = str(record.get("contact") or "").lower().strip()
    if any(contact.endswith(d) for d in SMOKE_CONTACT_DOMAINS):
        return True
    if any(contact.startswith(p) for p in SMOKE_CONTACT_PREFIXES):
        return True
    session = str(record.get("session_id") or "").lower()
    if any(session.startswith(p) for p in SMOKE_SESSION_PREFIXES):
        return True
    source = str(record.get("source") or "").lower()
    if source == "curl-smoke" or source.startswith("smoke-"):
        return True
    return False


def to_sft(record: dict, source_path: str) -> dict | None:
    user = (record.get("user") or "").strip()
    assistant = (record.get("assistant") or "").strip()
    if not user or not assistant:
        return None
    return {
        "messages": [
            {"role": "system", "content": POLLY_SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "ts": record.get("ts"),
            "session_id": record.get("session_id"),
            "intent": record.get("intent"),
            "provider": record.get("provider"),
            "source_path": source_path,
        },
    }


def list_chat_files(api, repo: str, month: str | None) -> Iterable[str]:
    files = api.list_repo_files(repo_id=repo, repo_type="dataset")
    for path in files:
        if not path.startswith(CHAT_PREFIX):
            continue
        if month and f"/{month}-" not in path and not path.startswith(f"{CHAT_PREFIX}{month}/"):
            # path layout is polly-chat-live/2026-05-09/...; match by YYYY-MM prefix
            if not path.startswith(f"{CHAT_PREFIX}{month}"):
                continue
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
        help="HF dataset to read from (default: issdandavis/polly-chat-live)",
    )
    parser.add_argument(
        "--month",
        help="Filter by year-month (e.g. 2026-05). Omit to consolidate everything.",
    )
    parser.add_argument(
        "--out",
        help="Local output path. Defaults to polly-sft-{month}.jsonl or "
        "polly-sft-all.jsonl.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Also upload the JSONL back to the dataset under polly-sft/{month or 'all'}.jsonl.",
    )
    smoke = parser.add_mutually_exclusive_group()
    smoke.add_argument(
        "--skip-smoke",
        action="store_true",
        default=True,
        help="Skip records flagged by the smoke heuristic (default).",
    )
    smoke.add_argument(
        "--include-smoke",
        action="store_true",
        help="Keep smoke-test records in the output.",
    )
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("[error] HF_TOKEN not set", file=sys.stderr)
        return 2

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[error] huggingface_hub not installed; run `pip install huggingface_hub`", file=sys.stderr)
        return 2

    api = HfApi(token=token)
    out_path = args.out or f"polly-sft-{args.month or 'all'}.jsonl"
    skip_smoke = not args.include_smoke

    kept = 0
    skipped_smoke = 0
    skipped_empty = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for path in list_chat_files(api, args.repo, args.month):
            record = download_record(api, args.repo, path)
            if not isinstance(record, dict):
                continue
            if skip_smoke and is_smoke(record):
                skipped_smoke += 1
                continue
            sft = to_sft(record, path)
            if sft is None:
                skipped_empty += 1
                continue
            out.write(json.dumps(sft, ensure_ascii=False) + "\n")
            kept += 1

    print(
        f"[done] kept={kept} skipped_smoke={skipped_smoke} skipped_empty={skipped_empty} "
        f"out={out_path}"
    )

    if args.upload and kept > 0:
        with open(out_path, "rb") as handle:
            blob = handle.read()
        target = f"polly-sft/{args.month or 'all'}.jsonl"
        api.upload_file(
            path_or_fileobj=io.BytesIO(blob),
            path_in_repo=target,
            repo_id=args.repo,
            repo_type="dataset",
            commit_message=f"chore(polly): consolidate {kept} SFT pair(s)",
        )
        print(f"[uploaded] {args.repo}:{target}")

    return 0 if kept > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
