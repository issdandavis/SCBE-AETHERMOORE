#!/usr/bin/env python3
"""Preflight check for Notion integration page access.

Usage:
  python scripts/notion_access_check.py --all
  python scripts/notion_access_check.py --config scripts/sync-config.json --all
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from notion_client import Client


def _get_token() -> str:
    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not token:
        raise ValueError("NOTION_TOKEN or NOTION_API_KEY environment variable required.")
    return token


def _load_sync_config(path: str) -> Dict[str, Dict[str, str]]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("sync-config.json must contain a top-level object.")
    return raw


def _extract_page_title(page: Dict[str, Any]) -> str:
    properties = page.get("properties", {})
    title_prop = properties.get("title", {})
    if isinstance(title_prop, dict) and title_prop.get("title"):
        return "".join(t.get("plain_text", "") for t in title_prop["title"])
    for value in properties.values():
        if isinstance(value, dict) and value.get("type") == "title":
            title = value.get("title", [])
            if title:
                return "".join(t.get("plain_text", "") for t in title)
    return "Untitled"


def _safe_id(entry_id: str) -> str:
    return str(entry_id).strip()


def check_pages(entries: List[Tuple[str, str]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    notion = Client(auth=_get_token())
    ok, fail = [], []
    for key, page_id in entries:
        normalized_id = _safe_id(page_id)
        try:
            page = notion.pages.retrieve(page_id=normalized_id)
            ok.append(
                {
                    "key": key,
                    "id": normalized_id,
                    "title": _extract_page_title(page),
                    "status": "OK",
                }
            )
        except Exception as exc:  # pragma: no cover - network/auth failure branch
            fail.append(
                {
                    "key": key,
                    "id": normalized_id,
                    "status": "FAIL",
                    "error": str(exc),
                    "hint": (
                        "Share this page/database with the Termial integration in Notion "
                        "(Settings → Connections → Share), then retry."
                    ),
                }
            )
    return ok, fail


def check_single(notion: Client, key: str, page_id: str) -> Dict[str, Any]:
    normalized_id = _safe_id(page_id)
    try:
        page = notion.pages.retrieve(page_id=normalized_id)
        return {
            "ok": True,
            "key": key,
            "id": normalized_id,
            "title": _extract_page_title(page),
        }
    except Exception as exc:
        return {
            "ok": False,
            "key": key,
            "id": normalized_id,
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser(description="Check Notion page access for configured IDs.")
    parser.add_argument(
        "--config",
        default="scripts/sync-config.json",
        help="Path to sync-config.json",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all entries in the config file.",
    )
    parser.add_argument(
        "--page-id",
        default=None,
        help="Check one page id directly, bypassing config.",
    )
    parser.add_argument(
        "--key",
        default=None,
        help="Optional label for direct page-id checks.",
    )
    args = parser.parse_args()

    if not args.page_id and not args.all:
        parser.error("Use --all to check config entries, or --page-id for a single page.")

    token = _get_token()
    notion = Client(auth=token)

    if args.page_id:
        key = args.key or "direct-check"
        result = check_single(notion, key, args.page_id)
        if result["ok"]:
            print(f'OK   {result["key"]:<24} {result["id"]}  "{result["title"]}"')
            return
        print(f'FAIL {result["key"]:<24} {result["id"]}')
        print(f'     {result["error"]}')
        print("     Hint: Share this page/database with Termial integration and retry.")
        raise SystemExit(1)

    config = _load_sync_config(args.config)
    entries = [(key, val["pageId"]) for key, val in config.items() if isinstance(val, dict) and "pageId" in val]
    if not entries:
        raise ValueError(f"No pageId entries found in {args.config}")

    ok, fail = check_pages(entries)

    for item in ok:
        print(f'OK   {item["key"]:<24} {item["id"]}  "{item["title"]}"')
    for item in fail:
        print(f'FAIL {item["key"]:<24} {item["id"]}')
        print(f'     {item["error"]}')
        print(f'     {item["hint"]}')

    print(f"\nSummary: {len(ok)} OK, {len(fail)} FAIL, total {len(entries)}")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

