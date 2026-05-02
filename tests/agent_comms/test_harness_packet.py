"""End-to-end test for the /harness/packet endpoint.

Guards:
- packet validation errors return 400
- budget overruns return 413 (no model call)
- a valid packet derefs path/manifest_id refs and emits a MergeReport
- the packet's request — not its full ref content — is what travels to models
- promote/hold/reject decisions follow both_ok + agreement
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from scripts import serve_geoseal_harness as harness
from src.agent_comms import (
    AgentPacketV1,
    Budget,
    ContextRef,
    Route,
    hash_state,
    new_task_id,
)


def _packet_dict(**overrides: Any) -> dict[str, Any]:
    base = AgentPacketV1(
        task_id=new_task_id("test"),
        phase="verify",
        route=Route(tongue="KO", domain="code", permission="read"),
        context_refs=[ContextRef(kind="path", value="README.md")],
        state_hash=hash_state("repo:main"),
        budget=Budget(max_input_tokens=4096, max_output_tokens=512),
        request="Verify the manifest summary at the referenced path.",
        expected_output="verdict",
    )
    data = base.to_dict()
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def _clear_ledger():
    """Wipe the module-level packet ledger between tests.

    The /harness/packet endpoint dedups by packet fingerprint, and
    `_packet_dict()` produces the same fingerprint across tests. Without
    this reset, a promote recorded in one test would short-circuit the
    next test's fan-out before its mocks fire.
    """
    harness._LEDGER._entries.clear()
    yield
    harness._LEDGER._entries.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(harness.app)


def _mock_call(text: str, ok: bool = True) -> dict[str, Any]:
    return {
        "ok": ok,
        "model": "mock",
        "provider": "mock-provider",
        "tool_adapter": "raw_json_only",
        "text": text,
        "finish_reason": "stop" if ok else "error",
        "usage": {},
        "latency_ms": 7,
    }


def test_packet_endpoint_rejects_invalid_phase(client: TestClient) -> None:
    bad = _packet_dict(phase="rubber_stamp")
    resp = client.post(
        "/harness/packet",
        json={"packet": bad, "models": ["m1", "m2"]},
    )
    assert resp.status_code == 400
    assert "phase" in resp.json()["detail"]


def test_packet_endpoint_rejects_over_budget(client: TestClient) -> None:
    big = _packet_dict(
        request="x" * 10_000,
        budget={"max_input_tokens": 64, "max_output_tokens": 64},
    )
    resp = client.post(
        "/harness/packet",
        json={"packet": big, "models": ["m1", "m2"]},
    )
    assert resp.status_code == 413


def test_packet_endpoint_promotes_on_agreement(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    text = json.dumps({"verdict": "ok"}, sort_keys=True)
    fake = AsyncMock(side_effect=[_mock_call(text), _mock_call(text)])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={
                "packet": _packet_dict(),
                "models": ["model-a", "model-b"],
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["merge_report"]["decision"] == "promote"
    assert body["merge_report"]["task_id"] == body["task_id"]
    assert body["merge_report"]["delta"]["refs_total"] == 1
    assert body["merge_report"]["delta"]["refs_resolved"] == 1
    assert body["lane_switch"]["ok"] is True


def test_packet_endpoint_holds_on_disagreement(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both models replied successfully but their answers don't match — hold for review."""
    monkeypatch.setenv("HF_TOKEN", "test-token")
    fake = AsyncMock(side_effect=[_mock_call("answer alpha"), _mock_call("answer beta")])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={"packet": _packet_dict(), "models": ["a", "b"]},
        )
    assert resp.status_code == 200
    assert resp.json()["merge_report"]["decision"] == "hold"


