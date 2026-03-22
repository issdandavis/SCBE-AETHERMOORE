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
from urllib import error as urllib_error
from urllib import request as urllib_request

from agents.browsers import get_chrome_launch_command, list_backends
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


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"} or normalized.startswith("127.")


def _read_json_url(url: str, timeout: float = 2.0) -> tuple[int, Any]:
    with urllib_request.urlopen(url, timeout=timeout) as response:
        status = getattr(response, "status", response.getcode())
        payload = response.read().decode("utf-8")
    return status, json.loads(payload)


def _format_target_list(targets: list[dict[str, Any]], limit: int = 5) -> str:
    labels = []
    for target in targets[:limit]:
        ident = str(target.get("id", "unknown"))
        title = str(target.get("title") or target.get("url") or target.get("type") or "untitled").strip()
        labels.append(f"{ident} ({title})")
    return ", ".join(labels) if labels else "none"


def _build_cdp_unavailable_message(host: str, port: int, detail: str) -> str:
    endpoint = f"http://{host}:{port}/json"
    if _is_loopback_host(host):
        launch_cmd = get_chrome_launch_command(port=port)
        return (
            f"CDP endpoint {endpoint} is unavailable ({detail}). "
            f"Start a local Chrome/Chromium instance with remote debugging enabled, for example: {launch_cmd}. "
            f"Then retry this command or switch backends with --backend playwright or --backend mock."
        )
    return (
        f"CDP endpoint {endpoint} is unavailable ({detail}). "
        f"Verify the remote browser is running with remote debugging enabled and that {endpoint} returns JSON."
    )


def _build_cdp_no_targets_message(host: str, port: int) -> str:
    endpoint = f"http://{host}:{port}/json"
    if _is_loopback_host(host):
        launch_cmd = get_chrome_launch_command(port=port)
        return (
            f"CDP endpoint {endpoint} responded, but it exposed no debuggable targets. "
            f"Start Chrome/Chromium with remote debugging enabled and open at least one tab. "
            f"Example launch command: {launch_cmd}."
        )
    return (
        f"CDP endpoint {endpoint} responded, but it exposed no debuggable targets. "
        f"Open a page in the remote browser or choose a valid --target-id before retrying."
    )


def _build_cdp_missing_target_message(
    host: str,
    port: int,
    target_id: str,
    targets: list[dict[str, Any]],
) -> str:
    endpoint = f"http://{host}:{port}/json"
    return (
        f"CDP endpoint {endpoint} responded, but no target matched --target-id {target_id}. "
        f"Available targets: {_format_target_list(targets)}. "
        f"Open the intended tab or pass a valid --target-id."
    )


def _build_cdp_missing_websocket_message(host: str, port: int, target: dict[str, Any]) -> str:
    endpoint = f"http://{host}:{port}/json"
    target_id = str(target.get("id", "unknown"))
    title = str(target.get("title") or target.get("url") or target.get("type") or "untitled").strip()
    return (
        f"CDP target {target_id} ({title}) from {endpoint} is missing webSocketDebuggerUrl. "
        f"Refresh or reopen that tab, or choose a different target."
    )


def _build_cdp_session_init_message(host: str, port: int, detail: str) -> str:
    endpoint = f"http://{host}:{port}/json"
    if _is_loopback_host(host):
        launch_cmd = get_chrome_launch_command(port=port)
        return (
            f"Failed to initialize the CDP session at {endpoint} ({detail}). "
            f"Reconfirm the local browser is still listening on that port and retry. "
            f"Example launch command: {launch_cmd}."
        )
    return (
        f"Failed to initialize the CDP session at {endpoint} ({detail}). "
        f"Verify the remote browser is still reachable and exposing a valid CDP target."
    )


def _build_session_init_error(args: argparse.Namespace, session: AetherbrowseSession) -> str:
    details = ""
    for entry in reversed(session.get_audit_log()):
        if entry.get("event") == "backend_init_failed":
            details = str(entry.get("error") or "").strip()
            break

    if args.backend == "cdp":
        return _build_cdp_session_init_message(
            args.host,
            args.port,
            details or "session initialization failed after the readiness probe passed",
        )

    if details:
        return f"Failed to initialize {args.backend} session/back-end ({details})."
    return f"Failed to initialize {args.backend} session/back-end."


async def _check_cdp_readiness(host: str, port: int, target_id: Optional[str]) -> Optional[str]:
    endpoint = f"http://{host}:{port}/json"
    try:
        status, targets = await asyncio.to_thread(_read_json_url, endpoint)
    except urllib_error.URLError as exc:
        detail = str(exc.reason or exc).strip()
        return _build_cdp_unavailable_message(host, port, detail)
    except Exception as exc:  # noqa: BLE001
        return _build_cdp_unavailable_message(host, port, str(exc).strip())

    if status != 200:
        return _build_cdp_unavailable_message(host, port, f"HTTP {status}")
    if not isinstance(targets, list):
        return _build_cdp_unavailable_message(host, port, f"unexpected payload type {type(targets).__name__}")
    if not targets:
        return _build_cdp_no_targets_message(host, port)

    if target_id:
        target = next((item for item in targets if str(item.get("id")) == target_id), None)
        if target is None:
            return _build_cdp_missing_target_message(host, port, target_id, targets)
    else:
        target = next((item for item in targets if item.get("type") == "page"), targets[0])

    if not target.get("webSocketDebuggerUrl"):
        return _build_cdp_missing_websocket_message(host, port, target)

    return None


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

    if args.backend == "cdp":
        readiness_error = await _check_cdp_readiness(args.host, args.port, args.target_id)
        if readiness_error:
            raise RuntimeError(readiness_error)

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

    session = AetherbrowseSession(cfg)
    try:
        if not await session.initialize():
            raise RuntimeError(_build_session_init_error(args, session))

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
    finally:
        await session.close()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not args.list_backends and args.command is None:
        parser.error("A command is required unless --list-backends is used.")

    try:
        asyncio.run(_main_async(args))
    except RuntimeError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
