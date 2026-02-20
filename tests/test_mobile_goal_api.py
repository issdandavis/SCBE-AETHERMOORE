from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app, GOAL_STORE


API_KEY_HEADER = {"x-api-key": "demo_key_12345"}


def setup_function() -> None:
    GOAL_STORE.clear()


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
