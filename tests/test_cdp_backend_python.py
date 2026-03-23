from __future__ import annotations

import pytest

from agents.browsers.cdp_backend import CDPBackend


@pytest.mark.asyncio
async def test_navigate_waits_for_ready_state(monkeypatch):
    backend = CDPBackend()
    states = iter(["loading", "interactive"])

    async def fake_send(method, params=None):
        assert method == "Page.navigate"
        assert params == {"url": "https://example.com"}
        return {"frameId": "frame-1", "loaderId": "loader-1"}

    async def fake_execute_script(script):
        assert script == "document.readyState"
        return next(states)

    monkeypatch.setattr(backend, "_send", fake_send)
    monkeypatch.setattr(backend, "execute_script", fake_execute_script)

    result = await backend.navigate("https://example.com")

    assert result["url"] == "https://example.com"
    assert result["frameId"] == "frame-1"
    assert backend.current_url == "https://example.com"


@pytest.mark.asyncio
async def test_navigate_raises_when_cdp_reports_error(monkeypatch):
    backend = CDPBackend()

    async def fake_send(method, params=None):
        return {"errorText": "net::ERR_NAME_NOT_RESOLVED"}

    monkeypatch.setattr(backend, "_send", fake_send)

    with pytest.raises(RuntimeError, match="Navigation failed: net::ERR_NAME_NOT_RESOLVED"):
        await backend.navigate("https://bad.invalid")
