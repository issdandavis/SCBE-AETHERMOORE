#!/usr/bin/env python3
"""Build the BookForge publishing-company delivery kit.

The output is intentionally source-driven: product docs and templates live in
`products/bookforge-publishing-company/`, while this script assembles a buyer
ZIP, manifest, and receipt under artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = REPO_ROOT / "products" / "bookforge-publishing-company"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "bookforge-publishing-company" / "latest"
DIST_ROOT = REPO_ROOT / "artifacts" / "bookforge-dist"
ZIP_NAME = "BookForge-Publishing-Company-Kit.zip"

REQUIRED_PRODUCT_FILES = {
    "START_HERE.md",
    "INSTALL.md",
    "company/COMPANY_BLUEPRINT.md",
    "company/FULFILLMENT_SOP.md",
    "company/CUSTOMER_POLICIES.md",
    "company/QUALITY_GATES.md",
    "company/ZERO_AD_LAUNCH_PLAN.md",
    "profiles/kdp-novel-5x8.json",
    "profiles/kdp-novel-5_5x8_5.json",
    "profiles/kdp-nonfiction-6x9.json",
    "profiles/kdp-hardcover-6x9.json",
    "profiles/kdp-poetry-5x8.json",
    "starter/manuscript.md",
    "starter/blurb.json",
    "templates/author-intake.md",
    "templates/blurb-workbench.md",
    "templates/build-audit-reply.md",
    "templates/build-receipt.md",
    "templates/delivery-email.md",
    "templates/kdp-upload-checklist.md",
    "templates/launch-post.md",
    "templates/production-ticket.md",
    "templates/store-listing.md",
}

EXTRA_FILES = {
    "docs/business/BOOKFORGE_PUBLISHING_COMPANY.md": "company/BOOKFORGE_PUBLISHING_COMPANY.md",
    "docs/product-delivery/BOOKFORGE_PUBLISHING_KIT.md": "delivery/BOOKFORGE_PUBLISHING_KIT.md",
    "docs/downloads/kdp-bookforge-checklist.md": "delivery/kdp-bookforge-checklist.md",
    "docs/bookforge-publishing-kit.html": "public-proof/bookforge-publishing-kit.html",
    "docs/packages/scbe-bookforge.html": "public-proof/scbe-bookforge-package-page.html",
    "packages/bookforge/README.md": "engine/README.md",
    "packages/bookforge/pyproject.toml": "engine/pyproject.toml",
}

OFFICIAL_REFERENCES = [
    "https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
    "https://kdp.amazon.com/en_US/help/topic/G201857950",
    "https://kdp.amazon.com/cover-calculator",
    "https://kdp.amazon.com/en_US/help/topic/G201953020",
    "https://packaging.python.org/en/latest/tutorials/packaging-projects/",
]


@dataclass(frozen=True)
class KitFile:
    source: str
    target: str
    bytes: int
    sha256: str


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect_product_files() -> list[tuple[Path, str]]:
    missing = [item for item in sorted(REQUIRED_PRODUCT_FILES) if not (PRODUCT_ROOT / item).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required product files: {', '.join(missing)}")

    files: list[tuple[Path, str]] = []
    for path in sorted(PRODUCT_ROOT.rglob("*")):
        if path.is_file():
            files.append((path, str(path.relative_to(PRODUCT_ROOT)).replace("\\", "/")))

    for source_rel, target in EXTRA_FILES.items():
        source = REPO_ROOT / source_rel
        if source.exists():
            files.append((source, target))

    if DIST_ROOT.exists():
        for path in sorted(DIST_ROOT.glob("scbe_bookforge-0.1.0*")):
            if path.is_file():
                files.append((path, f"engine-dist/{path.name}"))

    return files


def write_zip(files: list[tuple[Path, str]], zip_path: Path) -> list[KitFile]:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    written: list[KitFile] = []
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for source, target in files:
            data = source.read_bytes()
            info = ZipInfo(target)
            info.date_time = (2026, 7, 2, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            zf.writestr(info, data)
            written.append(KitFile(source=rel(source), target=target, bytes=len(data), sha256=sha256_bytes(data)))
    return written


def build(output_dir: Path = DEFAULT_OUTPUT) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / ZIP_NAME
    files = collect_product_files()
    written = write_zip(files, zip_path)
    zip_hash = sha256_bytes(zip_path.read_bytes())

    manifest = {
        "schema": "bookforge_publishing_company_kit_v1",
        "created_at_utc": now_utc(),
        "product_root": rel(PRODUCT_ROOT),
        "zip_path": rel(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": zip_hash,
        "file_count": len(written),
        "manual_delivery_price": "$19",
        "engine_status": {
            "pypi_name": "scbe-bookforge",
            "pypi_publish_required": True,
            "local_dist_included": any(item.target.startswith("engine-dist/") for item in written),
        },
        "official_references": OFFICIAL_REFERENCES,
        "files": [asdict(item) for item in written],
    }
    manifest_path = output_dir / "manifest.json"
    receipt_path = output_dir / "BUILD_RECEIPT.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.write_text(render_receipt(manifest), encoding="utf-8")
    verify_zip(zip_path)
    return manifest


def render_receipt(manifest: dict) -> str:
    lines = [
        "# BookForge Publishing Company Kit Receipt",
        "",
        f"- Created: `{manifest['created_at_utc']}`",
        f"- ZIP: `{manifest['zip_path']}`",
        f"- Bytes: `{manifest['zip_bytes']}`",
        f"- SHA256: `{manifest['zip_sha256']}`",
        f"- Files: `{manifest['file_count']}`",
        f"- Local engine dist included: `{manifest['engine_status']['local_dist_included']}`",
        "",
        "## External Rule Sources",
        "",
    ]
    lines.extend(f"- {url}" for url in manifest["official_references"])
    lines.extend(
        [
            "",
            "## Sale Boundary",
            "",
            "Manual delivery is ready. PyPI publication is still required before public install copy is fully true.",
            "",
        ]
    )
    return "\n".join(lines)


def verify_zip(zip_path: Path) -> None:
    with ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    missing = REQUIRED_PRODUCT_FILES - names
    if missing:
        raise RuntimeError(f"ZIP missing required files: {', '.join(sorted(missing))}")
    if "public-proof/bookforge-publishing-kit.html" not in names:
        raise RuntimeError("ZIP missing public proof page copy")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build(args.output_dir)
    if args.as_json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"Built {manifest['zip_path']} ({manifest['file_count']} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
