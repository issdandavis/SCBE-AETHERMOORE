#!/usr/bin/env python3
"""Context-aware code/conlang bridge for SCBE command intent.

This makes the conlang/code lane executable without pretending the tongue is
the executor. The bridge lowers intent into one neutral command plan, records
the tongue transport for the intent and command, then renders that plan into
multiple language faces.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scbe import encode_bytes  # type: ignore  # root CLI module
from src.coding_spine.command_compiler import compile_intent_to_plan
from src.tongues.role_registry import TONGUE_NAMES, resolve_tongue_jobs


LANGUAGE_FACES = (
    "command",
    "powershell",
    "bash",
    "python",
    "javascript",
    "json",
    "markdown",
)


@dataclass(frozen=True)
class BridgeRequest:
    intent: str
    source_language: str
    target_language: str
    tongue: str
    permission_mode: str
    requested_tool: str | None


def _normalize_tongue(tongue: str) -> str:
    normalized = tongue.strip().upper()
    if normalized not in TONGUE_NAMES:
        raise ValueError(f"unknown tongue {tongue!r}; choose one of {', '.join(TONGUE_NAMES)}")
    return normalized


def _quote_command_for_python(command: str) -> str:
    return json.dumps(command)


def _quote_command_for_js(command: str) -> str:
    return json.dumps(command)


def render_language_face(command: str | None, target_language: str, *, execute: bool = False) -> str:
    lang = target_language.strip().lower()
    if not command:
        return ""
    if lang == "command":
        return command
    if lang == "powershell":
        return command
    if lang == "bash":
        return command
    if lang == "python":
        return (
            "import subprocess\n"
            f"cmd = {_quote_command_for_python(command)}\n"
            "subprocess.run(cmd, shell=True, check=True)\n"
        )
    if lang == "javascript":
        return (
            "const { execSync } = require('node:child_process');\n"
            f"execSync({_quote_command_for_js(command)}, {{ stdio: 'inherit' }});\n"
        )
    if lang == "json":
        return json.dumps({"command": command, "execute": execute}, indent=2)
    if lang == "markdown":
        return f"```powershell\n{command}\n```"
    raise ValueError(f"unknown target language {target_language!r}; choose one of {', '.join(LANGUAGE_FACES)}")


def build_bridge(req: BridgeRequest, *, all_faces: bool = False) -> dict[str, Any]:
    tongue = _normalize_tongue(req.tongue)
    plan = compile_intent_to_plan(
        intent=req.intent,
        permission_mode=req.permission_mode,
        preferred_language=req.target_language,
        requested_tool=req.requested_tool,
    )
    command = plan.get("command", {}).get("template")
    target_faces = LANGUAGE_FACES if all_faces else (req.target_language,)
    rendered = {
        face: render_language_face(command, face)
        for face in target_faces
    }
    tongue_jobs = resolve_tongue_jobs(tongue)
    intent_bytes = req.intent.encode("utf-8")
    command_bytes = (command or "").encode("utf-8")
    context_packet = {
        "schema": "scbe_context_code_conlang_bridge_v1",
        "intent": {
            "text": req.intent,
            "source_language": req.source_language,
            "target_language": req.target_language,
            "permission_mode": req.permission_mode,
            "requested_tool": req.requested_tool,
            "sha256": sha256(intent_bytes).hexdigest(),
        },
        "tongue": {
            "code": tongue,
            "transport_atomic": tongue_jobs.transport_atomic,
            "paradigm_isomorphism": tongue_jobs.paradigm_isomorphism,
            "runtime_emission": tongue_jobs.runtime_emission,
            "spirit_narrative": tongue_jobs.spirit_narrative,
            "intent_tokens": encode_bytes(tongue, intent_bytes),
            "command_tokens": encode_bytes(tongue, command_bytes) if command else "",
        },
        "command_plan": plan,
        "language_faces": rendered,
        "execution": {
            "default": "not_executed",
            "rule": "Only run with --execute after command_plan.command.runnable is true.",
            "runnable": bool(plan.get("command", {}).get("runnable")),
        },
    }
    return context_packet


def maybe_execute(packet: dict[str, Any]) -> dict[str, Any]:
    command = packet.get("command_plan", {}).get("command", {}).get("template")
    runnable = bool(packet.get("command_plan", {}).get("command", {}).get("runnable"))
    if not command or not runnable:
        packet["execution"].update({"status": "blocked", "reason": "command is not runnable by policy"})
        return packet
    proc = subprocess.run(command, cwd=str(ROOT), shell=True, text=True, capture_output=True)
    packet["execution"].update(
        {
            "status": "executed",
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    )
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Context-aware code/conlang command bridge")
    parser.add_argument("intent", nargs="*", help="intent or command request")
    parser.add_argument("--source-language", default="natural")
    parser.add_argument("--target-language", default="python", choices=LANGUAGE_FACES)
    parser.add_argument("--tongue", default="KO")
    parser.add_argument("--permission-mode", default="observe")
    parser.add_argument("--tool", default=None, help="force a command compiler tool class")
    parser.add_argument("--all-faces", action="store_true", help="render every supported language face")
    parser.add_argument("--execute", action="store_true", help="execute the compiled command if policy permits")
    parser.add_argument("--fail-on-deny", action="store_true", help="return nonzero for denied plans even without execution")
    parser.add_argument("--json", action="store_true", help="print full JSON receipt")
    args = parser.parse_args(argv)

    intent = " ".join(args.intent).strip()
    if not intent:
        parser.error("intent is required")
    packet = build_bridge(
        BridgeRequest(
            intent=intent,
            source_language=args.source_language,
            target_language=args.target_language,
            tongue=args.tongue,
            permission_mode=args.permission_mode,
            requested_tool=args.tool,
        ),
        all_faces=args.all_faces,
    )
    if args.execute:
        packet = maybe_execute(packet)
    if args.json:
        print(json.dumps(packet, indent=2))
    else:
        plan = packet["command_plan"]
        print(
            f"{packet['schema']} tongue={packet['tongue']['code']} "
            f"tool={plan['tool']['class']} decision={plan['policy']['decision']} "
            f"runnable={plan['command']['runnable']}"
        )
        face = packet["language_faces"].get(args.target_language, "")
        if face:
            print(face)
    decision = packet["command_plan"]["policy"]["decision"]
    if args.execute and packet.get("execution", {}).get("status") == "blocked":
        return 2
    if args.execute and packet.get("execution", {}).get("returncode"):
        return int(packet["execution"]["returncode"])
    if args.fail_on_deny and decision == "DENY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
