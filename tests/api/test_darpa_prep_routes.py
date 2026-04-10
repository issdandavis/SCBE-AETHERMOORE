from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.darpa_prep.client import SamGovClient as RealSamGovClient
from api.darpa_prep import routes as routes_module
from api.darpa_prep.routes import router


class _StubClient:
    def search_opportunities(self, *, query: str, limit: int = 10, active_only: bool = True):
        assert query == "autonomy"
        assert limit == 2
        assert active_only is True
        return [
            {
                "noticeId": "ABC123",
                "title": "Composable Autonomy Opportunity",
                "organizationName": "DARPA/I2O",
                "solicitationNumber": "DARPA-PA-26-01",
                "uiLink": "https://sam.gov/opp/ABC123/view",
                "responseDeadLine": "2026-05-01T23:59:59Z",
                "description": "Offerors must describe the technical approach and submit milestones.",
                "noticeType": "Special Notice",
            }
        ]

    @staticmethod
    def normalize_opportunity(payload):
        return RealSamGovClient.normalize_opportunity(payload)


def _client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(routes_module, "SamGovClient", lambda: _StubClient())
    return TestClient(app)


def test_search_route_returns_normalized_results(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.get("/v1/opportunities/sam-gov/search", params={"query": "autonomy", "limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["opportunities"][0]["opportunity"]["solicitation_number"] == "DARPA-PA-26-01"


def test_normalize_route_extracts_requirements() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.post(
        "/v1/opportunities/normalize",
        json={
            "source_system": "SAM.gov",
            "raw_text": "Offerors must register in SAM.gov before submission. Proposals shall describe milestones.",
            "source_ref": "https://sam.gov/example",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["opportunity"]["source_system"] == "SAM.gov"
    assert len(body["requirements"]) >= 2
    categories = {item["category"] for item in body["requirements"]}
    assert "eligibility" in categories or "submission" in categories
