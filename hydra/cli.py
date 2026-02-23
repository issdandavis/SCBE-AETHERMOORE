#!/usr/bin/env python
"""
HYDRA CLI - Terminal Interface
==============================

Usage:
    python -m hydra                    # Start interactive mode
    python -m hydra status             # Show system status
    python -m hydra stats              # Show statistics
    echo '{"action":"navigate","target":"https://..."}' | python -m hydra

One-Click Workflows:
    python -m hydra workflow list                    # List templates
    python -m hydra workflow run login_and_scrape   # Run a workflow
"""

import asyncio
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from .spine import HydraSpine
from .head import HydraHead, create_claude_head
from .limbs import BrowserLimb, TerminalLimb, APILimb, MultiTabBrowserLimb
from .ledger import Ledger
from .librarian import Librarian
from .arxiv_retrieval import AI2AIRetrievalService, ArxivClient


BANNER = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██╗  ██╗██╗   ██╗██████╗ ██████╗  █████╗                                   ║
║   ██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██╔══██╗                                  ║
║   ███████║ ╚████╔╝ ██║  ██║██████╔╝███████║                                  ║
║   ██╔══██║  ╚██╔╝  ██║  ██║██╔══██╗██╔══██║                                  ║
║   ██║  ██║   ██║   ██████╔╝██║  ██║██║  ██║                                  ║
║   ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝                                  ║
║                                                                               ║
║                     SCBE-Governed AI Coordination                             ║
║                     "Many Heads, One Governed Body"                           ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="HYDRA - SCBE-Governed AI Coordination System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hydra                          Start interactive mode
  hydra status                   Show system status
  hydra stats                    Show statistics
  hydra execute '{"action":"navigate","target":"https://example.com"}'

Workflow Commands:
  hydra workflow list            List saved workflow templates
  hydra workflow run <name>      Execute a saved workflow
  hydra workflow show <name>     Show workflow definition

Memory Commands:
  hydra remember <key> <value>   Store a fact
  hydra recall <key>             Retrieve a fact
  hydra search <keywords>        Search memory

arXiv Commands:
  hydra arxiv search <query> [--cat cs.AI] [--max 5]
  hydra arxiv get <id1,id2,...>
  hydra arxiv outline <query> [--cat cs.AI] [--max 5]
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="interactive",
        help="Command to run (interactive, status, stats, execute, workflow, remember, recall, search, arxiv)"
    )

    parser.add_argument(
        "args",
        nargs="*",
        help="Command arguments"
    )

    parser.add_argument(
        "--scbe-url",
        default="http://127.0.0.1:8080",
        help="SCBE API URL"
    )

    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Don't show banner"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Initialize system
    ledger = Ledger()
    librarian = Librarian(ledger)
    spine = HydraSpine(ledger=ledger, scbe_url=args.scbe_url)

    # Route command
    if args.command == "interactive":
        if not args.no_banner:
            print(BANNER)
        await spine.start(terminal_mode=True)

    elif args.command == "status":
        await show_status(spine, librarian, args.json)

    elif args.command == "stats":
        await show_stats(librarian, args.json)

    elif args.command == "execute":
        if not args.args:
            print("Error: Provide JSON command")
            sys.exit(1)
        cmd = json.loads(args.args[0])
        result = await spine.execute(cmd)
        print(json.dumps(result, indent=2))

    elif args.command == "workflow":
        await handle_workflow(args.args, spine, librarian, args.json)

    elif args.command == "remember":
        if len(args.args) < 2:
            print("Error: Provide key and value")
            sys.exit(1)
        librarian.remember(args.args[0], args.args[1])
        print(f"Remembered: {args.args[0]}")

    elif args.command == "recall":
        if not args.args:
            print("Error: Provide key")
            sys.exit(1)
        value = librarian.recall(args.args[0])
        if args.json:
            print(json.dumps({"key": args.args[0], "value": value}))
        else:
            print(f"{args.args[0]}: {value}")

    elif args.command == "search":
        if not args.args:
            print("Error: Provide search keywords")
            sys.exit(1)
        from .librarian import MemoryQuery
        query = MemoryQuery(keywords=args.args)
        results = librarian.search(query)
        if args.json:
            print(json.dumps([{
                "key": r.key,
                "value": r.value,
                "relevance": r.relevance_score
            } for r in results], indent=2))
        else:
            for r in results:
                print(f"[{r.relevance_score:.2f}] {r.key}: {r.value}")

    elif args.command == "arxiv":
        handle_arxiv(args.args, librarian, args.json)

    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


