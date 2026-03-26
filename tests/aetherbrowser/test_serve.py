"""Tests for the FastAPI server."""

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient
import src.aetherbrowser.serve as serve_module
from src.aetherbrowser.provider_executor import ProviderExecutionResult

client = TestClient(serve_module.app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "agents" in data
        assert "providers" in data
        assert "executor" in data
        assert "local" in data["executor"]
        assert "model_id" in data["executor"]["local"]

    def test_health_shows_agent_count(self):
        r = client.get("/health")
        data = r.json()
        assert len(data["agents"]) == 6


class TestWebSocket:
    def test_ws_connect_and_command(self):
        class StubExecutor:
            async def execute(self, plan):
                return ProviderExecutionResult(
                    provider=plan.provider,
                    model_id="test-local",
                    text="stub execution",
                    attempted=[plan.provider],
                    fallback_used=False,
                )

        original = serve_module.executor
        serve_module.executor = StubExecutor()
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "command", "agent": "user", "payload": {"text": "Hello"}})
            messages = [ws.receive_json() for _ in range(7)]
            assert any(
                msg["type"] == "chat" and msg["payload"].get("execution", {}).get("model_id") == "test-local"
                for msg in messages
            )
            assert any(msg["type"] == "agent_status" and msg["payload"]["state"] == "done" for msg in messages)
        serve_module.executor = original

    def test_ws_high_risk_command_requests_zone_approval(self):
        serve_module.pending_zone_requests.clear()
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "agent": "user",
                    "payload": {"text": "Open the browser tab, fill the login form, and submit it"},
                }
            )
            messages = [ws.receive_json() for _ in range(4)]
            assert messages[0]["type"] == "agent_status"
            assert messages[1]["type"] == "chat"
            assert messages[1]["payload"]["plan"]["approval_required"] is True
            assert messages[2]["type"] == "agent_status"
            assert messages[2]["payload"]["state"] == "waiting"
            assert messages[3]["type"] == "zone_request"
            assert messages[3]["zone"] == "RED"

    def test_ws_page_context(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "page_context",
                    "agent": "user",
                    "payload": {
                        "url": "https://example.com",
                        "title": "Example",
                        "text": "This is a test page about AI safety and governance.",
                    },
                }
            )
            response = ws.receive_json()
            assert response["type"] in ("chat", "agent_status")

    def test_ws_rejects_invalid_type(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "hacked", "agent": "user", "payload": {}})
            response = ws.receive_json()
            assert response["type"] == "error"
