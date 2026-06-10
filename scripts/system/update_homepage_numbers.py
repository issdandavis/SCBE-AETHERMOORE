#!/usr/bin/env python3
"""Refresh the #numbers strip in docs/index.html from live badge files + HF API.

Run:
    python scripts/system/update_homepage_numbers.py

Updates the 8-cell numbers strip in-place. Safe to run in CI — reads
docs/static/badges/*.json for local counts, fetches HF API for model/dataset
counts, falls back to current values if the network is unavailable.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "docs" / "index.html"
BADGES = ROOT / "docs" / "static" / "badges"


def _fetch_json(url: str, timeout: int = 6) -> dict | list | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as exc:
        print(f"  warn: {url} — {exc}", file=sys.stderr)
        return None


def gather_counts() -> dict[str, str]:
    counts: dict[str, str] = {}

    # Local badge files
    tests_badge = _fetch_json(f"file://{(BADGES / 'tests.json').as_posix()}")
    if tests_badge and "message" in tests_badge:
        counts["tests"] = tests_badge["message"]

    loc_badge = _fetch_json(f"file://{(BADGES / 'loc.json').as_posix()}")
    if loc_badge and "message" in loc_badge:
        raw = loc_badge["message"].replace(",", "")
        try:
            n = int(raw)
            counts["loc"] = f"{n // 1000}K"
        except ValueError:
            counts["loc"] = loc_badge["message"]

    modules_badge = _fetch_json(f"file://{(BADGES / 'modules.json').as_posix()}")
    if modules_badge and "message" in modules_badge:
        counts["modules"] = modules_badge["message"]

    # HuggingFace API
    hf_models = _fetch_json("https://huggingface.co/api/models?author=issdandavis&limit=200")
    if isinstance(hf_models, list):
        counts["hf_models"] = str(len(hf_models))

    hf_datasets = _fetch_json("https://huggingface.co/api/datasets?author=issdandavis&limit=200")
    if isinstance(hf_datasets, list):
        counts["hf_datasets"] = str(len(hf_datasets))

    return counts


def update_numbers_strip(counts: dict[str, str]) -> bool:
    html = INDEX.read_text(encoding="utf-8")

    def replace_cell(label_text: str, new_value: str) -> str:
        nonlocal html
        # Find the cell by its label text, replace the number in the preceding div
        pattern = (
            r'(<div style="font-size: 28px;[^>]+>)' r"[^<]+" r"(</div>\s*<div[^>]+>[^<]*" + re.escape(label_text) + r")"
        )
        replacement = rf"\g<1>{new_value}\2"
        new_html, n = re.subn(pattern, replacement, html, count=1)
        if n:
            html = new_html
        return html

    changed = False
    old_html = html

    if "tests" in counts:
        val = counts["tests"].rstrip("+") + "+"
        replace_cell("Tests", val)
    if "hf_models" in counts:
        replace_cell("HF Models", counts["hf_models"])
    if "hf_datasets" in counts:
        replace_cell("Datasets", counts["hf_datasets"])
    if "modules" in counts:
        replace_cell("Modules", counts["modules"])
    if "loc" in counts:
        replace_cell("Lines of Code", counts["loc"])

    if html != old_html:
        INDEX.write_text(html, encoding="utf-8")
        changed = True

    return changed


def main() -> int:
    print("Gathering counts...")
    counts = gather_counts()
    print(f"  counts: {counts}")

    print("Updating docs/index.html numbers strip...")
    changed = update_numbers_strip(counts)
    if changed:
        print("  Updated.")
    else:
        print("  No changes (values already match).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
