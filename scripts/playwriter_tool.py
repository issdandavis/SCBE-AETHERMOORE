#!/usr/bin/env python3
"""SCBE Playwriter wrapper with practical commands for automation workflows.

Designed to be small and reliable:
- one clean path for session management
- one clean path for browser actions
- JSONL run logs for every plan step
- reusable, deterministic action plans for repeatability
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
PLAYWRITER_BIN = "playwriter"
SESSION_FILE = ROOT / ".scbe" / "playwriter_session.json"
DEFAULT_LOG_DIR = ROOT / "artifacts" / "playwriter" / "logs"
DEFAULT_SCREENSHOT_DIR = ROOT / "artifacts" / "playwriter" / "shots"
RUN_PREFIX = "run"
DEFAULT_TIMEOUT_MS = 120000
_PLAYWRITER_CMD: list[str] | None = None


def _playwriter_cmd() -> list[str]:
    global _PLAYWRITER_CMD
    if _PLAYWRITER_CMD is not None:
        return _PLAYWRITER_CMD

    if os.name == "nt":
        # On Windows, npm global shims are frequently .cmd wrappers.
        cmd_path = shutil.which(f"{PLAYWRITER_BIN}.cmd") or shutil.which(PLAYWRITER_BIN)
        ps1_path = shutil.which(f"{PLAYWRITER_BIN}.ps1")
        if cmd_path:
            _PLAYWRITER_CMD = [cmd_path]
            return _PLAYWRITER_CMD
        if ps1_path:
            _PLAYWRITER_CMD = ["pwsh", "-NoProfile", "-File", ps1_path]
            return _PLAYWRITER_CMD
    elif shutil.which(PLAYWRITER_BIN):
        _PLAYWRITER_CMD = [PLAYWRITER_BIN]
        return _PLAYWRITER_CMD

    if shutil.which("npx"):
        _PLAYWRITER_CMD = ["npx", "-y", PLAYWRITER_BIN]
        return _PLAYWRITER_CMD

    raise RuntimeError(
        "playwriter CLI not found.\n"
        "Install one of:\n"
        "  npm i -g playwriter\n"
        "  # or use npx (npm install npm)\n"
    )


@dataclass
class RunEvent:
    ts_utc: str
    step: int
    action: str
    ok: bool
    session: int | None
    payload: dict[str, Any]
    error: str | None = None


def _require_playwriter() -> None:
    _playwriter_cmd()


def _run(
    cmd: list[str],
    *,
    timeout_ms: int = 120000,
) -> subprocess.CompletedProcess:
    if cmd and cmd[0] == PLAYWRITER_BIN:
        cmd = _playwriter_cmd() + cmd[1:]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_ms / 1000,
    )


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_session(session_id: int) -> None:
    _ensure_parent(SESSION_FILE)
    SESSION_FILE.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "updated_at_utc": _now(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _read_session() -> int | None:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        raw = data.get("session_id")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.isdigit():
            return int(raw)
    except Exception:
        return None
    return None


def _parse_session(text: str) -> int | None:
    # Example outputs:
    # "Session 1 created."
    # "Created session: 1"
    # fallback to first bare integer
    for pat in (r"Session\s+(\d+)", r"\b(\d+)\b"):
        match = re.search(pat, text or "")
        if match:
            return int(match.group(1))
    return None


def _get_session(requested: int | None) -> int:
    if requested is not None:
        return requested
    saved = _read_session()
    if saved is not None:
        return saved
    proc = _run([PLAYWRITER_BIN, "session", "new"], timeout_ms=DEFAULT_TIMEOUT_MS)
    sid = _parse_session(proc.stdout or "")
    if proc.returncode != 0 or sid is None:
        raise RuntimeError(
            f"playwriter session create failed: {proc.stdout}\n{proc.stderr}".strip()
        )
    _save_session(sid)
    return sid


def _js(v: Any) -> str:
    return json.dumps(v)


def _loc(target: str) -> str:
    t = target.strip()
    if re.match(r"^e\d+$", t):
        return f"aria-ref={t}"
    if t.startswith("aria-ref=") or t.startswith("css=") or t.startswith("text="):
        return t
    if t.startswith("xpath="):
        return t
    return t


def _build_action_js(action: str, **kwargs: Any) -> str:
    if action == "goto":
        url = str(kwargs["url"])
        wait_until = str(kwargs.get("wait_until", "domcontentloaded"))
        timeout = int(kwargs.get("timeout", 120000))
        return (
            "await page.goto("
            f"{_js(url)}, {{ waitUntil: {_js(wait_until)}, timeout: {timeout} }});"
        )

    if action == "click":
        target = _loc(str(kwargs["target"]))
        return f"await page.locator({_js(target)}).first.click()"

    if action == "fill":
        target = _loc(str(kwargs["target"]))
        value = str(kwargs["value"])
        return f"await page.locator({_js(target)}).first.fill({_js(value)})"

    if action == "type":
        target = str(kwargs.get("target", "")).strip()
        value = str(kwargs["value"])
        delay = int(kwargs.get("delay", 0))
        if target:
            return (
                f"await page.locator({_js(_loc(target))}).first.type({_js(value)}, {{ delay: {delay} }})"
            )
        return f"await page.keyboard.insertText({_js(value)})"

    if action == "press":
        target = str(kwargs.get("target", "")).strip()
        key = str(kwargs["key"])
        if target:
            return (
                f"await page.locator({_js(_loc(target))}).first.press({_js(key)})"
            )
        return f"await page.keyboard.press({_js(key)})"

    if action == "wait":
        timeout = int(kwargs.get("timeout", 1000))
        return f"await page.waitForTimeout({timeout})"

    if action == "wait_for":
        target = _loc(str(kwargs["target"]))
        timeout = int(kwargs.get("timeout", 1000))
        state = str(kwargs.get("state", "visible"))
        return (
            f"await page.locator({_js(target)}).first.waitFor({{ state: {_js(state)}, timeout: {timeout} }})"
        )

    if action == "snapshot":
        return "console.log(JSON.stringify(await accessibilitySnapshot({ page })));"

    if action == "scroll":
        direction = str(kwargs.get("direction", "down"))
        amount = int(kwargs.get("amount", 700))
        steps = int(kwargs.get("steps", 1))
        if direction.lower() == "up":
            amount = -abs(amount)
        return (
            "await page.mouse.wheel(0, 0);\n"
            + "\n".join(
                f"await page.mouse.wheel(0, {amount}); await page.waitForTimeout(120);"
                for _ in range(max(1, steps))
            )
        )

    if action == "eval":
        code = str(kwargs["code"])
        if not code.strip():
            raise ValueError("eval action requires non-empty code")
        return code

    if action == "screenshot":
        out = Path(kwargs["path"])
        return f'await page.screenshot({{"path": {_js(str(out))}, "fullPage": true}}); console.log({_js(str(out))});'

    raise ValueError(f"Unsupported action: {action}")


def _run_js(session: int, js: str, timeout_ms: int) -> str:
    proc = _run([PLAYWRITER_BIN, "-s", str(session), "-e", js], timeout_ms=timeout_ms)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(
            f"playwriter eval failed (session={session}):\n{out}\n{(proc.stderr or '').strip()}".strip()
        )
    return out


def _append_log(log_file: Path, event: RunEvent) -> None:
    _ensure_parent(log_file)
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")


def _new_log_file(label: str | None = None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(c for c in (label or "run") if c.isalnum() or c in "-_")[:40] or "run"
    return DEFAULT_LOG_DIR / f"{stamp}_{safe_label}.jsonl"


def _normalize_snapshot(json_text: str) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(json_text)
    except Exception:
        return None


def cmd_session_new(_: argparse.Namespace) -> int:
    proc = _run([PLAYWRITER_BIN, "session", "new"], timeout_ms=DEFAULT_TIMEOUT_MS)
    sid = _parse_session(proc.stdout or "")
    if proc.returncode != 0 or sid is None:
        print(f"playwriter session new failed: {proc.stdout}\n{proc.stderr}".strip())
        return 1
    _save_session(sid)
    print(f"session={sid}")
    return 0


def cmd_session_show(_: argparse.Namespace) -> int:
    sid = _read_session()
    if sid is None:
        print("no-saved-session")
        return 1
    print(f"session={sid}")
    return 0


def cmd_session_list(_: argparse.Namespace) -> int:
    proc = _run([PLAYWRITER_BIN, "session", "list"], timeout_ms=DEFAULT_TIMEOUT_MS)
    print((proc.stdout or "").strip())
    if proc.stderr:
        if proc.stdout:
            print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode


def cmd_session_kill(args: argparse.Namespace) -> int:
    sid = args.session if args.session is not None else _read_session()
    if sid is None:
        print("No session found to kill.")
        return 1
    proc = _run([PLAYWRITER_BIN, "session", "delete", str(sid)], timeout_ms=DEFAULT_TIMEOUT_MS)
    if sid == _read_session():
        SESSION_FILE.unlink(missing_ok=True)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)
    return proc.returncode


def run_single(args: argparse.Namespace) -> int:
    _require_playwriter()
    sid = _get_session(args.session)
    action = args.command.replace("-", "_")
    payload: dict[str, Any] = {"action": action}
    if hasattr(args, "target") and args.target:
        payload["target"] = args.target
    if hasattr(args, "value") and args.value:
        if action == "eval":
            payload["code"] = args.value
        else:
            payload["value"] = args.value
    if hasattr(args, "url") and args.url:
        payload["url"] = args.url
    if hasattr(args, "key") and args.key:
        payload["key"] = args.key
    if hasattr(args, "ms") and args.ms:
        payload["ms"] = args.ms
    if hasattr(args, "direction") and args.direction:
        payload["direction"] = args.direction
    if hasattr(args, "steps") and args.steps is not None:
        payload["steps"] = args.steps
    if hasattr(args, "amount") and args.amount is not None:
        payload["amount"] = args.amount
    if hasattr(args, "wait_until") and args.wait_until:
        payload["wait_until"] = args.wait_until

    try:
        if action == "screenshot":
            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{args.name}_{sid}_{int(datetime.now(timezone.utc).timestamp())}.png"
            payload["path"] = str(out_path)
        js = _build_action_js(
            action,
            target=payload.get("target", ""),
            value=payload.get("value", ""),
            url=payload.get("url", ""),
            key=payload.get("key", ""),
            code=payload.get("code", ""),
            timeout=payload.get("timeout", args.timeout_ms),
            delay=payload.get("delay", 0),
            timeout_ms=args.timeout_ms,
            ms=payload.get("ms", 1000),
            direction=payload.get("direction", "down"),
            steps=payload.get("steps", 1),
            amount=payload.get("amount", 700),
            wait_until=payload.get("wait_until", "domcontentloaded"),
            path=payload.get("path", ""),
        )
        if args.dry_run:
            print(json.dumps({"dry_run": True, "session": sid, "action": action, "js": js}, indent=2))
            if action == "screenshot":
                print(f"would_save_to={payload['path']}")
            return 0
        out = _run_js(sid, js, timeout_ms=args.timeout_ms)
        if action == "snapshot":
            snap = _normalize_snapshot(out)
            if snap is None:
                print(out)
            else:
                print(json.dumps(snap, indent=2))
        else:
            print(out) if out else print(f"{action}=ok")
        if action == "screenshot":
            print(f"saved={payload['path']}")
        _save_session(sid)
        return 0
    except Exception as exc:
        print(f"[FAIL] {action} (session={sid}): {exc}")
        return 1


def run_plan(args: argparse.Namespace) -> int:
    _require_playwriter()
    sid = _get_session(args.session)
    plan_path = Path(args.plan).expanduser()
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        return 1

    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    steps: list[Any]
    manifest: dict[str, Any] = {}
    if isinstance(raw, list):
        steps = raw
    elif isinstance(raw, dict):
        manifest = dict(raw)
        steps = raw.get("steps", raw.get("actions", []))
        if not isinstance(steps, list):
            print("Plan must be list or {'steps': [...]} / {'actions': [...]}")
            return 1
    else:
        print("Plan JSON must be a list of actions or an object with steps/actions.")
        return 1

    log_file = Path(args.log or _new_log_file(args.label))
    failures = 0
    run_id = f"{RUN_PREFIX}-{int(datetime.now(timezone.utc).timestamp())}"
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            failures += 1
            event = RunEvent(
                ts_utc=_now(),
                step=idx,
                action="invalid",
                ok=False,
                session=sid,
                payload={"raw": step},
                error="step is not an object",
            )
            _append_log(log_file, event)
            if args.stop_on_error:
                break
            continue

        action = str(step.get("action", "")).strip()
        if not action:
            failures += 1
            event = RunEvent(
                ts_utc=_now(),
                step=idx,
                action="invalid",
                ok=False,
                session=sid,
                payload=step,
                error="missing action field",
            )
            _append_log(log_file, event)
            if args.stop_on_error:
                break
            continue

        try:
            out_name = None
            if action == "screenshot":
                out_name = step.get("name", f"step-{idx}")
                shot_dir = DEFAULT_SCREENSHOT_DIR
                shot_name = f"{_now().replace(':', '-')}_{out_name}_{sid}.png"
                shot_path = shot_dir / shot_name
                step = {**step, "path": str(shot_path)}

            js = _build_action_js(
                action,
                target=step.get("target", step.get("selector", "")),
                value=step.get("value", step.get("text", "")),
                url=step.get("url", ""),
                code=step.get("code", ""),
                timeout=step.get("timeout", args.timeout_ms),
                delay=int(step.get("delay", 0)),
                timeout_ms=args.timeout_ms,
                ms=int(step.get("ms", 1000)),
                direction=step.get("direction", "down"),
                steps=int(step.get("steps", 1)),
                amount=int(step.get("amount", 700)),
                wait_until=step.get("wait_until", "domcontentloaded"),
                state=step.get("state", "visible"),
                path=step.get("path", ""),
            )

            if args.dry_run:
                print(json.dumps({"run_id": run_id, "session": sid, "step": idx, "action": action, "js": js}, indent=2))
                event = RunEvent(
                    ts_utc=_now(),
                    step=idx,
                    action=action,
                    ok=True,
                    session=sid,
                    payload={"js": js, "dry_run": True},
                    error=None,
                )
            else:
                out = _run_js(sid, js, timeout_ms=args.timeout_ms)
                event = RunEvent(
                    ts_utc=_now(),
                    step=idx,
                    action=action,
                    ok=True,
                    session=sid,
                    payload={"out": out, "js": js},
                    error=None,
                )
            _append_log(log_file, event)
            print(f"[OK] {idx:02d} {action}" + (f" -> {out_name}" if out_name else ""))
            if action == "screenshot" and step.get("path"):
                _ensure_parent(Path(step["path"]))
                print(f"    saved={step['path']}")
        except Exception as exc:
            failures += 1
            _append_log(
                log_file,
                RunEvent(
                    ts_utc=_now(),
                    step=idx,
                    action=action,
                    ok=False,
                    session=sid,
                    payload=step,
                    error=str(exc),
                ),
            )
            print(f"[FAIL] {idx:02d} {action}: {exc}")
            if args.stop_on_error:
                break

    summary = {
        "session": sid,
        "steps": len(steps),
        "failed": failures,
        "run_id": run_id,
        "log": str(log_file),
        "manifest": manifest if manifest else {},
    }
    _append_log(log_file, RunEvent(ts_utc=_now(), step=len(steps) + 1, action="summary", ok=True, session=sid, payload=summary))
    print(json.dumps(summary, indent=2))
    return 0 if failures == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SCBE Playwriter utility")
    parser.add_argument("--session", type=int, default=None, help="Use a specific Playwriter session")
    parser.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS, help="JS eval timeout in ms")
    parser.add_argument("--dry-run", action="store_true", help="Plan or action review only")

    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new-session", help="Create and persist a new session")
    p_new.set_defaults(func=cmd_session_new)

    p_show = sub.add_parser("show-session", help="Show persisted session id")
    p_show.set_defaults(func=cmd_session_show)

    p_list = sub.add_parser("session-list", help="List playwriter sessions")
    p_list.set_defaults(func=cmd_session_list)

    p_kill = sub.add_parser("kill-session", help="Kill session (defaults to saved session)")
    p_kill.add_argument("--session", type=int, default=None)
    p_kill.set_defaults(func=cmd_session_kill)

    p_plan = sub.add_parser("run-plan", help="Run JSON action plan")
    p_plan.add_argument("plan", help="JSON file with steps or {'steps':[...]} / {'actions':[...]} ")
    p_plan.add_argument("--label", default="", help="Optional run label for log naming")
    p_plan.add_argument("--log", default="", help="Optional explicit log file path")
    p_plan.add_argument("--stop-on-error", action="store_true", help="Stop on first failure")
    p_plan.set_defaults(func=run_plan)

    for action in ("goto", "click", "fill", "type", "press", "snapshot", "screenshot", "eval", "wait", "wait-for", "scroll"):
        cmd = sub.add_parser(action, help=f"{action} action")
        cmd.add_argument("target", nargs="?", default="", help="target/selector/url depending on action")
        cmd.add_argument("value", nargs="?", default="", help="value/text/code for fill/type/eval")
        cmd.add_argument("--url", default="", help="URL for goto")
        cmd.add_argument("--key", default="", help="Key for press")
        cmd.add_argument("--name", default="shot", help="Screenshot filename stem")
        cmd.add_argument("--out-dir", default=str(DEFAULT_SCREENSHOT_DIR), help="Directory for screenshots")
        cmd.add_argument("--ms", type=int, default=1000, help="Wait milliseconds")
        cmd.add_argument("--direction", default="down", choices=("up", "down"), help="Scroll direction")
        cmd.add_argument("--steps", type=int, default=1, help="Scroll steps")
        cmd.add_argument("--amount", type=int, default=700, help="Scroll amount per step")
        cmd.add_argument("--wait-until", default="domcontentloaded", help="page.goto waitUntil")
        cmd.set_defaults(func=run_single)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    os.environ.setdefault("PYTHONUTF8", "1")
    _require_playwriter()

    if not args.command:
        parser.print_help()
        return 2

    action_commands = {"goto", "click", "fill", "type", "press", "snapshot", "screenshot", "eval", "wait", "wait-for", "scroll"}
    if args.command in action_commands:
        if args.command == "goto" and not args.url:
            args.url = args.target
        if args.command == "eval" and args.target and not args.value:
            args.value = args.target
            args.target = ""
    if args.command == "screenshot":
        if args.value:
            args.name = args.value
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
