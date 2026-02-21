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

from .spine import HydraSpine
from .head import HydraHead, create_claude_head
from .limbs import BrowserLimb, TerminalLimb, APILimb, MultiTabBrowserLimb
from .ledger import Ledger
from .librarian import Librarian
from .research import ResearchOrchestrator, ResearchConfig


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
  hydra switchboard stats
  hydra switchboard enqueue pilot '{"action":"navigate","target":"https://example.com"}'

Research Commands:
  hydra research "quantum computing 2025"          Run multi-agent research
  hydra research "AI safety" --mode httpx           Lightweight HTTP mode (default)
  hydra research "topic" --mode local               Full Playwright browser
  hydra research "topic" --providers claude,gpt     Choose LLM providers
  hydra research "topic" --max-subtasks 3           Limit parallel subtasks

Workflow Commands:
  hydra workflow list            List saved workflow templates
  hydra workflow run <name>      Execute a saved workflow
  hydra workflow show <name>     Show workflow definition

Memory Commands:
  hydra remember <key> <value>   Store a fact
  hydra recall <key>             Retrieve a fact
  hydra search <keywords>        Search memory
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="interactive",
        help="Command to run (interactive, status, stats, execute, research, workflow, remember, recall, search)"
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

    # Research-specific flags
    parser.add_argument(
        "--mode",
        default="httpx",
        choices=["httpx", "local", "cloud"],
        help="Browse mode: httpx (lightweight), local (Playwright), cloud (Docker workers)"
    )

    parser.add_argument(
        "--providers",
        default="claude,gpt,gemini",
        help="Comma-separated LLM providers (e.g. claude,gpt,gemini)"
    )

    parser.add_argument(
        "--max-subtasks",
        type=int,
        default=5,
        help="Max parallel subtasks for research (1-10)"
    )

    parser.add_argument(
        "--discovery",
        type=int,
        default=3,
        help="URLs to discover per subtask (1-10)"
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

    elif args.command == "research":
        if not args.args:
            print("Error: Provide a research query")
            print('  Example: python -m hydra research "quantum computing 2025"')
            sys.exit(1)
        query = " ".join(args.args)
        await handle_research(query, args)

    elif args.command == "switchboard":
        await handle_switchboard(args.args, spine, args.json)

    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


async def handle_research(query: str, args):
    """Run multi-agent research with live terminal progress."""
    as_json = args.json
    provider_list = [p.strip() for p in args.providers.split(",") if p.strip()]

    config = ResearchConfig(
        mode=args.mode,
        provider_order=provider_list,
        max_subtasks=max(1, min(10, args.max_subtasks)),
        discovery_per_subtask=max(1, min(10, args.discovery)),
    )

    if not as_json:
        print()
        print("=" * 60)
        print("  HYDRA RESEARCH")
        print("=" * 60)
        print(f"  Query:     {query}")
        print(f"  Mode:      {config.mode}")
        print(f"  Providers: {', '.join(config.provider_order)}")
        print(f"  Subtasks:  up to {config.max_subtasks}")
        print("=" * 60)
        print()

    # Build orchestrator
    if not as_json:
        print("[1/5] Building LLM providers...", end="", flush=True)

    orchestrator = ResearchOrchestrator(config=config)

    if not as_json:
        active = sorted(orchestrator.providers.keys())
        print(f" {len(active)} active: {', '.join(active)}")

    # Run research (the orchestrator handles decompose/discover/browse/synthesize)
    if not as_json:
        print("[2/5] Decomposing query into subtasks...")
        print("[3/5] Discovering URLs via Google News RSS...")
        print("[4/5] Browsing & extracting content...")
        print("[5/5] Synthesizing with all providers in parallel...")
        print()

    try:
        report = await orchestrator.research(query)
    finally:
        await orchestrator.close()

    # Output
    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
        return

    # Human-friendly terminal output — the "tiny window"
    meta = report.metadata
    print("-" * 60)
    print("  RESULTS")
    print("-" * 60)
    print()

    # Subtasks
    print(f"  Subtasks ({len(report.subtasks)}):")
    for st in report.subtasks:
        url_count = len(st.urls)
        print(f"    [{st.subtask_id}] {st.title} ({url_count} URLs)")
    print()

    # Sources
    ok_sources = [s for s in report.sources if s.status == "ok"]
    err_sources = [s for s in report.sources if s.status != "ok"]
    print(f"  Sources: {len(ok_sources)} fetched, {len(err_sources)} failed")
    for s in ok_sources[:8]:
        url_short = s.url[:60] + "..." if len(s.url) > 60 else s.url
        print(f"    OK  {url_short} ({s.chars} chars)")
    for s in err_sources[:4]:
        url_short = s.url[:60] + "..." if len(s.url) > 60 else s.url
        print(f"    ERR {url_short}: {s.error}")
    print()

    # Synthesis
    print("  Synthesis:")
    print("  " + "-" * 56)
    # Wrap synthesis text to ~76 chars for terminal
    synth_text = report.synthesis.strip()
    for line in synth_text.splitlines():
        while len(line) > 76:
            # Find a space near the 76-char mark
            split_at = line.rfind(" ", 0, 76)
            if split_at <= 0:
                split_at = 76
            print(f"  {line[:split_at]}")
            line = line[split_at:].lstrip()
        print(f"  {line}")
    print("  " + "-" * 56)
    print()

    # Provider summaries (condensed)
    provider_summaries = meta.get("provider_summaries", {})
    if len(provider_summaries) > 1:
        print(f"  Provider perspectives ({len(provider_summaries)}):")
        for name, summary in provider_summaries.items():
            first_line = summary.strip().splitlines()[0][:80] if summary.strip() else "(empty)"
            marker = "*" if name == meta.get("synthesis_provider") else " "
            print(f"   {marker}{name}: {first_line}")
        print()

    # Timing
    elapsed_ms = meta.get("elapsed_ms", 0)
    if elapsed_ms > 0:
        elapsed_sec = elapsed_ms / 1000.0
        print(f"  Completed in {elapsed_sec:.1f}s")
    print("=" * 60)
    print()


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


async def handle_switchboard(args: list, spine: HydraSpine, as_json: bool):
    """Handle switchboard commands."""
    if not args:
        print("Switchboard commands: stats, enqueue, post, messages")
        return

    subcmd = args[0]

    if subcmd == "stats":
        result = await spine.execute({"action": "switchboard_stats"})
        print(json.dumps(result, indent=2))
        return

    if subcmd == "enqueue":
        if len(args) < 3:
            print("Usage: hydra switchboard enqueue <role> '<task_json>'")
            return
        role = args[1]
        task = json.loads(args[2])
        result = await spine.execute(
            {
                "action": "switchboard_enqueue",
                "role": role,
                "task": task,
                "dedupe_key": task.get("dedupe_key"),
            }
        )
        print(json.dumps(result, indent=2))
        return

    if subcmd == "post":
        if len(args) < 3:
            print("Usage: hydra switchboard post <channel> <message>")
            return
        channel = args[1]
        message = {"text": " ".join(args[2:])}
        result = await spine.execute(
            {
                "action": "switchboard_post_message",
                "channel": channel,
                "message": message,
            }
        )
        print(json.dumps(result, indent=2))
        return

    if subcmd == "messages":
        if len(args) < 2:
            print("Usage: hydra switchboard messages <channel> [since_id]")
            return
        channel = args[1]
        since_id = int(args[2]) if len(args) > 2 else 0
        result = await spine.execute(
            {
                "action": "switchboard_get_messages",
                "channel": channel,
                "since_id": since_id,
            }
        )
        print(json.dumps(result, indent=2))
        return

    print("Usage: hydra switchboard [stats|enqueue|post|messages] ...")


def run():
    """Entry point for package."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
