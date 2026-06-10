import os


def test_health_always_open(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_op_open_in_dev_mode(client, monkeypatch):
    monkeypatch.delenv("AETHER_DESKTOP_API_KEY", raising=False)
    payload = {
        "op": "echo",
        "args": {"msg": "hello"},
        "request_id": "auth-dev-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_op_rejects_missing_key(client, monkeypatch):
    monkeypatch.setenv("AETHER_DESKTOP_API_KEY", "secret123")
    payload = {
        "op": "echo",
        "args": {"msg": "hello"},
        "request_id": "auth-missing-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 401


def test_op_rejects_wrong_key(client, monkeypatch):
    monkeypatch.setenv("AETHER_DESKTOP_API_KEY", "secret123")
    payload = {
        "op": "echo",
        "args": {"msg": "hello"},
        "request_id": "auth-wrong-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload, headers={"X-API-Key": "wrongkey"})
    assert resp.status_code == 401


def test_op_accepts_correct_key(client, monkeypatch):
    monkeypatch.setenv("AETHER_DESKTOP_API_KEY", "secret123")
    payload = {
        "op": "echo",
        "args": {"msg": "hello"},
        "request_id": "auth-ok-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload, headers={"X-API-Key": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
