#!/usr/bin/env python3
"""SCBE Secret Store — shared credential access and text sanitization utilities.

Provides:
- get_secret / set_secret: env-first credential lookup with fallback to local store
- redact_sensitive_text: strip API keys, tokens, passwords from strings
- sensitive_fingerprint: PBKDF2-based fingerprint for audit without exposing values
- mask_value: show only last 4 chars of a secret
- read_json / write_json: safe JSON I/O with path validation
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SENSITIVE_METADATA_ITERATIONS = 120_000

_SENSITIVE_TEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Authorization:\s*Bearer\s+[^\s]+", re.IGNORECASE), "Authorization: Bearer [redacted]"),
    (re.compile(r"\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+['\"]?", re.IGNORECASE), r"\1=[redacted]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[redacted]"),
    (re.compile(r"\bhf_[A-Za-z0-9_-]{8,}\b"), "[redacted]"),
    (re.compile(r"\bghp_[A-Za-z0-9_-]{8,}\b"), "[redacted]"),
    (re.compile(r"\bshpat_[0-9A-Fa-f]{8,}\b"), "[redacted]"),
    (re.compile(r"\brk_live_[A-Za-z0-9_-]{8,}\b"), "[redacted]"),
    (re.compile(r"\bxoxe\.[A-Za-z0-9_.-]{8,}\b"), "[redacted]"),
]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SECRETS_DIR = _REPO_ROOT / "config" / "connector_oauth"
_STORE_PATH = _SECRETS_DIR / ".secrets.json"

# ---------------------------------------------------------------------------
# Core: get_secret / set_secret
# ---------------------------------------------------------------------------


def get_secret(name: str, default: str = "") -> str:
    """Return secret value: env var first, then local store, then default."""
    env_val = os.getenv(name, "").strip()
    if env_val:
        return env_val
    store = _load_store()
    entry = store.get(name)
    if isinstance(entry, dict):
        return str(entry.get("value", default)).strip() or default
    if isinstance(entry, str):
        return entry.strip() or default
    return default


def set_secret(name: str, value: str, *, note: str = "", tongue: str | None = None) -> None:
    """Persist secret to local store and set in current process env."""
    store = _load_store()
    entry: dict[str, Any] = {"value": value, "note": note}
    if tongue:
        entry["tongue"] = tongue
    store[name] = entry
    _save_store(store)
    os.environ[name] = value


def _load_store() -> dict[str, Any]:
    if not _STORE_PATH.exists():
        return {}
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_store(store: dict[str, Any]) -> None:
    _SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Text sanitization
# ---------------------------------------------------------------------------


def redact_sensitive_text(text: str | None) -> str:
    """Strip known secret patterns from text for safe logging."""
    value = str(text or "")
    for pattern, replacement in _SENSITIVE_TEXT_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def sensitive_fingerprint(value: str, *, salt_env: str = "SCBE_METADATA_HASH_KEY", salt_default: str = "scbe-metadata") -> str:
    """PBKDF2 fingerprint for audit without exposing the actual value."""
    salt = os.getenv(salt_env, salt_default).encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt, SENSITIVE_METADATA_ITERATIONS)
    return derived.hex()


def mask_value(val: str) -> str:
    """Show only the last 4 characters of a secret."""
    if len(val) <= 4:
        return "****"
    return f"****{val[-4:]}"


def text_metadata(text: str) -> dict[str, Any]:
    """Return audit-safe metadata about a text value."""
    return {
        "present": bool(text),
        "length": len(text),
        "pbkdf2_sha256": sensitive_fingerprint(text) if text else "",
    }


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------


def read_json(path: Path, default: Any = None) -> Any:
    """Read JSON file, returning default on any error."""
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any, *, sanitize: bool = True) -> None:
    """Write JSON to path, optionally sanitizing sensitive keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = sanitize_for_report(payload) if sanitize else payload
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sanitize_for_report(payload: Any) -> Any:
    """Recursively strip sensitive key values from a dict/list for disk or stdout."""
    sensitive_fragments = {
        "api_key", "content", "prompt", "token", "secret", "authorization",
        "x-api-key", "stdout", "stderr", "response", "response_excerpt",
        "raw", "key_value", "alias_value", "password", "credential",
    }
    if isinstance(payload, dict):
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            key_lower = str(key).lower()
            if any(f in key_lower for f in sensitive_fragments) and not (
                key_lower.endswith("_metadata") or key_lower.endswith("_summary")
            ):
                clean[key] = "[redacted]"
            else:
                clean[key] = sanitize_for_report(value)
        return clean
    if isinstance(payload, list):
        return [sanitize_for_report(item) for item in payload]
    return payload
