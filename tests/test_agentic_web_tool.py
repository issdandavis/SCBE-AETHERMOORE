#!/usr/bin/env python3
"""Tests for scripts/agentic_web_tool.py browser + fallback behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.agentic_web_tool import (
    _http_fetch,
    _http_fetch_html,
    _save_capture,
    _search_duckduckgo,
    _capture_with_fallback,
    CaptureResult,
)


def test_http_fetch_parses_title_and_links(monkeypatch):
    html = """
    <html>
      <head><title>Test Page</title></head>
      <body>
        <a href="https://a.com">A</a>
        <a href="https://b.com">B</a>
      </body>
    </html>
    """

    def fake_http_fetch_html(
        url: str,
        timeout: int = 25,
        *,
        intent: str = "agentic",
        action: str = "fetch",
    ):
        return 200, html

    monkeypatch.setattr("scripts.agentic_web_tool._http_fetch_html", fake_http_fetch_html)
    result = _http_fetch("https://example.com")
    assert result.title == "Test Page"
    assert result.status_code == 200
    assert result.method == "http"
    assert len(result.links) == 2
    assert result.links[0]["href"] == "https://a.com"


def test_save_capture_writes_artifacts(tmp_path):
    result = CaptureResult(
        url="https://example.com",
        title="Example",
        status_code=200,
        text_snippet="hello",
        links=[{"href": "https://example.com/x", "text": "x"}],
        method="http",
    )
    path = _save_capture(tmp_path, result)
    assert path.exists()
    assert path.suffix == ".json"
    data = path.read_text(encoding="utf-8")
    assert '"status_code": 200' in data
    assert '"result_count"' not in data


def test_capture_with_fallback_playwright_success(monkeypatch, tmp_path):
    async def fake_playwright_capture(
        url: str,
        output_dir: Path,
        timeout_ms: int = 30000,
        *,
        intent: str = "agentic",
    ):
        return CaptureResult(
            url=url,
            title="ok",
            status_code=200,
            text_snippet="x",
            links=[],
            method="playwright",
            screenshot_path="x.png",
        )

    monkeypatch.setattr("scripts.agentic_web_tool._playwright_capture", fake_playwright_capture)
    result = _capture_with_fallback("https://example.com", tmp_path, engine="playwright")
    assert result.method == "playwright"
    assert result.screenshot_path == "x.png"


def test_capture_with_fallback_playwright_fallback_to_http(monkeypatch, tmp_path):
    async def fake_playwright_capture(
        url: str,
        output_dir: Path,
        timeout_ms: int = 30000,
        *,
        intent: str = "agentic",
    ):
        raise RuntimeError("pw fail")

    calls: dict[str, Any] = {}

    def fake_http_fetch(
        url: str,
        timeout: int = 25,
        *,
        intent: str = "agentic",
        action: str = "fetch",
    ):
        calls["intent"] = intent
        calls["action"] = action
        return CaptureResult(
            url=url,
            title="fallback",
            status_code=200,
            text_snippet="fallback text",
            links=[],
            method="http",
        )

    monkeypatch.setattr("scripts.agentic_web_tool._playwright_capture", fake_playwright_capture)
    monkeypatch.setattr("scripts.agentic_web_tool._http_fetch", fake_http_fetch)
    result = _capture_with_fallback("https://example.com", tmp_path, engine="playwright")
    assert result.method == "http-fallback"
    assert result.warning == "playwright_failed: pw fail"
    assert calls["intent"] == "agentic"
    assert calls["action"] == "playwright_fallback"


def test_capture_with_fallback_forwards_intent_to_http_fetch_on_fallback(monkeypatch, tmp_path):
    async def fake_playwright_capture(
        url: str,
        output_dir: Path,
        timeout_ms: int = 30000,
        *,
        intent: str = "agentic",
    ):
        raise RuntimeError("playwright down")

    intents: dict[str, Any] = {}

    def fake_http_fetch(
        url: str,
        timeout: int = 25,
        *,
        intent: str = "agentic",
        action: str = "fetch",
    ):
        intents["value"] = intent
        intents["action"] = action
        return CaptureResult(
            url=url,
            title="fallback-intent",
            status_code=200,
            text_snippet="fallback",
            links=[],
            method="http",
        )

    monkeypatch.setattr("scripts.agentic_web_tool._playwright_capture", fake_playwright_capture)
    monkeypatch.setattr("scripts.agentic_web_tool._http_fetch", fake_http_fetch)
    result = _capture_with_fallback(
        "https://example.com",
        tmp_path,
        engine="playwright",
        intent="proof-of-work",
    )
    assert result.method == "http-fallback"
    assert intents["value"] == "proof-of-work"
    assert intents["action"] == "playwright_fallback"
    assert result.title == "fallback-intent"


def test_search_duckduckgo_parse(monkeypatch):
    html = """
    <a class="result__a" href="https://duck1.com">Result 1</a>
    <a class="result__a" href="https://duck2.com">Result 2</a>
    """

    def fake_http_fetch_html(
        url: str,
        timeout: int = 25,
        *,
        intent: str = "agentic",
        action: str = "fetch",
    ):
        return 200, html

    monkeypatch.setattr("scripts.agentic_web_tool._http_fetch_html", fake_http_fetch_html)
    results = _search_duckduckgo("query", max_results=1)
    assert len(results) == 1
    assert results[0]["url"] == "https://duck1.com"
