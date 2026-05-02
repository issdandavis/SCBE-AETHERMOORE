"""HTTP-level smoke tests for the headless Word endpoints."""

from __future__ import annotations

import io
import zipfile

import pytest

pytest.importorskip("docx", reason="python-docx not installed")
pytest.importorskip("fastapi.testclient", reason="fastapi[test] not installed")

from fastapi.testclient import TestClient  # noqa: E402

from app import app, sync  # noqa: E402
from headless import DOCX_MIME  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_sync():
    sync.documents.clear()
    yield
    sync.documents.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _is_docx(data: bytes) -> bool:
    if not data.startswith(b"PK"):
        return False
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return "word/document.xml" in set(zf.namelist())


def test_export_docx_404_when_missing(client):
    r = client.get("/doc/never-existed/export.docx")
    assert r.status_code == 404


def test_export_docx_returns_binary(client):
    sync.get_or_create("export-test").insert(0, "Hello.")
    r = client.get("/doc/export-test/export.docx")
    assert r.status_code == 200
    assert r.headers["content-type"] == DOCX_MIME
    assert "export-test.docx" in r.headers["content-disposition"]
    assert _is_docx(r.content)


def test_headless_generate_returns_docx_with_record_headers(client):
    r = client.post(
        "/headless/generate",
        json={
            "doc_id": "gen-1",
            "prompt": "Draft a status update.",
            "provider": "echo",
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == DOCX_MIME
    assert "X-Spiralword-Record" in r.headers
    assert "X-Spiralword-Docx-Sha256" in r.headers
    assert len(r.headers["X-Spiralword-Docx-Sha256"]) == 64
    assert _is_docx(r.content)


def test_headless_record_lookup(client):
    gen = client.post(
        "/headless/generate",
        json={"doc_id": "lookup", "prompt": "anything", "provider": "echo"},
    )
    rec_id = gen.headers["X-Spiralword-Record"]

    r = client.get(f"/headless/record/{rec_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "headless_generate"
    assert rec_id in body["governance_decision"]


def test_headless_generate_blocked_returns_403(client, monkeypatch):
    from ai_ports import ai_ports

    monkeypatch.setitem(ai_ports._providers, "echo", lambda p, o=None: "[BLOCKED] denied")
    r = client.post(
        "/headless/generate",
        json={"doc_id": "blk", "prompt": "x", "provider": "echo"},
    )
    assert r.status_code == 403
    assert "denied" in r.json()["detail"]
