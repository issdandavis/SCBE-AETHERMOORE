"""
@file headless_productivity.py
@module scripts/headless_productivity
@layer Layer 12, Layer 13, Layer 14
@component Headless Browser Productivity CLI

Unified CLI for headless browser productivity workflows:
  - Research: multi-tongue parallel web research → structured documents
  - Extract:  scrape specific pages → DOCX/Markdown/JSON
  - Push:     push extracted content to GitHub (files or issues)
  - Dispatch: send payloads through registered connectors (Zapier, n8n, etc.)
  - Workflow:  run multi-step workflows from a JSON definition file

All actions go through SCBE governance (Harmonic Wall, Layer 12-13).

Usage:
    # Research a topic and save as markdown
    python scripts/headless_productivity.py research \\
        --query "AI safety hyperbolic geometry" \\
        --output report.md

    # Extract content from specific pages
    python scripts/headless_productivity.py extract \\
        --urls https://example.com https://docs.python.org \\
        --format docx --output research.docx

    # Push a document to GitHub
    python scripts/headless_productivity.py push \\
        --file artifacts/documents/report.md \\
        --repo owner/repo --path docs/report.md --branch main

    # Dispatch through a connector
    python scripts/headless_productivity.py dispatch \\
        --connector zapier \\
        --endpoint "https://hooks.zapier.com/hooks/catch/123/abc/" \\
        --payload '{"action": "notify", "message": "Research done"}'

    # Run a multi-step workflow
    python scripts/headless_productivity.py workflow \\
        --workflow-file examples/productivity_workflow.json

    # Interactive mode — open persistent browsers, run commands
    python scripts/headless_productivity.py interactive \\
        --session research-session-1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher
from browser.extensions.doc_handler import DocHandler, ExtractedDocument
from browser.persistent_limb import (
    GovernanceDecision,
    PersistentBrowserLimb,
    evaluate_browser_action,
)

logger = logging.getLogger("headless-productivity")


# ── Research Command ────────────────────────────────────────────────────

async def cmd_research(args: argparse.Namespace) -> None:
    """Research a topic using parallel headless browsers."""
    tongues = args.tongues.split(",") if args.tongues else ["KO", "AV", "CA"]
    doc_handler = DocHandler(output_dir=args.output_dir)

    print(f"[research] Launching {len(tongues)} browser fingers...")
    print(f"[research] Query: {args.query}")
    print(f"[research] Max URLs: {args.max_urls}")

    async with PersistentBrowserLimb(
        session_id=args.session or f"research-{int(time.time())}",
        tongues=tongues,
        governance_enabled=not args.no_governance,
    ) as limb:
        # Step 1: AV scouts the search engine
        search_url = f"https://www.google.com/search?q={args.query.replace(' ', '+')}"
        print(f"[research] AV scouting: {search_url}")

        nav_result = await limb.navigate("AV", search_url)
        if nav_result.get("blocked"):
            print(f"[research] BLOCKED by governance: {nav_result}")
            return

        links = await limb.extract_links("AV")
        # Filter out search engine internal links
        skip_patterns = [
            "google.com/search", "accounts.google", "support.google",
            "maps.google", "translate.google", "webcache.google",
        ]
        candidate_urls = [
            link for link in links
            if not any(skip in link for skip in skip_patterns)
        ][:args.max_urls * 2]

        print(f"[research] Discovered {len(candidate_urls)} candidate URLs")

        # Step 2: Governance filter
        safe_urls = []
        for url in candidate_urls:
            gov = evaluate_browser_action("CA", url, "navigate")
            if gov.decision in (GovernanceDecision.ALLOW, GovernanceDecision.QUARANTINE):
                safe_urls.append(url)
            else:
                print(f"[research] Filtered: {url[:60]} ({gov.decision.value})")
            if len(safe_urls) >= args.max_urls:
                break

        print(f"[research] {len(safe_urls)} URLs passed governance")

        # Step 3: Extract content from safe URLs using CA finger
        extractions = []
        for url in safe_urls:
            print(f"[research] Extracting: {url[:80]}")
            nav = await limb.navigate("CA", url)
            if not nav.get("blocked"):
                text = await limb.extract_text("CA", args.selector)
                title_text = await limb.extract_text("CA", "title")
                page_links = await limb.extract_links("CA")
                extractions.append({
                    "url": url,
                    "title": title_text[:200],
                    "text": text[:args.max_chars],
                    "links": page_links[:20],
                })

        print(f"[research] Extracted content from {len(extractions)} pages")

        # Step 4: Build document
        doc = doc_handler.merge_extractions(
            title=args.title or f"Research: {args.query}",
            extractions=extractions,
            metadata={
                "query": args.query,
                "session_id": limb.session_id,
                "tongues": tongues,
                "governance": not args.no_governance,
            },
        )

        # Step 5: Save in requested format
        output_path = args.output
        if args.format == "docx":
            path = doc_handler.save_docx(doc, output_path)
        elif args.format == "json":
            path = doc_handler.save_json(doc, output_path)
        elif args.format == "text":
            path = doc_handler.save_plain_text(doc, output_path)
        else:
            path = doc_handler.save_markdown(doc, output_path)

        print(f"[research] Document saved: {path}")
        print(f"[research] Doc ID: {doc.doc_id}")
        print(f"[research] Sources: {len(doc.source_urls)}")

        # Optional: push to GitHub
        if args.github_repo:
            gh_path = args.github_path or f"docs/research/{doc.doc_id}.md"
            result = doc_handler.push_to_github(
                doc, path=gh_path, branch=args.github_branch or "main"
            )
            if result["success"]:
                print(f"[research] Pushed to GitHub: {result['url']}")
            else:
                print(f"[research] GitHub push failed: {result.get('error')}")


# ── Extract Command ─────────────────────────────────────────────────────

async def cmd_extract(args: argparse.Namespace) -> None:
    """Extract content from specific URLs."""
    doc_handler = DocHandler(
        github_token=args.github_token or os.getenv("GITHUB_TOKEN", ""),
        github_repo=args.github_repo or os.getenv("GITHUB_REPO", ""),
        output_dir=args.output_dir,
    )

    print(f"[extract] Processing {len(args.urls)} URLs...")

    async with PersistentBrowserLimb(
        session_id=args.session or f"extract-{int(time.time())}",
        tongues=["CA"],
        governance_enabled=not args.no_governance,
    ) as limb:
        extractions = []
        for url in args.urls:
            print(f"[extract] → {url[:80]}")
            nav = await limb.navigate("CA", url)
            if nav.get("blocked"):
                print(f"  BLOCKED: {nav.get('governance', {}).get('explanation', 'unknown')}")
                continue

            text = await limb.extract_text("CA", args.selector)
            title_text = await limb.extract_text("CA", "title")
            links = await limb.extract_links("CA")

            extractions.append({
                "url": url,
                "title": title_text[:200],
                "text": text[:args.max_chars],
                "links": links[:20],
            })
            print(f"  Extracted {len(text)} chars, {len(links)} links")

        if not extractions:
            print("[extract] No content extracted")
            return

        doc = doc_handler.merge_extractions(
            title=args.title or "Extracted Content",
            extractions=extractions,
        )

        if args.format == "docx":
            path = doc_handler.save_docx(doc, args.output)
        elif args.format == "json":
            path = doc_handler.save_json(doc, args.output)
        elif args.format == "text":
            path = doc_handler.save_plain_text(doc, args.output)
        else:
            path = doc_handler.save_markdown(doc, args.output)

        print(f"[extract] Saved: {path}")


# ── Push Command ────────────────────────────────────────────────────────

async def cmd_push(args: argparse.Namespace) -> None:
    """Push a local file to GitHub."""
    doc_handler = DocHandler(
        github_token=args.github_token or os.getenv("GITHUB_TOKEN", ""),
        github_repo=args.repo,
    )

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[push] File not found: {args.file}")
        return

    content = file_path.read_text(encoding="utf-8")
    doc = ExtractedDocument(
        title=file_path.stem,
        content=content,
    )

    if args.as_issue:
        result = doc_handler.push_to_github_issue(doc, labels=args.labels)
        if result["success"]:
            print(f"[push] Issue created: {result['url']}")
        else:
            print(f"[push] Failed: {result.get('error')}")
    else:
        result = doc_handler.push_to_github(
            doc,
            path=args.path,
            branch=args.branch,
            format="text" if file_path.suffix == ".txt" else "markdown",
        )
        if result["success"]:
            print(f"[push] {result['action'].title()}: {result['url']}")
        else:
            print(f"[push] Failed: {result.get('error')}")


# ── Dispatch Command ────────────────────────────────────────────────────

async def cmd_dispatch(args: argparse.Namespace) -> None:
    """Dispatch a payload through a connector."""
    dispatcher = ConnectorDispatcher(audit_dir=args.audit_dir)

    config = ConnectorConfig(
        connector_id=args.connector,
        kind=args.kind or "generic_webhook",
        endpoint_url=args.endpoint,
        auth_type=args.auth_type or "none",
        auth_token=args.auth_token or "",
        auth_header_name=args.auth_header or "Authorization",
    )
    dispatcher.register(config)

    payload = json.loads(args.payload) if isinstance(args.payload, str) else args.payload
    print(f"[dispatch] Sending to {args.connector} ({args.endpoint[:60]})")

    result = dispatcher.dispatch(args.connector, payload)
    if result.success:
        print(f"[dispatch] Success: HTTP {result.status_code} in {result.elapsed_ms:.0f}ms")
        if args.verbose:
            print(f"[dispatch] Response: {result.response_body[:500]}")
    else:
        print(f"[dispatch] Failed: {result.error}")


# ── Workflow Command ────────────────────────────────────────────────────

async def cmd_workflow(args: argparse.Namespace) -> None:
    """Run a multi-step workflow from a JSON definition."""
    wf_path = Path(args.workflow_file)
    if not wf_path.exists():
        print(f"[workflow] File not found: {args.workflow_file}")
        return

    wf = json.loads(wf_path.read_text(encoding="utf-8"))
    steps = wf.get("steps", [])
    print(f"[workflow] Running '{wf.get('name', 'unnamed')}' — {len(steps)} steps")

    doc_handler = DocHandler(
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_repo=os.getenv("GITHUB_REPO", ""),
        output_dir=wf.get("output_dir", "artifacts/documents"),
    )
    dispatcher = ConnectorDispatcher()

    # Register connectors from workflow definition
    for conn_def in wf.get("connectors", []):
        config = ConnectorConfig(
            connector_id=conn_def["connector_id"],
            kind=conn_def.get("kind", "generic_webhook"),
            endpoint_url=conn_def["endpoint_url"],
            auth_type=conn_def.get("auth_type", "none"),
            auth_token=conn_def.get("auth_token", os.getenv(conn_def.get("auth_token_env", ""), "")),
            auth_header_name=conn_def.get("auth_header_name", "Authorization"),
        )
        dispatcher.register(config)

    session_id = wf.get("session_id", f"workflow-{int(time.time())}")
    tongues = wf.get("tongues", ["KO", "AV", "CA"])
    all_extractions: List[Dict[str, Any]] = []

    async with PersistentBrowserLimb(
        session_id=session_id,
        tongues=tongues,
        governance_enabled=wf.get("governance", True),
    ) as limb:
        for i, step in enumerate(steps, 1):
            action = step.get("action", "")
            print(f"\n[workflow] Step {i}/{len(steps)}: {action}")

            if action == "navigate":
                tongue = step.get("tongue", "CA")
                url = step["url"]
                result = await limb.navigate(tongue, url)
                print(f"  → {url[:60]} ({result.get('governance', {}).get('decision', 'N/A')})")

            elif action == "extract":
                tongue = step.get("tongue", "CA")
                selector = step.get("selector", "body")
                text = await limb.extract_text(tongue, selector)
                title = await limb.extract_text(tongue, "title")
                links = await limb.extract_links(tongue)
                current_url = step.get("url", "unknown")
                extraction = {
                    "url": current_url,
                    "title": title[:200],
                    "text": text[:step.get("max_chars", 5000)],
                    "links": links[:20],
                }
                all_extractions.append(extraction)
                print(f"  Extracted {len(text)} chars")

            elif action == "navigate_and_extract":
                tongue = step.get("tongue", "CA")
                url = step["url"]
                selector = step.get("selector", "body")
                nav = await limb.navigate(tongue, url)
                if not nav.get("blocked"):
                    text = await limb.extract_text(tongue, selector)
                    title = await limb.extract_text(tongue, "title")
                    links = await limb.extract_links(tongue)
                    all_extractions.append({
                        "url": url,
                        "title": title[:200],
                        "text": text[:step.get("max_chars", 5000)],
                        "links": links[:20],
                    })
                    print(f"  Extracted {len(text)} chars from {url[:60]}")
                else:
                    print(f"  BLOCKED: {url[:60]}")

            elif action == "screenshot":
                tongue = step.get("tongue", "CA")
                path = step.get("path", f"artifacts/screenshots/step_{i}.png")
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                await limb.screenshot(tongue, path)
                print(f"  Screenshot: {path}")

            elif action == "save_document":
                fmt = step.get("format", "markdown")
                title = step.get("title", "Workflow Output")
                doc = doc_handler.merge_extractions(
                    title=title,
                    extractions=all_extractions,
                    metadata={"workflow": wf.get("name"), "session_id": session_id},
                )
                if fmt == "docx":
                    path = doc_handler.save_docx(doc, step.get("path"))
                elif fmt == "json":
                    path = doc_handler.save_json(doc, step.get("path"))
                elif fmt == "text":
                    path = doc_handler.save_plain_text(doc, step.get("path"))
                else:
                    path = doc_handler.save_markdown(doc, step.get("path"))
                print(f"  Saved: {path}")

            elif action == "push_github":
                title = step.get("title", "Workflow Output")
                doc = doc_handler.merge_extractions(title=title, extractions=all_extractions)
                gh_path = step["path"]
                branch = step.get("branch", "main")
                result = doc_handler.push_to_github(doc, path=gh_path, branch=branch)
                if result["success"]:
                    print(f"  Pushed: {result['url']}")
                else:
                    print(f"  Push failed: {result.get('error')}")

            elif action == "dispatch":
                connector_id = step["connector_id"]
                payload = step.get("payload", {})
                # Inject extractions into payload if requested
                if step.get("include_extractions"):
                    payload["extractions"] = all_extractions
                result = dispatcher.dispatch(connector_id, payload)
                if result.success:
                    print(f"  Dispatched to {connector_id}: HTTP {result.status_code}")
                else:
                    print(f"  Dispatch failed: {result.error}")

            elif action == "wait":
                secs = step.get("seconds", 1)
                print(f"  Waiting {secs}s...")
                await asyncio.sleep(secs)

            else:
                print(f"  Unknown action: {action}")

    print(f"\n[workflow] Complete. {len(all_extractions)} total extractions.")


# ── Interactive Command ─────────────────────────────────────────────────

async def cmd_interactive(args: argparse.Namespace) -> None:
    """Interactive headless browser session."""
    tongues = args.tongues.split(",") if args.tongues else ["KO", "AV", "CA"]
    doc_handler = DocHandler(output_dir=args.output_dir)

    print("=" * 60)
    print("  SCBE AetherBrowse — Interactive Headless Browser")
    print("=" * 60)
    print(f"  Session: {args.session}")
    print(f"  Tongues: {', '.join(tongues)}")
    print(f"  Governance: {'ON' if not args.no_governance else 'OFF'}")
    print()
    print("Commands:")
    print("  nav <tongue> <url>      — Navigate a finger")
    print("  text <tongue> [sel]     — Extract text (default: body)")
    print("  links <tongue>          — Extract links")
    print("  shot <tongue> <path>    — Screenshot")
    print("  save <format> [path]    — Save extractions (md/docx/json/txt)")
    print("  status                  — Limb status")
    print("  quit                    — Exit")
    print()

    all_extractions: List[Dict[str, Any]] = []

    async with PersistentBrowserLimb(
        session_id=args.session,
        tongues=tongues,
        governance_enabled=not args.no_governance,
    ) as limb:
        print("[ready] Browser fingers active. Type a command.\n")

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("aetherbrowse> ")
                )
            except (EOFError, KeyboardInterrupt):
                break

            parts = line.strip().split(None, 2)
            if not parts:
                continue

            cmd = parts[0].lower()

            if cmd in ("quit", "exit", "q"):
                break

            elif cmd == "nav" and len(parts) >= 3:
                tongue, url = parts[1].upper(), parts[2]
                result = await limb.navigate(tongue, url)
                gov = result.get("governance", {})
                if result.get("blocked"):
                    print(f"  BLOCKED: {gov.get('explanation', 'governance denied')}")
                else:
                    print(f"  {gov.get('decision', 'OK')} — {result.get('title', '')[:60]}")

            elif cmd == "text":
                tongue = parts[1].upper() if len(parts) > 1 else "CA"
                sel = parts[2] if len(parts) > 2 else "body"
                text = await limb.extract_text(tongue, sel)
                print(text[:2000])
                all_extractions.append({
                    "url": "interactive",
                    "title": f"extraction-{len(all_extractions)+1}",
                    "text": text[:5000],
                    "links": [],
                })

            elif cmd == "links":
                tongue = parts[1].upper() if len(parts) > 1 else "CA"
                links = await limb.extract_links(tongue)
                for link in links[:20]:
                    print(f"  {link}")
                print(f"  ({len(links)} total)")

            elif cmd == "shot" and len(parts) >= 3:
                tongue, path = parts[1].upper(), parts[2]
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                await limb.screenshot(tongue, path)
                print(f"  Saved: {path}")

            elif cmd == "save":
                fmt = parts[1] if len(parts) > 1 else "md"
                path = parts[2] if len(parts) > 2 else None
                if not all_extractions:
                    print("  No extractions to save")
                    continue
                doc = doc_handler.merge_extractions(
                    title=f"Interactive Session {args.session}",
                    extractions=all_extractions,
                )
                if fmt == "docx":
                    p = doc_handler.save_docx(doc, path)
                elif fmt == "json":
                    p = doc_handler.save_json(doc, path)
                elif fmt in ("txt", "text"):
                    p = doc_handler.save_plain_text(doc, path)
                else:
                    p = doc_handler.save_markdown(doc, path)
                print(f"  Saved: {p}")

            elif cmd == "status":
                s = limb.status()
                print(json.dumps(s, indent=2))

            else:
                print(f"  Unknown command: {cmd}")

    print("\n[done] Session closed. Browser data persisted to disk.")


# ── CLI Parser ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="SCBE AetherBrowse — Headless Browser Productivity CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    sub = p.add_subparsers(dest="command", required=True)

    # ── research ──
    r = sub.add_parser("research", help="Research a topic with parallel browsers")
    r.add_argument("--query", required=True, help="Search query")
    r.add_argument("--max-urls", type=int, default=5, help="Max URLs to extract")
    r.add_argument("--max-chars", type=int, default=5000, help="Max chars per page")
    r.add_argument("--selector", default="body", help="CSS selector for extraction")
    r.add_argument("--title", default=None, help="Document title")
    r.add_argument("--format", choices=["markdown", "docx", "json", "text"], default="markdown")
    r.add_argument("--output", default=None, help="Output file path")
    r.add_argument("--output-dir", default="artifacts/documents")
    r.add_argument("--session", default=None, help="Session ID")
    r.add_argument("--tongues", default="KO,AV,CA", help="Comma-separated tongues")
    r.add_argument("--no-governance", action="store_true")
    r.add_argument("--github-repo", default=None)
    r.add_argument("--github-path", default=None)
    r.add_argument("--github-branch", default="main")
    r.add_argument("--github-token", default=None)

    # ── extract ──
    e = sub.add_parser("extract", help="Extract content from specific URLs")
    e.add_argument("--urls", nargs="+", required=True, help="URLs to extract")
    e.add_argument("--max-chars", type=int, default=5000)
    e.add_argument("--selector", default="body")
    e.add_argument("--title", default=None)
    e.add_argument("--format", choices=["markdown", "docx", "json", "text"], default="markdown")
    e.add_argument("--output", default=None)
    e.add_argument("--output-dir", default="artifacts/documents")
    e.add_argument("--session", default=None)
    e.add_argument("--no-governance", action="store_true")
    e.add_argument("--github-token", default=None)
    e.add_argument("--github-repo", default=None)

    # ── push ──
    pu = sub.add_parser("push", help="Push a file to GitHub")
    pu.add_argument("--file", required=True, help="Local file to push")
    pu.add_argument("--repo", required=True, help="GitHub repo (owner/repo)")
    pu.add_argument("--path", required=True, help="File path in repo")
    pu.add_argument("--branch", default="main")
    pu.add_argument("--github-token", default=None)
    pu.add_argument("--as-issue", action="store_true", help="Create as GitHub issue instead")
    pu.add_argument("--labels", nargs="*", default=["aetherbrowse"])

    # ── dispatch ──
    d = sub.add_parser("dispatch", help="Dispatch payload to a connector")
    d.add_argument("--connector", required=True, help="Connector ID")
    d.add_argument("--endpoint", required=True, help="Connector endpoint URL")
    d.add_argument("--payload", required=True, help="JSON payload string")
    d.add_argument("--kind", default="generic_webhook")
    d.add_argument("--auth-type", default="none")
    d.add_argument("--auth-token", default="")
    d.add_argument("--auth-header", default="Authorization")
    d.add_argument("--audit-dir", default="artifacts/connector_dispatches")

    # ── workflow ──
    w = sub.add_parser("workflow", help="Run a multi-step workflow from JSON")
    w.add_argument("--workflow-file", required=True, help="Workflow JSON file")

    # ── interactive ──
    i = sub.add_parser("interactive", help="Interactive browser session")
    i.add_argument("--session", default=f"interactive-{int(time.time())}")
    i.add_argument("--tongues", default="KO,AV,CA")
    i.add_argument("--output-dir", default="artifacts/documents")
    i.add_argument("--no-governance", action="store_true")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    cmd_map = {
        "research": cmd_research,
        "extract": cmd_extract,
        "push": cmd_push,
        "dispatch": cmd_dispatch,
        "workflow": cmd_workflow,
        "interactive": cmd_interactive,
    }

    handler = cmd_map.get(args.command)
    if handler is None:
        parser.print_help()
        return

    asyncio.run(handler(args))


if __name__ == "__main__":
    main()
