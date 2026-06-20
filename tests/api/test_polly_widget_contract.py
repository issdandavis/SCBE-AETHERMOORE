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
        "api/polly/chat.js must emit assistant reply under `text:` key — " "widget reads it from there"
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


def test_sidebar_sends_scbe_web_agent_role_packet() -> None:
    """The v2 sidebar should prime Polly with the public SCBE web-agent role."""
    src = _read(ROOT / "docs" / "static" / "polly-sidebar.js")
    assert "POLLY_AGENT_ROLE" in src
    assert re.search(r"role:\s*['\"]scbe-web-agent['\"]", src)
    assert "superpowers:subagent-driven-development" in src
    assert "polly_role: pollyRolePacket()" in src
    assert "agent-task packet" in src


def test_sidebar_has_pre_ai_routes_for_zero_cost_chat() -> None:
    """The visible Polly chat must route useful questions without paid model calls."""
    for filename in ["polly-sidebar.js", "polly-sidebar-agent.js"]:
        src = _read(ROOT / "docs" / "static" / filename)
        assert "function preAiReply" in src
        assert "function preAiFallback" in src
        assert "Pre-AI" in src
        assert "POLLY_ENABLE_BACKEND_CHAT" in src
        assert "POLLY_ENABLE_BROWSER_LLM" in src
        assert "STATIC_ONLY" in src
        assert "staticBackendNotice" in src
        assert "Static Polly commands" in src
        assert "workflow snapshot" in src.lower()
        assert "ai-workflow-snapshot.html" in src
        assert "proof-workbench.html" in src


def test_ai_workflow_snapshot_page_is_static_intake() -> None:
    """The $99 intake page must work without a backend form service."""
    src = _read(ROOT / "docs" / "ai-workflow-snapshot.html")
    assert "$99" in src
    assert "Download intake JSON" in src
    assert "packet_type" in src
    assert "aethermoore_ai_workflow_snapshot_intake_v1" in src
    assert "POLLY_STATIC_ONLY" in src
    assert 'data-polly-static="true"' in src
    assert "fetch(" not in src
    assert "mailto:" not in src
    assert 'action="' not in src


def test_sidebar_has_useful_product_and_agent_starters() -> None:
    """Cold visitors should see starters that route to useful deterministic paths."""
    src = _read(ROOT / "docs" / "static" / "polly-sidebar.js")
    for prompt in [
        "What should I buy if I am new here?",
        "How much is the workflow snapshot?",
        "Make my AI agent safer",
        "Search the web for AI agent governance",
    ]:
        assert prompt in src


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
