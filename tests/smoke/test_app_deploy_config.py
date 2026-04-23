from __future__ import annotations

from pathlib import Path


def test_app_index_does_not_hardcode_localhost_api() -> None:
    app_index = Path(__file__).resolve().parents[2] / "app" / "index.html"
    content = app_index.read_text(encoding="utf-8")

    assert "const API_URL = 'http://localhost:3000';" not in content
    assert "resolveApiBase()" in content
    assert "meta name=\"scbe-api-base\"" in content

