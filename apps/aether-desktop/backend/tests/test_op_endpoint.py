import httpx
import respx


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


@respx.mock
def test_llm_chat_calls_ollama_and_returns_ok(client):
    stream_lines = (
        b'{"model":"llama3","message":{"role":"assistant","content":"Hello"},"done":false}\n'
        b'{"model":"llama3","message":{"role":"assistant","content":" world"},"done":false}\n'
        b'{"model":"llama3","message":{"role":"assistant","content":""},"done":true}\n'
    )
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, content=stream_lines)
    )
    payload = {
        "op": "llm.chat",
        "args": {"messages": [{"role": "user", "content": "hi"}], "model": "llama3"},
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
def test_llm_chat_returns_error_when_ollama_unavailable(client):
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("refused"))
    payload = {
        "op": "llm.chat",
        "args": {"messages": [{"role": "user", "content": "hi"}]},
        "request_id": "test-chat-002",
        "origin": {"kind": "app", "id": "chat-window"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "OLLAMA_UNAVAILABLE"
