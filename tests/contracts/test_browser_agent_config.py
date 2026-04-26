from __future__ import annotations

import importlib

import pytest


def test_browser_agent_requires_explicit_api_key(monkeypatch) -> None:
    monkeypatch.delenv("SCBE_API_KEY", raising=False)

    import agents.browser_agent as browser_agent

    module = importlib.reload(browser_agent)

    with pytest.raises(RuntimeError, match="SCBE_API_KEY is required"):
        module.SCBEBrowserAgent(agent_name="test-agent", agent_id="agent-001")
