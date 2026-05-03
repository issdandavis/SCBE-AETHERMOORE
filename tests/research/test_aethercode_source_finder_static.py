from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    return (ROOT / "kindle-app" / "www" / name).read_text(encoding="utf-8")


def test_aethercode_index_has_source_finder_workspace() -> None:
    html = _read("index.html")

    assert 'data-center-view="sources"' in html
    assert "Governed RAG Intake" in html
    assert "SOURCE_ROUTES" in html
    assert "scbe_github_pages_site" in html
    assert "tor_trusted_onion_research" in html
    assert "QUARANTINE_BY_DEFAULT" in html
    assert "renderSourceTerminal" in html


def test_aethercode_arena_has_same_source_finder_workspace() -> None:
    html = _read("arena.html")

    assert 'data-center-view="sources"' in html
    assert "Governed RAG Intake" in html
    assert "SOURCE_ROUTES" in html
    assert "scbe_github_pages_site" in html
    assert "starlink_public_space_telemetry" in html
    assert "QUARANTINE_LIVE_OPERATIONS" in html
    assert "geoseal research-terminal" in html
