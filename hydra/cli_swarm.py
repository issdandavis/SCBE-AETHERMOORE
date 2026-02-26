"""
HYDRA Swarm Browser CLI
========================

Standalone CLI to launch the 6-agent Sacred Tongue swarm browser.
No AI vendor dependency — uses local LLMs or HuggingFace endpoints.

Usage:
    python -m hydra.cli_swarm "search for SCBE-AETHERMOORE on GitHub"
    python -m hydra.cli_swarm --provider local --base-url http://localhost:1234/v1 "navigate to example.com"
    python -m hydra.cli_swarm --provider hf --model mistralai/Mistral-7B-Instruct-v0.3 "research quantum cryptography"
    python -m hydra.cli_swarm --dry-run "test task"
"""

import argparse
import asyncio
import sys

from .swarm_browser import SwarmBrowser


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hydra-swarm",
        description="HYDRA 6-Agent Sacred Tongue Swarm Browser",
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Web task to execute (natural language)",
    )
    parser.add_argument(
        "--provider",
        default="local",
        choices=["local", "hf", "huggingface"],
        help="LLM provider (default: local)",
    )
    parser.add_argument(
        "--model",
        default="local-model",
        help="Model name or HF model ID",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:1234/v1",
        help="Base URL for local provider (default: LM Studio)",
    )
    parser.add_argument(
        "--backend",
        default="playwright",
        choices=["playwright", "selenium", "cdp"],
        help="Browser backend (default: playwright)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mock mode — no real browser, just print actions",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Launch, print swarm status, and exit",
    )

    args = parser.parse_args()

    if not args.task and not args.status:
        parser.print_help()
        sys.exit(1)

    swarm = SwarmBrowser(
        provider_type=args.provider,
        model=args.model,
        base_url=args.base_url,
        backend_type=args.backend,
        dry_run=args.dry_run,
    )

    async def run():
        await swarm.launch()

        if args.status:
            import json
            print(json.dumps(swarm.get_status(), indent=2))
        elif args.task:
            result = await swarm.execute_task(args.task)
            import json
            print("\n" + json.dumps(result, indent=2, default=str))

        await swarm.shutdown()

    asyncio.run(run())


if __name__ == "__main__":
    main()
