#!/usr/bin/env python3
"""Verify the static docs surface has required pages and live checkout links."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PLACEHOLDER_PATTERNS = (
    re.compile(r"buy\.stripe\.com/test_", re.I),
    re.compile(r"ko-fi\.com/s/placeholder", re.I),
    re.compile(r"example\.com", re.I),
)


def verify_docs_surface(root: Path, required: list[str], *, require_checkout: bool = False) -> tuple[bool, list[str]]:
    findings: list[str] = []
    if not root.exists():
        return False, [f"root missing: {root}"]

    combined = ""
    for rel in required:
        path = root / rel
        if not path.exists():
            findings.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        combined += "\n" + text
        title_ok = "<html" in text.lower() or rel.lower().endswith((".md", ".txt"))
        findings.append(f"{rel}: {'ok' if title_ok else 'warning:no-html-root'}")

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(combined):
            findings.append(f"blocker: placeholder checkout/reference matched {pattern.pattern}")

    if require_checkout and "https://buy.stripe.com/" not in combined:
        findings.append("blocker: no Stripe hosted checkout link found")

    ok = not any(item.startswith("blocker:") or item.endswith(": missing") for item in findings)
    return ok, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="docs")
    parser.add_argument("--require", action="append", default=[])
    parser.add_argument("--require-checkout", action="store_true")
    args = parser.parse_args(argv)

    required = args.require or ["index.html"]
    ok, findings = verify_docs_surface(Path(args.root), required, require_checkout=args.require_checkout)
    for finding in findings:
        print(f"[docs-publish-surface] {finding}")
    if not ok:
        return 1
    print("[docs-publish-surface] docs surface verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
