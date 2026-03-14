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
from difflib import get_close_matches
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

from .spine import HydraSpine
from .head import HydraHead, create_claude_head
from .limbs import BrowserLimb, TerminalLimb, APILimb, MultiTabBrowserLimb
from .ledger import Ledger
from .librarian import Librarian
from .arxiv_retrieval import AI2AIRetrievalService, ArxivClient
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

ASCII_BANNER = """
===========================================================================
 HYDRA :: SCBE-Governed AI Coordination
 "Many Heads, One Governed Body"
===========================================================================
"""

CLI_VERSION = "1.3.0"

SUPPORTED_COMMANDS = {
    "interactive",
    "status",
    "stats",
    "execute",
    "workflow",
    "remember",
    "recall",
    "search",
    "arxiv",
    "research",
    "switchboard",
    "canvas",
    "branch",
    "lattice25d",
}

COMMAND_ALIASES = {
    "i": "interactive",
    "st": "status",
    "statistics": "stats",
    "exec": "execute",
    "wf": "workflow",
    "sb": "switchboard",
    "cv": "canvas",
    "paint": "canvas",
    "br": "branch",
    "l25": "lattice25d",
}


def _normalize_command(command: str) -> str:
    key = command.strip().lower()
    return COMMAND_ALIASES.get(key, key)


def _resolve_command_and_args(
    command: Optional[str],
    raw_args: List[str],
    stdin_payload: str,
) -> Tuple[str, List[str], str]:
    if command:
        normalized = _normalize_command(command)
        args = list(raw_args)
        if normalized == "execute" and not args and stdin_payload:
            args = [stdin_payload]
        return normalized, args, command

    if stdin_payload:
        return "execute", [stdin_payload, *raw_args], "execute"

    return "interactive", list(raw_args), "interactive"


def _read_stdin_payload() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read().strip()
    except Exception:
        return ""


def _print_banner() -> None:
    encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
    if "utf" in encoding:
        print(BANNER)
        return

    try:
        BANNER.encode(sys.stdout.encoding or "utf-8")
    except Exception:
        print(ASCII_BANNER)
        return

    print(BANNER)


def _load_json_object(raw: str, context: str) -> Optional[dict]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON for {context}: {exc}")
        return None

    if not isinstance(payload, dict):
        print(f"Error: {context} must be a JSON object")
        return None

    return payload


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

arXiv Commands:
  hydra arxiv search <query> [--cat cs.AI] [--max 5]
  hydra arxiv get <id1,id2,...>
  hydra arxiv outline <query> [--cat cs.AI] [--max 5]

Canvas Commands (multi-step orchestrated workflows):
  hydra canvas list                                List available recipes
  hydra canvas show article                        Show recipe steps & colors
  hydra canvas run article --topic "AI safety"     Run full article pipeline
  hydra canvas run research --topic "chladni modes" Deep multi-source research
  hydra canvas paint "signed Chladni modes"        Freeform article canvas
  hydra canvas run training --topic "governance"   Generate SFT training data
  hydra canvas run content --topic "SCBE update"   Multi-platform content

Lattice Commands (2.5D hyperbolic lattice ops):
  hydra lattice25d sample --count 12
  hydra lattice25d notes --glob "docs/**/*.md" --max-notes 40
  hydra lattice25d notes --no-glob --note "inline note" --json

