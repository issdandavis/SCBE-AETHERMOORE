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
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts.system.scbe_tool_context import evaluate_tool_context
except ModuleNotFoundError:  # Direct script execution from scripts/system.
    from scbe_tool_context import evaluate_tool_context

SCHEMA_VERSION = "scbe.hook_router.v2"
AGENTHOOK_SCHEMA_VERSION = 1
AGENTHOOK_SPEC_VERSION = "0.2-draft"
AGENTHOOK_SOURCE = "scbe-hook-router"
CHAIN_GENESIS = "0" * 64
DEFAULT_DECISION = "allow"

SECRET_KEY_RE = re.compile(r"(token|secret|password|passwd|api[_-]?key|bearer|authorization|credential)", re.I)
SECRET_VALUE_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{12,}|" r"hf_[A-Za-z0-9_]{12,}|xox[baprs]-[A-Za-z0-9-]{12,})"
)

HIGH_RISK_COMMAND_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[^\n\r;]*[fd])\b", re.I),
        "destructive git operation",
    ),
    (
        re.compile(r"\bRemove-Item\b[^\n\r;]*\s-(Recurse|r)\b[^\n\r;]*\s-(Force|f)\b", re.I),
        "recursive forced delete",
    ),
    (re.compile(r"\brm\s+-[^\n\r;]*r[^\n\r;]*f\b", re.I), "recursive forced delete"),
    (re.compile(r"\b(del|erase)\b[^\n\r;]*\s/(s|q)\b", re.I), "recursive delete"),
    (
        re.compile(r"\b(format|diskpart|bcdedit)\b", re.I),
        "disk/system mutation command",
    ),
    (
        re.compile(r"\b(npm|pnpm|yarn)\s+publish\b|\bpython\s+-m\s+twine\s+upload\b", re.I),
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
        return {"_raw_stdin_sha256": hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()}
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


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    """Serialize receipt writers on Windows and POSIX without a dependency."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _canonical_event_hash(event: dict[str, Any]) -> str:
    canonical = json.loads(json.dumps(event))
    canonical.get("metadata", {}).get("scbe", {}).pop("event_hash", None)
    payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_chain_state(path: Path) -> tuple[int, str]:
    if not path.exists():
        return 0, CHAIN_GENESIS
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            scbe = event["metadata"]["scbe"]
            return int(scbe["sequence"]), str(scbe["event_hash"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return 0, CHAIN_GENESIS


def _append_chained_jsonl(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with _exclusive_lock(lock_path):
        sequence, previous_hash = _last_chain_state(path)
        scbe = event.setdefault("metadata", {}).setdefault("scbe", {})
        scbe["sequence"] = sequence + 1
        scbe["previous_event_hash"] = previous_hash
        scbe["event_hash"] = _canonical_event_hash(event)
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return event


def verify_receipt_chain(path: Path) -> dict[str, Any]:
    """Verify order and hashes without trusting the final digest alone."""

    previous_hash = CHAIN_GENESIS
    expected_sequence = 1
    errors: list[str] = []
    count = 0
    if not path.exists():
        return {"valid": True, "events": 0, "head": CHAIN_GENESIS, "errors": []}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        try:
            event = json.loads(line)
            scbe = event["metadata"]["scbe"]
            sequence = int(scbe["sequence"])
            recorded_previous = str(scbe["previous_event_hash"])
            recorded_hash = str(scbe["event_hash"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"line {line_number}: malformed receipt ({type(error).__name__})")
            continue
        if sequence != expected_sequence:
            errors.append(f"line {line_number}: expected sequence {expected_sequence}, got {sequence}")
        if recorded_previous != previous_hash:
            errors.append(f"line {line_number}: previous hash mismatch")
        calculated_hash = _canonical_event_hash(event)
        if recorded_hash != calculated_hash:
            errors.append(f"line {line_number}: event hash mismatch")
        previous_hash = recorded_hash
        expected_sequence = sequence + 1
    return {"valid": not errors, "events": count, "head": previous_hash, "errors": errors}


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
    tool_input = _tool_input(payload)
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def _tool_input(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("tool_input")
    if not isinstance(value, dict):
        value = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    return value


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _optional_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _agenthook_event_type(event: str) -> str:
    aliases = {
        "Stop": "SessionEnd",
        "SubagentStart": "AgentHandoff",
        "SubagentStop": "AgentHandoff",
    }
    candidate = aliases.get(event, event)
    return candidate if re.fullmatch(r"[A-Z][A-Za-z0-9]*", candidate or "") else "UnknownEvent"


def _evidence_phase(event: str) -> str:
    if event in {"PreToolUse", "UserPromptSubmit", "PreLLMCall"}:
        return "pre_commit"
    if event in {"PostToolUse", "PostLLMCall", "ModelResponse", "Stop", "SessionEnd", "ErrorOccurred"}:
        return "post_hoc"
    return "observational"


def _normalized_tool_fields(
    root: Path,
    payload: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    """Derive conservative portable hints while preserving the native tool call."""

    explicit = {
        key: payload[key]
        for key in ("action", "resource_kind", "resource", "resource_scope", "operation_risk")
        if key in payload and payload[key] is not None
    }
    if explicit:
        return _scrub(explicit)

    tool_name = str(payload.get("tool_name") or payload.get("tool") or "").lower()
    tool_input = _tool_input(payload)
    command = _command_from_tool(payload)
    fields: dict[str, Any] = {}

    if command or any(word in tool_name for word in ("shell", "exec", "command", "terminal")):
        fields.update(
            action="execute",
            resource_kind="shell",
            resource={
                "cwd": str(payload.get("cwd") or root),
                "command_sha256": hashlib.sha256(command.encode("utf-8", "replace")).hexdigest(),
            },
            resource_scope="workspace",
        )
    else:
        action = next(
            (word for word in ("delete", "publish", "write", "edit", "read", "search", "query", "send", "open") if word in tool_name),
            None,
        )
        if action:
            fields["action"] = action
        target = next(
            (
                tool_input[key]
                for key in ("path", "file_path", "directory", "url", "uri", "repo", "repository")
                if isinstance(tool_input.get(key), str) and tool_input[key]
            ),
            None,
        )
        if target:
            fields["resource"] = _scrub(target)
            is_url = str(target).startswith(("http://", "https://"))
            fields["resource_kind"] = "url" if is_url else ("directory" if "directory" in tool_input else "file")
            fields["resource_scope"] = "public_web" if is_url else "workspace"

    reason_text = " ".join(reasons).lower()
    if "exfiltration" in reason_text:
        fields["operation_risk"] = "external_transfer"
    elif "publish" in reason_text or "deploy" in reason_text:
        fields["operation_risk"] = "publication"
    elif reasons:
        fields["operation_risk"] = "destructive_write"
    elif fields.get("action") in {"write", "edit", "delete"}:
        fields["operation_risk"] = "write"
    return fields


def _classify_prompt(prompt: str) -> dict[str, Any]:
    lowered = prompt.lower()
    labels: list[str] = []
    if any(word in lowered for word in ("delete", "remove", "clean", "space", "offload")):
        labels.append("filesystem-risk")
    if any(word in lowered for word in ("push", "merge", "publish", "deploy", "release")):
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
    root: Path,
    event: str,
    payload: dict[str, Any],
    decision: str,
    reasons: list[str],
    tool_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    git_state = _git_state(root)
    event_type = _agenthook_event_type(event)
    receipt: dict[str, Any] = {
        "schema_version": AGENTHOOK_SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": _utc_timestamp(),
        "source": AGENTHOOK_SOURCE,
        "evidence_phase": _evidence_phase(event),
        "metadata": {
            "publisher_id": "com.aethermoore.scbe.hookrouter",
            "scbe": {
                "schema_version": SCHEMA_VERSION,
                "agenthook_spec": AGENTHOOK_SPEC_VERSION,
                "native_event": event,
                "cwd": str(Path(str(payload.get("cwd") or root)).resolve()),
                "repo_root": str(root),
                "git": git_state,
                "decision": decision,
                "reasons": reasons,
                "native_payload": _scrub(payload),
            },
        },
    }
    agent_id = _optional_text(payload, "agent_id", "agentId") or os.environ.get("SCBE_AGENT_ID")
    session_id = _optional_text(payload, "session_id", "sessionId", "conversation_id") or os.environ.get(
        "SCBE_SESSION_ID"
    )
    correlation_id = _optional_text(payload, "correlation_id", "correlationId", "run_id")
    if agent_id:
        receipt["agent_id"] = agent_id
    if session_id:
        receipt["session_id"] = session_id
    if correlation_id:
        receipt["correlation_id"] = correlation_id
    if event_type in {"PreToolUse", "PostToolUse"}:
        receipt["tool_name"] = str(payload.get("tool_name") or payload.get("tool") or "unknown")
        receipt["tool_input"] = _scrub(_tool_input(payload))
        normalized = _normalized_tool_fields(root, payload, reasons)
        receipt.update(normalized)
        receipt["metadata"]["scbe"]["tool_context"] = tool_context or evaluate_tool_context(payload, normalized)
    return receipt


def _session_context(root: Path, receipt: dict[str, Any]) -> str:
    git_state = receipt["metadata"]["scbe"]["git"]
    state = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": receipt["timestamp"],
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


def handle_event(event: str, payload: dict[str, Any], root: Path) -> tuple[int, dict[str, Any], bool]:
    event = event or str(payload.get("hook_event_name") or "Unknown")
    decision = DEFAULT_DECISION
    reasons: list[str] = []
    tool_context: dict[str, Any] | None = None

    if event == "UserPromptSubmit":
        prompt = str(payload.get("user_prompt") or "")
        classification = _classify_prompt(prompt)
        reasons = list(classification["labels"])
        decision = classification["risk"]
    elif event == "PreToolUse":
        decision, reasons = _classify_tool(payload)
        normalized = _normalized_tool_fields(root, payload, reasons)
        tool_context = evaluate_tool_context(payload, normalized)
        if tool_context["enforcement_requested"] and not tool_context["policy_eligible"]:
            decision = "deny"
            reasons.append(f"capability gate: {tool_context['admission_hint']}")
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

    receipt = _receipt(root, event, payload, decision, reasons, tool_context)
    _append_chained_jsonl(root / ".scbe" / "ops" / "tool_receipts.jsonl", receipt)

    if event == "SessionStart":
        return 0, {"additionalContext": _session_context(root, receipt)}, True

    if event == "PreCompact":
        _write_json(root / ".scbe" / "session" / "compact_state.json", receipt)
        return (
            0,
            {"additionalContext": "SCBE compact state saved to .scbe/session/compact_state.json"},
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
                "systemMessage": "SCBE hook bridge blocked tool use: " + "; ".join(reasons),
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
    parser = argparse.ArgumentParser(description="Route Codex/Claude hook events through SCBE local policy")
    parser.add_argument(
        "event",
        nargs="?",
        default="",
        help="Hook event name, e.g. SessionStart or PreToolUse",
    )
    parser.add_argument("--repo-root", default="", help="Override SCBE repo root")
    parser.add_argument(
        "--verify-log",
        action="store_true",
        help="Verify the local hash-linked receipt log and exit",
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else _repo_root()
    if args.verify_log:
        report = verify_receipt_chain(root / ".scbe" / "ops" / "tool_receipts.jsonl")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["valid"] else 1
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
