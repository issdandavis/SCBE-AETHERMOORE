from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "artifacts" / "webtoon" / "panel_prompts"
MANHWA_DIR = REPO_ROOT / "kindle-app" / "www" / "manhwa"
CATALOG_PATH = MANHWA_DIR / "catalog.json"


VARIANT_LABELS = {
    "hq": "Reference Panels",
    "generated": "AI Draft Panels",
    "text": "Text Overlay",
    "clean": "Image Only",
}

VARIANT_FOLDERS = (
    ("hq", "hq"),
    ("gen", "generated"),
    ("text", "text"),
    ("clean", "clean"),
)

DEFAULT_VARIANT_ORDER = ("hq", "text", "clean", "generated")
DEFAULT_VARIANT_OVERRIDES = {
    "ch01": "generated",
}


def humanize_chapter_id(chapter_id: str) -> str:
    if chapter_id.startswith("ch") and chapter_id[2:].isdigit():
        return f"Chapter {int(chapter_id[2:])}"
    if chapter_id.startswith("int") and chapter_id[3:].isdigit():
        return f"Interlude {int(chapter_id[3:])}"
    if chapter_id == "rootlight":
        return "Rootlight"
    return chapter_id.replace("-", " ").replace("_", " ").title()


def sorted_image_paths(folder: Path) -> list[str]:
    return [
        f"./manhwa/{folder.parent.name}/{folder.name}/{image.name}"
        for image in sorted(folder.glob("*"))
        if image.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]


def build_catalog() -> list[dict]:
    prompt_meta: dict[str, str] = {}
    order: list[str] = []
    for prompt_file in sorted(PROMPTS_DIR.glob("*_prompts.json")):
        data = json.loads(prompt_file.read_text(encoding="utf-8"))
        chapter_id = data["chapter_id"]
        prompt_meta[chapter_id] = data.get("title") or humanize_chapter_id(chapter_id)
        order.append(chapter_id)

    catalog: list[dict] = []
    for chapter_id in order:
        chapter_dir = MANHWA_DIR / chapter_id
        if not chapter_dir.exists():
            continue

        variants: dict[str, dict] = {}
        for variant_name, key in VARIANT_FOLDERS:
            folder = chapter_dir / variant_name
            if not folder.exists():
                continue
            slices = sorted_image_paths(folder)
            if not slices:
                continue
            variants[key] = {
                "label": VARIANT_LABELS[key],
                "slices": slices,
            }

        if not variants:
            continue

        default_variant = DEFAULT_VARIANT_OVERRIDES.get(chapter_id, "")
        if default_variant and default_variant not in variants:
            default_variant = ""

        default_variant = next(
            (
                variant_key
                for variant_key in ([default_variant] if default_variant else []) + list(DEFAULT_VARIANT_ORDER)
                if variant_key in variants
            ),
            next(iter(variants)),
        )
        catalog.append(
            {
                "id": chapter_id,
                "title": prompt_meta.get(chapter_id, humanize_chapter_id(chapter_id)),
                "defaultVariant": default_variant,
                "variants": variants,
            }
        )

    return catalog


def main() -> None:
    catalog = build_catalog()
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(json.dumps({"catalog": str(CATALOG_PATH), "chapters": len(catalog)}))


if __name__ == "__main__":
    main()
