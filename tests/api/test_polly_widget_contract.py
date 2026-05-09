"""Regression test for the Polly widget client-side response-key contract.

Prior incident (2026-05-09, fixed in PR #1522): the widget at
docs/static/polly-hf-chat.js read the assistant reply from `data.response`,
but `/v1/polly/chat` (both the Vercel JS handler in api/polly/chat.js and
the Python polly_routes.py) returns it under `data.text`. Every chat reply
on the live aethermoore.com/SCBE-AETHERMOORE/hire.html surfaced as
"Request failed" — the bug was silent because Pages hadn't auto-deployed
the widget since 2026-03 (separately fixed in PR #1523).

This test locks the contract from both sides:
- Server side: api/polly/chat.js MUST return the assistant reply under `text:`
- Client side: docs/static/polly-hf-chat.js AND kindle-app/www/static/...
  MUST accept `data.text` (with optional `data.response` fallback for any
  legacy backend)

If a future refactor swaps either side without the other, this test fails
and the bug is caught at PR time instead of after deploy.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    assert path.exists(), f"missing widget source: {path}"
    return path.read_text(encoding="utf-8")


def test_chat_handler_emits_assistant_text_under_text_key() -> None:
    """The Vercel JS chat handler must return the assistant reply as `text:`."""
    src = _read(ROOT / "api" / "polly" / "chat.js")
    # Look for at least one `text:` literal in the response payload position.
    # (The handler builds replies in multiple branches — research, commerce,
    # llm fallback, offline-router. All must use `text` as the key.)
    assert re.search(r"\btext:\s*", src), (
        "api/polly/chat.js must emit assistant reply under `text:` key — "
        "widget reads it from there"
    )


def test_widget_accepts_text_key_from_chat_response() -> None:
    """docs/static/polly-hf-chat.js must accept `data.text` from /v1/polly/chat.

    Reading only `data.response` (the prior bug) silently breaks the chat —
    every reply throws "Polly returned no assistant text" and renders as
    "Request failed" to the user.
    """
    src = _read(ROOT / "docs" / "static" / "polly-hf-chat.js")
    assert "data.text" in src, (
        "docs/static/polly-hf-chat.js must read the assistant reply from "
        "`data.text` — `/v1/polly/chat` (both Vercel JS and Python) returns "
        "the assistant message under that key"
    )


def test_kindle_widget_accepts_text_key_from_chat_response() -> None:
    """kindle-app PWA widget must accept the same response shape."""
    src = _read(ROOT / "kindle-app" / "www" / "static" / "polly-hf-chat.js")
    assert "data.text" in src, (
        "kindle-app/www/static/polly-hf-chat.js must read assistant reply "
        "from `data.text` (mirror of docs/static/polly-hf-chat.js)"
    )


def test_widget_does_not_only_read_response_key() -> None:
    """Catch the exact prior-bug pattern: ONLY reading `data.response`.

    `data.text || data.response` is fine (text-first with legacy fallback).
    Just `data.response` was the bug — reject that pattern explicitly.
    """
    for path in [
        ROOT / "docs" / "static" / "polly-hf-chat.js",
        ROOT / "kindle-app" / "www" / "static" / "polly-hf-chat.js",
    ]:
        src = _read(path)
        # Find the requestScbePolly function body
        match = re.search(
            r"function requestScbePolly[\s\S]+?\n\s{2}\}\s*\n",
            src,
        )
        assert match, f"could not locate requestScbePolly in {path.name}"
        body = match.group(0)
        # Must reference data.text — bare data.response is the bug
        if "data.text" not in body:
            raise AssertionError(
                f"{path.name}: requestScbePolly does not read `data.text` — "
                f"this was the prior bug (PR #1522). Use `data.text || data.response`."
            )
