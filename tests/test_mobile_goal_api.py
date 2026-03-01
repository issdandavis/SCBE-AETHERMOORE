from __future__ import annotations

from fastapi.testclient import TestClient

import src.api.main as api_main
from src.api.main import app, GOAL_STORE, CONNECTOR_STORE


API_KEY_HEADER = {"x-api-key": "demo_key_12345"}


def setup_function() -> None:
    GOAL_STORE.clear()
    CONNECTOR_STORE.clear()


def test_mobile_goal_create_and_list() -> None:
    client = TestClient(app)

    payload = {
        "goal": "Run today's storefront operations and resolve customer messages",
        "channel": "store_ops",
        "priority": "high",
        "execution_mode": "simulate",
        "targets": ["https://example-store.test/admin"],
        "require_human_for_high_risk": True,
    }
    create = client.post("/mobile/goals", headers=API_KEY_HEADER, json=payload)
    assert create.status_code == 200
    body = create.json()
    assert body["status"] == "accepted"
    assert body["data"]["status"] == "queued"
    assert body["data"]["channel"] == "store_ops"

    listed = client.get("/mobile/goals", headers=API_KEY_HEADER)
    assert listed.status_code == 200
    rows = listed.json()["data"]
    assert len(rows) == 1
    assert rows[0]["goal"] == payload["goal"]


def test_mobile_goal_requires_approval_for_high_risk_step() -> None:
    client = TestClient(app)
    create = client.post(
        "/mobile/goals",
        headers=API_KEY_HEADER,
        json={
            "goal": "Operate online store autonomously",
            "channel": "store_ops",
            "priority": "critical",
            "execution_mode": "simulate",
            "targets": [],
            "require_human_for_high_risk": True,
        },
    )
    assert create.status_code == 200
    goal_id = create.json()["data"]["goal_id"]

    # Step 1 (low risk)
    r1 = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "running"

    # Step 2 (medium risk)
    r2 = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "running"

    # Step 3 (high risk) should block and require review
    r3 = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r3.status_code == 200
    assert r3.json()["status"] == "blocked"
    assert r3.json()["data"]["status"] == "review_required"

    # Approve then continue
    appr = client.post(
        f"/mobile/goals/{goal_id}/approve",
        headers=API_KEY_HEADER,
        json={"note": "approve high risk action from mobile"},
    )
    assert appr.status_code == 200
    assert appr.json()["data"]["approved_high_risk"] is True

    r4 = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r4.status_code == 200
    assert r4.json()["data"]["status"] in {"running", "completed"}

    # Final step
    r5 = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r5.status_code == 200
    assert r5.json()["data"]["status"] == "completed"


def test_connector_register_and_bind_to_goal() -> None:
    client = TestClient(app)

    conn_resp = client.post(
        "/mobile/connectors",
        headers=API_KEY_HEADER,
        json={
            "name": "n8n-store-ops",
            "kind": "n8n",
            "endpoint_url": "https://example.invalid/webhook/store-ops",
            "auth_type": "header",
            "auth_header_name": "x-n8n-key",
            "auth_token": "test-token",
            "enabled": True,
        },
    )
    assert conn_resp.status_code == 200
    connector_id = conn_resp.json()["data"]["connector_id"]

    goal_resp = client.post(
        "/mobile/goals",
        headers=API_KEY_HEADER,
        json={
            "goal": "Run store workflow through connector",
            "channel": "store_ops",
            "priority": "high",
            "execution_mode": "simulate",
            "targets": [],
            "require_human_for_high_risk": True,
        },
    )
    assert goal_resp.status_code == 200
    goal_id = goal_resp.json()["data"]["goal_id"]

    bind_resp = client.post(
        f"/mobile/goals/{goal_id}/bind-connector",
        headers=API_KEY_HEADER,
        json={"connector_id": connector_id},
    )
    assert bind_resp.status_code == 200
    assert bind_resp.json()["data"]["execution_mode"] == "connector"
    assert bind_resp.json()["data"]["connector_id"] == connector_id


