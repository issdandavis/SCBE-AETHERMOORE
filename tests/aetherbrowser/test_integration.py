"""
Integration test: full backend message flow.
Tests the complete path from WebSocket command to agent response.
"""

from fastapi.testclient import TestClient
import src.aetherbrowser.serve as serve_module
from src.aetherbrowser.provider_executor import ProviderExecutionResult

client = TestClient(serve_module.app)


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

        class StubExecutor:
            async def execute(self, plan):
                return ProviderExecutionResult(
                    provider=plan.provider,
                    model_id="test-local",
                    text="research stub",
                    attempted=[plan.provider],
                    fallback_used=False,
                )

        original = serve_module.executor
        serve_module.executor = StubExecutor()
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "agent": "user",
                    "payload": {"text": "Research hyperbolic competitors"},
                }
            )
            # "research" + "competitors" triggers research task type
            # -> roles KO, AV, CA, RU, DR (5 roles)
            # Messages: KO working, KO chat, 4x assigned, KO done = 7
            messages = _drain(ws, 9)

            types = [m["type"] for m in messages]
            agents = [m.get("agent") for m in messages]

            assert "agent_status" in types
            assert "chat" in types
            assert "KO" in agents
            plan_messages = [m for m in messages if m["type"] == "chat" and "plan" in m.get("payload", {})]
            assert plan_messages
            assert plan_messages[0]["payload"]["plan"]["risk_tier"] == "low"
            execution_messages = [m for m in messages if m["type"] == "chat" and "execution" in m.get("payload", {})]
            assert execution_messages
            assert execution_messages[0]["payload"]["execution"]["model_id"] == "test-local"
        serve_module.executor = original

    def test_high_risk_command_waits_for_zone_decision_then_resumes(self):
        class StubExecutor:
            async def execute(self, plan):
                return ProviderExecutionResult(
                    provider=plan.provider,
                    model_id="test-local",
                    text="high risk stub",
                    attempted=[plan.provider],
                    fallback_used=False,
                )

        original = serve_module.executor
        serve_module.executor = StubExecutor()
        serve_module.pending_zone_requests.clear()
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "agent": "user",
                    "payload": {"text": "Open the browser tab, fill the login form, and submit it"},
                }
            )
            initial = _drain(ws, 4)
            zone_request = initial[-1]
            assert zone_request["type"] == "zone_request"
            assert zone_request["zone"] == "RED"

            ws.send_json(
                {
                    "type": "zone_response",
                    "agent": "user",
                    "payload": {"request_seq": zone_request["seq"], "decision": "allow_once"},
                }
            )
            resumed = _drain(ws, 6)
            assert resumed[0]["type"] == "chat"
            assert resumed[0]["agent"] == "RU"
            assert resumed[-1]["type"] == "agent_status"
            assert resumed[-1]["agent"] == "KO"
            assert resumed[-1]["payload"]["state"] == "done"
        serve_module.executor = original

    def test_page_context_produces_analysis(self):
        """Sending page context should produce CA analysis.

        Expected flow:
          1. agent_status CA analyzing
          2. chat CA (summary)
          3. agent_status CA done
          4. chat DR (structured topics, because topics detected)
        """
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "page_context",
                    "agent": "user",
                    "payload": {
                        "url": "https://example.com/ai-safety",
                        "title": "AI Safety Research",
                        "text": "Machine learning security requires governance frameworks. "
                        "Neural networks need adversarial defense mechanisms. "
                        "Hyperbolic geometry provides exponential cost scaling.",
                    },
                }
            )
            # Topics detected (AI/ML + Security) -> 4 messages total
            messages = _drain(ws, 4)

            ca_msgs = [m for m in messages if m.get("agent") == "CA"]
            assert len(ca_msgs) >= 1
            analysis_messages = [m for m in messages if "page_analysis" in m.get("payload", {})]
            assert analysis_messages
            assert analysis_messages[0]["payload"]["page_analysis"]["risk_tier"] == "low"

    def test_health_reflects_squad_state(self):
        """Health endpoint should show all 6 agents."""
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "ok"
        assert len(data["agents"]) == 6


class TestErrorHandling:
    def test_empty_command_returns_error(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_json(
                {
                    "type": "command",
                    "agent": "user",
                    "payload": {"text": ""},
                }
            )
            msg = ws.receive_json()
            assert msg["type"] == "error"

    def test_malformed_json_handled(self):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("not json at all")
            msg = ws.receive_json()
            assert msg["type"] == "error"
