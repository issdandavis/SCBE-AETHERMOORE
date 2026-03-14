#!/usr/bin/env python3
"""
@file cli.py
@module spiral-word-app/cli
@layer Layer 12, Layer 14
@component Terminal CLI for SpiralWord

Command-line interface for AI and human access to SpiralWord documents.
Supports read, write, AI-assisted editing, and audit inspection.

Usage:
    python cli.py read mydoc
    python cli.py write mydoc "Hello world"
    python cli.py insert mydoc --pos 5 "inserted text"
    python cli.py ai mydoc --provider echo "Improve this paragraph"
    python cli.py audit
    python cli.py providers
    python cli.py docs
"""

import argparse
import json
import sys

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx", file=sys.stderr)
    sys.exit(1)


DEFAULT_BASE = "http://localhost:8000"


def _client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=30.0)


def cmd_read(args):
    """Read a document."""
    with _client(args.base) as c:
        r = c.get(f"/doc/{args.doc_id}")
        r.raise_for_status()
        data = r.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(data.get("text", ""))


def cmd_write(args):
    """Replace entire document content."""
    with _client(args.base) as c:
        r = c.post(
            f"/doc/{args.doc_id}/replace",
            json={"content": args.content, "site_id": args.site_id},
        )
        r.raise_for_status()
        print(f"OK: v{r.json()['version']}")


def cmd_insert(args):
    """Insert text at a position."""
    with _client(args.base) as c:
        r = c.post(
            f"/doc/{args.doc_id}/insert",
            json={
                "position": args.pos,
                "content": args.content,
                "site_id": args.site_id,
            },
        )
        r.raise_for_status()
        d = r.json()
        print(f"OK: v{d['version']} op={d['op_id']}")


def cmd_delete(args):
    """Delete text at a position."""
    with _client(args.base) as c:
        r = c.post(
            f"/doc/{args.doc_id}/delete",
            json={
                "position": args.pos,
                "length": args.length,
                "site_id": args.site_id,
            },
        )
        r.raise_for_status()
        d = r.json()
        print(f"OK: v{d['version']} op={d['op_id']}")


def cmd_ai(args):
    """AI-assisted edit."""
    with _client(args.base) as c:
        payload = {
            "prompt": args.prompt,
            "provider": args.provider,
            "site_id": args.site_id,
        }
        if args.model:
            payload["options"] = {"model": args.model}

        r = c.post(f"/doc/{args.doc_id}/ai", json=payload)
        r.raise_for_status()
        d = r.json()

        if d["status"] == "blocked":
            print(f"BLOCKED: {d['message']}", file=sys.stderr)
            sys.exit(1)

        print(f"OK: v{d['version']} provider={d['ai_provider']} "
              f"tongue={d['tongue']} conf={d['confidence']:.2f} "
              f"len={d['generated_length']}")


def cmd_docs(args):
    """List all documents."""
    with _client(args.base) as c:
        r = c.get("/docs")
        r.raise_for_status()
        docs = r.json()
        if not docs:
            print("No documents.")
            return
        for d in docs:
            print(f"  {d['doc_id']:20s}  v{d['version']:>4d}  "
                  f"{d['op_count']:>4d} ops  {d['text'][:40]!r}")


def cmd_providers(args):
    """List available AI providers."""
    with _client(args.base) as c:
        r = c.get("/ai/providers")
        r.raise_for_status()
        for p in r.json()["providers"]:
            print(f"  {p}")


def cmd_audit(args):
    """Show recent audit log entries."""
    with _client(args.base) as c:
        r = c.get("/audit", params={"n": args.count})
        r.raise_for_status()
        entries = r.json()
        if not entries:
            print("No audit entries.")
            return
        for e in entries:
            print(f"  [{e['action']:12s}] doc={e['doc_id']} "
                  f"site={e['site_id']} tongue={e['tongue']} "
                  f"decision={e['governance_decision']}")


def cmd_check(args):
    """Test a governance decision."""
    with _client(args.base) as c:
        r = c.get(
            "/governance/check",
            params={"action": args.action, "prompt": args.prompt or ""},
        )
        r.raise_for_status()
        d = r.json()
        status = "ALLOW" if d["allowed"] else "DENY"
        print(f"{status}: {d['reason']} (tongue={d['tongue']} conf={d['confidence']:.2f})")


def main():
    parser = argparse.ArgumentParser(
        prog="spiralword",
        description="SpiralWord CLI — Collaborative editor with SCBE governance",
    )
    parser.add_argument(
        "--base", default=DEFAULT_BASE, help="Server base URL"
    )
    parser.add_argument(
        "--site-id", default="cli", help="Site/user ID for edits"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # read
    p = sub.add_parser("read", help="Read a document")
    p.add_argument("doc_id")
    p.add_argument("--json", action="store_true", help="Output full JSON")
    p.set_defaults(func=cmd_read)

    # write (replace all)
    p = sub.add_parser("write", help="Replace document content")
    p.add_argument("doc_id")
    p.add_argument("content")
    p.set_defaults(func=cmd_write)

    # insert
    p = sub.add_parser("insert", help="Insert text at position")
    p.add_argument("doc_id")
    p.add_argument("content")
    p.add_argument("--pos", type=int, default=0, help="Insert position")
    p.set_defaults(func=cmd_insert)

    # delete
    p = sub.add_parser("delete", help="Delete text at position")
    p.add_argument("doc_id")
    p.add_argument("--pos", type=int, default=0, help="Delete position")
    p.add_argument("--length", type=int, default=1, help="Characters to delete")
    p.set_defaults(func=cmd_delete)

    # ai
    p = sub.add_parser("ai", help="AI-assisted edit")
    p.add_argument("doc_id")
    p.add_argument("prompt")
    p.add_argument("--provider", default="echo", help="AI provider name")
    p.add_argument("--model", default=None, help="Model override")
    p.set_defaults(func=cmd_ai)

    # docs
    p = sub.add_parser("docs", help="List all documents")
    p.set_defaults(func=cmd_docs)

    # providers
    p = sub.add_parser("providers", help="List AI providers")
    p.set_defaults(func=cmd_providers)

    # audit
    p = sub.add_parser("audit", help="Show audit log")
    p.add_argument("--count", type=int, default=20, help="Number of entries")
    p.set_defaults(func=cmd_audit)

    # governance check
    p = sub.add_parser("check", help="Test a governance decision")
    p.add_argument("action", help="Action to check (read/insert/delete/etc.)")
    p.add_argument("--prompt", default="", help="Optional prompt for intent classification")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
