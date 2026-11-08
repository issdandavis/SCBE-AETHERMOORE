"""Regression checks for GHSA-7rh5-2f26-qfj7 code paths.

Covers tenant isolation on governance audit reads, API-key requirements for
the shared /mesh and /search routers, and connector egress policy. These tests
do not contact production and do not open a socket to a blocked destination.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import Any

import pytest

from src.api.connector_url_policy import (
    ConnectorURLRejected,
    GuardedRedirectHandler,
    address_is_blocked,
    build_connector_opener,
    enforce_connected_peer,
    open_connector_request,
    validate_connector_endpoint,
)

pytestmark = [pytest.mark.security, pytest.mark.unit]

_PUBLIC_IP = "93.184.216.34"


class _FakeSocket:
    def __init__(self, peer: tuple[Any, ...]) -> None:
        self._peer = peer
        self.closed = False

    def getpeername(self) -> tuple[Any, ...]:
        return self._peer

    def close(self) -> None:
        self.closed = True


class _FakeResponse:
    def __init__(self, status: int = 204) -> None:
        self.status = status

    def read(self) -> bytes:
        return b""

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _public_dns(monkeypatch: pytest.MonkeyPatch, ip: str = _PUBLIC_IP) -> None:
    def fake(host: str, port: int, *args: object, **kwargs: object) -> list[tuple[Any, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake)


def _refuse_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("connector egress attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", fail)


def test_public_https_connector_urls_stay_valid() -> None:
    zapier = validate_connector_endpoint("https://hooks.zapier.com/hooks/catch/1/abc/", resolve_dns=False)
    shopify = validate_connector_endpoint(
        "https://demo-store.myshopify.com/admin/api/2025-10/graphql.json",
        resolve_dns=False,
    )
    configured = validate_connector_endpoint("https://example.invalid/webhook/store-ops", resolve_dns=False)
    literal = validate_connector_endpoint("https://8.8.8.8/hook", resolve_dns=False)

    assert zapier == "https://hooks.zapier.com/hooks/catch/1/abc/"
    assert shopify.endswith("/graphql.json")
    assert configured == "https://example.invalid/webhook/store-ops"
    assert literal == "https://8.8.8.8/hook"


def test_connector_policy_rejects_local_metadata_and_noncanonical_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SCBE_CONNECTOR_ALLOW_PRIVATE_NETWORKS", raising=False)
    monkeypatch.delenv("SCBE_CONNECTOR_ALLOW_INSECURE_HTTP", raising=False)
    blocked = [
        "http://hooks.zapier.com/hooks/catch/1/abc",
        "https://127.0.0.1/admin",
        "https://10.1.2.3/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/",
        "https://[::ffff:127.0.0.1]/",
        "https://2130706433/",
        "https://0177.0.0.1/",
        "https://user:secret@hooks.zapier.com/hooks/catch/1/abc",
        "file:///etc/passwd",
        "https://metadata.google.internal/computeMetadata/v1/",
        "https://localhost/webhook",
        "http://localhost:5678/webhook/flow",
    ]
    for url in blocked:
        with pytest.raises(ConnectorURLRejected):
            validate_connector_endpoint(url, resolve_dns=False)


def test_private_opt_in_keeps_metadata_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCBE_CONNECTOR_ALLOW_PRIVATE_NETWORKS", "1")
    monkeypatch.setenv("SCBE_CONNECTOR_ALLOW_INSECURE_HTTP", "1")

    assert validate_connector_endpoint("https://10.1.2.3/hook", resolve_dns=False) == "https://10.1.2.3/hook"
    assert validate_connector_endpoint("http://localhost:5678/webhook/flow", resolve_dns=False).startswith(
        "http://localhost:5678/"
    )
    with pytest.raises(ConnectorURLRejected):
        validate_connector_endpoint("https://169.254.169.254/latest/meta-data", resolve_dns=False)
    with pytest.raises(ConnectorURLRejected):
        validate_connector_endpoint("https://100.100.100.200/", resolve_dns=False)
    with pytest.raises(ConnectorURLRejected):
        validate_connector_endpoint("https://metadata.google.internal/", resolve_dns=False)


def test_resolution_to_any_blocked_address_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _refuse_network(monkeypatch)

    def mixed(host: str, port: int, *args: object, **kwargs: object) -> list[tuple[Any, ...]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (_PUBLIC_IP, port or 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", port or 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", mixed)
    with pytest.raises(ConnectorURLRejected) as blocked:
        open_connector_request(urllib.request.Request("https://hooks.example/hook", method="POST"), timeout=2)
    assert blocked.value.code == "connector_destination_blocked"


def test_connected_peer_outside_policy_is_closed() -> None:
    enforce_connected_peer(_FakeSocket(("8.8.8.8", 443)))
    blocked = _FakeSocket(("169.254.169.254", 80, 0, 0))
    with pytest.raises(ConnectorURLRejected):
        enforce_connected_peer(blocked)
    assert blocked.closed is True
    assert address_is_blocked(ipaddress.ip_address("fd00:ec2::254")) is True
    assert address_is_blocked(ipaddress.ip_address("::ffff:8.8.8.8")) is False
    assert address_is_blocked(ipaddress.ip_address("::ffff:169.254.169.254")) is True


def test_redirect_to_metadata_is_rejected_and_cross_origin_drops_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _public_dns(monkeypatch)
    handler = GuardedRedirectHandler()
    original = urllib.request.Request(
        "https://hooks.zapier.com/hooks/catch/1/abc",
        data=b"{}",
        headers={"Authorization": "Bearer secret", "Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(ConnectorURLRejected):
        handler.redirect_request(original, None, 302, "Found", {}, "https://169.254.169.254/latest/meta-data")

    same_host = handler.redirect_request(
        original,
        None,
        302,
        "Found",
        {},
        "https://hooks.zapier.com/hooks/catch/1/next",
    )
    assert same_host is not None
    assert any(key.lower() == "authorization" for key in same_host.headers)

    other_host = handler.redirect_request(original, None, 302, "Found", {}, "https://example.com/hook")
    assert other_host is not None
    assert not any(key.lower() == "authorization" for key in other_host.headers)


def test_connector_opener_ignores_environment_proxies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8080")
    opener = build_connector_opener()
    assert not any("127.0.0.1:8080" in str(getattr(handler, "proxies", "")) for handler in opener.handlers)
    assert not any(
        handler.__class__.__name__ in {"FileHandler", "FTPHandler", "DataHandler"} for handler in opener.handlers
    )
    default_opener = urllib.request.build_opener()
    default_proxy_values = [
        str(value)
        for handler in default_opener.handlers
        for value in (getattr(handler, "proxies", None) or {}).values()
    ]
    assert any("127.0.0.1:8080" in value for value in default_proxy_values)


def test_open_connector_request_does_not_connect_to_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    _refuse_network(monkeypatch)

    def fail_dns(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("metadata literal should be rejected before DNS")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)
    with pytest.raises(ConnectorURLRejected):
        open_connector_request(
            urllib.request.Request("https://169.254.169.254/latest/meta-data", method="GET"), timeout=2
        )


@pytest.fixture
def mvp_api():
    pytest.importorskip("fastapi")
    import src.api.main as api_main

    return api_main


def test_mvp_mesh_and_search_require_api_key(mvp_api, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    import src.api.mesh_routes as mesh_routes

    calls = {"mesh": 0}

    def forbidden_mesh() -> None:
        calls["mesh"] += 1
        raise AssertionError("unauthenticated mesh handler ran")

    monkeypatch.setattr(mesh_routes, "_get_mesh", forbidden_mesh)
    client = TestClient(mvp_api.app)
    unauthenticated = [
        ("post", "/mesh/query", {"text": "tenant boundary"}),
        ("get", "/mesh/stats", None),
        ("post", "/search/query", {"query": "governance"}),
        ("get", "/search/health", None),
    ]
    for method, path, payload in unauthenticated:
        response = client.request(method, path, json=payload)
        assert response.status_code == 401, path
    assert calls["mesh"] == 0

    class _Mesh:
        def query(self, **_kwargs: object) -> list[dict[str, str]]:
            return [{"id": "node-1"}]

    monkeypatch.setattr(mesh_routes, "_get_mesh", lambda: _Mesh())
    mesh_ok = client.post("/mesh/query", headers={"x-api-key": "demo_key_12345"}, json={"text": "governance"})
    search_ok = client.post(
        "/search/enrich",
        headers={"SCBE_api_key": "demo_key_12345"},
        json={"title": "note", "content": "public governance note"},
    )
    assert mesh_ok.status_code == 200
    assert search_ok.status_code == 200


def test_connector_registration_rejects_unsafe_destinations_and_headers(mvp_api) -> None:
    from fastapi.testclient import TestClient

    client = TestClient(mvp_api.app)
    headers = {"x-api-key": "demo_key_12345"}
    rejected = [
        {"name": "metadata", "kind": "generic_webhook", "endpoint_url": "https://169.254.169.254/latest/meta-data"},
        {"name": "file", "kind": "generic_webhook", "endpoint_url": "file:///etc/passwd"},
        {"name": "loopback", "kind": "n8n", "endpoint_url": "http://127.0.0.1:5678/webhook/flow"},
        {"name": "shop-ip", "kind": "shopify", "shop_domain": "169.254.169.254"},
        {"name": "shop-suffix", "kind": "shopify", "shop_domain": "shop.myshopify.com.evil.com"},
        {
            "name": "host-header",
            "kind": "generic_webhook",
            "endpoint_url": "https://hooks.zapier.com/hooks/catch/1/abc",
            "default_headers": {"Host": "169.254.169.254"},
        },
    ]
    for payload in rejected:
        response = client.post("/mobile/connectors", headers=headers, json=payload)
        assert response.status_code == 400, payload["name"]
        assert "latest/meta-data" not in response.text
        assert "passwd" not in response.text

    allowed = client.post(
        "/mobile/connectors",
        headers=headers,
        json={"name": "zapier", "kind": "zapier", "endpoint_url": "https://hooks.zapier.com/hooks/catch/1/abc"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["endpoint_url"] == "https://hooks.zapier.com/hooks/catch/1/abc"


def test_dispatch_calls_policy_helper_and_blocks_metadata_without_connecting(
    mvp_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refuse_network(monkeypatch)
    monkeypatch.setattr(
        mvp_api.urlrequest,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("raw urlopen")),
    )
    connector_id = "conn_metadata"
    mvp_api.CONNECTOR_STORE[connector_id] = {
        "connector_id": connector_id,
        "enabled": True,
        "endpoint_url": "https://169.254.169.254/latest/meta-data",
        "auth_type": "bearer",
        "auth_token": "super-secret",
        "auth_header_name": "x-api-key",
    }
    record = {
        "execution_mode": "connector",
        "connector_id": connector_id,
        "payload_mode": "scbe_step",
        "goal_id": "goal",
        "channel": "custom",
        "priority": "normal",
        "targets": [],
        "owner": "demo_user",
        "default_headers": {},
        "http_method": "POST",
        "timeout_seconds": 2,
    }
    blocked = mvp_api._dispatch_connector_step(record, {"name": "analyze_goal", "risk": "low"})
    assert blocked["ok"] is False
    assert blocked["code"] == "connector_destination_blocked"
    assert "super-secret" not in str(blocked)

    captured: dict[str, Any] = {}

    def fake_open(req: urllib.request.Request, timeout: float) -> _FakeResponse:
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["authorization"] = req.get_header("Authorization")
        return _FakeResponse()

    monkeypatch.setattr(mvp_api, "open_connector_request", fake_open)
    mvp_api.CONNECTOR_STORE[connector_id]["endpoint_url"] = "https://hooks.zapier.com/hooks/catch/1/abc"
    allowed = mvp_api._dispatch_connector_step(record, {"name": "analyze_goal", "risk": "low"})
    assert allowed["ok"] is True
    assert captured["url"] == "https://hooks.zapier.com/hooks/catch/1/abc"
    assert captured["authorization"] == "Bearer super-secret"
    mvp_api.CONNECTOR_STORE.pop(connector_id, None)


@pytest.fixture
def governance_api():
    pytest.importorskip("fastapi")
    import api.main as governance_api

    saved_keys = dict(governance_api.VALID_API_KEYS)
    saved_decisions = dict(governance_api.DECISIONS_STORE)
    governance_api.VALID_API_KEYS.clear()
    governance_api.VALID_API_KEYS.update({"tenant-a-key": "tenant_a", "tenant-b-key": "tenant_b"})
    governance_api.DECISIONS_STORE.clear()
    try:
        yield governance_api
    finally:
        governance_api.VALID_API_KEYS.clear()
        governance_api.VALID_API_KEYS.update(saved_keys)
        governance_api.DECISIONS_STORE.clear()
        governance_api.DECISIONS_STORE.update(saved_decisions)


def test_audit_read_is_isolated_by_tenant(governance_api) -> None:
    from fastapi.testclient import TestClient

    governance_api.DECISIONS_STORE["dec_victim"] = {
        "decision_id": "dec_victim",
        "tenant": "tenant_a",
        "decision": "DENY",
        "target": "secret-target",
    }
    governance_api.DECISIONS_STORE["dec_unowned"] = {"decision_id": "dec_unowned", "decision": "ALLOW"}
    client = TestClient(governance_api.app)

    missing = client.get("/v1/audit/dec_victim")
    assert missing.status_code == 401
    wrong = client.get("/v1/audit/dec_victim", headers={"X-API-Key": "not-a-key"})
    assert wrong.status_code == 403
    cross = client.get("/v1/audit/dec_victim", headers={"SCBE_api_key": "tenant-b-key"})
    assert cross.status_code == 404
    assert "secret-target" not in cross.text
    absent = client.get("/v1/audit/dec_missing", headers={"X-API-Key": "tenant-a-key"})
    assert absent.status_code == 404
    assert absent.json()["detail"] == cross.json()["detail"]
    owner = client.get("/v1/audit/dec_victim", headers={"X-API-Key": "tenant-a-key"})
    assert owner.status_code == 200
    assert owner.json()["tenant"] == "tenant_a"
    assert owner.json()["target"] == "secret-target"
    unowned = client.get("/v1/audit/dec_unowned", headers={"X-API-Key": "tenant-a-key"})
    assert unowned.status_code == 404


def test_governance_mesh_requires_api_key(governance_api, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    import src.api.mesh_routes as mesh_routes

    def forbidden_mesh() -> None:
        raise AssertionError("unauthenticated mesh handler ran")

    monkeypatch.setattr(mesh_routes, "_get_mesh", forbidden_mesh)
    client = TestClient(governance_api.app)
    denied = client.post("/mesh/query", json={"text": "shared index"})
    assert denied.status_code == 401

    class _Mesh:
        def stats(self) -> dict[str, bool]:
            return {"ok": True}

    monkeypatch.setattr(mesh_routes, "_get_mesh", lambda: _Mesh())
    allowed = client.get("/mesh/stats", headers={"X-API-Key": "tenant-a-key"})
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True