async def show_status(spine: HydraSpine, librarian: Librarian, as_json: bool):
    """Show system status."""
    stats = librarian.get_stats()

    status = {
        "session_id": spine.ledger.session_id,
        "active_heads": len(spine.heads),
        "active_limbs": len(spine.limbs),
        "active_workflows": len(spine.workflows),
        "total_entries": stats.get("total_entries", 0),
        "memory_facts": stats.get("memory_facts", 0),
        "scbe_url": spine.scbe_url,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if as_json:
        print(json.dumps(status, indent=2))
    else:
        print("\n" + "=" * 50)
        print("HYDRA SYSTEM STATUS")
        print("=" * 50)
        for k, v in status.items():
            print(f"  {k}: {v}")
        print("=" * 50 + "\n")


async def show_stats(librarian: Librarian, as_json: bool):
    """Show detailed statistics."""
    stats = librarian.get_stats()

    if as_json:
        print(json.dumps(stats, indent=2))
    else:
        print("\n" + "=" * 50)
        print("HYDRA STATISTICS")
        print("=" * 50)
        print(f"  Session:       {stats.get('session_id', 'unknown')}")
        print(f"  Total Entries: {stats.get('total_entries', 0)}")
        print(f"  Memory Facts:  {stats.get('memory_facts', 0)}")
        print(f"  Active Heads:  {stats.get('active_heads', 0)}")
        print(f"  Active Limbs:  {stats.get('active_limbs', 0)}")
        print(f"  Cache Hits:    {stats.get('cache_hits', 0)}")
        print(f"  Cache Misses:  {stats.get('cache_misses', 0)}")
        print(f"  Hit Rate:      {stats.get('cache_hit_rate', 0):.2%}")
        print("\n  By Entry Type:")
        for t, c in stats.get('by_type', {}).items():
            print(f"    {t}: {c}")
        print("\n  By Decision:")
        for d, c in stats.get('by_decision', {}).items():
            print(f"    {d}: {c}")
        print("=" * 50 + "\n")


async def handle_workflow(args: list, spine: HydraSpine, librarian: Librarian, as_json: bool):
    """Handle workflow commands."""
    if not args:
        print("Workflow commands: list, run, show, save")
        return

    subcmd = args[0]

    if subcmd == "list":
        templates = librarian.list_workflow_templates()
        if as_json:
            print(json.dumps(templates))
        else:
            print("\nSaved Workflows:")
            for t in templates:
                print(f"  - {t}")
            print()

    elif subcmd == "run" and len(args) > 1:
        name = args[1]
        template = librarian.get_workflow_template(name)
        if not template:
            print(f"Workflow not found: {name}")
            return

        workflow_id = spine.define_workflow(
            template.get("name"),
            template.get("phases", [])
        )
        result = await spine.execute({
            "action": "workflow",
            "workflow_id": workflow_id
        })
        print(json.dumps(result, indent=2))

    elif subcmd == "show" and len(args) > 1:
        name = args[1]
        template = librarian.get_workflow_template(name)
        if template:
            print(json.dumps(template, indent=2))
        else:
            print(f"Workflow not found: {name}")

    elif subcmd == "save" and len(args) > 2:
        name = args[1]
        definition = json.loads(args[2])
        librarian.save_workflow_template(
            name,
            definition.get("phases", []),
            definition.get("description", "")
        )
        print(f"Saved workflow: {name}")

    else:
        print("Usage: hydra workflow [list|run|show|save] [name] [definition]")


def _parse_arxiv_options(tokens: List[str]) -> Tuple[str, Optional[str], int, bool, bool]:
    query_parts: List[str] = []
    category: Optional[str] = None
    max_results = 5
    remember = True
    raw_query = False

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "--max" and idx + 1 < len(tokens):
            max_results = max(1, int(tokens[idx + 1]))
            idx += 2
            continue
        if tok == "--cat" and idx + 1 < len(tokens):
            category = tokens[idx + 1]
            idx += 2
            continue
        if tok == "--no-memory":
            remember = False
            idx += 1
            continue
        if tok == "--raw-query":
            raw_query = True
            idx += 1
            continue

        query_parts.append(tok)
        idx += 1

    return " ".join(query_parts).strip(), category, max_results, remember, raw_query


def handle_arxiv(args: List[str], librarian: Librarian, as_json: bool) -> None:
    """Handle HYDRA arXiv retrieval commands."""
    if not args or args[0] in {"help", "-h", "--help"}:
        print("Usage:")
        print("  hydra arxiv search <query> [--cat cs.AI] [--max 5] [--no-memory] [--raw-query]")
        print("  hydra arxiv get <id1,id2,...>")
        print("  hydra arxiv outline <query> [--cat cs.AI] [--max 5]")
        return

    subcmd = args[0]
    service = AI2AIRetrievalService(client=ArxivClient(), librarian=librarian)

    if subcmd == "search":
        query, category, max_results, remember, raw_query = _parse_arxiv_options(args[1:])
        if not query:
            print("Error: Provide a search query")
            return

        packet = service.retrieve_arxiv_packet(
            requester="hydra-cli",
            query=query,
            category=category,
            max_results=max_results,
            remember=remember,
            raw_query=raw_query,
        )
        if as_json:
            print(json.dumps(packet, indent=2))
            return

        print(f"\n[arxiv] packet={packet['packet_id']} returned={packet['returned_results']} total={packet['total_results']}")
        for idx, paper in enumerate(packet.get("papers", []), start=1):
            print(f"{idx}. {paper['arxiv_id']} :: {paper['title']}")
            if paper.get("pdf_url"):
                print(f"   pdf: {paper['pdf_url']}")
        print()
        return

    if subcmd == "get":
        raw_ids = " ".join(args[1:]).strip()
        if not raw_ids:
            print("Error: Provide at least one arXiv id")
            return
        ids: List[str] = []
        for part in raw_ids.split(","):
            clean = part.strip()
            if clean:
                ids.append(clean)
        papers = service.client.fetch_by_ids(ids)
        payload = [p.to_dict() for p in papers]
        if as_json:
            print(json.dumps(payload, indent=2))
            return

        print()
        for idx, paper in enumerate(payload, start=1):
            print(f"{idx}. {paper['arxiv_id']} :: {paper['title']}")
            print(f"   authors: {', '.join(paper['authors'][:5])}")
            print(f"   abs: {paper['abs_url']}")
        print()
        return

    if subcmd == "outline":
        query, category, max_results, remember, raw_query = _parse_arxiv_options(args[1:])
        if not query:
            print("Error: Provide a query for outline")
            return
        packet = service.retrieve_arxiv_packet(
            requester="hydra-cli",
            query=query,
            category=category,
            max_results=max_results,
            remember=remember,
            raw_query=raw_query,
        )
        print(service.build_related_work_outline(packet))
        return

    print(f"Unknown arxiv subcommand: {subcmd}")


def run():
    """Entry point for package."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
