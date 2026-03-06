"""
Integration test: full backend message flow.
Tests the complete path from WebSocket command to agent response.
"""
import json
import pytest
from fastapi.testclient import TestClient
from src.aetherbrowser.serve import app

client = TestClient(app)


def _drain(ws, count: int) -> list[dict]:
    """Read exactly *count* messages from the WebSocket."""
    return [ws.receive_json() for _ in range(count)]


class TestFullCommandFlow:
    def test_research_command_produces_agent_messages(self):
        """A research command should produce KO status + chat + agent assignments.

        Expected flow for "Research hyperbolic competitors":
          1. agent_status KO working
          2. chat KO (complexity + assignment summary)
          3-6. agent_status for each non-KO role (AV, CA, RU, DR)
          7. agent_status KO done
        """
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "type": "command",
                "agent": "user",
                "payload": {"text": "Research hyperbolic competitors"},
            })
            # "research" + "competitors" triggers research task type
            # -> roles KO, AV, CA, RU, DR (5 roles)
            # Messages: KO working, KO chat, 4x assigned, KO done = 7
            messages = _drain(ws, 7)

            types = [m["type"] for m in messages]
            agents = [m.get("agent") for m in messages]

            assert "agent_status" in types
            assert "chat" in types
            assert "KO" in agents

    def test_page_context_produces_analysis(self):
        """Sending page context should produce CA analysis.

        Expected flow:
          1. agent_status CA analyzing
          2. chat CA (summary)
          3. agent_status CA done
          4. chat DR (structured topics, because topics detected)
        """
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "type": "page_context",
                "agent": "user",
                "payload": {
                    "url": "https://example.com/ai-safety",
                    "title": "AI Safety Research",
                    "text": "Machine learning security requires governance frameworks. "
                            "Neural networks need adversarial defense mechanisms. "
                            "Hyperbolic geometry provides exponential cost scaling.",
                },
            })
            # Topics detected (AI/ML + Security) -> 4 messages total
            messages = _drain(ws, 4)

            ca_msgs = [m for m in messages if m.get("agent") == "CA"]
            assert len(ca_msgs) >= 1

    def test_health_reflects_squad_state(self):
        """Health endpoint should show all 6 agents."""
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "ok"
        assert len(data["agents"]) == 6


class TestErrorHandling:
    def test_empty_command_returns_error(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json({
                "type": "command",
                "agent": "user",
                "payload": {"text": ""},
            })
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_malformed_json_handled(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("not json at all")
            msg = ws.receive_json()
            assert msg["type"] == "error"
