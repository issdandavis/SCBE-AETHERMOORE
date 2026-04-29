"""
Agent Bus CLI — industry-standard shape per 2026 SOTA review of
Browser-use, SkyVern, Stagehand, Manus.

Examples:
  python -m agents.agent_bus_cli run "What is post-quantum cryptography?"
  python -m agents.agent_bus_cli run "Compare React vs Vue" --mode swarm --budget 1.00
  python -m agents.agent_bus_cli analyze https://example.com --mode headed
  python -m agents.agent_bus_cli perf
  python -m agents.agent_bus_cli train --dry-run
  python -m agents.agent_bus_cli generate-tool word_count "Count words in text" \\
      --param text=str
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Dict


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="agent-bus", description="SCBE Agent Bus CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    common_modes = ("headless", "headed", "swarm")

    run = sub.add_parser("run", help="Ask a question with web research + LLM")
    run.add_argument("prompt")
    run.add_argument("--mode", choices=common_modes, default="headless")
    run.add_argument("--max-sources", type=int, default=3)
    run.add_argument("--budget", type=float, default=0.0, help="Max USD-equivalent (0 = unbounded; advisory)")
    run.add_argument("--no-search", action="store_true")
    run.add_argument("--agent-id", default="agent-bus-cli")

    summ = sub.add_parser("summarize", help="Search + summarize")
    summ.add_argument("query")
    summ.add_argument("--mode", choices=common_modes, default="headless")
    summ.add_argument("--max-sources", type=int, default=5)
    summ.add_argument("--agent-id", default="agent-bus-cli")

    ana = sub.add_parser("analyze", help="Analyze a single page")
    ana.add_argument("url")
    ana.add_argument("--mode", choices=common_modes, default="headless")
    ana.add_argument("--agent-id", default="agent-bus-cli")

    sub.add_parser("perf", help="Show recent performance window")

    train = sub.add_parser("train", help="Maybe trigger a self-training run")
    train.add_argument("--dry-run", action="store_true")

    gen = sub.add_parser("generate-tool", help="LLM-generate a new tool for the bus")
    gen.add_argument("name")
    gen.add_argument("description")
    gen.add_argument("--param", action="append", default=[], help="name=type, repeatable")
    gen.add_argument("--mode", choices=common_modes, default="headless")
    gen.add_argument("--agent-id", default="agent-bus-cli")

    decide = sub.add_parser("decide", help="Ask the swarm for consensus on an action")
    decide.add_argument("action")
    decide.add_argument("--agent-id", default="agent-bus-cli")

    return p.parse_args()


async def _run(args: argparse.Namespace) -> Dict[str, Any]:
    from agents.agent_bus import AgentBus

    bus = AgentBus(browser_mode=args.mode, agent_id=args.agent_id)
    await bus.start()
    try:
        result = await bus.ask(
            args.prompt,
            search_first=not args.no_search,
            max_sources=args.max_sources,
        )
    finally:
        await bus.stop()
    return result


async def _summarize(args: argparse.Namespace) -> Dict[str, Any]:
    from agents.agent_bus import AgentBus

    bus = AgentBus(browser_mode=args.mode, agent_id=args.agent_id)
    await bus.start()
    try:
        return await bus.search_and_summarize(args.query, max_sources=args.max_sources)
    finally:
        await bus.stop()


async def _analyze(args: argparse.Namespace) -> Dict[str, Any]:
    from agents.agent_bus import AgentBus

    bus = AgentBus(browser_mode=args.mode, agent_id=args.agent_id)
    await bus.start()
    try:
        return await bus.analyze_page(args.url)
    finally:
        await bus.stop()


def _perf() -> Dict[str, Any]:
    from agents.agent_bus_training import TrainingTrigger

    perf = TrainingTrigger().measure()
    if perf is None:
        return {"perf": None, "reason": "no_events"}
    return {"perf": perf.__dict__}


async def _train(args: argparse.Namespace) -> Dict[str, Any]:
    from agents.agent_bus import AgentBus

    bus = AgentBus(agent_id="agent-bus-trainer")
    return await bus.maybe_train(dry_run=args.dry_run)


async def _generate_tool(args: argparse.Namespace) -> Dict[str, Any]:
    from agents.agent_bus import AgentBus

    params: Dict[str, str] = {}
    for entry in args.param:
        if "=" in entry:
            k, v = entry.split("=", 1)
            params[k] = v
    bus = AgentBus(browser_mode=args.mode, agent_id=args.agent_id)
    await bus.start()
    try:
        ok = await bus.generate_tool(args.name, args.description, params)
        return {"name": args.name, "registered": ok}
    finally:
        await bus.stop()


async def _decide(args: argparse.Namespace) -> Dict[str, Any]:
    from agents.agent_bus import AgentBus

    bus = AgentBus(browser_mode="swarm", agent_id=args.agent_id)
    await bus.start()
    try:
        return await bus.team_decide(args.action)
    finally:
        await bus.stop()


def main() -> int:
    args = _parse_args()
    if args.cmd == "run":
        result = asyncio.run(_run(args))
    elif args.cmd == "summarize":
        result = asyncio.run(_summarize(args))
    elif args.cmd == "analyze":
        result = asyncio.run(_analyze(args))
    elif args.cmd == "perf":
        result = _perf()
    elif args.cmd == "train":
        result = asyncio.run(_train(args))
    elif args.cmd == "generate-tool":
        result = asyncio.run(_generate_tool(args))
    elif args.cmd == "decide":
        result = asyncio.run(_decide(args))
    else:
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
