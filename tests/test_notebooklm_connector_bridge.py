from __future__ import annotations

from urllib.parse import urlparse

import pytest

pytest.importorskip("httpx", reason="httpx is required for connector bridge tests")

from src.fleet.connector_bridge import ConnectorBridge, ConnectorCapability


def test_notebooklm_connector_registered() -> None:
    bridge = ConnectorBridge()
    infos = {info.platform: info for info in bridge.list_connectors()}
    assert "notebooklm" in infos
    assert "automations" in infos
    caps = infos["notebooklm"].capabilities
    assert ConnectorCapability.CREATE in caps
    assert ConnectorCapability.UPDATE in caps
    assert ConnectorCapability.SEARCH in caps


@pytest.mark.asyncio
async def test_notebooklm_create_notebook_routes_to_script(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = ConnectorBridge()
    seen: dict[str, list[str]] = {}

    async def _fake_runner(args: list[str]) -> dict:
        seen["args"] = args
        return {
            "ok": True,
            "action": "create-notebook",
            "notebook_url": "https://notebooklm.google.com/notebook/demo-id",
        }

    monkeypatch.setattr(bridge, "_run_notebooklm_connector", _fake_runner)

    result = await bridge.execute(
        "notebooklm",
        "create_notebook",
        {
            "session_id": "9",
            "title": "Deep Research Alpha",
            "workspace_url": "https://notebooklm.google.com/",
            "timeout_ms": 15000,
        },
    )
    assert result.success is True
    assert "--action" in seen["args"]
    assert "create-notebook" in seen["args"]
    assert "--title" in seen["args"]
    assert "Deep Research Alpha" in seen["args"]


@pytest.mark.asyncio
async def test_notebooklm_add_source_requires_required_fields() -> None:
    bridge = ConnectorBridge()
    result = await bridge.execute("notebooklm", "add_source_url", {})
    assert result.success is False
    assert "source_url is required" in result.error


@pytest.mark.asyncio
async def test_notebooklm_seed_notebooks_passes_source_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = ConnectorBridge()
    seen: dict[str, list[str]] = {}

    async def _fake_runner(args: list[str]) -> dict:
        seen["args"] = args
        return {"ok": True, "action": "seed-notebooks", "count": 2}

    monkeypatch.setattr(bridge, "_run_notebooklm_connector", _fake_runner)

    result = await bridge.execute(
        "notebooklm",
        "seed_notebooks",
        {
            "session_id": "1",
            "count": 2,
            "name_prefix": "Auto Research",
            "source_urls": ["https://arxiv.org", "https://example.com/report"],
        },
    )
    assert result.success is True
    assert seen["args"].count("--source-url") == 2
    seen_hosts = {(urlparse(arg).hostname or "") for arg in seen["args"] if urlparse(arg).scheme == "https"}
    assert "arxiv.org" in seen_hosts
    assert "example.com" in seen_hosts


@pytest.mark.asyncio
async def test_notebooklm_resolve_routes_action(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = ConnectorBridge()
    seen: dict[str, list[str]] = {}

    async def _fake_runner(args: list[str]) -> dict:
        seen["args"] = args
        return {
            "ok": True,
            "action": "resolve-notebook",
            "notebook_url": "https://notebooklm.google.com/notebook/demo-id",
        }

    monkeypatch.setattr(bridge, "_run_notebooklm_connector", _fake_runner)

    result = await bridge.execute("notebooklm", "resolve_notebook", {"title": "Hydra Research 01"})
    assert result.success is True
    assert "resolve-notebook" in seen["args"]
    assert "--title" in seen["args"]


@pytest.mark.asyncio
async def test_automation_connector_posts_to_local_hub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCBE_AUTOMATIONS_URL", "http://127.0.0.1:8001/v1/automations/emit")
    bridge = ConnectorBridge()
    seen: dict[str, object] = {}

    async def _fake_post(url: str, payload: dict[str, object]) -> dict[str, object]:
        seen["url"] = url
        seen["payload"] = payload
        return {"status_code": 200, "response": {"ok": True}}

    monkeypatch.setattr(bridge, "_post_json", _fake_post)

    result = await bridge.execute(
        "automations",
        "trigger",
        {"event": "lead.created", "payload": {"lead_id": "demo"}},
    )

    assert result.success is True
    assert seen["url"] == "http://127.0.0.1:8001/v1/automations/emit"
    assert seen["payload"] == {"event": "lead.created", "payload": {"lead_id": "demo"}}


@pytest.mark.asyncio
async def test_automation_connector_requires_event() -> None:
    bridge = ConnectorBridge()
    result = await bridge.execute("automations", "trigger", {"payload": {"lead_id": "demo"}})
    assert result.success is False
    assert "event is required" in result.error
