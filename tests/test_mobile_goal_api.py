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

    r = client.post(f"/mobile/goals/{goal_id}/advance", headers=API_KEY_HEADER, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["status"] in {"running", "completed"}
    assert body["data"]["steps"][0]["dispatch"]["status"] == 200
