from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import free_llm_routes


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(free_llm_routes.free_llm_router)
    monkeypatch.setattr(free_llm_routes, "VALID_API_KEYS", {"test-key": "tester"})
    return TestClient(app)


def test_free_llm_provider_registry_lists_default_open_lanes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    client = _client(monkeypatch)

    response = client.get("/hydra/free-llm/providers", headers={"x-api-key": "test-key"})

    assert response.status_code == 200
    registry = response.json()["data"]
    assert registry["version"] == "hydra-free-llm-registry-v1"
    assert {"offline", "ollama", "huggingface"}.issubset(registry["providers"])
    assert registry["providers"]["offline"]["available"] is True
    assert registry["providers"]["ollama"]["privacy"] == "local"
    assert registry["providers"]["huggingface"]["token_present"] is False
    assert "openclaw" in registry["agent_launchers"]["integrations"]
    assert registry["agent_launchers"]["aliases"]["clawdbot"] == "openclaw"


def test_free_llm_dispatch_offline_returns_deterministic_local_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(free_llm_routes, "REPO_ROOT", tmp_path)
    client = _client(monkeypatch)

    response = client.post(
        "/hydra/free-llm/dispatch",
        headers={"x-api-key": "test-key"},
        json={"provider": "offline", "prompt": "write a test", "dry_run": False},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["version"] == "hydra-free-llm-dispatch-v1"
    assert data["route"]["provider"] == "offline"
    assert data["route"]["privacy"] == "local"
    assert data["result"]["finish_reason"] == "offline_deterministic"
    assert "No remote model was called" in data["result"]["text"]
    assert data["bus_event"]["version"] == "hydra-free-llm-bus-event-v1"
    assert data["bus_event"]["origin"] == "outside"
    assert data["bus_event"]["prompt"]["sha256"]
    assert "write a test" not in json.dumps(data["bus_event"])
    bus_path = tmp_path / ".scbe" / "packets" / "free_llm_dispatch.jsonl"
    assert bus_path.exists()
    saved = json.loads(bus_path.read_text(encoding="utf-8").splitlines()[-1])
    assert saved["event_id"] == data["bus_event"]["event_id"]


def test_free_llm_internal_dispatch_marks_inside_bus_origin(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(free_llm_routes, "REPO_ROOT", tmp_path)

    response = free_llm_routes.dispatch_free_llm_request(
        free_llm_routes.FreeLLMDispatchRequest(provider="offline", prompt="internal build task"),
        user="hydra",
        origin="inside",
    )

    data = response["data"]
    assert data["route"]["provider"] == "offline"
    assert data["bus_event"]["origin"] == "inside"
    assert data["bus_event"]["user"] == "hydra"
    assert "internal build task" not in json.dumps(data["bus_event"])


def test_free_llm_bus_handles_real_geoseal_publish_readiness_task(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(free_llm_routes, "REPO_ROOT", tmp_path)
    prompt = (
        "Inspect GeoSeal CLI publish readiness: verify bin/geoseal.cjs, "
        "src/geoseal_cli.py, package.json bin mapping, npm pack guard, and "
        "agent bus smoke tests. Return blockers only."
    )

    response = free_llm_routes.dispatch_free_llm_request(
        free_llm_routes.FreeLLMDispatchRequest(
            provider="offline",
            prompt=prompt,
            metadata={"task_type": "geoseal_publish_readiness", "artifact": "npm_cli"},
        ),
        user="hydra",
        origin="inside",
    )

    data = response["data"]
    assert data["route"]["provider"] == "offline"
    assert data["result"]["finish_reason"] == "offline_deterministic"
    event = data["bus_event"]
    assert event["origin"] == "inside"
    assert event["prompt"]["chars"] == len(prompt)
    assert event["prompt"]["sha256"]
    assert event["result"]["text_sha256"]
    assert "GeoSeal CLI publish readiness" not in json.dumps(event)

    bus_path = tmp_path / ".scbe" / "packets" / "free_llm_dispatch.jsonl"
    saved = json.loads(bus_path.read_text(encoding="utf-8").splitlines()[-1])
    assert saved["event_id"] == event["event_id"]
    assert saved["route"]["provider"] == "offline"


def test_free_llm_dispatch_dry_run_routes_to_requested_provider(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(free_llm_routes, "REPO_ROOT", tmp_path)
    client = _client(monkeypatch)

    response = client.post(
        "/hydra/free-llm/dispatch",
        headers={"x-api-key": "test-key"},
        json={
            "provider": "ollama",
            "prompt": "hello",
            "dry_run": True,
            "model": "qwen-test",
        },
    )

    assert response.status_code == 200
    route = response.json()["data"]["route"]
    assert route["provider"] == "ollama"
    assert route["kind"] == "ollama"
    assert route["model"] == "qwen-test"
    assert route["dry_run"] is True
    assert response.json()["data"]["bus_event"]["result"]["finish_reason"] is None


def test_free_llm_auto_dispatch_falls_back_to_offline_when_ollama_unreachable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(free_llm_routes, "REPO_ROOT", tmp_path)
    client = _client(monkeypatch)

    def _raise(*args, **kwargs):
        raise RuntimeError("provider_unreachable")

    monkeypatch.setattr(free_llm_routes, "_ollama_dispatch", _raise)

    response = client.post(
        "/hydra/free-llm/dispatch",
        headers={"x-api-key": "test-key"},
        json={"prompt": "hello"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["route"]["provider"] == "offline"
    assert data["result"]["fallback_from"] == "ollama"
    assert data["bus_event"]["error"] == "provider_unreachable"


def test_free_llm_custom_local_provider_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SCBE_FREE_LLM_PROVIDERS",
        json.dumps(
            {
                "my-local-ai": {
                    "enabled": True,
                    "endpoint": "http://127.0.0.1:9999/v1/chat/completions",
                    "model": "my-code-worker",
                    "privacy": "local",
                }
            }
        ),
    )
    client = _client(monkeypatch)

    response = client.get("/hydra/free-llm/providers", headers={"x-api-key": "test-key"})

    assert response.status_code == 200
    provider = response.json()["data"]["providers"]["my-local-ai"]
    assert provider["kind"] == "custom"
    assert provider["privacy"] == "local"
    assert provider["default_model"] == "my-code-worker"


def test_ollama_launch_plan_normalizes_alias_and_extra_args() -> None:
    plan = free_llm_routes.build_ollama_launch_plan(
        free_llm_routes.OllamaLaunchPlanRequest(
            integration="clawdbot",
            model="qwen2.5-coder:0.5b",
            extra_args=["--sandbox", "workspace-write"],
        ),
        user="tester",
    )

    assert plan["version"] == "hydra-ollama-launch-plan-v1"
    assert plan["integration"] == "openclaw"
    assert plan["command"] == [
        "ollama",
        "launch",
        "openclaw",
        "--yes",
        "--model",
        "qwen2.5-coder:0.5b",
        "--",
        "--sandbox",
        "workspace-write",
    ]
