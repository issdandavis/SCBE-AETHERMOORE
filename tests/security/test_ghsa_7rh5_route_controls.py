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
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:8080")
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


class _AuditDocument:
    def __init__(self, rows, key):
        self.rows, self.key = rows, key

    @property
    def exists(self):
        return self.key in self.rows

    def get(self):
        return self

    def to_dict(self):
        return dict(self.rows[self.key])

    def set(self, row):
        self.rows[self.key] = dict(row)

    def update(self, values):
        self.rows[self.key].update(values)


class _AuditQuery:
    def __init__(self, rows, filters=(), cap=None):
        self.rows, self.filters, self.cap = rows, filters, cap

    def document(self, key):
        return _AuditDocument(self.rows, key)

    def where(self, field, op, value):
        assert op == "=="
        return _AuditQuery(self.rows, (*self.filters, (field, value)), self.cap)

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, cap):
        # Tenant restriction must be applied before the limit.
        assert any(field == "tenant" for field, _ in self.filters)
        return _AuditQuery(self.rows, self.filters, cap)

    def stream(self):
        keys = [key for key, row in self.rows.items() if all(row.get(f) == v for f, v in self.filters)]
        return [_AuditDocument(self.rows, key) for key in keys[: self.cap]]


class _AuditDB:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return _AuditQuery(self.collections.setdefault(name, {}))


@pytest.fixture(params=[False, True], ids=["cache", "firestore"])
def isolated_audit_store(request, monkeypatch):
    import api.persistence as persistence

    monkeypatch.setattr(persistence, "_get_db", lambda: None)
    store = persistence.SCBEPersistence()
    if request.param:
        store.db = _AuditDB()
    return store


def _write_audit(store, tenant, decision="DENY"):
    return store.log_decision(
        agent_id="shared-agent",
        action="READ",
        decision=decision,
        trust_score=0.5,
        risk_level="HIGH",
        context={"tenant": "tenant_b"},
        consensus_result={},
        tenant=tenant,
    )


def test_persistent_audit_scope_and_derived_alerts(isolated_audit_store):
    store = isolated_audit_store
    victim = _write_audit(store, "tenant_a")
    own = _write_audit(store, "tenant_b")
    ownerless = {
        **store.get_audit_log(victim, tenant="tenant_a"),
        "audit_id": "legacy",
        "context": {"tenant": "tenant_b"},
    }
    ownerless.pop("tenant")
    if store.db:
        store.db.collection(store.COLLECTION_AUDIT).document("legacy").set(ownerless)
    else:
        store._local_cache["audit"].insert(0, ownerless)

    rows = store.get_audit_logs(tenant="tenant_b", agent_id="shared-agent", decision="DENY", limit=1)
    assert [row["audit_id"] for row in rows] == [own]
    assert store.get_audit_log(victim, tenant="tenant_b") is None
    assert store.get_audit_log("legacy", tenant="tenant_b") is None
    assert store.get_audit_log(victim, tenant="tenant_a")["tenant"] == "tenant_a"
    assert store.get_metrics(tenant="tenant_b")["total_decisions"] == 1
    assert store.get_audit_logs(tenant="tenant_b", decision="ALLOW") == []

    alert_a = store.get_pending_alerts(tenant="tenant_a")[0]
    assert store.mark_alert_sent(alert_a["alert_id"], tenant="tenant_b") is False
    assert store.get_pending_alerts(tenant="tenant_a")[0]["sent"] is False
    assert store.mark_alert_sent(alert_a["alert_id"], tenant="tenant_a") is True
    assert store.get_pending_alerts(tenant="tenant_a") == []
    assert len(store.get_pending_alerts(tenant="tenant_b")) == 1
    with pytest.raises(ValueError):
        store.get_audit_logs(tenant="")


def test_firestore_error_fallback_keeps_tenant_filter(isolated_audit_store):
    store = isolated_audit_store
    store.db = None
    _write_audit(store, "tenant_a")
    own = _write_audit(store, "tenant_b")

    class FailedDB:
        def collection(self, _name):
            raise RuntimeError("database unavailable")

    store.db = FailedDB()
    assert [row["audit_id"] for row in store.get_audit_logs(tenant="tenant_b")] == [own]
    assert all(row["tenant"] == "tenant_b" for row in store.get_pending_alerts(tenant="tenant_b"))


