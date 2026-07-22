from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "site" / "build_github_map.py"
SPEC = importlib.util.spec_from_file_location("build_github_map", SCRIPT)
assert SPEC and SPEC.loader
build_github_map = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_github_map
SPEC.loader.exec_module(build_github_map)


def test_every_html_page_has_one_live_and_source_mapping():
    items = build_github_map.pages()
    actual = {
        f"docs/{path.relative_to(build_github_map.DOCS).as_posix()}" for path in build_github_map.DOCS.rglob("*.html")
    }

    assert len(items) == 81
    assert {item.path for item in items} == actual
    assert len({item.live_url for item in items}) == len(items)
    assert len({item.source_url for item in items}) == len(items)
    assert all(item.live_url.startswith("https://aethermoore.com/") for item in items)
    assert all(item.source_url.startswith(build_github_map.SOURCE_ROOT) for item in items)


def test_committed_map_matches_generator():
    expected = build_github_map.render(build_github_map.pages())
    assert build_github_map.OUTPUT.read_text(encoding="utf-8") == expected
