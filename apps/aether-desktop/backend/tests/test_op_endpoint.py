import asyncio

import httpx
import respx

from backend.handlers.llm_chat import llm_chat_handler
from backend.models import OperationDecision


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_echo_op_returns_ok(client):
    payload = {
        "op": "echo",
        "args": {"msg": "hello world"},
        "request_id": "test-echo-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["request_id"] == "test-echo-001"
    assert data["output"]["echo"] == "hello world"


def test_denied_op_returns_ok_false_without_calling_handler(client):
    payload = {
        "op": "terminal.shell.raw",
        "args": {"cmd": "rm -rf /"},
        "request_id": "test-deny-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "DENY"


def test_unknown_op_returns_quarantined(client):
    payload = {
        "op": "magic.unicorn",
        "args": {},
        "request_id": "test-unknown-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] in ("QUARANTINE", "OP_NOT_FOUND")


def test_escalated_op_does_not_dispatch(client, monkeypatch):
    def escalate(_req):
        return OperationDecision(
            request_id="test-escalate-001",
            decision="ESCALATE",
            zone="YELLOW",
            reason="manual approval required",
            policy="test-escalate",
            latency_ms=0.1,
        )

    monkeypatch.setattr("backend.main.govern", escalate)
    payload = {
        "op": "echo",
        "args": {"msg": "should not dispatch"},
        "request_id": "test-escalate-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "ESCALATE"


_OLLAMA_URL = "http://localhost:11434/api/chat"


@respx.mock
def test_llm_chat_calls_ollama_and_returns_ok(client):
    stream_lines = (
        b'{"model":"llama3","message":{"role":"assistant","content":"Hello"},"done":false}\n'
        b'{"model":"llama3","message":{"role":"assistant","content":" world"},"done":false}\n'
        b'{"model":"llama3","message":{"role":"assistant","content":""},"done":true}\n'
    )
    respx.post(_OLLAMA_URL).mock(return_value=httpx.Response(200, content=stream_lines))
    payload = {
        "op": "llm.chat",
        "args": {
            "messages": [{"role": "user", "content": "hi"}],
            "model": "llama3",
            "provider_url": _OLLAMA_URL,
        },
        "request_id": "test-chat-001",
        "origin": {"kind": "app", "id": "chat-window"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "content" in data["output"]


@respx.mock
def test_dry_run_llm_chat_does_not_call_ollama(client):
    route = respx.post(_OLLAMA_URL).mock(return_value=httpx.Response(500, text="should not be called"))
    payload = {
        "op": "llm.chat",
        "args": {"messages": [{"role": "user", "content": "hi"}], "model": "llama3"},
        "request_id": "test-chat-dry-run-001",
        "origin": {"kind": "app", "id": "chat-window"},
        "privacy": "local_only",
        "dry_run": True,
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["output"]["dry_run"] is True
    assert data["output"]["operation"]["op"] == "llm.chat"
    assert route.called is False


@respx.mock
def test_llm_chat_returns_error_when_ollama_unavailable(client):
    respx.post(_OLLAMA_URL).mock(side_effect=httpx.ConnectError("refused"))
    payload = {
        "op": "llm.chat",
        "args": {"messages": [{"role": "user", "content": "hi"}], "provider_url": _OLLAMA_URL},
        "request_id": "test-chat-002",
        "origin": {"kind": "app", "id": "chat-window"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "LLM_UNAVAILABLE"


@respx.mock
def test_llm_chat_error_emits_done_event():
    async def run():
        respx.post(_OLLAMA_URL).mock(side_effect=httpx.ConnectError("refused"))
        queue = asyncio.Queue()
        req = {
            "op": "llm.chat",
            "args": {"messages": [{"role": "user", "content": "hi"}], "provider_url": _OLLAMA_URL},
            "request_id": "test-chat-events-error-001",
            "origin": {"kind": "app", "id": "chat-window"},
            "privacy": "local_only",
        }
        from backend.models import OperationRequest

        result = await llm_chat_handler(OperationRequest(**req), event_queue=queue)
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        return result, event

    result, event = asyncio.run(run())
    assert result.ok is False
    assert event["type"] == "done"
    assert event["error_code"] == "LLM_UNAVAILABLE"
