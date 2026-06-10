"""CLI entry for the governed browser-tab manifest layer.

Fetches a URL over HTTP, builds a governed, context-frugal manifest, and prints it as
JSON. This is the harness/agent-bus surface: an agent can learn *what a page contains*
(outline + safety tier) for a few hundred tokens instead of pulling the whole page into
context, and only drill into a section when it needs one.

Usage:
    python -m src.aetherbrowser.tab_manifest_cli <url> [--json]
    python -m src.aetherbrowser.tab_manifest_cli <url> --section "Distance" [--allow-untrusted]

Notes:
    * Reference/research domains and the operator's own site are trusted by default
      (see :data:`TRUSTED_REFERENCE_DOMAINS`); unknown domains still quarantine.
    * Plain HTTP fetch only — client-rendered SPAs return an empty shell and should be
      rendered headless first (out of scope for this CLI).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from src.aetherbrowser.tab_manifest import TabStore

# Deterministic-ish default; the harness can pass --fetched-at for reproducibility.
_DEFAULT_FETCHED_AT = 0.0
_USER_AGENT = "SCBE-AetherBrowser/1.0 (+governed tab manifest)"


def _fetch(url: str, *, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (governed downstream)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, "ignore")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tab-manifest", description="Governed browser-tab manifest")
    parser.add_argument("url", help="URL to fetch and digest")
    parser.add_argument("--section", help="Return one section body instead of the manifest")
    parser.add_argument("--allow-untrusted", action="store_true", help="Read a quarantined tab's section")
    parser.add_argument("--fetched-at", type=float, default=_DEFAULT_FETCHED_AT, help="Timestamp for the tab id")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default)")
    args = parser.parse_args(argv)

    try:
        html = _fetch(args.url)
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        print(json.dumps({"ok": False, "error": f"fetch failed: {exc}", "url": args.url}))
        return 1

    store = TabStore()  # trusts reference domains by default
    manifest = store.save(args.url, html, fetched_at=args.fetched_at)

    if args.section:
        result = store.read_section(manifest.tab_id, args.section, allow_untrusted=args.allow_untrusted)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 2

    payload = {"ok": True, **manifest.to_context_dict(), "token_estimate": manifest.token_estimate}
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
