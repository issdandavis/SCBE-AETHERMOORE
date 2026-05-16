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

    for src_rel, _dst_rel in package_products.MAKING_OF_FILES:
        if not (repo_root / src_rel).exists():
            missing.append(src_rel)

    assert missing == []


def test_packaged_product_smoke(tmp_path: Path):
    toolkit = package_products.package_toolkit(tmp_path)
    vault = package_products.package_vault(tmp_path)
    making_of = package_products.package_making_of(tmp_path)

    assert toolkit.exists()
    assert vault.exists()
    assert making_of.exists()
    assert toolkit.stat().st_size > 0
    assert vault.stat().st_size > 0
    assert making_of.stat().st_size > 0


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


def test_making_of_zip_excludes_manuscripts_and_includes_process_guides(tmp_path: Path):
    making_of = package_products.package_making_of(tmp_path)

    with ZipFile(making_of) as zf:
        names = set(zf.namelist())
        readme = zf.read("README.md").decode("utf-8")
        process_notes = zf.read("PROCESS_NOTES.txt").decode("utf-8")

    assert "guides/ai-writing-system-guide.md" in names
    assert "guides/humanization-pass-checklist.md" in names
    assert "guides/aethermoore-writing-techniques-fieldbook.md" in names
    assert "site-source/books.html" in names
    assert "does NOT include the manuscript text" in readme
    assert "Amazon/KDP sells the finished book" in process_notes


def test_production_pack_support_email_is_current():
    inventory = package_products.REPO_ROOT / "deliverables" / "SCBE_Production_Pack" / "PACKAGE_INVENTORY.json"
    payload = json.loads(inventory.read_text(encoding="utf-8"))
    assert payload["support_email"] == "ai@aethermoore.com"
