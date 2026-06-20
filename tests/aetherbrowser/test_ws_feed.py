"""Tests for the WebSocket message protocol."""

import json
import pytest
from src.aetherbrowser.ws_feed import WsFeed, Agent, Zone


def _make_chat(feed):
    msg = feed.chat(Agent.KO, "Hello world", model="opus")
    assert msg["agent"] == "KO"
    assert msg["payload"]["text"] == "Hello world"
    assert msg["model"] == "opus"
    assert "ts" in msg
    assert "seq" in msg
    return msg


def _make_agent_status(feed):
    msg = feed.agent_status(Agent.AV, "scouting", model="flash")
    assert msg["agent"] == "AV"
    assert msg["payload"]["state"] == "scouting"
    return msg


def _make_zone_request(feed):
    msg = feed.zone_request(
        Agent.RU,
        Zone.YELLOW,
        url="https://api.example.com",
        action="write",
        description="Post to external API",
    )
    assert msg["zone"] == "YELLOW"
    assert msg["payload"]["url"] == "https://api.example.com"
    return msg


def _make_progress(feed):
    msg = feed.progress(Agent.CA, current=3, total=10, label="Extracting pages")
    assert msg["payload"]["current"] == 3
    assert msg["payload"]["total"] == 10
    return msg


def _make_error(feed):
    msg = feed.error("Connection failed", agent=Agent.KO)
    assert msg["payload"]["reason"] == "Connection failed"
    return msg


class TestMessageCreation:
    @pytest.mark.parametrize(
        "factory,expected_type",
        [
            (_make_chat, "chat"),
            (_make_agent_status, "agent_status"),
            (_make_zone_request, "zone_request"),
            (_make_progress, "progress"),
            (_make_error, "error"),
        ],
    )
    def test_create_message(self, factory, expected_type):
        feed = WsFeed()
        msg = factory(feed)
        assert msg["type"] == expected_type

    def test_create_chat_message_with_structured_payload(self):
        feed = WsFeed()
        msg = feed.chat(
            Agent.KO,
            "Plan ready",
            payload={"plan": {"intent": "research", "risk_tier": "low"}},
        )
        assert msg["payload"]["text"] == "Plan ready"
        assert msg["payload"]["plan"]["intent"] == "research"

    def test_sequence_increments(self):
        feed = WsFeed()
        m1 = feed.chat(Agent.KO, "first")
        m2 = feed.chat(Agent.AV, "second")
        assert m2["seq"] == m1["seq"] + 1

    def test_parse_command(self):
        raw = json.dumps(
            {
                "type": "command",
                "agent": "user",
                "payload": {"text": "Research hyperbolic competitors"},
            }
        )
        msg = WsFeed.parse(raw)
        assert msg["type"] == "command"
        assert msg["agent"] == "user"

    def test_parse_rejects_invalid_type(self):
        raw = json.dumps({"type": "hacked", "agent": "user", "payload": {}})
        with pytest.raises(ValueError, match="Invalid message type"):
            WsFeed.parse(raw)

    def test_parse_rejects_oversized(self):
        raw = "x" * (1_048_577)
        with pytest.raises(ValueError, match="oversized"):
            WsFeed.parse(raw)

    def test_zone_response_roundtrip(self):
        feed = WsFeed()
        req = feed.zone_request(
            Agent.RU,
            Zone.RED,
            url="https://bank.com",
            action="read",
            description="Financial site",
        )
        resp_raw = json.dumps(
            {
                "type": "zone_response",
                "agent": "user",
                "payload": {"request_seq": req["seq"], "decision": "deny"},
            }
        )
        resp = WsFeed.parse(resp_raw)
        assert resp["type"] == "zone_response"
        assert resp["payload"]["decision"] == "deny"