def test_packet_endpoint_flags_unsignaled_cross_provider_lane_change(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cross-provider agreement without a blinker/signal must hold, not promote."""
    monkeypatch.setenv("HF_TOKEN", "test-token")
    text = json.dumps({"verdict": "ok"}, sort_keys=True)
    fake = AsyncMock(side_effect=[_mock_call(text), _mock_call(text)])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={
                "packet": _packet_dict(),
                "models": ["ollama:model-a", "deepseek:model-b"],
                "bypass_ledger": True,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["lane_switch"]["ok"] is False
    assert body["lane_switch"]["signal_required"] is True
    assert body["merge_report"]["decision"] == "hold"
    assert "lane_switch:flagged" in body["merge_report"]["evidence"]


def test_packet_endpoint_accepts_signaled_cross_provider_lane_change(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    text = json.dumps({"verdict": "ok"}, sort_keys=True)
    fake = AsyncMock(side_effect=[_mock_call(text), _mock_call(text)])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={
                "packet": _packet_dict(),
                "models": ["ollama:model-a", "deepseek:model-b"],
                "lane_signal": "provider-pair:ollama->deepseek:compare-local-vs-remote",
                "bypass_ledger": True,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["lane_switch"]["ok"] is True
    assert body["lane_switch"]["signal_present"] is True
    assert body["merge_report"]["decision"] == "promote"
    assert "lane_switch:ok" in body["merge_report"]["evidence"]


def test_packet_endpoint_rejects_when_both_fail(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    fake = AsyncMock(side_effect=[_mock_call("", ok=False), _mock_call("", ok=False)])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={"packet": _packet_dict(), "models": ["a", "b"]},
        )
    assert resp.status_code == 200
    assert resp.json()["merge_report"]["decision"] == "reject"


def test_packet_endpoint_only_sends_request_not_ref_bodies(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack #1 fix: model pair receives the compressed prompt, not pasted file content."""
    monkeypatch.setenv("HF_TOKEN", "test-token")
    captured: dict[str, str] = {}

    async def _capture(client_, model, prompt, system, temperature, max_tokens, token):  # type: ignore[no-untyped-def]
        captured["prompt"] = prompt
        captured["system"] = system
        return _mock_call("verdict:ok")

    pkt = _packet_dict(request="Tiny instruction.")
    with patch.object(harness, "_call_hf", _capture):
        resp = client.post(
            "/harness/packet",
            json={"packet": pkt, "models": ["a", "b"], "include_excerpts": False},
        )
    assert resp.status_code == 200
    prompt = captured["prompt"]
    assert "Tiny instruction." in prompt
    assert "context_refs:" in prompt
    # README content should NOT appear in the prompt when include_excerpts is False
    assert "excerpt:" not in prompt


def test_packet_endpoint_resolves_manifest_id(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    pkt = _packet_dict(
        context_refs=[{"kind": "manifest_id", "value": "2026-05-02-aligned-foundations-v2", "bytes": None}]
    )
    fake = AsyncMock(side_effect=[_mock_call("ok"), _mock_call("ok")])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={"packet": pkt, "models": ["a", "b"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ref_summaries"][0]["resolved"] is True
    assert body["ref_summaries"][0]["path"].endswith("2026-05-02-aligned-foundations-v2-manifest.json")


def test_packet_endpoint_short_circuits_on_ledger_hit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second identical packet must reuse the cached MergeReport without re-fanning."""
    monkeypatch.setenv("HF_TOKEN", "test-token")
    text = json.dumps({"verdict": "ok"}, sort_keys=True)
    fake = AsyncMock(side_effect=[_mock_call(text), _mock_call(text)])
    pkt = _packet_dict()
    with patch.object(harness, "_call_hf", fake):
        first = client.post("/harness/packet", json={"packet": pkt, "models": ["a", "b"]})
        # second call uses a fresh task_id so we can prove the cached entry
        # was reused (fingerprint excludes task_id) and re-stamped
        second_pkt = _packet_dict()
        second = client.post("/harness/packet", json={"packet": second_pkt, "models": ["a", "b"]})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["merge_report"]["decision"] == "promote"

    body = second.json()
    assert body.get("cached") is True
    assert body["merge_report"]["decision"] == "promote"
    assert "ledger:hit" in body["merge_report"]["evidence"]
    assert body["merge_report"]["delta"]["cached"] is True
    assert body["merge_report"]["task_id"] == body["task_id"]
    # The cached short-circuit must NOT call the model pair again.
    assert fake.await_count == 2


def test_packet_endpoint_bypass_ledger_forces_fan_out(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """bypass_ledger=True must skip the cache and re-call the model pair."""
    monkeypatch.setenv("HF_TOKEN", "test-token")
    text = json.dumps({"verdict": "ok"}, sort_keys=True)
    fake = AsyncMock(side_effect=[_mock_call(text)] * 4)
    with patch.object(harness, "_call_hf", fake):
        client.post("/harness/packet", json={"packet": _packet_dict(), "models": ["a", "b"]})
        resp = client.post(
            "/harness/packet",
            json={"packet": _packet_dict(), "models": ["a", "b"], "bypass_ledger": True},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("cached") is not True
    # Fan-out happened twice (2 calls each).
    assert fake.await_count == 4


def test_packet_endpoint_rejects_path_traversal(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Refs that escape REPO_ROOT must not resolve."""
    monkeypatch.setenv("HF_TOKEN", "test-token")
    pkt = _packet_dict(
        context_refs=[
            {"kind": "path", "value": "../../etc/passwd", "bytes": None},
        ]
    )
    fake = AsyncMock(side_effect=[_mock_call("ok"), _mock_call("ok")])
    with patch.object(harness, "_call_hf", fake):
        resp = client.post(
            "/harness/packet",
            json={"packet": pkt, "models": ["a", "b"]},
        )
    assert resp.status_code == 200
    assert resp.json()["ref_summaries"][0]["resolved"] is False
