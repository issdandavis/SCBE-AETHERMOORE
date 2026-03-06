"""Tests for the FastAPI server."""
import json
import pytest
from fastapi.testclient import TestClient
from src.aetherbrowser.serve import app

client = TestClient(app)

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "agents" in data

    def test_health_shows_agent_count(self):
        r = client.get("/health")
        data = r.json()
        assert len(data["agents"]) == 6

class TestWebSocket:
    def test_ws_connect_and_command(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "command", "agent": "user", "payload": {"text": "Hello"}})
            # Should get at least one response (agent_status or chat)
            response = ws.receive_json()
            assert response["type"] in ("chat", "agent_status", "error")
            assert "seq" in response

    def test_ws_page_context(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "type": "page_context",
                "agent": "user",
                "payload": {
                    "url": "https://example.com",
                    "title": "Example",
                    "text": "This is a test page about AI safety and governance.",
                },
            })
            response = ws.receive_json()
            assert response["type"] in ("chat", "agent_status")

    def test_ws_rejects_invalid_type(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "hacked", "agent": "user", "payload": {}})
            response = ws.receive_json()
            assert response["type"] == "error"
