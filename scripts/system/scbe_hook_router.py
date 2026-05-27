"""SCBE hook router for agent harness reflexes.

This script is intentionally small and deterministic. It lets Codex/Claude-style
hooks attach to SCBE without putting policy logic inside a plugin cache:

  hook event -> local classifier -> receipt -> optional allow/deny/context JSON

The router is safe to call with no stdin, malformed stdin, or unknown events. It
never calls an LLM, never uses network, and scrubs secret-shaped values before
writing receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "scbe.hook_router.v1"
DEFAULT_DECISION = "allow"

SECRET_KEY_RE = re.compile(
    r"(token|secret|password|passwd|api[_-]?key|bearer|authorization|credential)", re.I
)
SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{12,}|"
    r"hf_[A-Za-z0-9_]{12,}|xox[baprs]-[A-Za-z0-9-]{12,})"
)

HIGH_RISK_COMMAND_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[^\n\r;]*[fd])\b", re.I),
        "destructive git operation",
    ),
    (
        re.compile(
            r"\bRemove-Item\b[^\n\r;]*\s-(Recurse|r)\b[^\n\r;]*\s-(Force|f)\b", re.I
        ),
        "recursive forced delete",
    ),
    (re.compile(r"\brm\s+-[^\n\r;]*r[^\n\r;]*f\b", re.I), "recursive forced delete"),
    (re.compile(r"\b(del|erase)\b[^\n\r;]*\s/(s|q)\b", re.I), "recursive delete"),
    (
        re.compile(r"\b(format|diskpart|bcdedit)\b", re.I),
        "disk/system mutation command",
    ),
    (
        re.compile(
            r"\b(npm|pnpm|yarn)\s+publish\b|\bpython\s+-m\s+twine\s+upload\b", re.I
        ),
        "package publish",
    ),
    (
        re.compile(r"\bgh\s+release\s+(create|delete)\b|\bgh\s+repo\s+delete\b", re.I),
        "GitHub release/repo mutation",
    ),
    (
        re.compile(r"\b(vercel|railway|netlify)\s+(deploy|remove|delete)\b", re.I),
        "deploy mutation",
    ),
    (
        re.compile(
            r"\b(curl|Invoke-WebRequest|iwr|wget)\b[^\n\r]*(\$env:|%[A-Z_]*(TOKEN|KEY|SECRET)[A-Z_]*%)",
            re.I,
        ),
        "possible secret exfiltration",
    ),
)


def _repo_root() -> Path:
    env_root = os.environ.get("SCBE_REPO_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        root = Path(env_root).expanduser()
        if (root / "package.json").exists():
            return root.resolve()

    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "package.json").exists() and (parent / "src").exists():
            return parent
    return Path.cwd().resolve()


def _read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "_raw_stdin_sha256": hashlib.sha256(
                raw.encode("utf-8", "replace")
            ).hexdigest()
        }
    return parsed if isinstance(parsed, dict) else {"payload": parsed}


def _scrub(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth_limit>"
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            if SECRET_KEY_RE.search(text_key):
                scrubbed[text_key] = "<redacted>"
            else:
                scrubbed[text_key] = _scrub(item, depth=depth + 1)
        return scrubbed
    if isinstance(value, list):
        return [_scrub(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, str):
        value = SECRET_VALUE_RE.sub("<redacted>", value)
        if len(value) > 4000:
            return value[:4000] + "...<truncated>"
        return value
    return value


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, sort_keys=True) + "\n")


def _git_state(root: Path) -> dict[str, Any]:
    def run_git(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except Exception:
            return ""
        return (completed.stdout or "").strip()

    return {
        "branch": run_git("branch", "--show-current") or "unknown",
        "head": run_git("rev-parse", "--short", "HEAD") or "unknown",
        "dirty": bool(run_git("status", "--porcelain")),
    }


def _command_from_tool(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = (
            payload.get("parameters")
            if isinstance(payload.get("parameters"), dict)
            else {}
        )
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def _classify_prompt(prompt: str) -> dict[str, Any]:
    lowered = prompt.lower()
    labels: list[str] = []
    if any(
        word in lowered for word in ("delete", "remove", "clean", "space", "offload")
    ):
        labels.append("filesystem-risk")
    if any(
        word in lowered for word in ("push", "merge", "publish", "deploy", "release")
    ):
        labels.append("release-risk")
    if any(word in lowered for word in ("token", "secret", "key", "credential")):
        labels.append("secrets-risk")
    if any(word in lowered for word in ("test", "benchmark", "verify", "harness")):
        labels.append("verification")
    return {"labels": labels, "risk": "review" if labels else "normal"}


def _classify_tool(payload: dict[str, Any]) -> tuple[str, list[str]]:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    command = _command_from_tool(payload)
    reasons: list[str] = []

    if command:
        for pattern, reason in HIGH_RISK_COMMAND_PATTERNS:
            if pattern.search(command):
                reasons.append(reason)

    if tool_name.lower().endswith("shell_command") and re.search(
        r"\b(public|publish|deploy|delete|reset)\b", command, re.I
    ):
        reasons.append("shell mutation requires explicit DCP path")

    return ("deny" if reasons else DEFAULT_DECISION), reasons


def _receipt(
    root: Path, event: str, payload: dict[str, Any], decision: str, reasons: list[str]
) -> dict[str, Any]:
    git_state = _git_state(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "event": event,
        "generated_at": time.time(),
        "cwd": str(Path(str(payload.get("cwd") or root)).resolve()),
        "repo_root": str(root),
        "git": git_state,
        "decision": decision,
        "reasons": reasons,
        "tool_name": payload.get("tool_name") or payload.get("tool"),
        "payload": _scrub(payload),
    }


def _session_context(root: Path, receipt: dict[str, Any]) -> str:
    git_state = receipt["git"]
    state = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": receipt["generated_at"],
        "repo_root": str(root),
        "git": git_state,
        "receipt_log": str(root / ".scbe" / "ops" / "tool_receipts.jsonl"),
        "compact_state": str(root / ".scbe" / "session" / "compact_state.json"),
    }
    _write_json(root / ".scbe" / "session" / "state.json", state)
    return (
        "<SCBE_HOOK_BRIDGE>\n"
        f"schema={SCHEMA_VERSION}\n"
        f"repo_root={root}\n"
        f"branch={git_state['branch']} head={git_state['head']} dirty={git_state['dirty']}\n"
        "hook_policy=fast_local_receipts; pretool blocks obvious destructive/exfil/publish/deploy commands; "
        "completion still requires explicit verification gates.\n"
        "</SCBE_HOOK_BRIDGE>"
    )


def handle_event(
    event: str, payload: dict[str, Any], root: Path
) -> tuple[int, dict[str, Any], bool]:
    event = event or str(payload.get("hook_event_name") or "Unknown")
    decision = DEFAULT_DECISION
    reasons: list[str] = []

    if event == "UserPromptSubmit":
        prompt = str(payload.get("user_prompt") or "")
        classification = _classify_prompt(prompt)
        reasons = list(classification["labels"])
        decision = classification["risk"]
    elif event == "PreToolUse":
        decision, reasons = _classify_tool(payload)
    elif event in {
        "SessionStart",
        "PostToolUse",
        "PreCompact",
        "PostCompact",
        "Stop",
        "SubagentStart",
        "SubagentStop",
    }:
        decision = DEFAULT_DECISION
    else:
        reasons.append("unknown_event_logged_only")

    receipt = _receipt(root, event, payload, decision, reasons)
    _append_jsonl(root / ".scbe" / "ops" / "tool_receipts.jsonl", receipt)

    if event == "SessionStart":
        return 0, {"additionalContext": _session_context(root, receipt)}, True

    if event == "PreCompact":
        _write_json(root / ".scbe" / "session" / "compact_state.json", receipt)
        return (
            0,
            {
                "additionalContext": "SCBE compact state saved to .scbe/session/compact_state.json"
            },
            True,
        )

    if event == "Stop":
        _write_json(root / ".scbe" / "session" / "final_receipt.json", receipt)
        return (
            0,
            {"decision": "approve", "systemMessage": "SCBE final receipt written."},
            True,
        )

    if event == "PreToolUse" and decision == "deny":
        return (
            2,
            {
                "hookSpecificOutput": {"permissionDecision": "deny"},
                "systemMessage": "SCBE hook bridge blocked tool use: "
                + "; ".join(reasons),
            },
            False,
        )

    if event == "UserPromptSubmit" and reasons:
        return (
            0,
            {"additionalContext": "SCBE prompt route: " + ", ".join(reasons)},
            True,
        )

    return 0, {"continue": True, "suppressOutput": True}, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Route Codex/Claude hook events through SCBE local policy"
    )
    parser.add_argument(
        "event",
        nargs="?",
        default="",
        help="Hook event name, e.g. SessionStart or PreToolUse",
    )
    parser.add_argument("--repo-root", default="", help="Override SCBE repo root")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else _repo_root()
    payload = _read_input()
    code, output, use_stdout = handle_event(args.event, payload, root)
    text = json.dumps(output, ensure_ascii=False)
    if use_stdout:
        print(text)
    else:
        print(text, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
