from __future__ import annotations

import json
from pathlib import Path

from scripts.system.build_public_github_map import build_public_github_map


def test_build_public_github_map_maps_nested_pages_and_is_idempotent(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    nested = docs / "research" / "index.html"
    nested.parent.mkdir(parents=True)
    (docs / "index.html").write_text("<!doctype html><title>Home</title><body>home</body>\n", encoding="utf-8")
    nested.write_text("<!doctype html><title>Research Library</title><body>research</body>\n", encoding="utf-8")

    first = build_public_github_map(docs)
    second = build_public_github_map(docs)

    payload = json.loads((docs / "github-map.json").read_text(encoding="utf-8"))
    records = {page["source_path"]: page for page in payload["pages"]}
    nested_html = nested.read_text(encoding="utf-8")

    assert first["pages"] == 3
    assert second["updated"] == 0
    assert records["docs/research/index.html"]["public_url"] == "https://aethermoore.com/research/"
    assert records["docs/research/index.html"]["source_url"].endswith("/docs/research/index.html")
    assert nested_html.count("data-aether-source") == 1
    assert 'src="../assets/source-map.js"' in nested_html
