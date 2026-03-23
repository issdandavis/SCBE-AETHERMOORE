from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_webtoon_catalog import build_catalog, CATALOG_PATH, MANHWA_DIR


SOURCE_ROOT = REPO_ROOT / "artifacts" / "webtoon" / "generated_router_hf_full_book"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def iter_chapter_dirs(source_root: Path) -> list[Path]:
    return sorted(
        chapter_dir
        for chapter_dir in source_root.iterdir()
        if chapter_dir.is_dir() and not chapter_dir.name.startswith("_")
    )


def sync_generated_panels(source_root: Path = SOURCE_ROOT, manhwa_root: Path = MANHWA_DIR) -> dict[str, int]:
    summary: dict[str, int] = {}

    for chapter_dir in iter_chapter_dirs(source_root):
        image_paths = [
            image_path
            for image_path in sorted(chapter_dir.iterdir())
            if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if not image_paths:
            continue

        dest_dir = manhwa_root / chapter_dir.name / "gen"
        dest_dir.mkdir(parents=True, exist_ok=True)

        for stale_path in dest_dir.iterdir():
            if stale_path.is_file() and stale_path.suffix.lower() in IMAGE_EXTENSIONS:
                stale_path.unlink()

        for image_path in image_paths:
            shutil.copy2(image_path, dest_dir / image_path.name)

        summary[chapter_dir.name] = len(image_paths)

    return summary


def write_catalog() -> list[dict]:
    catalog = build_catalog()
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return catalog


def main() -> None:
    copied = sync_generated_panels()
    catalog = write_catalog()
    print(
        json.dumps(
            {
                "source_root": str(SOURCE_ROOT),
                "manhwa_root": str(MANHWA_DIR),
                "chapters_synced": len(copied),
                "copied_counts": copied,
                "catalog": str(CATALOG_PATH),
                "catalog_chapters": len(catalog),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
