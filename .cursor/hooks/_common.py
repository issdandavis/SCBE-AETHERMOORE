#!/usr/bin/env python
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence


AUDIT_DIR = ".cursor/logs/hooks"
AUDIT_PATH = os.path.join(AUDIT_DIR, "events.jsonl")
SUMMARY_PATH = os.path.join(AUDIT_DIR, "summaries.jsonl")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_payload() -> Dict[str, Any]:
    raw = ""
    try:
        import sys

        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def print_json(obj: Dict[str, Any]) -> None:
    import sys

    sys.stdout.write(json.dumps(obj, ensure_ascii=True))


def allow(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response: Dict[str, Any] = {"permission": "allow"}
    if extra:
        response.update(extra)
    return response


def ask(user_message: str, agent_message: Optional[str] = None) -> Dict[str, str]:
    response = {"permission": "ask", "user_message": user_message}
    if agent_message:
        response["agent_message"] = agent_message
    return response


def deny(user_message: str, agent_message: Optional[str] = None) -> Dict[str, str]:
    response = {"permission": "deny", "user_message": user_message}
    if agent_message:
        response["agent_message"] = agent_message
    return response


def append_jsonl(path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")


def write_event(event_name: str, payload: Dict[str, Any], extras: Optional[Dict[str, Any]] = None) -> None:
    record: Dict[str, Any] = {
        "ts": now_iso(),
        "event": event_name,
        "payload_preview": compact_payload(payload, max_chars=1200),
    }
    if extras:
        record.update(extras)
    append_jsonl(AUDIT_PATH, record)


def write_summary(summary_name: str, payload: Dict[str, Any], extras: Optional[Dict[str, Any]] = None) -> None:
    record: Dict[str, Any] = {
        "ts": now_iso(),
        "summary": summary_name,
        "payload_preview": compact_payload(payload, max_chars=1000),
    }
    if extras:
        record.update(extras)
    append_jsonl(SUMMARY_PATH, record)


def first_str(payload: Dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def nested_str(payload: Dict[str, Any], parent: str, key: str) -> str:
    value = payload.get(parent)
    if isinstance(value, dict):
        nested = value.get(key)
        if isinstance(nested, str):
            return nested
    return ""


def nested_any(payload: Dict[str, Any], path: Sequence[str]) -> Any:
    cur: Any = payload
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def safe_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


def tool_name(payload: Dict[str, Any]) -> str:
    candidates = [
        first_str(payload, ("tool_name", "tool", "name")),
        nested_str(payload, "arguments", "tool_name"),
        safe_str(nested_any(payload, ("tool", "name"))),
    ]
    for value in candidates:
        if value:
            return value
    return ""


def pick_first(payload: Dict[str, Any], candidates: Sequence[Sequence[str]]) -> str:
    for path in candidates:
        value = nested_any(payload, path)
        text = safe_str(value).strip()
        if text:
            return text
    return ""


def gather_strings(node: Any, acc: List[str], depth: int = 0) -> None:
    if depth > 4:
        return
    if isinstance(node, str):
        if node:
            acc.append(node)
        return
    if isinstance(node, dict):
        for value in node.values():
            gather_strings(value, acc, depth + 1)
        return
    if isinstance(node, list):
        for value in node:
            gather_strings(value, acc, depth + 1)


def compact_payload(payload: Dict[str, Any], max_chars: int = 1000) -> str:
    parts: List[str] = []
    gather_strings(payload, parts)
    merged = " | ".join(parts)
    if len(merged) <= max_chars:
        return merged
    return merged[:max_chars] + "...[truncated]"


def bool_from_payload(payload: Dict[str, Any], keys: Sequence[str]) -> bool:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            return value
    return False
