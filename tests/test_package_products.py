from __future__ import annotations

from pathlib import Path
import json
from zipfile import ZipFile

import scripts.package_products as package_products


def test_packaged_product_sources_exist():
    repo_root = package_products.REPO_ROOT

    missing: list[str] = []
    for src_rel, _dst_rel in package_products.TOOLKIT_FILES:
        if not (repo_root / src_rel).exists():
            missing.append(src_rel)

    for src_rel in package_products.VAULT_SFT_FILES:
        if not (repo_root / src_rel).exists():
            missing.append(src_rel)

    for src_rel, _dst_rel in package_products.VAULT_EXTRA_FILES:
        if not (repo_root / src_rel).exists():
            missing.append(src_rel)

    for src_rel, _dst_rel in package_products.WRITING_PACK_FILES:
        if not (repo_root / src_rel).exists():
            missing.append(src_rel)

    assert missing == []


def test_packaged_product_smoke(tmp_path: Path):
    toolkit = package_products.package_toolkit(tmp_path)
    vault = package_products.package_vault(tmp_path)
    writing = package_products.package_writing(tmp_path)

    assert toolkit.exists()
    assert vault.exists()
    assert writing.exists()
    assert toolkit.stat().st_size > 0
    assert vault.stat().st_size > 0
    assert writing.stat().st_size > 0


def test_toolkit_zip_contains_promised_buyer_templates(tmp_path: Path):
    toolkit = package_products.package_toolkit(tmp_path)

    with ZipFile(toolkit) as zf:
        names = set(zf.namelist())

    assert {
        "BUYER_START_GUIDE.md",
        "templates/decision-record-template.md",
        "templates/threshold-worksheet.md",
        "templates/pilot-checklist.md",
        "templates/review-notes-template.md",
        "quickstart/README.md",
    }.issubset(names)


def test_writing_pack_zip_contains_promised_guides(tmp_path: Path):
    writing = package_products.package_writing(tmp_path)

    with ZipFile(writing) as zf:
        names = set(zf.namelist())
        metadata = json.loads(zf.read("metadata.json").decode("utf-8"))

    assert {
        "README.md",
        "guides/ai-writing-system-guide.md",
        "guides/humanization-pass-checklist.md",
        "guides/security-governance-checklist.md",
        "guides/aethermoore-writing-techniques-fieldbook.md",
        "metadata.json",
    }.issubset(names)
    assert metadata["product"] == "AetherMoore Writing Technique Pack"
    assert "KDP/Amazon" in metadata["kdp_boundary"]


def test_production_pack_support_email_is_current():
    inventory = package_products.REPO_ROOT / "deliverables" / "SCBE_Production_Pack" / "PACKAGE_INVENTORY.json"
    payload = json.loads(inventory.read_text(encoding="utf-8"))
    assert payload["support_email"] == "ai@aethermoore.com"
