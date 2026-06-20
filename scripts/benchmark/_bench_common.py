#!/usr/bin/env python3
"""Shared utilities for SCBE benchmark adapters.

Provides: SHA-256 receipt chaining, OpenAI-compatible model calls, namespace helpers.
All other adapters import from here to avoid duplicating the chain implementation.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

# ── Hashing ────────────────────────────────────────────────────────────────────


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ── Receipt chaining ───────────────────────────────────────────────────────────


def make_receipt(
    case_id: str,
    label: str,
    expected: str | None,
    got: str | None,
    extra: dict[str, Any],
    correct: bool,
    prev_hash: str,
    ts: str,
    *,
    near_miss: bool = False,
) -> dict[str, Any]:
    """Build a chained receipt for one eval case.

    `label` is a short human-readable description (question text, scenario title, etc.)
    `expected`/`got` are string identifiers being compared (tool names, decisions, etc.)
    `extra` carries adapter-specific detail (args, turns, category, etc.)
    """
    payload = json.dumps(
        {"case_id": case_id, "expected": expected, "got": got, "correct": correct, "ts": ts},
        sort_keys=True,
    )
    receipt_hash = _sha256(prev_hash + payload)
    return {
        "case_id": case_id,
        "label": label[:160] + ("..." if len(label) > 160 else ""),
        "expected": expected,
        "got": got,
        "correct": correct,
        "near_miss": near_miss,
        "ts": ts,
        "prev_hash": prev_hash,
        "receipt_hash": receipt_hash,
        **extra,
    }


def same_namespace(a: str, b: str) -> bool:
    """True when two hyphen-delimited tool names share the same prefix segment."""
    return a.split("-")[0] == b.split("-")[0]


# ── OpenAI-compatible model call ───────────────────────────────────────────────


def call_model_once(
    endpoint: str,
    model: str,
    messages: list[dict[str, Any]],
    tool_schemas: list[dict[str, Any]],
    *,
    timeout: int = 60,
    auth_token: str | None = None,
    max_tokens: int = 512,
    temperature: float = 0.0,
) -> tuple[str | None, dict[str, Any], str, str | None]:
    """Single model call with tool schemas.

    Returns (tool_name, tool_args, raw_snippet, text_content).
    text_content is the assistant's text response when no tool is called.
    Raises ConnectionError on network/auth failure.
    """
    try:
        import openai  # type: ignore[import]
    except ImportError as exc:
        raise ConnectionError("openai SDK not installed; run: pip install openai") from exc

    try:
        client = openai.OpenAI(
            base_url=endpoint.rstrip("/"),
            api_key=auth_token or "no-key",
            timeout=timeout,
        )
        tools_payload = [{"type": "function", "function": s} for s in tool_schemas]
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_payload,
            tool_choice="auto",
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:  # noqa: BLE001
        raise ConnectionError(f"Model call failed ({endpoint}): {exc}") from exc

    message = resp.choices[0].message
    raw_snippet = json.dumps(message.model_dump(), default=str)[:600]
    text_content = message.content or None

    tool_calls = message.tool_calls or []
    if tool_calls:
        fn = tool_calls[0].function
        called_name = fn.name
        raw_args = fn.arguments or "{}"
        try:
            called_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            called_args = {"_raw": raw_args}
        return called_name, called_args, raw_snippet, text_content

    return None, {}, raw_snippet, text_content


# ── Rate-limit courtesy ────────────────────────────────────────────────────────


def rate_sleep(ms: int = 50) -> None:
    time.sleep(ms / 1000.0)
