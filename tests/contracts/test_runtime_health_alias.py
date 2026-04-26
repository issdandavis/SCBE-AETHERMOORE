from __future__ import annotations

from fastapi.testclient import TestClient

import src.api.main as api_main


def test_runtime_health_aliases_match() -> None:
    with TestClient(api_main.app) as client:
        health = client.get("/health")
        versioned = client.get("/v1/health")

    assert health.status_code == 200
    assert versioned.status_code == 200
    assert health.json() == versioned.json()