def test_audit_routes_stamp_and_enforce_authenticated_tenant(governance_api, isolated_audit_store, monkeypatch):
    from fastapi.testclient import TestClient

    store = isolated_audit_store
    monkeypatch.setattr(governance_api, "get_persistence", lambda: store)
    client = TestClient(governance_api.app)
    headers_a = {"X-API-Key": "tenant-a-key"}
    headers_b = {"X-API-Key": "tenant-b-key"}
    response = client.post(
        "/v1/authorize",
        headers=headers_a,
        json={"agent_id": "writer-agent", "action": "READ", "target": "private", "context": {"tenant": "tenant_b"}},
    )
    assert response.status_code == 200
    written = store.get_audit_logs(tenant="tenant_a")
    assert len(written) == 1
    assert written[0]["context"]["tenant"] == "tenant_b"
    assert written[0]["tenant"] == "tenant_a"
    _write_audit(store, "tenant_a")
    _write_audit(store, "tenant_b")

    assert client.get("/v1/audit").status_code == 401
    assert client.get("/v1/audit", headers={"X-API-Key": "invalid"}).status_code == 403
    listing = client.get("/v1/audit?tenant=tenant_a&agent_id=shared-agent&limit=1", headers=headers_b)
    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert all(row["tenant"] == "tenant_b" for row in listing.json()["logs"])
    for pending in ["true", "false"]:
        alerts = client.get(f"/v1/alerts?pending_only={pending}", headers=headers_b)
        assert alerts.status_code == 200
        assert len(alerts.json()) == 1
        assert alerts.json()[0]["audit_id"] == store.get_audit_logs(tenant="tenant_b")[0]["audit_id"]
    assert client.get("/v1/metrics", headers=headers_b).json()["total_decisions"] == 1
    alert_id = store.get_pending_alerts(tenant="tenant_a")[0]["alert_id"]
    assert client.post(f"/v1/alerts/{alert_id}/ack", headers=headers_b).status_code == 404
    assert client.post(f"/v1/alerts/{alert_id}/ack", headers=headers_a).status_code == 200


def test_explicit_shopify_endpoint_keeps_graphql_default(mvp_api):
    from fastapi.testclient import TestClient

    client = TestClient(mvp_api.app)
    for mode in [None, "raw_step"]:
        payload = {
            "name": f"explicit-shopify-{mode}",
            "kind": "shopify",
            "endpoint_url": "https://demo-store.myshopify.com/admin/api/2025-10/graphql.json",
        }
        if mode:
            payload["payload_mode"] = mode
        response = client.post("/mobile/connectors", headers={"x-api-key": "demo_key_12345"}, json=payload)
        assert response.status_code == 200
        assert response.json()["data"]["payload_mode"] == (mode or "shopify_graphql_read")
        mvp_api.CONNECTOR_STORE.pop(response.json()["data"]["connector_id"])


def test_security_regressions_are_in_core_ci():
    from scripts.system.run_core_python_checks import build_pytest_command, CORE_SMOKE_PATHS

    command = build_pytest_command(CORE_SMOKE_PATHS)
    for path in ["tests/security/test_ghsa_7rh5_route_controls.py", "tests/test_mobile_goal_api.py"]:
        assert path in command
        assert f"--ignore={path}" not in command


def test_audit_listing_does_not_disclose_other_tenants(governance_api, isolated_audit_store, monkeypatch):
    from fastapi.testclient import TestClient

    store = isolated_audit_store
    store.db = None
    store._local_cache["audit"] = [
        {"audit_id": "victim", "tenant": "tenant_a", "agent_id": "same-agent", "decision": "DENY"},
        {"audit_id": "legacy", "agent_id": "same-agent", "context": {"tenant": "tenant_b"}, "decision": "DENY"},
        {"audit_id": "own", "tenant": "tenant_b", "agent_id": "same-agent", "decision": "DENY"},
    ]
    monkeypatch.setattr(governance_api, "get_persistence", lambda: store)
    response = TestClient(governance_api.app).get("/v1/audit?limit=1", headers={"X-API-Key": "tenant-b-key"})
    assert response.status_code == 200
    assert [row["audit_id"] for row in response.json()["logs"]] == ["own"]


@pytest.mark.parametrize(
    "url",
    [
        "https://hooks.zapier.com:abc/hook",
        "https://hooks.zapier.com:65536/hook",
        "https://hooks.zapier.com:-1/hook",
        "https://[::1/hook",
        "https://01.2.3.4/hook",
        "https://hooks.zapier.com\uff1a443/hook",
    ],
)
def test_malformed_connector_urls_are_controlled_rejections(mvp_api, monkeypatch, url):
    from fastapi.testclient import TestClient

    _refuse_network(monkeypatch)
    with pytest.raises(ConnectorURLRejected):
        validate_connector_endpoint(url, resolve_dns=False)
    with pytest.raises(ConnectorURLRejected):
        validate_connector_endpoint(url, resolve_dns=True)
    previous_ids = set(mvp_api.CONNECTOR_STORE)
    response = TestClient(mvp_api.app).post(
        "/mobile/connectors",
        headers={"x-api-key": "demo_key_12345"},
        json={"name": "invalid-url", "kind": "generic_webhook", "endpoint_url": url},
    )
    assert response.status_code == 400
    assert response.json() == {"status": "error", "error": "connector endpoint is not allowed", "code": 400}
    assert set(mvp_api.CONNECTOR_STORE) == previous_ids


@pytest.mark.parametrize(
    "domain", ["https://shop.myshopify.com:abc", "https://[broken", "https://shop.myshopify.com:65536"]
)
def test_malformed_shopify_domain_is_controlled_rejection(mvp_api, domain):
    from fastapi.testclient import TestClient

    response = TestClient(mvp_api.app).post(
        "/mobile/connectors",
        headers={"x-api-key": "demo_key_12345"},
        json={"name": "invalid-shop", "kind": "shopify", "shop_domain": domain},
    )
    assert response.status_code == 400


def test_valid_connector_port_is_preserved():
    assert validate_connector_endpoint("https://hooks.example.com:8443/hook", resolve_dns=False) == (
        "https://hooks.example.com:8443/hook"
    )
