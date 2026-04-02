from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import CustomerContext
import api.research_routes as research_routes


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(research_routes.router)
    app.dependency_overrides[research_routes.verify_api_key_with_legacy] = lambda: CustomerContext(
        customer_id="test-customer",
        customer_email="test@example.com",
        tier="PRO",
        api_key_id="test-key",
    )
    return TestClient(app)


def test_upload_and_dedupe(monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RESEARCH_STORE_DIR", str(tmp_path))
    client = _client()
    payload = {
        "title": "Quiet Launch Notes",
        "content": "Research packet for a quiet launch with grounded customer discovery.",
        "source_type": "note",
        "tags": ["launch", "customer"],
    }

    first = client.post("/v1/research/upload", json=payload)
    second = client.post("/v1/research/upload", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert first.json()["document_id"] == second.json()["document_id"]


def test_search_and_document_retrieval(monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RESEARCH_STORE_DIR", str(tmp_path))
    client = _client()
    upload = client.post(
        "/v1/research/upload",
        json={
            "title": "Kaggle Comparison Plan",
            "content": "Compare the helper export lane against the Kaggle training lane for grounded evaluation.",
            "source_url": "https://example.com/kaggle-plan",
            "source_type": "spec",
            "tags": ["kaggle", "training"],
        },
    )
    document_id = upload.json()["document_id"]

    search = client.get("/v1/research/search", params={"q": "Kaggle grounded", "limit": 5})
    doc = client.get(f"/v1/research/documents/{document_id}")

    assert search.status_code == 200
    body = search.json()
    assert body["count"] == 1
    assert body["hits"][0]["document_id"] == document_id
    assert "Kaggle" in body["hits"][0]["snippet"]

    assert doc.status_code == 200
    doc_body = doc.json()
    assert doc_body["title"] == "Kaggle Comparison Plan"
    assert doc_body["source_url"] == "https://example.com/kaggle-plan"


def test_grounded_chat_injects_research_context(monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RESEARCH_STORE_DIR", str(tmp_path))
    client = _client()
    client.post(
        "/v1/research/upload",
        json={
            "title": "Research Hub Contract",
            "content": "The research hub should support uploads, lexical search, and API-key-gated AI access.",
            "source_type": "design",
            "tags": ["api", "research"],
        },
    )

    captured = {}

    def fake_chat(model, messages, max_tokens, temperature):
        captured["model"] = model
        captured["messages"] = messages
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        return "Grounded reply."

    monkeypatch.setattr(research_routes, "_call_huggingface_chat", fake_chat)

    response = client.post(
        "/v1/research/chat",
        json={
            "model": "issdandavis/scbe-pivot-qwen-0.5b",
            "messages": [
                {"role": "system", "content": "Stay grounded."},
                {"role": "user", "content": "How should the research hub work for other AI clients?"},
            ],
            "max_tokens": 320,
            "temperature": 0.2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Grounded reply."
    assert body["research_hits"]
    assert captured["model"] == "issdandavis/scbe-pivot-qwen-0.5b"
    assert any(
        "Research Hub Contract" in message["content"] or "API-key-gated AI access" in message["content"]
        for message in captured["messages"]
    )


def test_mobile_chat_requires_explicit_host_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RESEARCH_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("SCBE_ALLOW_LOCAL_MOBILE_CHAT", raising=False)
    client = _client()

    response = client.post(
        "/v1/research/mobile-chat",
        json={
            "model": "issdandavis/scbe-pivot-qwen-0.5b",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 403
    assert "SCBE_ALLOW_LOCAL_MOBILE_CHAT=1" in response.json()["detail"]


def test_mobile_chat_uses_same_grounded_path_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("SCBE_RESEARCH_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("SCBE_ALLOW_LOCAL_MOBILE_CHAT", "1")
    client = _client()
    client.post(
        "/v1/research/upload",
        json={
            "title": "Mobile Lane Ops",
            "content": "The phone lane should use a host-side proxy route so the emulator never stores provider keys.",
            "source_type": "ops",
            "tags": ["mobile", "proxy"],
        },
    )

    captured = {}

    def fake_chat(model, messages, max_tokens, temperature):
        captured["model"] = model
        captured["messages"] = messages
        return "Proxy-backed reply."

    monkeypatch.setattr(research_routes, "_call_huggingface_chat", fake_chat)

    response = client.post(
        "/v1/research/mobile-chat",
        json={
            "model": "issdandavis/scbe-pivot-qwen-0.5b",
            "messages": [{"role": "user", "content": "How should the phone lane handle tokens?"}],
            "max_tokens": 256,
            "temperature": 0.2,
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Proxy-backed reply."
    assert any("host-side proxy route" in message["content"] for message in captured["messages"])
