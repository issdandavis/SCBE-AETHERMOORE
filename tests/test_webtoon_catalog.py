from __future__ import annotations

import json
from pathlib import Path

from scripts import build_webtoon_catalog
from scripts.build_webtoon_catalog import build_catalog


def test_catalog_prefers_generated_panels_for_ch01(tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
    import pytest  # noqa: F811

    # Set up a minimal prompts directory with a ch01 entry
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "ch01_prompts.json").write_text(
        json.dumps({"chapter_id": "ch01", "title": "Chapter 1"}), encoding="utf-8"
    )

    # Set up a minimal manhwa directory with ch01 hq and gen variants
    manhwa_dir = tmp_path / "manhwa"
    hq_dir = manhwa_dir / "ch01" / "hq"
    gen_dir = manhwa_dir / "ch01" / "gen"
    hq_dir.mkdir(parents=True)
    gen_dir.mkdir(parents=True)
    (hq_dir / "panel01.png").write_bytes(b"fake")
    (gen_dir / "panel01.png").write_bytes(b"fake")

    monkeypatch.setattr(build_webtoon_catalog, "PROMPTS_DIR", prompts_dir)
    monkeypatch.setattr(build_webtoon_catalog, "MANHWA_DIR", manhwa_dir)

    catalog = build_catalog()
    ch01 = next(chapter for chapter in catalog if chapter["id"] == "ch01")

    assert ch01["defaultVariant"] == "generated"
    assert ch01["variants"]["hq"]["label"] == "Reference Panels"
    assert "generated" in ch01["variants"]
