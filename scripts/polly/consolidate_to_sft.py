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
LEAD_PREFIX = "polly-leads/"

# project_type → offer Polly should steer the buyer toward. Mirrors
# the JS commerce catalog at api/polly/commerce.js but kept inline so
# the training script doesn't take a Node dependency. When the
# project_type isn't in this map, fall through to advisory-call.
LEAD_OFFER_MAP = {
    "audit": ("Adversarial audit ($5k–$15k, 1–3 weeks)", "advisory-call"),
    "custom-overlay": ("Custom governance overlay ($25k–$80k, 4–10 weeks)", "advisory-call"),
    "advisory-call": ("Short advisory call ($300, 60 min)", "advisory-call"),
    "subcontract": ("Federal subcontract role ($150–$250/hr)", "advisory-call"),
    "training": ("Custom AI safety training engagement", "advisory-call"),
    "other": ("AI Governance Snapshot ($500, fixed scope)", "snapshot"),
}

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


def lead_to_sft(record: dict, source_path: str) -> dict | None:
    # Captured leads contain genuine buying-intent text we wrote 0% of.
    # Convert each into an SFT pair so the model learns to recognize and
    # route real intent shapes. The user side reconstructs what a buyer
    # would type in chat; the assistant side steers them to the right
    # offer using the same routing the JS commerce module would pick.
    project_type = str(record.get("project_type") or "").strip().lower()
    budget = str(record.get("budget") or "").strip()
    timeline = str(record.get("timeline") or "").strip()
    description = str(record.get("description") or "").strip()
    if not description and not project_type:
        return None

    user_parts = []
    if project_type:
        user_parts.append(f"I'm looking for help with {project_type.replace('-', ' ')}.")
    if budget and budget != "open":
        user_parts.append(f"Budget is around {budget}.")
    if timeline and timeline != "open":
        user_parts.append(f"Timeline {timeline}.")
    if description:
        user_parts.append(description)
    user = " ".join(user_parts).strip()
    if not user:
        return None

    offer_label, offer_kind = LEAD_OFFER_MAP.get(
        project_type, ("AI Governance Snapshot ($500, fixed scope)", "snapshot")
    )
    if offer_kind == "snapshot":
        assistant = (
            f"From what you described, the right starting point is the {offer_label}. "
            "It's one workflow, one written read, three prioritized fixes, and an evidence "
            "checklist — five business days from intake. Buy here: "
            "https://aethermoore.com/SCBE-AETHERMOORE/governance-snapshot.html"
        )
    else:
        assistant = (
            f"What you're describing fits {offer_label}. The fastest path is a short call to "
            "scope it — email issdandavis7795@gmail.com with a one-paragraph outcome and I'll "
            "reply same day. Full menu: https://aethermoore.com/SCBE-AETHERMOORE/hire.html"
        )

    return {
        "messages": [
            {"role": "system", "content": POLLY_SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "ts": record.get("ts"),
            "session_id": None,
            "intent": "lead",
            "provider": "lead-template",
            "project_type": project_type or None,
            "budget": budget or None,
            "timeline": timeline or None,
            "source_path": source_path,
        },
    }


def list_files_under(api, repo: str, prefix: str, month: str | None) -> Iterable[str]:
    # Generic version of the prior list_chat_files — works for both
    # polly-chat-live/ and polly-leads/ since the date-folder layout is
    # identical between them.
    files = api.list_repo_files(repo_id=repo, repo_type="dataset")
    for path in files:
        if not path.startswith(prefix):
            continue
        if month and f"/{month}-" not in path and not path.startswith(f"{prefix}{month}/"):
            if not path.startswith(f"{prefix}{month}"):
                continue
        yield path


def list_chat_files(api, repo: str, month: str | None) -> Iterable[str]:
    return list_files_under(api, repo, CHAT_PREFIX, month)


def list_lead_files(api, repo: str, month: str | None) -> Iterable[str]:
    return list_files_under(api, repo, LEAD_PREFIX, month)


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
        help="Local output path. Defaults to polly-sft-{month}.jsonl or " "polly-sft-all.jsonl.",
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
    leads = parser.add_mutually_exclusive_group()
    leads.add_argument(
        "--include-leads",
        action="store_true",
        default=True,
        help="Also pull polly-leads/ records and synthesize SFT pairs from them (default).",
    )
    leads.add_argument(
        "--skip-leads",
        action="store_true",
        help="Skip lead records; use chat turns only.",
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

    include_leads = not args.skip_leads

    kept_chat = 0
    kept_leads = 0
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
            kept_chat += 1

        if include_leads:
            for path in list_lead_files(api, args.repo, args.month):
                record = download_record(api, args.repo, path)
                if not isinstance(record, dict):
                    continue
                if skip_smoke and is_smoke(record):
                    skipped_smoke += 1
                    continue
                sft = lead_to_sft(record, path)
                if sft is None:
                    skipped_empty += 1
                    continue
                out.write(json.dumps(sft, ensure_ascii=False) + "\n")
                kept_leads += 1

    kept = kept_chat + kept_leads
    print(
        f"[done] kept={kept} (chat={kept_chat}, leads={kept_leads}) "
        f"skipped_smoke={skipped_smoke} skipped_empty={skipped_empty} out={out_path}"
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
