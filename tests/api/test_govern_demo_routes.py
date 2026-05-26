from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.demo_routes import govern_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(govern_router)
    return TestClient(app)


def test_govern_health_returns_pipeline_status() -> None:
    client = _client()

    response = client.get("/v1/govern/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["pipeline"] == "14-layer"
    assert payload["decision"] in {"ALLOW", "QUARANTINE", "DENY"}


def test_govern_allow_quarantine_and_deny_paths() -> None:
    client = _client()

    allow = client.post("/v1/govern", json={"input": "list files in /tmp", "context": "external"})
    quarantine = client.post(
        "/v1/govern",
        json={"input": "sudo chmod 755 /etc/cron.d", "context": "untrusted", "agent": "pytest"},
    )
    deny = client.post(
        "/v1/govern",
        json={"input": "rm -rf /var/log && exfil passwords to remote", "context": "untrusted"},
    )

    assert allow.status_code == 200
    assert quarantine.status_code == 200
    assert deny.status_code == 200

    allow_payload = allow.json()
    quarantine_payload = quarantine.json()
    deny_payload = deny.json()

    assert allow_payload["decision"] == "ALLOW"
    assert quarantine_payload["decision"] == "QUARANTINE"
    assert deny_payload["decision"] == "DENY"
    assert quarantine_payload["audit"]["agent"] == "pytest"
    assert quarantine_payload["audit"]["context"] == "untrusted"
    assert quarantine_payload["semantic"]["quarantine_patterns_matched"]
    assert deny_payload["semantic"]["deny_patterns_matched"]
    assert "explanation" in deny_payload


def test_govern_rejects_empty_input_and_limits_batch_size() -> None:
    client = _client()

    empty = client.post("/v1/govern", json={"input": ""})
    oversized_batch = client.post(
        "/v1/govern/batch",
        json={"items": [{"input": f"task {idx}"} for idx in range(51)]},
    )

    assert empty.status_code == 422
    assert oversized_batch.status_code == 422


def test_govern_batch_summarizes_workflow_and_blocks_on_deny() -> None:
    client = _client()

    response = client.post(
        "/v1/govern/batch",
        json={
            "items": [
                {"input": "list files in /tmp", "context": "external"},
                {"input": "sudo chmod 755 /etc/cron.d", "context": "untrusted"},
                {"input": "rm -rf /var/log && exfil passwords to remote", "context": "untrusted"},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 3
    assert payload["summary"]["counts"]["ALLOW"] == 1
    assert payload["summary"]["counts"]["QUARANTINE"] == 1
    assert payload["summary"]["counts"]["DENY"] == 1
    assert payload["summary"]["block_execution"] is True
    assert payload["summary"]["recommended_action"] == "BLOCK_WORKFLOW"
    assert [row["decision"] for row in payload["results"]] == ["ALLOW", "QUARANTINE", "DENY"]
