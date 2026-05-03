from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_arena_html_prefers_backend_provider_router() -> None:
    html = _read("kindle-app/www/arena.html")

    assert "loadBackendProviders" in html
    assert "/v1/providers" in html
    assert "/v1/chat" in html
    assert "backend_chat_available" in html
    assert "callBackendProvider" in html


def test_arena_html_requests_python_intent_overlay_and_records_receipts() -> None:
    html = _read("kindle-app/www/arena.html")

    assert "/v1/arena/intent-overlay" in html
    assert "ARENA INTENT BLOCK" in html
    assert "aethercode_arena_receipt_v1" in html
    assert "previous_receipt" in html


def test_index_html_matches_arena_integration_surface() -> None:
    html = _read("kindle-app/www/index.html")

    assert "loadBackendProviders" in html
    assert "/v1/arena/intent-overlay" in html
    assert "aethercode_arena_receipt_v1" in html


def test_aetherbrowser_api_exposes_intent_overlay_endpoint() -> None:
    api = _read("scripts/aetherbrowser/api_server.py")

    assert "ArenaIntentOverlayRequest" in api
    assert '@app.post("/v1/arena/intent-overlay")' in api
    assert "backend_chat_available" in api
