"""Tests for the attestation verification API endpoints.

Uses FastAPI TestClient with an injected in-memory metering store.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

# Ensure imports resolve correctly
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from api.metering import MeteringStore, ATTESTATION_VERIFICATIONS
from src.api.attest_routes import attest_router, set_attest_metering_store, ATTESTATION_VERIFICATIONS
from src.api.saas_routes import VALID_API_KEYS

# Standalone FastAPI app for testing (avoids heavy main.py imports)
from fastapi import FastAPI

_test_app = FastAPI()
_test_app.include_router(attest_router)
client = TestClient(_test_app)

API_KEY = "demo_key_12345"
HEADERS = {"x-api-key": API_KEY}


@pytest.fixture(autouse=True)
def _fresh_metering(tmp_path):
    """Inject a temp SQLite metering store for each test."""
    db = str(tmp_path / "test_metering.db")
    store = MeteringStore(db_path=db)
    set_attest_metering_store(store)
    yield store


def _valid_packet() -> dict:
    """Return a canonical valid egg-attest packet as a dict."""
    now = datetime.now(timezone.utc)
    return {
        "spec": "SCBE-AETHERMOORE/egg-attest@v1",
        "agent_id": "hkdf://H1+ctx->ed25519:7f2ac3",
        "ritual": {
            "intent_sha256": "b7b10000000000000000000000000000000000000000000000000000000000e9",
            "tongue_quorum": {
                "k": 4,
                "n": 6,
                "phi_weights": [0.618, 0.382, 0.618, 0.382, 0.618, 0.382],
            },
            "geoseal": {
                "scheme": "GeoSeal@v2",
                "region": "Poincare-B(0.42,0.17)",
                "proof": "zkp:abc123",
            },
            "timebox": {
                "t0": now.isoformat(),
                "delta_s": 900,
            },
        },
        "anchors": {
            "H0_envelope": "sha3-256:ab12ef",
            "H1_merkle_root": "sha3-256:77aa19",
            "pq_sigs": [
                {"alg": "ML-DSA-65", "signer": "tongue:KO", "sig": "uZk..."},
                {"alg": "Falcon-1024", "signer": "tongue:AV", "sig": "pQ5..."},
            ],
            "h2_external": {
                "sigstore_bundle": "base64:abc",
                "sbom_digest": "sha256:deadbeef",
            },
        },
        "gates": {
            "syntax": "pass",
            "integrity": "pass",
            "quorum": {"pass": True, "k": 4, "weighted_phi": 1.0},
            "geo_time": "pass",
            "policy": {"decision": "allow", "risk": 0.07},
        },
        "hatch": {
            "boot_epoch": 0,
            "kdf": "HKDF-SHA3",
            "boot_key_fp": "fp:01c9aa",
            "attestation_A0": "cose-sign1:abc123",
        },
        "signature": {
            "alg": "COSI-threshold-PQ",
            "signers": ["KO", "AV", "RU", "CA"],
            "sig": "AAECAwQF",
        },
    }


# ---------------------------------------------------------------------------
# POST /v1/attest/verify
# ---------------------------------------------------------------------------


class TestVerify:
    def test_valid_packet_returns_valid(self):
        resp = client.post("/v1/attest/verify", json=_valid_packet(), headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["errors"] == []
        assert body["verification_id"].startswith("av_")
        assert "gates_summary" in body

    def test_invalid_spec_returns_errors(self):
        pkt = _valid_packet()
        pkt["spec"] = "WRONG"
        resp = client.post("/v1/attest/verify", json=pkt, headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert any(e["path"] == "spec" for e in body["errors"])

    def test_expired_timebox_detected(self):
        pkt = _valid_packet()
        pkt["ritual"]["timebox"]["t0"] = "2020-01-01T00:00:00Z"
        pkt["ritual"]["timebox"]["delta_s"] = 60
        resp = client.post("/v1/attest/verify", json=pkt, headers=HEADERS)
        body = resp.json()
        assert body["valid"] is False
        assert any(e["path"] == "ritual.timebox" for e in body["errors"])

    def test_duplicate_signers_rejected(self):
        pkt = _valid_packet()
        pkt["anchors"]["pq_sigs"] = [
            {"alg": "ML-DSA-65", "signer": "tongue:KO", "sig": "a"},
            {"alg": "Falcon-1024", "signer": "tongue:KO", "sig": "b"},
        ]
        resp = client.post("/v1/attest/verify", json=pkt, headers=HEADERS)
        body = resp.json()
        assert body["valid"] is False
        assert any(e["path"] == "anchors.pq_sigs" for e in body["errors"])

    def test_k_gt_n_rejected(self):
        pkt = _valid_packet()
        pkt["ritual"]["tongue_quorum"]["k"] = 7
        pkt["gates"]["quorum"]["k"] = 7
        resp = client.post("/v1/attest/verify", json=pkt, headers=HEADERS)
        body = resp.json()
        assert body["valid"] is False

    def test_missing_api_key_returns_422(self):
        resp = client.post("/v1/attest/verify", json=_valid_packet())
        assert resp.status_code == 422

    def test_invalid_api_key_returns_401(self):
        resp = client.post("/v1/attest/verify", json=_valid_packet(), headers={"x-api-key": "bad"})
        assert resp.status_code == 401

    def test_metering_increments(self, _fresh_metering):
        client.post("/v1/attest/verify", json=_valid_packet(), headers=HEADERS)
        client.post("/v1/attest/verify", json=_valid_packet(), headers=HEADERS)
        now = datetime.utcnow()
        rows = _fresh_metering.export_monthly_usage(now.year, now.month)
        total = sum(r.count for r in rows if r.metric_name == ATTESTATION_VERIFICATIONS)
        assert total == 2


# ---------------------------------------------------------------------------
# POST /v1/attest/batch
# ---------------------------------------------------------------------------


class TestBatchVerify:
    def test_batch_all_valid(self):
        packets = [_valid_packet() for _ in range(3)]
        resp = client.post("/v1/attest/batch", json={"packets": packets}, headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["passed"] == 3
        assert body["failed"] == 0

    def test_batch_mixed_results(self):
        good = _valid_packet()
        bad = _valid_packet()
        bad["spec"] = "WRONG"
        resp = client.post("/v1/attest/batch", json={"packets": [good, bad]}, headers=HEADERS)
        body = resp.json()
        assert body["total"] == 2
        assert body["passed"] == 1
        assert body["failed"] == 1

    def test_batch_meters_per_packet(self, _fresh_metering):
        packets = [_valid_packet() for _ in range(5)]
        client.post("/v1/attest/batch", json={"packets": packets}, headers=HEADERS)
        now = datetime.utcnow()
        rows = _fresh_metering.export_monthly_usage(now.year, now.month)
        total = sum(r.count for r in rows if r.metric_name == ATTESTATION_VERIFICATIONS)
        assert total == 5

    def test_batch_rejects_empty(self):
        resp = client.post("/v1/attest/batch", json={"packets": []}, headers=HEADERS)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /v1/attest/schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_returns_json_schema(self):
        resp = client.get("/v1/attest/schema")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("$id") == "https://scbe.dev/schemas/egg_attest_v1.schema.json"
        assert body.get("title") == "SCBE Egg Attestation v1"


# ---------------------------------------------------------------------------
# GET /v1/attest/stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_returns_zero_when_no_usage(self):
        resp = client.get("/v1/attest/stats", headers=HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_verifications"] == 0

    def test_reflects_usage_after_verify(self, _fresh_metering):
        # Make 3 verifications
        for _ in range(3):
            client.post("/v1/attest/verify", json=_valid_packet(), headers=HEADERS)
        resp = client.get("/v1/attest/stats", headers=HEADERS)
        body = resp.json()
        assert body["total_verifications"] == 3
