"""Red-zone integration tests for the curved browser and phase-tunnel lane."""

from __future__ import annotations

import math
import re
from html import unescape
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient

import src.aetherbrowser.serve as serve_module
from src.aetherbrowser.phase_tunnel import (
    KernelStack,
    TunnelOutcome,
    compute_transmission,
    compute_transparency_frequency,
)
from src.aetherbrowser.provider_executor import ProviderExecutionResult

client = TestClient(serve_module.app)
FIXTURE_PATH = Path("tests/e2e/fixtures/red-zone-site.html")


def _strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(text).split())


def _load_red_zone_payload() -> dict:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = _strip_tags(title_match.group(1)) if title_match else "Red Zone"

    headings = [
        {"level": f"H{level}", "text": _strip_tags(text)}
        for level, text in re.findall(r"<h([1-6])[^>]*>(.*?)</h\1>", html, re.IGNORECASE | re.DOTALL)
    ]
    links = [
        {"href": href, "text": _strip_tags(text)}
        for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
    ]
    buttons = []
    for attrs, text in re.findall(r"<button([^>]*)>(.*?)</button>", html, re.IGNORECASE | re.DOTALL):
        type_match = re.search(r'type="([^"]+)"', attrs, re.IGNORECASE)
        buttons.append(
            {
                "text": _strip_tags(text),
                "type": (type_match.group(1) if type_match else "button").lower(),
            }
        )
    forms = []
    for idx, (attrs, body) in enumerate(re.findall(r"<form([^>]*)>(.*?)</form>", html, re.IGNORECASE | re.DOTALL)):
        method_match = re.search(r'method="([^"]+)"', attrs, re.IGNORECASE)
        forms.append(
            {
                "index": idx,
                "method": (method_match.group(1) if method_match else "get").lower(),
                "fields": [
                    {
                        "name": name,
                        "type": field_type.lower(),
                    }
                    for field_type, name in re.findall(
                        r'<input[^>]+type="([^"]+)"[^>]+name="([^"]+)"',
                        body,
                        re.IGNORECASE,
                    )
                ],
            }
        )

    text = _strip_tags(re.sub(r"<style.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL))

    return {
        "url": "https://suspicious-downloads.example.test",
        "title": title,
        "text": text,
        "headings": headings,
        "links": links,
        "forms": forms,
        "buttons": buttons,
        "tabs": [
            {
                "title": title,
                "url": "https://suspicious-downloads.example.test",
                "active": True,
            }
        ],
        "page_type": "form",
    }


def _hyperbolic_distance_from_radius(radius: float) -> float:
    clamped = min(max(radius, 0.0), 0.99)
    return 2 * math.atanh(clamped) if clamped > 0 else 0.0


def _drain(ws, count: int) -> list[dict]:
    return [ws.receive_json() for _ in range(count)]


class TestRedZoneIntegration:
    def test_red_zone_fixture_emits_high_risk_analysis_and_topology(self):
        payload = _load_red_zone_payload()

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "page_context", "agent": "user", "payload": payload})
            messages = _drain(ws, 5)

        analysis_message = next(
            msg for msg in messages if msg["type"] == "chat" and "page_analysis" in msg.get("payload", {})
        )
        topology_message = next(msg for msg in messages if msg["type"] == "topology")

        analysis = analysis_message["payload"]["page_analysis"]
        topology = topology_message["payload"]

        assert analysis["risk_tier"] == "high"
        assert analysis["topology_lens"]["zone"] == "RED"
        assert analysis["topology_lens"]["trust_distance"] > 0
        assert "identity boundary present" in analysis["topology_lens"]["boundary_signals"]
        assert "state-change controls exposed" in analysis["topology_lens"]["boundary_signals"]

        assert topology["center"]["label"].startswith("Suspicious Downloads Portal")
        assert topology["node_count"] >= 8
        zones = {node["zone"] for node in topology["nodes"]}
        assert {"GREEN", "YELLOW", "RED"} <= zones

    def test_phase_tunnel_blocks_red_commit_and_preserves_green_preview(self):
        payload = _load_red_zone_payload()

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "page_context", "agent": "user", "payload": payload})
            messages = _drain(ws, 5)

        topology = next(msg for msg in messages if msg["type"] == "topology")["payload"]
        red_node = next(node for node in topology["nodes"] if node["zone"] == "RED")
        green_node = next(node for node in topology["nodes"] if node["zone"] == "GREEN")

        low_trust_kernel = KernelStack(genesis_hash="red-zone-low")
        red_result = compute_transmission(
            _hyperbolic_distance_from_radius(red_node["radius"]),
            agent_phase=0.0,
            target_zone=red_node["zone"],
            kernel=low_trust_kernel,
        )

        high_trust_kernel = KernelStack(genesis_hash="red-zone-high")
        for idx in range(15):
            high_trust_kernel.add_scar(f"lifetime_{idx}")
        green_d_h = _hyperbolic_distance_from_radius(green_node["radius"])
        green_phase = compute_transparency_frequency(green_node["zone"], green_d_h)
        green_result = compute_transmission(
            green_d_h,
            agent_phase=green_phase,
            target_zone=green_node["zone"],
            kernel=high_trust_kernel,
        )

        assert red_result.outcome in {
            TunnelOutcome.REFLECT,
            TunnelOutcome.COLLAPSE,
            TunnelOutcome.ATTENUATE,
        }
        assert red_result.commit_allowed is False

        assert green_result.outcome in {TunnelOutcome.ATTENUATE, TunnelOutcome.TUNNEL}
        assert green_result.transmission_coeff > red_result.transmission_coeff

    def test_red_zone_analysis_can_run_on_stubbed_huggingface_lane(self):
        payload = _load_red_zone_payload()

        class StubExecutor:
            async def execute(self, plan):
                assert plan.provider == "huggingface"
                return ProviderExecutionResult(
                    provider=plan.provider,
                    model_id="hf-test-lane",
                    text=f"hf stub analyzed {payload['title']}",
                    attempted=[plan.provider],
                    fallback_used=False,
                )

        original = serve_module.executor
        serve_module.executor = StubExecutor()
        try:
            with client.websocket_connect("/ws") as ws:
                ws.send_json(
                    {
                        "type": "command",
                        "agent": "user",
                        "payload": {
                            "text": f"Research the page titled {payload['title']} and summarize safe exits.",
                            "routing": {
                                "preferences": {"KO": "huggingface"},
                                "auto_cascade": False,
                            },
                        },
                    }
                )
                messages = _drain(ws, 9)
        finally:
            serve_module.executor = original

        execution_message = next(
            msg for msg in messages if msg["type"] == "chat" and "execution" in msg.get("payload", {})
        )
        plan_message = next(msg for msg in messages if msg["type"] == "chat" and "plan" in msg.get("payload", {}))

        assert plan_message["payload"]["plan"]["provider"] == "huggingface"
        assert execution_message["payload"]["execution"]["provider"] == "huggingface"
        assert execution_message["payload"]["execution"]["model_id"] == "hf-test-lane"
