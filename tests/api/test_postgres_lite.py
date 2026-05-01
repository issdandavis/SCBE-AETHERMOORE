"""Postgres lite probe and health wiring."""

from __future__ import annotations

import pytest

from src.api.postgres_lite import health_postgres_payload, probe_postgres, resolved_postgres_dsn


def test_resolved_dsn_empty_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCBE_POSTGRES_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert resolved_postgres_dsn() is None


def test_resolved_dsn_prefers_scbe_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCBE_POSTGRES_URL", "postgresql://a:a@localhost:1/db")
    monkeypatch.setenv("DATABASE_URL", "postgresql://b:b@localhost:2/db")
    assert resolved_postgres_dsn() == "postgresql://a:a@localhost:1/db"


def test_resolved_dsn_skips_sqlite_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCBE_POSTGRES_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/x.db")
    assert resolved_postgres_dsn() is None


def test_probe_not_configured() -> None:
    r = probe_postgres(dsn="")
    assert r["configured"] is False
    assert r["reachable"] is False


def test_probe_unreachable_tcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCBE_POSTGRES_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Nothing listens on this port in CI — exercise driver path quickly.
    bad = "postgresql://scbe:scbe@127.0.0.1:59999/scbe"
    r = probe_postgres(dsn=bad, timeout_s=1.0)
    assert r["configured"] is True
    assert r["reachable"] is False
    assert r.get("driver") == "psycopg3"
    assert "error" in r


def test_health_payload_shape() -> None:
    p = health_postgres_payload(timeout_s=1.0)
    assert "configured" in p
    assert "reachable" in p


def test_geoseal_service_health_has_postgres_key() -> None:
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "postgres_lite" in body
    assert isinstance(body["postgres_lite"], dict)