def test_connector_templates_and_shopify_autobuild() -> None:
    client = TestClient(app)

    templates = client.get("/mobile/connectors/templates", headers=API_KEY_HEADER)
    assert templates.status_code == 200
    rows = templates.json()["data"]
    assert any(t["kind"] == "zapier" for t in rows)
    assert any(t["kind"] == "shopify" for t in rows)

    shopify_conn = client.post(
        "/mobile/connectors",
        headers=API_KEY_HEADER,
        json={
            "name": "shopify-admin-read",
            "kind": "shopify",
            "shop_domain": "demo-store.myshopify.com",
            "auth_type": "header",
            "auth_header_name": "X-Shopify-Access-Token",
            "auth_token": "test-token",
            "enabled": True,
        },
    )
    assert shopify_conn.status_code == 200
    data = shopify_conn.json()["data"]
    assert data["endpoint_url"] == "https://demo-store.myshopify.com/admin/api/2025-10/graphql.json"
    assert data["payload_mode"] == "shopify_graphql_read"
    assert data["auth_header_name"] == "X-Shopify-Access-Token"


def test_connector_mode_dispatch_success_path(monkeypatch) -> None:
    client = TestClient(app)

    conn_resp = client.post(
        "/mobile/connectors",
        headers=API_KEY_HEADER,
        json={
            "name": "zapier-store-ops",
            "kind": "zapier",
            "endpoint_url": "https://example.invalid/hooks/catch",
            "auth_type": "none",
            "enabled": True,
        },
    )
    connector_id = conn_resp.json()["data"]["connector_id"]

    goal_resp = client.post(
        "/mobile/goals",
        headers=API_KEY_HEADER,
        json={
            "goal": "Connector mode execution",
            "channel": "store_ops",
            "priority": "normal",
            "execution_mode": "connector",
            "connector_id": connector_id,
            "targets": [],
            "require_human_for_high_risk": False,
        },
    )
    assert goal_resp.status_code == 200
    goal_id = goal_resp.json()["data"]["goal_id"]

    monkeypatch.setattr(
        api_main,
        "_dispatch_connector_step",
        lambda record, step: {"ok": True, "status": 200, "detail": "accepted"},
    )
    monkeypatch.setattr(
        api_main,
        "_evaluate_connector_policy",
        lambda record, step: {
            "version": "policy_v1",
            "verdict": "ALLOW",
            "decision": "ALLOW",
            "risk_score": 0.1,
            "coherence": 0.9,
            "threat_count": 0,
            "timestamp": "2026-03-01T00:00:00Z",
            "profile": "enterprise",
        },
    )

    r = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["status"] in {"running", "completed"}
    assert body["data"]["steps"][0]["dispatch"]["status"] == 200


def test_connector_mode_policy_rejects_and_logs(monkeypatch) -> None:
    client = TestClient(app)

    conn_resp = client.post(
        "/mobile/connectors",
        headers=API_KEY_HEADER,
        json={
            "name": "zapier-reject-test",
            "kind": "n8n",
            "endpoint_url": "https://example.invalid/hooks/reject",
            "auth_type": "none",
            "enabled": True,
        },
    )
    connector_id = conn_resp.json()["data"]["connector_id"]

    goal_resp = client.post(
        "/mobile/goals",
        headers=API_KEY_HEADER,
        json={
            "goal": "Connector mode policy rejection test",
            "channel": "store_ops",
            "priority": "normal",
            "execution_mode": "connector",
            "connector_id": connector_id,
            "targets": [],
            "require_human_for_high_risk": False,
        },
    )
    goal_id = goal_resp.json()["data"]["goal_id"]

    monkeypatch.setattr(
        api_main,
        "_evaluate_connector_policy",
        lambda record, step: {
            "version": "policy_v1",
            "verdict": "DENY",
            "decision": "DENY",
            "risk_score": 0.95,
            "coherence": 0.0,
            "threat_count": 4,
            "timestamp": "2026-03-01T00:00:00Z",
            "profile": "enterprise",
        },
    )

    r = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["governance"]["verdict"] == "DENY"


