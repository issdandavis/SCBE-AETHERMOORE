"""Smoke tests for system browser wrapper wiring."""

from __future__ import annotations

import pytest

from src.browser.headless import PageResult, ResearchReport, SearchResult, ThreatScan
from scripts.system import ai_browser


class _FakeHeadlessBrowser:
    def __init__(self, *_, **__):
        self.closed = False
        self.closed_with = None
        self.stats = {"fetched": 0, "blocked": 0, "errors": 0}
        self._scan = ThreatScan(
            verdict="CLEAN",
            risk_score=0.0,
            prompt_hits=(),
            malware_hits=(),
            reasons=(),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_) -> None:
        return None

    async def close(self):
        self.closed = True

    async def search(self, query: str, num_results: int = 10):
        return [
            SearchResult(
                title="Result A",
                url="https://example.com/a",
                snippet="OK",
                position=1,
                governance_verdict="CLEAN",
                governance_score=0.0,
            ),
        ][:num_results]

    async def fetch(self, url: str, use_playwright: bool = False):
        return PageResult(
            url=url,
            title="Smoke Page",
            text="smoke test",
            scan=self._scan,
            status_code=200,
            elapsed_ms=12.5,
            timestamp="2026-03-01T00:00:00Z",
            fetch_tier="httpx" if not use_playwright else "playwright",
        )

    async def research(self, query: str, depth: int = 3, use_playwright_for_js: bool = False):
        return ResearchReport(
            query=query,
            total_pages=depth,
            clean_pages=depth,
            blocked_pages=0,
            elapsed_ms=33.3,
            timestamp="2026-03-01T00:00:00Z",
            results=[await self.fetch("https://example.com/smoke")],
            search_results=[
                SearchResult(
                    title="Result A",
                    url="https://example.com/a",
                    snippet="OK",
                )
            ],
        )

    async def research_and_store(self, query: str, depth: int = 3, output_dir=None):
        report = await self.research(query, depth=depth)
        report.summary = f"stored:{output_dir}" if output_dir else "stored"
        return report


@pytest.mark.homebrew
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ai_browser_search_smoke(monkeypatch):
    monkeypatch.setattr(ai_browser, "HeadlessBrowser", _FakeHeadlessBrowser)
    payload = await ai_browser.run_cli(["search", "smoke query", "-n", "1"])
    assert payload["command"] == "search"
    assert payload["results"][0]["url"] == "https://example.com/a"
    assert payload["results"][0]["governance_verdict"] == "CLEAN"
    assert payload["governance_score"] == 0.0
    assert any(item.startswith("evidence://search/smoke query?") for item in payload["evidence"])


@pytest.mark.homebrew
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ai_browser_fetch_smoke(monkeypatch):
    monkeypatch.setattr(ai_browser, "HeadlessBrowser", _FakeHeadlessBrowser)
    payload = await ai_browser.run_cli(["fetch", "https://example.com/smoke"])
    assert payload["command"] == "fetch"
    assert payload["result"]["url"] == "https://example.com/smoke"
    assert payload["result"]["scan_verdict"] == "CLEAN"
    assert payload["governance_verdict"] == "CLEAN"
    assert payload["evidence"][0].startswith("evidence://fetch/https://example.com/smoke?")


@pytest.mark.homebrew
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ai_browser_research_smoke(monkeypatch):
    monkeypatch.setattr(ai_browser, "HeadlessBrowser", _FakeHeadlessBrowser)
    payload = await ai_browser.run_cli(["research", "smoke query", "--depth", "2"])
    assert payload["command"] == "research"
    assert payload["report"]["total_pages"] == 2
    assert payload["report"]["clean_pages"] == 2
    assert any(item.startswith("evidence://research/smoke query?") for item in payload["evidence"])
