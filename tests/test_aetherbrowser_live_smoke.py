from __future__ import annotations

from scripts.aetherbrowser_live_smoke import (
    summarize_page_flow,
    summarize_research_flow,
    summarize_zone_gate,
)


def test_summarize_research_flow_extracts_execution_and_states():
    messages = [
        {"type": "agent_status", "payload": {"state": "working"}},
        {"type": "chat", "payload": {"plan": {"provider": "local", "risk_tier": "low"}}},
        {
            "type": "chat",
            "payload": {
                "execution": {
                    "provider": "local",
                    "model_id": "local-control",
                    "fallback_used": False,
                }
            },
        },
        {"type": "agent_status", "payload": {"state": "done"}},
    ]

    summary = summarize_research_flow(messages)

    assert summary["execution_provider"] == "local"
    assert summary["execution_model"] == "local-control"
    assert summary["plan_provider"] == "local"
    assert summary["plan_risk_tier"] == "low"
    assert summary["status_sequence"] == ["working", "done"]


def test_summarize_zone_gate_extracts_request_and_resume():
    initial = [
        {"type": "agent_status", "payload": {"state": "working"}},
        {"type": "agent_status", "payload": {"state": "waiting"}},
        {"type": "zone_request", "seq": 12, "zone": "RED"},
    ]
    resumed = [
        {
            "type": "chat",
            "payload": {
                "execution": {
                    "provider": "local",
                    "model_id": "local-control",
                }
            },
        },
        {"type": "agent_status", "payload": {"state": "done"}},
    ]

    summary = summarize_zone_gate(initial, resumed)

    assert summary["zone"] == "RED"
    assert summary["request_seq"] == 12
    assert summary["initial_states"] == ["working", "waiting"]
    assert summary["resumed_states"] == ["done"]
    assert summary["execution_provider"] == "local"


def test_summarize_page_flow_extracts_analysis_payload():
    messages = [
        {
            "type": "chat",
            "payload": {
                "page_analysis": {
                    "title": "AI Safety Research",
                    "risk_tier": "low",
                    "intent": "research",
                    "topics": ["ai", "security"],
                    "next_actions": [
                        {"label": "Inspect cited paper"},
                        {"label": "Compare governance systems"},
                    ],
                }
            },
        }
    ]

    summary = summarize_page_flow(messages)

    assert summary["title"] == "AI Safety Research"
    assert summary["risk_tier"] == "low"
    assert summary["intent"] == "research"
    assert summary["topics"] == ["ai", "security"]
    assert summary["next_actions"] == ["Inspect cited paper", "Compare governance systems"]
