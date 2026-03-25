from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import src.api.saas_routes as saas_routes
from api.metering import (
    AUDIT_REPORT_GENERATIONS,
    GOVERNANCE_EVALUATIONS,
    WORKFLOW_EXECUTIONS,
    MeteringStore,
)
from src.api.main import app

API_KEY_HEADER = {"x-api-key": "demo_key_12345"}
PILOT_KEY_HEADER = {"x-api-key": "pilot_key_67890"}


@pytest.fixture
def client(tmp_path) -> TestClient:
    saas_routes.reset_saas_state()
    saas_routes.set_saas_metering_store(MeteringStore(str(tmp_path / "saas_metering.db")))
    return TestClient(app)


def _create_tenant(client: TestClient, name: str = "SCBE Design Partner") -> str:
    response = client.post(
        "/saas/tenants",
        headers=API_KEY_HEADER,
        json={"name": name, "plan": "growth", "governance_profile": "strict", "region": "us"},
    )
    assert response.status_code == 200
    return response.json()["data"]["tenant_id"]


def _create_flock(client: TestClient, tenant_id: str, name: str = "demo-flock") -> str:
    response = client.post(
        f"/saas/tenants/{tenant_id}/flocks",
        headers=API_KEY_HEADER,
        json={
            "name": name,
            "mission": "Run governed autonomous workflows",
            "heartbeat_timeout_seconds": 10,
            "freeze_after_missed_heartbeats": 2,
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["flock_id"]


def test_create_tenant_and_flock(client: TestClient) -> None:
    tenant_id = _create_tenant(client)
    flock_id = _create_flock(client, tenant_id)

    tenant_list = client.get("/saas/tenants", headers=API_KEY_HEADER)
    assert tenant_list.status_code == 200
    assert tenant_list.json()["data"][0]["tenant_id"] == tenant_id

    flock = client.get(f"/saas/flocks/{flock_id}", headers=API_KEY_HEADER)
    assert flock.status_code == 200
    body = flock.json()["data"]
    assert body["tenant_id"] == tenant_id
    assert body["dashboard"]["health"]["total"] == 0


def test_tenant_isolation_between_api_keys(client: TestClient) -> None:
    tenant_id = _create_tenant(client)

    response = client.get(f"/saas/tenants/{tenant_id}", headers=PILOT_KEY_HEADER)
    assert response.status_code == 404


def test_task_flow_updates_workflow_usage(client: TestClient) -> None:
    tenant_id = _create_tenant(client)
    flock_id = _create_flock(client, tenant_id)

    sheep_resp = client.post(
        f"/saas/flocks/{flock_id}/sheep",
        headers=API_KEY_HEADER,
        json={"name": "Builder", "track": "functions"},
    )
    assert sheep_resp.status_code == 200
    sheep_id = sheep_resp.json()["data"]["sheep_id"]

    task_resp = client.post(
        f"/saas/flocks/{flock_id}/tasks",
        headers=API_KEY_HEADER,
        json={
            "description": "Build the launch demo",
            "track": "functions",
            "priority": 3,
            "auto_assign": True,
            "sheep_id": sheep_id,
        },
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["data"]["dashboard"]["tasks"][0]["task_id"]

    complete = client.post(
        f"/saas/flocks/{flock_id}/tasks/{task_id}/complete",
        headers=API_KEY_HEADER,
        json={"success": True, "result": {"demo": "ready"}},
    )
    assert complete.status_code == 200
    dashboard = complete.json()["data"]["dashboard"]
    assert dashboard["health"]["completed_tasks"] == 1

    usage = client.get(
        f"/saas/tenants/{tenant_id}/usage",
        headers=API_KEY_HEADER,
        params={"year": datetime.utcnow().year, "month": datetime.utcnow().month},
    )
    assert usage.status_code == 200
    totals = usage.json()["data"]["totals"]
    assert totals[WORKFLOW_EXECUTIONS] == 1


def test_governance_and_audit_increment_usage(client: TestClient) -> None:
    tenant_id = _create_tenant(client)
    flock_id = _create_flock(client, tenant_id)

    validator = client.post(
        f"/saas/flocks/{flock_id}/sheep",
        headers=API_KEY_HEADER,
        json={"name": "Validator", "track": "governance"},
    )
    assert validator.status_code == 200

    gov = client.post(
        "/saas/governance/check",
        headers=API_KEY_HEADER,
        json={"tenant_id": tenant_id, "flock_id": flock_id, "action": "deploy-enterprise-pilot"},
    )
    assert gov.status_code == 200
    assert gov.json()["data"]["consensus"] == "ALLOW"

    audit = client.get(f"/saas/tenants/{tenant_id}/audit-report", headers=API_KEY_HEADER)
    assert audit.status_code == 200
    totals = audit.json()["data"]["totals"]
    assert totals["flocks"] == 1
    assert totals["agents"] == 1

    usage = client.get(
        f"/saas/tenants/{tenant_id}/usage",
        headers=API_KEY_HEADER,
        params={"year": datetime.utcnow().year, "month": datetime.utcnow().month},
    )
    assert usage.status_code == 200
    usage_totals = usage.json()["data"]["totals"]
    assert usage_totals[GOVERNANCE_EVALUATIONS] == 1
    assert usage_totals[AUDIT_REPORT_GENERATIONS] == 1


def test_refresh_reassigns_stale_task(client: TestClient) -> None:
    tenant_id = _create_tenant(client)
    flock_id = _create_flock(client, tenant_id)

    sheep_one = client.post(
        f"/saas/flocks/{flock_id}/sheep",
        headers=API_KEY_HEADER,
        json={"name": "Alpha", "track": "system"},
    )
    sheep_two = client.post(
        f"/saas/flocks/{flock_id}/sheep",
        headers=API_KEY_HEADER,
        json={"name": "Beta", "track": "system"},
    )
    assert sheep_one.status_code == 200
    assert sheep_two.status_code == 200
    sheep_one_id = sheep_one.json()["data"]["sheep_id"]
    sheep_two_id = sheep_two.json()["data"]["sheep_id"]

    task_resp = client.post(
        f"/saas/flocks/{flock_id}/tasks",
        headers=API_KEY_HEADER,
        json={
            "description": "Recover stalled customer workflow",
            "track": "system",
            "priority": 2,
            "auto_assign": True,
            "sheep_id": sheep_one_id,
        },
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["data"]["dashboard"]["tasks"][0]["task_id"]

    flock = saas_routes.SAAS_FLOCKS[flock_id]["flock"]
    flock.sheep[sheep_one_id].last_heartbeat = flock.sheep[sheep_one_id].last_heartbeat - 120

    refresh = client.post(
        f"/saas/flocks/{flock_id}/refresh",
        headers=API_KEY_HEADER,
        json={"auto_redistribute": True},
    )
    assert refresh.status_code == 200
    body = refresh.json()["data"]
    assert sheep_one_id in body["refresh"]["stale_agents"]
    assert body["refresh"]["reassigned_tasks"] == 1

    tasks = {task["task_id"]: task for task in body["flock"]["dashboard"]["tasks"]}
    assert tasks[task_id]["status"] == "active"
    assert tasks[task_id]["owner"] == sheep_two_id
