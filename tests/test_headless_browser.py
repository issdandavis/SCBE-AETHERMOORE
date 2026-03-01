#!/usr/bin/env python3
"""Tests for scripts/headless_browser.py (Playwright headless workflow helpers)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from scripts.browser_autodoor import AutoDoorDecision, AUTODOOR_INTENT
from scripts.headless_browser import (
    Action,
    BrowserResult,
    DEFAULT_TIMEOUT_MS,
    _try_governance_scan,
    parse_args,
    run_cli,
)


class _FakePage:
    def __init__(self):
        self.url = "https://example.com"


class _FakeHeadlessBrowser:
    def __init__(self, *args: Any, **kwargs: Any):
        self.page = _FakePage()
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc: Any):
        return None

    async def start(self):
        return None

    async def stop(self):
        return None

    async def navigate(self, url: str, wait_until: str = "domcontentloaded", *, intent: str | None = None):
        self.calls.append(("navigate", url, wait_until))
        return BrowserResult(action="navigate", success=True, url=url, data={"status": 200, "title": "Example"})

    async def screenshot(self, *args: Any, **kwargs: Any):
        self.calls.append(("screenshot", args, kwargs))
        return BrowserResult(action="screenshot", success=True, url=self.page.url, data={"path": kwargs.get("path"), "full_page": kwargs.get("full_page")})

    async def extract_text(self, selector: str = "body"):
        self.calls.append(("extract_text", selector))
        return BrowserResult(action="extract", success=True, url=self.page.url, data={"text": "hello", "length": 5, "selector": selector})

    async def get_full_text(self):
        self.calls.append(("get_full_text",))
        return BrowserResult(action="text", success=True, url=self.page.url, data={"text": "Hello world", "length": 11})

    async def fill(self, selector: str, value: str):
        self.calls.append(("fill", selector, value))
        return BrowserResult(action="fill", success=True, url=self.page.url, data={"selector": selector, "length": len(value)})

    async def click(self, selector: str):
        self.calls.append(("click", selector))
        return BrowserResult(action="click", success=True, url=self.page.url, data={"selector": selector})

    async def evaluate(self, script: str):
        self.calls.append(("evaluate", script))
        return BrowserResult(action="evaluate", success=True, url=self.page.url, data={"result": "ok"})

    async def save_pdf(self, path: str | None = None):
        self.calls.append(("save_pdf", path))
        return BrowserResult(action="pdf", success=True, url=self.page.url, data={"path": path})


def test_parse_args_defaults():
    args = parse_args(["--url", "https://example.com", "--action", "text"])
    assert args.url == "https://example.com"
    assert args.action == "text"
    assert args.timeout == DEFAULT_TIMEOUT_MS
    assert args.headed is False
    assert args.action in [a.value for a in Action]


@pytest.mark.asyncio
async def test_run_cli_fill_requires_selector_and_value(monkeypatch):
    monkeypatch.setattr("scripts.headless_browser.HeadlessBrowser", _FakeHeadlessBrowser)
    args = parse_args(["--url", "https://example.com", "--action", "fill", "--value", "x"])
    result = await run_cli(args)
    assert result.success is False
    assert result.action == "fill"
    assert "selector" in (result.error or "")
    assert not result.governance


@pytest.mark.asyncio
async def test_run_cli_text_action_uses_no_governance(monkeypatch):
    called = {"govern": False}
    monkeypatch.setattr("scripts.headless_browser.HeadlessBrowser", _FakeHeadlessBrowser)
    result = await run_cli(parse_args(["--url", "https://example.com", "--action", "text"]))
    assert result.success is True
    assert result.action == "text"
    assert result.data["text"] == "Hello world"
    assert not called["govern"]


@pytest.mark.asyncio
async def test_run_cli_text_action_passes_intent_to_door_headers(monkeypatch):
    recorded = {}

    def fake_auto_door(url: str, *, action: str, intent: str, key_map=None, now_ms=None):
        recorded["url"] = url
        recorded["action"] = action
        recorded["intent"] = intent
        return AutoDoorDecision(
            matched_key=True,
            has_secret=True,
            headers={"X-SCBE-Time-Intent": "x", "Authorization": "Bearer xyz"},
            api_key_hint="key-hash",
            context={"action": action},
        )

    class _FakeContext:
        def set_extra_http_headers(self, headers: dict[str, str]):
            recorded["headers"] = headers

    class _DoorPage:
        def __init__(self):
            self.url = "https://example.com"
            self.context = _FakeContext()

        def set_default_timeout(self, *_: Any, **__: Any):
            return None

        def set_default_navigation_timeout(self, *_: Any, **__: Any):
            return None

    class _DoorBrowser(_FakeHeadlessBrowser):
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__()
            self.page = _DoorPage()

        async def navigate(self, url: str, wait_until: str = "domcontentloaded", *, intent: str | None = None):
            recorded["url"] = url
            recorded["action"] = "navigate"
            recorded["intent"] = intent
            if self.page.context:
                self.page.context.set_extra_http_headers(fake_auto_door(url, action="navigate", intent=intent or "agentic").headers)
            return BrowserResult(
                action="navigate",
                success=True,
                url=url,
                data={"status": 200, "title": "Example"},
            )

    monkeypatch.setattr("scripts.headless_browser.build_auto_door_headers", fake_auto_door)
    monkeypatch.setattr("scripts.headless_browser.HeadlessBrowser", _DoorBrowser)

    result = await run_cli(
        parse_args(["--url", "https://example.com", "--action", "text", "--intent", "proof-of-work"])
    )
    assert result.success is True
    assert recorded["url"] == "https://example.com"
    assert recorded["action"] == "navigate"
    assert recorded["intent"] == "proof-of-work"
    assert recorded["headers"]["Authorization"] == "Bearer xyz"


def test_try_governance_scan_returns_none_when_modules_missing(monkeypatch):
    # Ensure the function doesn't hard-fail if governance models are unavailable.
    # Remove any real module and inject nothing.
    monkeypatch.setitem(__import__("sys").modules, "agents.browser.phdm_brain", None)
    assert _try_governance_scan("hello", "https://example.com") is None


def test_try_governance_scan_works_with_fake_phdm(monkeypatch):
    class FakeResult:
        decision = SimpleNamespace(value="ALLOW")
        risk_score = 0.01
        hyperbolic_distance = 0.2
        radius = 0.5
        message = "ok"

    def fake_create_phdm_brain(safe_radius: float = 0.92, dim: int = 16):
        def check_containment(_embedding: Any) -> FakeResult:
            return FakeResult()

        class _Brain:
            def check_containment(self, embedding: Any) -> FakeResult:
                return check_containment(embedding)

        return _Brain()

    fake_mod = SimpleNamespace(create_phdm_brain=fake_create_phdm_brain, SimplePHDM=object)
    monkeypatch.setitem(__import__("sys").modules, "agents.browser.phdm_brain", fake_mod)

    result = _try_governance_scan("hello world", "https://example.com/path")
    assert result is not None
    assert result["decision"] == "ALLOW"
    assert result["risk_score"] == 0.01
    assert result["url_domain"] == "example.com"
