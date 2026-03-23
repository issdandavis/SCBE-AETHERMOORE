from __future__ import annotations

from scripts.build_webtoon_catalog import build_catalog


def test_catalog_prefers_generated_panels_for_ch01() -> None:
    catalog = build_catalog()
    ch01 = next(chapter for chapter in catalog if chapter["id"] == "ch01")

    assert ch01["defaultVariant"] == "generated"
    assert ch01["variants"]["hq"]["label"] == "Reference Panels"
    assert "generated" in ch01["variants"]
