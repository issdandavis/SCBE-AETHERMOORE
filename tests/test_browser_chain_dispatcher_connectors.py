"""Connector/function wiring tests for browser_chain_dispatcher."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.system.browser_chain_dispatcher as dispatcher_mod
from scripts.system.browser_chain_dispatcher import BrowserChainDispatcher, build_default_fleet


def _dispatcher() -> BrowserChainDispatcher:
    dispatcher = BrowserChainDispatcher()
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    return dispatcher


def test_provider_mesh_status_shape():
    dispatcher = _dispatcher()
    status = dispatcher.get_provider_mesh_status()
    assert "claude_code" in status
    assert "groq" in status
    assert "cerebras" in status
    assert "google_ai" in status
    assert "grok_xai" in status
    assert "huggingface" in status
    assert "ollama_local" in status
    assert "summary" in status
    assert "ready_count" in status["summary"]


def test_domain_connection_plan_github_has_channel_data():
    dispatcher = _dispatcher()
    plan = dispatcher.get_domain_connection_plan("github.com", task_type="api sync")
    assert plan["service"] in ("GitHub", "github.com")
    assert isinstance(plan["available_channels"], list)
    assert plan["recommended_channel"] in {"api", "cli", "browser"}
    assert "missing_env_vars" in plan


def test_assign_task_includes_connection_plan_and_provider_mesh():
    dispatcher = _dispatcher()
    result = dispatcher.assign_task("github.com", "api sync")
    assert result["ok"] is True
    assert "connection_plan" in result
    assert "provider_mesh" in result
    assert result["connection_channel"] in {"api", "cli", "browser"}


def test_strict_connectivity_blocks_unknown_domain():
    dispatcher = _dispatcher()
    result = dispatcher.assign_task("unknown.invalid", "navigate", strict_connectivity=True)
    assert result["ok"] is False
    assert result["error"] == "connector_not_ready"
    assert "connection_plan" in result


def test_provider_mesh_uses_secret_store_fallback(monkeypatch):
    dispatcher = _dispatcher()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    def _fake_pick_secret(*names: str):
        if "GROQ_API_KEY" in names:
            return "GROQ_API_KEY", "gsk-test-secret"
        return "", ""

    monkeypatch.setattr(dispatcher_mod, "pick_secret", _fake_pick_secret)
    status = dispatcher.get_provider_mesh_status()
    assert status["groq"]["ready"] is True
    assert "GROQ_API_KEY" in status["groq"]["active_secret_vars"]
