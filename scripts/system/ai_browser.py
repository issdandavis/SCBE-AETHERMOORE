#!/usr/bin/env python3
"""System entrypoint for the SCBE governed browser worker."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any, Dict, List, Sequence

from src.browser.headless import HeadlessBrowser
from src.browser.headless import scan_content

logger = logging.getLogger("ai-browser")


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for the system AI browser tool."""
    parser = argparse.ArgumentParser(description="SCBE AI browser worker")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Max retries for transient failures")
    parser.add_argument("--retry-backoff", type=float, default=0.5, help="Retry backoff base in seconds")
    parser.add_argument("--disable-playwright", action="store_true", help="Disable Playwright fallback tier")

    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search DuckDuckGo")
    search.add_argument("query", help="Search query")
    search.add_argument("-n", "--num-results", type=int, default=10)

    fetch = sub.add_parser("fetch", help="Fetch URL")
    fetch.add_argument("url", help="URL to fetch")
    fetch.add_argument("--playwright", action="store_true", help="Force Playwright for JS-heavy sites")

    research = sub.add_parser("research", help="Search and fetch top docs")
    research.add_argument("query", help="Research query")
    research.add_argument("-d", "--depth", type=int, default=3)
    research.add_argument("--store", action="store_true", help="Write results to training intake JSONL")
    research.add_argument("--output-dir", default=None, help="Custom output directory for --store")

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(list(argv) if argv is not None else None)


async def run_cli(argv: Sequence[str] | None = None) -> Dict[str, Any]:
    """Run one command and return structured payload."""
    args = parse_args(argv)

    async with HeadlessBrowser(
        timeout=args.timeout,
        enable_playwright=not args.disable_playwright,
        max_retries=args.retries,
        retry_backoff=args.retry_backoff,
    ) as browser:
        if args.command == "search":
            results = await browser.search(args.query, num_results=args.num_results)
            query_scan = scan_content(args.query)
            evidence = [
                (
                    f"evidence://search/{args.query}?"
                    f"attempts=1&governance_verdict={query_scan.verdict}&governance_score={query_scan.risk_score:.4f}"
                )
            ]
            return {
                "command": "search",
                "query": args.query,
                "stats": browser.stats,
                "governance_verdict": query_scan.verdict,
                "governance_score": query_scan.risk_score,
                "results": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": r.snippet,
                        "governance_score": r.governance_score,
                        "governance_verdict": r.governance_verdict,
                        "attempts": r.attempts,
                    }
                    for r in results
                ],
                "evidence": evidence,
            }

        if args.command == "fetch":
            page = await browser.fetch(args.url, use_playwright=args.playwright)
            evidence = [
                (
                    "evidence://fetch/"
                    f"{args.url}?governance_verdict={page.scan.verdict if page.scan else 'UNSCANNED'}"
                    f"&governance_score={page.scan.risk_score if page.scan else 0.0:.4f}"
                    f"&attempts={page.attempts}"
                )
            ]
            return {
                "command": "fetch",
                "governance_verdict": page.scan.verdict if page.scan else "UNSCANNED",
                "governance_score": page.scan.risk_score if page.scan else 0.0,
                "stats": browser.stats,
                "result": page.to_dict(),
                "evidence": evidence,
            }

        if args.command == "research":
            if args.store:
                report = await browser.research_and_store(
                    args.query,
                    depth=args.depth,
                    output_dir=args.output_dir,
                )
                marker_pages = [
                    (
                        f"evidence://research/{args.query}/page/{idx}?"
                        f"governance_verdict={r.scan.verdict if r.scan else 'UNSCANNED'}&"
                        f"governance_score={r.scan.risk_score if r.scan else 0.0:.4f}&"
                        f"attempts={r.attempts}"
                    )
                    for idx, r in enumerate(report.results)
                ]
                return {
                    "command": "research-store",
                    "query": args.query,
                    "stats": browser.stats,
                    "report": report.to_dict(),
                    "evidence": [
                        f"evidence://research/{args.query}?depth={args.depth}&action=research-store",
                        *marker_pages,
                    ],
                }

            report = await browser.research(args.query, depth=args.depth)
            marker_pages = [
                (
                    f"evidence://research/{args.query}/page/{idx}?"
                    f"governance_verdict={r.scan.verdict if r.scan else 'UNSCANNED'}&"
                    f"governance_score={r.scan.risk_score if r.scan else 0.0:.4f}&"
                    f"attempts={r.attempts}"
                )
                for idx, r in enumerate(report.results)
            ]
            return {
                "command": "research",
                "query": args.query,
                "stats": browser.stats,
                "report": report.to_dict(),
                "evidence": [
                    f"evidence://research/{args.query}?depth={args.depth}&action=research",
                    *marker_pages,
                ],
            }

    raise RuntimeError(f"unsupported command: {args.command}")


def _format_for_stdout(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def main(argv: Sequence[str] | None = None) -> int:
    payload = asyncio.run(run_cli(argv))
    print(_format_for_stdout(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
