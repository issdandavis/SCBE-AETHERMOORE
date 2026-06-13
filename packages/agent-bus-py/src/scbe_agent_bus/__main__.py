"""scbe-agent-bus CLI: read JSON event(s) from stdin or --input, emit JSONL results."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import AgentBusError, run_batch, scan_agent_request


def _read_input(input_path: str) -> str:
    if input_path:
        return Path(input_path).read_text(encoding="utf-8")
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def _parse_events(raw: str) -> list[dict]:
    text = (raw or "").strip()
    if not text:
        return []
    parsed: Any = json.loads(text)
    if isinstance(parsed, list):
        return [e for e in parsed if isinstance(e, dict)]
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        return [e for e in parsed["items"] if isinstance(e, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scbe-agent-bus",
        description="Pipeable SCBE agent-bus runner. Reads JSON event(s) from stdin/--input.",
    )
    parser.add_argument("--repo-root", default=os.getcwd())
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--python", default="")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Run the lightweight governance scan instead of the full agent-bus runner.",
    )
    args = parser.parse_args(argv)

    raw = _read_input(args.input)
    events = _parse_events(raw)
    if not events:
        print("scbe-agent-bus: no events provided", file=sys.stderr)
        return 2

    if args.scan:
        rows = [
            scan_agent_request(
                action=str(event.get("action") or event.get("task_type") or "EXECUTE"),
                target=str(event.get("target") or event.get("task") or ""),
                command=str(event.get("command") or event.get("operation_command") or ""),
                observed=str(event.get("observed") or ""),
                context=(event.get("context") if isinstance(event.get("context"), dict) else {}),
            )
            for event in events
        ]
        output = "\n".join(json.dumps(row) for row in rows) + "\n"
        if args.output:
            out_path = Path(args.output).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return 0 if all(row["decision"] != "DENY" for row in rows) else 1

    try:
        rows = run_batch(
            events,
            repo_root=args.repo_root,
            python=args.python or None,
            continue_on_error=args.continue_on_error,
        )
    except AgentBusError as exc:
        print(f"scbe-agent-bus: {exc}", file=sys.stderr)
        return 2

    output = "\n".join(json.dumps(row) for row in rows) + "\n"
    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    return 0 if all(row["ok"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
