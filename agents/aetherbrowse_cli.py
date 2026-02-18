"""AetherBrowse CLI
===================

CDP-first CLI entrypoint for governed browser actions.
Provides a small command surface for Phase-1 wiring:
- launch/attach to a browser backend
- validate each action via PHDM + bounds checks
- execute action
- return structured audit outputs
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import shlex
from typing import Any, Dict, Optional

from agents.browsers import list_backends
from agents.browser.session_manager import AetherbrowseSession, AetherbrowseSessionConfig


def _load_actions(path: str) -> list[dict[str, str]]:
    """Load action scripts from JSON or line-based command format."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: one action per line
        entries: list[dict[str, str]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = shlex.split(line)
            if not parts:
                continue
            action = parts[0]
            target = parts[1] if len(parts) > 1 else ""
            value = " ".join(parts[2:]) if len(parts) > 2 else None
            entry = {"action": action, "target": target}
            if value is not None:
                entry["value"] = value
            entries.append(entry)
        return entries
    else:
        if isinstance(data, list):
            return [dict(item) for item in data]
        raise ValueError("Action script must be a JSON array of {action,target,value?} objects.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AetherBrowse: SCBE-governed browser control"
    )

    parser.add_argument(
        "--backend",
        default="cdp",
        choices=["auto", "cdp", "playwright", "selenium", "chrome_mcp", "mock"],
        help="Backend driver (CDP default).",
    )
    parser.add_argument("--list-backends", action="store_true", help="Print available backends and exit.")
    parser.add_argument("--host", default="127.0.0.1", help="Backend host for CDP/remote services.")
    parser.add_argument("--port", type=int, default=9222, help="Backend port for CDP mode.")
    parser.add_argument("--target-id", default=None, help="CDP target id (optional).")
    parser.add_argument("--chrome-mcp-tab-id", type=int, default=None, help="Chrome MCP tab id (optional).")
    parser.add_argument("--playwright-browser", default="chromium", help="Playwright browser type.")
    parser.add_argument("--selenium-browser", default="chrome", help="Selenium browser type.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser backends in headless mode.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser backends in non-headless mode.",
    )
    parser.add_argument("--agent-id", default="aetherbrowse-ops", help="Agent identifier.")
    parser.add_argument("--auto-escalate", action="store_true", help="Automatically allow escalations.")
    parser.add_argument("--audit-only", action="store_true", help="Validate actions but do not execute.")
    parser.add_argument("--safe-radius", type=float, default=0.92, help="PHDM safe radius.")
    parser.add_argument("--dim", type=int, default=16, help="PHDM embedding dimension.")
    parser.add_argument("--sensitivity-factor", type=float, default=1.0, help="Scale all sensitivity scores.")
    parser.add_argument("--training-log", type=Path, default=None, help="Append run audit records to JSONL for training.")
    parser.set_defaults(headless=True)

    subparsers = parser.add_subparsers(dest="command", required=False)

    for action in ("navigate", "click", "type", "scroll", "snapshot", "screenshot", "extract", "close"):
        p = subparsers.add_parser(action, help=f"{action.title()} browser action.")
        p.add_argument("target", nargs="?", default="", help="Target URL or selector or direction.")

        if action == "type":
            p.add_argument("value", help="Text payload for type action.")

    script_parser = subparsers.add_parser("run-script", help="Run a JSON or line-based action script.")
    script_parser.add_argument("script", help="Path to action script file.")

    return parser


async def _execute_action(
    session: AetherbrowseSession,
    command: str,
    target: str,
    value: Optional[str],
    audit_only: bool,
) -> Dict[str, Any]:
    if command == "screenshot":
        return await session.execute_action("screenshot", target or "full_page", None, audit_only=audit_only)
    if command == "snapshot":
        return await session.execute_action("snapshot", target or session.current_url, None, audit_only=audit_only)
    if command == "extract":
        return await session.execute_action("extract", target or session.current_url, None, audit_only=audit_only)
    if command == "scroll":
        direction = target or "down"
        return await session.execute_action("scroll", direction, None, audit_only=audit_only)
    if command == "close":
        await session.close()
        return {"action": "close", "executed": True, "decision": "ALLOW", "message": "Session closed."}
    if command == "type":
        return await session.execute_action("type", target, value or "", audit_only=audit_only)

    return await session.execute_action(command, target, value, audit_only=audit_only)


async def _run_script(session: AetherbrowseSession, script_path: str, audit_only: bool) -> list[dict[str, Any]]:
    actions = _load_actions(script_path)
    results = []
    for action in actions:
        action_name = str(action.get("action", "")).strip().lower()
        target = str(action.get("target", ""))
        value = action.get("value")
        result = await _execute_action(session, action_name, target, value, audit_only)
        results.append(result)
    return results


def _append_training_records(path: Path, session: AetherbrowseSession, results: list[dict[str, Any]]) -> None:
    # Normalize audit payloads into model-focused training records.
    with path.open("a", encoding="utf-8") as f:
        for item in results:
            audit = item.get("audit", {})
            record = {
                "event_type": "browser_action",
                "session_id": item.get("session_id", session.session_id),
                "agent_id": session.config.agent_id,
                "backend": session.config.backend,
                "action": item.get("action"),
                "target": item.get("target"),
                "decision": item.get("decision"),
                "executed": bool(item.get("executed", False)),
                "validation_decision": audit.get("validation", {}).get("decision"),
                "validation_risk": audit.get("validation", {}).get("phdm_risk", None),
                "snapshot": audit.get("snapshot"),
                "error": item.get("error"),
            }
            f.write(json.dumps(record, default=str) + "\n")


async def _main_async(args: argparse.Namespace) -> None:
    if args.list_backends:
        print(json.dumps(list_backends(), indent=2, default=str))
        return

    cfg = AetherbrowseSessionConfig(
        backend=args.backend,
        host=args.host,
        port=args.port,
        target_id=args.target_id,
        agent_id=args.agent_id,
        headless=args.headless,
        playwright_browser=args.playwright_browser,
        selenium_browser=args.selenium_browser,
        chrome_mcp_tab_id=args.chrome_mcp_tab_id,
        auto_escalate=args.auto_escalate,
        safe_radius=args.safe_radius,
        phdm_dim=args.dim,
        sensitivity_factor=args.sensitivity_factor,
    )

    async with AetherbrowseSession(cfg) as session:
        if not await session.initialize():
            raise RuntimeError("Failed to initialize session/back-end.")

        if args.command == "run-script":
            results = await _run_script(session, args.script, args.audit_only)
        else:
            results = [
                await _execute_action(
                    session,
                    args.command,
                    args.target,
                    getattr(args, "value", None),
                    args.audit_only,
                )
            ]

        payload = {
            "session_id": session.session_id,
            "results": results,
            "audit_log": session.get_audit_log(),
        }

        if args.training_log:
            _append_training_records(args.training_log, session, results)

        print(json.dumps(payload, indent=2, default=str))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not args.list_backends and args.command is None:
        parser.error("A command is required unless --list-backends is used.")

    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