Branch Commands (ChoiceScript branching + council):
  hydra branch list                                 List branch templates and strategies
  hydra branch show research_pipeline --topic "swarm"
  hydra branch run research_pipeline --topic "swarm navigation" --strategy all_paths
  hydra branch run training_funnel --strategy scored --providers claude,gpt,gemini
  hydra branch run content_publisher --export-n8n workflows/n8n/branch.workflow.json
        """
    )
    if hasattr(parser, "suggest_on_error"):
        parser.suggest_on_error = True

    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        help=(
            "Command to run (interactive, status, stats, execute, research, workflow, "
            "remember, recall, search, arxiv, switchboard, canvas, branch, lattice25d). If omitted and stdin has "
            "JSON, HYDRA runs execute."
        ),
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
    parser.add_argument(
        "--version",
        action="version",
        version=f"HYDRA CLI {CLI_VERSION}",
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

    args, passthrough_args = parser.parse_known_args()
    if passthrough_args:
        args.args.extend(passthrough_args)
    stdin_payload = _read_stdin_payload()
    command, cmd_args, raw_command = _resolve_command_and_args(args.command, args.args, stdin_payload)

    if command not in SUPPORTED_COMMANDS:
        print(f"Unknown command: {raw_command}")
        suggestions = get_close_matches(command, sorted(SUPPORTED_COMMANDS), n=3)
        if suggestions:
            print(f"Did you mean: {', '.join(suggestions)}?")
        parser.print_help()
        sys.exit(1)

    if command == "lattice25d":
        try:
            handle_lattice25d(cmd_args, args)
        except ImportError as exc:
            print(f"Error: lattice25d module not available: {exc}")
            print("Ensure hydra/lattice25d_ops.py and hydra/octree_sphere_grid.py exist.")
            sys.exit(1)
        return

    # Initialize system
    ledger = Ledger()
    librarian = Librarian(ledger)
    spine = HydraSpine(ledger=ledger, scbe_url=args.scbe_url)

    # Route command
    if command == "interactive":
        if not args.no_banner and sys.stdout.isatty():
            _print_banner()
        await spine.start(terminal_mode=True)

    elif command == "status":
        await show_status(spine, librarian, args.json)

    elif command == "stats":
        await show_stats(librarian, args.json)

    elif command == "execute":
        if not cmd_args:
            print("Error: Provide JSON command")
            sys.exit(1)
        cmd = _load_json_object(cmd_args[0], "execute command")
        if cmd is None:
            sys.exit(1)
        result = await spine.execute(cmd)
        print(json.dumps(result, indent=2))

    elif command == "workflow":
        await handle_workflow(cmd_args, spine, librarian, args.json)

    elif command == "remember":
        if len(cmd_args) < 2:
            print("Error: Provide key and value")
            sys.exit(1)
        librarian.remember(cmd_args[0], cmd_args[1])
        print(f"Remembered: {cmd_args[0]}")

    elif command == "recall":
        if not cmd_args:
            print("Error: Provide key")
            sys.exit(1)
        value = librarian.recall(cmd_args[0])
        if args.json:
            print(json.dumps({"key": cmd_args[0], "value": value}))
        else:
            print(f"{cmd_args[0]}: {value}")

    elif command == "search":
        if not cmd_args:
            print("Error: Provide search keywords")
            sys.exit(1)
        from .librarian import MemoryQuery
        query = MemoryQuery(keywords=cmd_args)
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

    elif command == "arxiv":
        handle_arxiv(cmd_args, librarian, args.json)
    elif command == "research":
        if not cmd_args:
            print("Error: Provide a research query")
            print('  Example: python -m hydra research "quantum computing 2025"')
            sys.exit(1)
        query = " ".join(cmd_args)
        await handle_research(query, args)

    elif command == "canvas":
        try:
            handle_canvas(cmd_args, args)
        except ImportError as exc:
            print(f"Error: Canvas module not available: {exc}")
            print("Ensure hydra/canvas.py exists.")
            sys.exit(1)

    elif command == "branch":
        try:
            handle_branch(cmd_args, args)
        except ImportError as exc:
            print(f"Error: Branch module not available: {exc}")
            print("Ensure hydra/branch_orchestrator.py and workflows/n8n/choicescript_branching_engine.py exist.")
            sys.exit(1)

    elif command == "switchboard":
        await handle_switchboard(cmd_args, spine, args.json)


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
        definition = _load_json_object(args[2], "workflow definition")
        if definition is None:
            return
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
        task = _load_json_object(args[2], "switchboard task")
        if task is None:
            return
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
        try:
            since_id = int(args[2]) if len(args) > 2 else 0
        except ValueError:
            print("Error: since_id must be an integer")
            return
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


def _parse_branch_options(tokens: List[str], default_providers: str) -> Optional[Dict[str, Any]]:
    options: Dict[str, Any] = {
        "topic": "",
        "strategy": "all_paths",
        "max_paths": 20,
        "max_depth": 50,
        "context": {},
        "providers": [p.strip() for p in default_providers.split(",") if p.strip()],
        "enable_council": True,
        "export_n8n_path": None,
        "export_choicescript_path": None,
    }
    trailing_topic_parts: List[str] = []

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "--topic" and idx + 1 < len(tokens):
            options["topic"] = tokens[idx + 1]
            idx += 2
            continue
        if tok == "--strategy" and idx + 1 < len(tokens):
            options["strategy"] = tokens[idx + 1]
            idx += 2
            continue
        if tok == "--max-paths" and idx + 1 < len(tokens):
            try:
                options["max_paths"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --max-paths expects an integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--max-depth" and idx + 1 < len(tokens):
            try:
                options["max_depth"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --max-depth expects an integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--providers" and idx + 1 < len(tokens):
            options["providers"] = [p.strip() for p in tokens[idx + 1].split(",") if p.strip()]
            idx += 2
            continue
        if tok == "--context" and idx + 1 < len(tokens):
            parsed = _load_json_object(tokens[idx + 1], "branch context")
            if parsed is None:
                return None
            options["context"] = parsed
            idx += 2
            continue
        if tok == "--no-council":
            options["enable_council"] = False
            idx += 1
            continue
        if tok == "--export-n8n" and idx + 1 < len(tokens):
            options["export_n8n_path"] = tokens[idx + 1]
            idx += 2
            continue
        if tok == "--export-choicescript" and idx + 1 < len(tokens):
            options["export_choicescript_path"] = tokens[idx + 1]
            idx += 2
            continue

        trailing_topic_parts.append(tok)
        idx += 1

    if not options["topic"] and trailing_topic_parts:
        options["topic"] = " ".join(trailing_topic_parts).strip()

    return options


def _parse_triplet(raw: str, context: str) -> Optional[List[float]]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) != 3:
        print(f"Error: {context} expects 3 comma-separated floats")
        return None
    try:
        return [float(parts[0]), float(parts[1]), float(parts[2])]
    except ValueError:
        print(f"Error: {context} contains invalid float values: {raw}")
        return None


def _parse_lattice25d_options(tokens: List[str]) -> Optional[Dict[str, Any]]:
    options: Dict[str, Any] = {
        "glob": "docs/**/*.md",
        "include_glob": True,
        "max_notes": 40,
        "inline_notes": [],
        "count": 12,
        "cell_size": 0.4,
        "max_depth": 6,
        "phase_weight": 0.35,
        "index_mode": "grid",
        "qt_capacity": 8,
        "qt_z_variance": 0.01,
        "qt_extent": 0.35,
        "radius": 0.72,
        "query_intent": [0.9, 0.1, 0.1],
        "query_x": 0.1,
        "query_y": 0.1,
        "query_phase": 0.0,
        "query_top_k": 5,
    }

    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]

        if tok in {"--glob", "--notes-glob"} and idx + 1 < len(tokens):
            options["glob"] = tokens[idx + 1]
            options["include_glob"] = True
            idx += 2
            continue
        if tok == "--no-glob":
            options["include_glob"] = False
            idx += 1
            continue
        if tok == "--max-notes" and idx + 1 < len(tokens):
            try:
                options["max_notes"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --max-notes expects integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--note" and idx + 1 < len(tokens):
            options["inline_notes"].append(tokens[idx + 1])
            idx += 2
            continue
        if tok == "--count" and idx + 1 < len(tokens):
            try:
                options["count"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --count expects integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--cell-size" and idx + 1 < len(tokens):
            try:
                options["cell_size"] = float(tokens[idx + 1])
            except ValueError:
                print(f"Error: --cell-size expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--max-depth" and idx + 1 < len(tokens):
            try:
                options["max_depth"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --max-depth expects integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--phase-weight" and idx + 1 < len(tokens):
            try:
                options["phase_weight"] = float(tokens[idx + 1])
            except ValueError:
                print(f"Error: --phase-weight expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--index" and idx + 1 < len(tokens):
            mode = tokens[idx + 1].strip().lower()
            if mode not in {"grid", "quadtree", "hybrid"}:
                print(f"Error: --index must be grid|quadtree|hybrid, got: {tokens[idx + 1]}")
                return None
            options["index_mode"] = mode
            idx += 2
            continue
        if tok == "--qt-capacity" and idx + 1 < len(tokens):
            try:
                options["qt_capacity"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --qt-capacity expects integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--qt-z-var" and idx + 1 < len(tokens):
            try:
                options["qt_z_variance"] = max(0.0, float(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --qt-z-var expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--qt-extent" and idx + 1 < len(tokens):
            try:
                options["qt_extent"] = max(0.01, float(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --qt-extent expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--radius" and idx + 1 < len(tokens):
            try:
                options["radius"] = float(tokens[idx + 1])
            except ValueError:
                print(f"Error: --radius expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--query-intent" and idx + 1 < len(tokens):
            parsed = _parse_triplet(tokens[idx + 1], "--query-intent")
            if parsed is None:
                return None
            options["query_intent"] = parsed
            idx += 2
            continue
        if tok == "--query-x" and idx + 1 < len(tokens):
            try:
                options["query_x"] = float(tokens[idx + 1])
            except ValueError:
                print(f"Error: --query-x expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--query-y" and idx + 1 < len(tokens):
            try:
                options["query_y"] = float(tokens[idx + 1])
            except ValueError:
                print(f"Error: --query-y expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--query-phase" and idx + 1 < len(tokens):
            try:
                options["query_phase"] = float(tokens[idx + 1])
            except ValueError:
                print(f"Error: --query-phase expects float, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue
        if tok == "--query-top-k" and idx + 1 < len(tokens):
            try:
                options["query_top_k"] = max(1, int(tokens[idx + 1]))
            except ValueError:
                print(f"Error: --query-top-k expects integer, got: {tokens[idx + 1]}")
                return None
            idx += 2
            continue

        options["inline_notes"].append(tok)
        idx += 1

    return options


def handle_lattice25d(args: List[str], parsed_args) -> None:
    """Handle 2.5D hyperbolic lattice workflows in the main HYDRA CLI."""
    from .lattice25d_ops import (
        NoteRecord,
        build_lattice25d_payload,
        load_notes_from_glob,
        sample_notes,
    )

    as_json = parsed_args.json

    if not args or args[0] in {"help", "-h", "--help"}:
        print("Lattice25D Commands:")
        print("  hydra lattice25d sample [--count N] [--cell-size F] [--phase-weight F] [--json]")
        print("  hydra lattice25d notes [--glob PATTERN] [--max-notes N] [--note \"text\"] [--json]")
        print("                 [--cell-size F] [--max-depth N] [--phase-weight F] [--radius F]")
        print("                 [--index grid|quadtree|hybrid] [--qt-capacity N] [--qt-z-var F] [--qt-extent F]")
        print("                 [--query-intent a,b,c] [--query-x X] [--query-y Y] [--query-phase P] [--query-top-k K]")
        print()
        print("Examples:")
        print("  hydra lattice25d sample --count 16")
        print("  hydra lattice25d notes --glob \"docs/**/*.md\" --max-notes 50")
        print("  hydra lattice25d notes --no-glob --note \"council decision packet\" --json")
        return

    subcmd = args[0].strip().lower()
    options = _parse_lattice25d_options(args[1:])
    if options is None:
        return

    notes: List[NoteRecord] = []
    if subcmd == "sample":
        notes = sample_notes(options["count"])
    elif subcmd == "notes":
        for idx, text in enumerate(options["inline_notes"]):
            text_value = (text or "").strip()
            if not text_value:
                continue
            notes.append(
                NoteRecord(
                    note_id=f"inline-{idx}",
                    text=text_value,
                    tags=("inline", "cli"),
                    source="cli",
                    authority="internal",
                    tongue="DR",
                )
            )

        if options["include_glob"]:
            remaining = max(0, int(options["max_notes"]) - len(notes))
            if remaining > 0:
                notes.extend(
                    load_notes_from_glob(
                        pattern=options["glob"],
                        max_notes=remaining,
                        source="repo",
                        authority="internal",
                    )
                )
    else:
        print(f"Unknown lattice25d subcommand: {subcmd}")
        print("Try: hydra lattice25d help")
        return

    if not notes:
        print("Error: No notes found. Provide --note text or enable --glob with valid files.")
        return

    payload = build_lattice25d_payload(
        notes,
        cell_size=options["cell_size"],
        max_depth=options["max_depth"],
        phase_weight=options["phase_weight"],
        index_mode=options["index_mode"],
        quadtree_capacity=options["qt_capacity"],
        quadtree_z_variance=options["qt_z_variance"],
        quadtree_query_extent=options["qt_extent"],
        radius=options["radius"],
        query_intent=options["query_intent"],
        query_x=options["query_x"],
        query_y=options["query_y"],
        query_phase=options["query_phase"],
        query_top_k=options["query_top_k"],
    )

    if as_json:
        print(json.dumps(payload, indent=2))
        return

    print()
    print("=" * 60)
    print("  HYDRA LATTICE25D")
    print("=" * 60)
    print(f"  Mode:        {subcmd}")
    print(f"  Notes:       {payload['ingested_count']}")
    print(f"  Glob:        {options['glob'] if options['include_glob'] else '(disabled)'}")
    stats = payload["stats"]
    print(f"  Cells:       {stats['occupied_cells']} occupied, {stats['overlap_cells']} overlap")
    print(f"  Lace edges:  {payload['lace_edge_count']}")
    print(f"  Octree vox:  {stats['octree_voxel_count']}")
    print(f"  Weight avg:  {stats['semantic_weight_avg']:.3f}")
    print(f"  Index mode:  {stats.get('index_mode', options['index_mode'])}")
    qt = stats.get("quadtree")
    if isinstance(qt, dict):
        print(
            "  Quadtree:    "
            f"nodes={qt.get('node_count', 0)} "
            f"leaves={qt.get('leaf_count', 0)} "
            f"depth={qt.get('max_depth_used', 0)}"
        )
    print()
    print("  Nearest Bundles:")
    for row in payload.get("nearest", [])[:5]:
        print(
            f"    - {row['note_label']:28s} "
            f"tongue={row['tongue']:2s} d={row['distance']:.4f}"
        )
    print("=" * 60)
    print()


def handle_branch(args: List[str], parsed_args) -> None:
    """Handle ChoiceScript branch workflow commands."""
    from .branch_orchestrator import (
        graph_choicescript,
        list_graph_templates,
        list_strategies,
        run_branch_workflow,
    )

    if not args or args[0] in {"help", "-h", "--help"}:
        print("Branch Commands:")
        print("  hydra branch list")
        print("  hydra branch show <graph> [--topic T]")
        print("  hydra branch run <graph> [--topic T] [--strategy S] [--max-paths N] [--max-depth N]")
        print("                 [--providers claude,gpt,gemini] [--context '{\"k\":\"v\"}']")
        print("                 [--no-council] [--export-n8n path] [--export-choicescript path]")
        print()
        print(f"Available graphs: research_pipeline, content_publisher, training_funnel")
        print(f"Available strategies: {', '.join(list_strategies())}")
        return

    subcmd = args[0].strip().lower()
    as_json = parsed_args.json
    default_providers = parsed_args.providers

    if subcmd == "list":
        payload = {"graphs": list_graph_templates(), "strategies": list_strategies()}
        if as_json:
            print(json.dumps(payload, indent=2))
            return
        print("\nAvailable Branch Graphs:")
        print("-" * 70)
        for entry in payload["graphs"]:
            print(f"  [{entry['name']:17s}] scenes={entry['scene_count']:2d} start={entry['start']}")
        print(f"\nStrategies: {', '.join(payload['strategies'])}\n")
        return

    if subcmd == "show":
        graph_name = args[1] if len(args) > 1 else "research_pipeline"
        options = _parse_branch_options(args[2:], default_providers)
        if options is None:
            return
        try:
            choicescript = graph_choicescript(graph_name, topic=options["topic"])
        except ValueError as exc:
            print(f"Error: {exc}")
            return
        if as_json:
            print(json.dumps({"graph_name": graph_name, "choicescript": choicescript}, indent=2))
        else:
            print(choicescript)
        return

    if subcmd == "run":
        graph_name = args[1] if len(args) > 1 else "research_pipeline"
        options = _parse_branch_options(args[2:], default_providers)
        if options is None:
            return
        try:
            payload = run_branch_workflow(
                graph_name=graph_name,
                topic=options["topic"],
                strategy=options["strategy"],
                context=options["context"],
                max_paths=options["max_paths"],
                max_depth=options["max_depth"],
                providers=options["providers"],
                enable_council=options["enable_council"],
                export_n8n_path=options["export_n8n_path"],
                export_choicescript_path=options["export_choicescript_path"],
            )
        except ValueError as exc:
            print(f"Error: {exc}")
            return

        if as_json:
            print(json.dumps(payload, indent=2))
            return

        print()
        print("=" * 60)
        print("  HYDRA BRANCH")
        print("=" * 60)
        print(f"  Graph:      {payload['graph_name']}")
        print(f"  Strategy:   {payload['strategy']}")
        print(f"  Topic:      {options['topic'] or '(default)'}")
        print(f"  Paths:      {payload['paths_explored']}")
        print(f"  Coverage:   {payload['coverage']:.0%} ({int(payload['coverage'] * payload['total_scenes'])}/{payload['total_scenes']})")
        best = payload.get("best_path")
        if best:
            print(f"  Best Path:  {' -> '.join(best['scenes'])} (score={best['score']:.3f})")
        print()

        print("  Explored Paths:")
        for path in payload.get("all_paths", []):
            status = "OK" if not path.get("error") else path["error"]
            print(f"    [{path['id']}] {' -> '.join(path['scenes'])} | score={path['score']:.3f} | {status}")
        print()

        council = payload.get("council")
        if council:
            print("  Council:")
            print(f"    Winner: {council.get('winner_path_id')}")
            votes = council.get("votes", [])
            for vote in votes:
                print(f"    - {vote['provider']}: {vote['path_id']} ({vote['score']:.3f}, {vote['reason']})")
            print()

        exports = payload.get("exports", {})
        if exports:
            print("  Exports:")
            for key, path in exports.items():
                print(f"    - {key}: {path}")
            print()

        print("=" * 60)
        print()
        return

    print(f"Unknown branch subcommand: {subcmd}")
    print("Try: hydra branch help")


def handle_canvas(args: List[str], parsed_args) -> None:
    """Handle canvas multi-step workflow commands."""
    from .canvas import list_recipes, run_recipe, RECIPE_REGISTRY

    if not args or args[0] in {"help", "-h", "--help"}:
        print("Canvas Commands (multi-step orchestrated workflows):")
        print("  hydra canvas list                        List available recipes")
        print("  hydra canvas show <recipe>               Show recipe steps")
        print("  hydra canvas run <recipe> [--topic T]    Run a recipe")
        print("  hydra canvas paint <topic> [--steps N]   Freeform canvas (article recipe)")
        print()
        print("Recipes combine HYDRA commands as LEGO blocks:")
        print("  research -> draft -> edit -> expand -> fact-check -> publish")
        print("  Each step assigned to a model color (non-overlapping lanes)")
        print("  Roundabouts enable intelligent backtracking on quality gates")
        return

    subcmd = args[0]
    provider_list = [p.strip() for p in parsed_args.providers.split(",") if p.strip()]
    as_json = parsed_args.json

    if subcmd == "list":
        recipes = list_recipes()
        if as_json:
            print(json.dumps(recipes, indent=2))
            return
        print("\nAvailable Canvas Recipes:")
        print("-" * 70)
        for r in recipes:
            colors = ", ".join(r["colors"]) if r["colors"] else "auto"
            print(f"  [{r['name']:10s}] {r['steps']:2d} steps | colors: {colors}")
            if r["description"]:
                print(f"              {r['description']}")
        print()
        return

    if subcmd == "show":
        name = args[1] if len(args) > 1 else "article"
        builder = RECIPE_REGISTRY.get(name)
        if not builder:
            print(f"Unknown recipe: {name}. Available: {list(RECIPE_REGISTRY.keys())}")
            return
        steps = builder("example_topic")
        if as_json:
            from dataclasses import asdict
            print(json.dumps([asdict(s) for s in steps], indent=2, default=str))
            return

        print(f"\nRecipe: {name} ({len(steps)} steps)")
        print("-" * 60)
        for i, step in enumerate(steps, 1):
            color = step.assigned_color.value if step.assigned_color else "auto"
            deps = f" <- [{', '.join(step.depends_on)}]" if step.depends_on else ""
            bt = f" [backtrack -> {step.backtrack_to}]" if step.backtrack_to else ""
            print(f"  {i:2d}. [{color:6s}] {step.step_id:25s} {step.step_type.value:15s}{deps}{bt}")
            if step.description:
                print(f"      {step.description[:70]}")
        print()
        return

    if subcmd in ("run", "paint"):
        # Extract topic from args or --topic flag
        topic = ""
        max_steps = 0  # 0 = no limit
        remaining = args[1:]
        topic_parts: List[str] = []
        i = 0
        recipe_name = "article"  # default for paint
        while i < len(remaining):
            if remaining[i] == "--topic" and i + 1 < len(remaining):
                topic = remaining[i + 1]
                i += 2
                continue
            if remaining[i] == "--steps" and i + 1 < len(remaining):
                try:
                    max_steps = int(remaining[i + 1])
                except ValueError:
                    pass
                i += 2
                continue
            topic_parts.append(remaining[i])
            i += 1

        if subcmd == "run" and topic_parts:
            # First arg is recipe name for 'run'
            recipe_name = topic_parts[0]
            topic = topic or " ".join(topic_parts[1:]) or "general topic"
        elif subcmd == "paint":
            topic = topic or " ".join(topic_parts) or "general topic"

        if recipe_name not in RECIPE_REGISTRY:
            print(f"Unknown recipe: {recipe_name}. Available: {list(RECIPE_REGISTRY.keys())}")
            return

        if not as_json:
            print()
            print("=" * 60)
            print("  HYDRA CANVAS")
            print("=" * 60)
            print(f"  Recipe:    {recipe_name}")
            print(f"  Topic:     {topic}")
            print(f"  Providers: {', '.join(provider_list)}")
            if max_steps:
                print(f"  Max Steps: {max_steps}")
            print("=" * 60)
            print()

        result = run_recipe(recipe_name, topic, providers=provider_list, max_steps=max_steps)

        if as_json:
            # Remove large render for JSON output
            result.pop("canvas_render", None)
            print(json.dumps(result, indent=2))
            return

        summary = result["summary"]
        print(f"  Steps: {summary['completed']}/{summary['total_steps']} completed")
        print(f"  Colors: {summary['colors_used']}")
        print(f"  Strokes: {summary['canvas_strokes']}")
        print(f"  Duration: {summary['total_duration_ms']:.1f}ms")
        if summary["roundabouts_triggered"]:
            print(f"  Backtracked: {summary['roundabouts_triggered']} times")
        print()

        print("  Step Execution:")
        for sr in result["step_results"]:
            color_badge = f"[{sr['color']:6s}]" if sr["color"] else "[      ]"
            provider = f"({sr['provider']})" if sr["provider"] else ""
            status_icon = "OK" if sr["status"] == "done" else "XX"
            print(f"    {status_icon} {color_badge} {sr['step_id']:25s} {provider}")
        print()

        # Show canvas (abbreviated)
        render = result.get("canvas_render", "")
        if render:
            print("-" * 60)
            print("  KNOWLEDGE CANVAS")
            print("-" * 60)
            lines = render.splitlines()
            for line in lines[:30]:
                print(f"  {line}")
            if len(lines) > 30:
                print(f"  ... ({len(lines) - 30} more lines)")
        print("=" * 60)
        print()
        return

    print(f"Unknown canvas subcommand: {subcmd}")
    print("Try: hydra canvas help")


def run():
    """Entry point for package."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)


if __name__ == "__main__":
    run()
