from __future__ import annotations

from pathlib import Path

from scripts.sync_full_book_panels_to_phone import sync_generated_panels


def touch_png(path: Path, payload: bytes = b"png") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def test_sync_generated_panels_replaces_stale_gen_files(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    manhwa_root = tmp_path / "manhwa"

    touch_png(source_root / "ch01" / "ch01-v4-p01.png", b"new-1")
    touch_png(source_root / "ch01" / "ch01-v4-p02.png", b"new-2")
    touch_png(source_root / "ch02" / "ch02-p01.png", b"next")
    (source_root / "_verification").mkdir(parents=True, exist_ok=True)
    (source_root / "ch01" / "ignore.json").write_text("{}", encoding="utf-8")

    touch_png(manhwa_root / "ch01" / "gen" / "old-panel.png", b"old")

    summary = sync_generated_panels(source_root=source_root, manhwa_root=manhwa_root)

    assert summary == {"ch01": 2, "ch02": 1}
    assert not (manhwa_root / "ch01" / "gen" / "old-panel.png").exists()
    assert (manhwa_root / "ch01" / "gen" / "ch01-v4-p01.png").read_bytes() == b"new-1"
    assert (manhwa_root / "ch01" / "gen" / "ch01-v4-p02.png").read_bytes() == b"new-2"
    assert (manhwa_root / "ch02" / "gen" / "ch02-p01.png").read_bytes() == b"next"
