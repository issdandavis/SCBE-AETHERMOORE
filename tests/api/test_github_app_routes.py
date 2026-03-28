import hashlib
import hmac
import json

import pytest

try:
    from cryptography.fernet import Fernet  # noqa: F401
except BaseException:
    pytest.skip(
        "cryptography package not functional (cffi backend missing)",
        allow_module_level=True,
    )

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.github_app.routes import router
import api.github_app.routes as routes_module
from api.github_app.scoring import assess_pull_request_intent


class _StubService:
    def __init__(self, secret: str = "test-secret") -> None:
        self.is_configured = True
        self.secret = secret
        self.last_event = None
        self.last_payload = None
        self.last_delivery = None

    def verify_signature(self, payload_body: bytes, signature_header: str | None) -> bool:
        if not signature_header:
            return False
        digest = hmac.new(
            self.secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={digest}", signature_header)

    async def handle_event(self, *, event: str, payload: dict, delivery_id: str | None = None) -> dict:
        self.last_event = event
        self.last_payload = payload
        self.last_delivery = delivery_id
        return {
            "status": "processed",
            "event": event,
            "delivery_id": delivery_id,
        }

    def health_status(self) -> dict:
        return {"configured": True}


def _client(monkeypatch, service: _StubService | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    stub = service or _StubService()
    routes_module.get_github_app_service.cache_clear()
    monkeypatch.setattr(routes_module, "get_github_app_service", lambda: stub)
    return TestClient(app)


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_rejects_invalid_signature(monkeypatch) -> None:
    client = _client(monkeypatch)
    body = json.dumps({"zen": "Keep it logically awesome."}).encode("utf-8")
    response = client.post(
        "/v1/github-app/webhook",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=bad",
        },
        content=body,
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook signature"


def test_webhook_processes_valid_pull_request(monkeypatch) -> None:
    stub = _StubService()
    client = _client(monkeypatch, stub)
    payload = {
        "action": "opened",
        "number": 42,
        "repository": {"full_name": "issdandavis/SCBE-AETHERMOORE"},
        "pull_request": {
            "title": "Add health check",
            "body": "Includes tests and docs.",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/v1/github-app/webhook",
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": _signature(stub.secret, body),
        },
        content=body,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert stub.last_event == "pull_request"
    assert stub.last_delivery == "delivery-123"
    assert stub.last_payload["number"] == 42


def test_assess_pull_request_intent_allows_safe_change() -> None:
    assessment = assess_pull_request_intent(
        action="opened",
        actor="issda",
        repository="issdandavis/SCBE-AETHERMOORE",
        title="Add health endpoint documentation",
        body="Adds a clear rollout note, validation coverage, and docs for the new endpoint.",
        additions=42,
        deletions=6,
        changed_files_count=3,
        filenames=["docs/03-deployment/github-app-latticegate.md", "api/main.py"],
        head_sha="abc123",
    )
    assert assessment.decision == "ALLOW"
    assert assessment.safety_score >= 0.40
    assert not assessment.risk_hits


def test_assess_pull_request_intent_quarantines_risky_change() -> None:
    assessment = assess_pull_request_intent(
        action="synchronize",
        actor="issda",
        repository="issdandavis/SCBE-AETHERMOORE",
        title="Production hotfix disable auth",
        body="Skip tests and bypass auth so the deploy can land faster. Token handling changed too.",
        additions=900,
        deletions=300,
        changed_files_count=18,
        filenames=[".github/workflows/deploy.yml", "api/auth.py", ".env.production"],
        head_sha="def456",
    )
    assert assessment.decision in {"QUARANTINE", "DENY"}
    assert assessment.risk_hits
    assert assessment.privileged_files
