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
