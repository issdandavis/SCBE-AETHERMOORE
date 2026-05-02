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


@pytest.fixture
def client() -> TestClient:
    return TestClient(harness.app)


def _mock_call(text: str, ok: bool = True) -> dict[str, Any]:
    return {
        "ok": ok,
        "model": "mock",
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