def test_connector_webhook_smoke(monkeypatch) -> None:
    client = TestClient(app)

    conn_resp = client.post(
        "/mobile/connectors",
        headers=API_KEY_HEADER,
        json={
            "name": "shopify-webhook-smoke",
            "kind": "shopify",
            "shop_domain": "demo-store.myshopify.com",
            "auth_type": "header",
            "auth_header_name": "X-Shopify-Access-Token",
            "auth_token": "test-token",
            "enabled": True,
            "webhook_url": "https://example.invalid/hooks/webhook",
        },
    )
    connector_id = conn_resp.json()["data"]["connector_id"]

    goal_resp = client.post(
        "/mobile/goals",
        headers=API_KEY_HEADER,
        json={
            "goal": "Connector mode webhook smoke",
            "channel": "store_ops",
            "priority": "normal",
            "execution_mode": "connector",
            "connector_id": connector_id,
            "targets": [],
            "require_human_for_high_risk": False,
        },
    )
    goal_id = goal_resp.json()["data"]["goal_id"]

    calls = []
    monkeypatch.setattr(
        api_main,
        "_evaluate_connector_policy",
        lambda record, step: {
            "version": "policy_v1",
            "verdict": "ALLOW",
            "decision": "ALLOW",
            "risk_score": 0.1,
            "coherence": 0.9,
            "threat_count": 0,
            "timestamp": "2026-03-01T00:00:00Z",
            "profile": "enterprise",
        },
    )
    monkeypatch.setattr(
        api_main,
        "_dispatch_connector_step",
        lambda record, step: {"ok": True, "status": 200, "detail": "accepted"},
    )
    monkeypatch.setattr(
        api_main,
        "_emit_connector_webhook",
        lambda connector, payload: calls.append(payload) or {"ok": True, "status": 200},
    )

    r = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["governance"]["verdict"] == "ALLOW"
    assert calls, "expected local webhook callback payload"
    assert calls[0]["goal_id"] == goal_id
    assert calls[0]["policy"]["decision"] == "ALLOW"


def test_connector_policy_check_submit_edit_paths(monkeypatch) -> None:
    client = TestClient(app)

    conn_resp = client.post(
        "/mobile/connectors",
        headers=API_KEY_HEADER,
        json={
            "name": "policy-check-shopify",
            "kind": "shopify",
            "shop_domain": "demo-store.myshopify.com",
            "auth_type": "header",
            "auth_header_name": "X-Shopify-Access-Token",
            "auth_token": "test-token",
            "webhook_url": "https://example.invalid/hooks/policy-check",
            "enabled": True,
        },
    )
    connector_id = conn_resp.json()["data"]["connector_id"]

    calls: list[dict] = []

    allow_policy = {
        "version": "policy_v1",
        "verdict": "ALLOW",
        "decision": "ALLOW",
        "risk_score": 0.11,
        "coherence": 0.94,
        "threat_count": 0,
        "timestamp": "2026-03-01T00:00:00Z",
        "profile": "enterprise",
    }
    deny_policy = {
        "version": "policy_v1",
        "verdict": "DENY",
        "decision": "DENY",
        "risk_score": 0.99,
        "coherence": 0.01,
        "threat_count": 7,
        "timestamp": "2026-03-01T00:00:00Z",
        "profile": "enterprise",
    }

    monkeypatch.setattr(
        api_main,
        "_evaluate_connector_policy",
        lambda record, step: allow_policy,
    )
    monkeypatch.setattr(
        api_main,
        "_emit_connector_webhook",
        lambda connector, payload: calls.append(payload) or {"ok": True, "status": 200},
    )

    allow_resp = client.post(
        "/mobile/connectors/policy-check",
        headers=API_KEY_HEADER,
        json={
            "action": "submit",
            "goal": "Shopify product edit submit flow",
            "channel": "store_ops",
            "priority": "high",
            "step_risk": "medium",
            "owner": "shopify-app",
            "targets": ["gid://shopify/Product/123"],
            "connector_id": connector_id,
            "emit_webhook": True,
        },
    )
    assert allow_resp.status_code == 200
    allow_body = allow_resp.json()
    assert allow_body["action"] == "submit"
    assert allow_body["policy"]["verdict"] == "ALLOW"
    assert calls
    assert calls[0]["event"] == "policy_check"
    assert calls[0]["action"] == "submit"
    assert calls[0]["policy"]["decision"] == "ALLOW"

    calls.clear()
    monkeypatch.setattr(
        api_main,
        "_evaluate_connector_policy",
        lambda record, step: deny_policy,
    )

    deny_resp = client.post(
        "/mobile/connectors/policy-check",
        headers=API_KEY_HEADER,
        json={
            "action": "edit",
            "goal": "Shopify dangerous product delete",
            "channel": "store_ops",
            "priority": "critical",
            "step_risk": "high",
            "owner": "shopify-app",
            "targets": ["gid://shopify/Product/456"],
            "connector_id": connector_id,
            "emit_webhook": True,
        },
    )
    assert deny_resp.status_code == 200
    deny_body = deny_resp.json()
    assert deny_body["action"] == "edit"
    assert deny_body["policy"]["verdict"] == "DENY"
    assert calls
    assert calls[0]["action"] == "edit"
    assert calls[0]["policy"]["decision"] == "DENY"
