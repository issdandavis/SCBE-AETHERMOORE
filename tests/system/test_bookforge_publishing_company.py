from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from scripts.system import build_bookforge_publishing_company as company


def test_bookforge_company_kit_builds_zip(tmp_path: Path) -> None:
    manifest = company.build(tmp_path)
    zip_path = Path(manifest["zip_path"])
    if not zip_path.is_absolute():
        zip_path = company.REPO_ROOT / zip_path

    assert zip_path.exists()
    assert manifest["schema"] == "bookforge_publishing_company_kit_v1"
    assert manifest["manual_delivery_price"] == "$19"
    assert manifest["file_count"] >= len(company.REQUIRED_PRODUCT_FILES)

    with ZipFile(zip_path) as zf:
        names = set(zf.namelist())

    assert company.REQUIRED_PRODUCT_FILES.issubset(names)
    assert "public-proof/bookforge-publishing-kit.html" in names
    assert "delivery/BOOKFORGE_PUBLISHING_KIT.md" in names


def test_bookforge_company_profiles_are_valid_json() -> None:
    profile_dir = company.PRODUCT_ROOT / "profiles"
    profiles = sorted(profile_dir.glob("*.json"))

    assert len(profiles) >= 5
    for path in profiles:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["source"] == "../starter/manuscript.md"
        assert payload["trim"]
        assert payload["page_count"] > 0
        assert payload["print"]["ink"]


def test_bookforge_offer_pages_reference_manual_delivery() -> None:
    proof = (company.REPO_ROOT / "docs" / "bookforge-publishing-kit.html").read_text(encoding="utf-8")
    delivery = (company.REPO_ROOT / "docs" / "product-delivery" / "BOOKFORGE_PUBLISHING_KIT.md").read_text(
        encoding="utf-8"
    )

    assert "Buy $19 Kit" in proof
    assert "manual delivery" in proof.lower()
    assert "BookForge-Publishing-Company-Kit.zip" in delivery
