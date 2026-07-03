from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"


def test_package_product_catalog_points_to_real_pages() -> None:
    catalog = json.loads((DOCS / "package-products.json").read_text(encoding="utf-8"))

    assert catalog["schema"] == "aethermoore-package-products-v1"
    assert {item["id"] for item in catalog["products"]} == {
        "scbe-aethermoore",
        "scbe-aethermoore-cli",
        "scbe-agent-bus",
        "scbe-bookforge",
    }

    for product in catalog["products"]:
        assert (DOCS / product["page"]).exists(), product["page"]
        assert product["primary_install"]
        assert product["headline"]
        assert product["audience"]
        assert product["use_cases"]


def test_packages_hub_links_each_product_page_and_install_command() -> None:
    page = (DOCS / "packages.html").read_text(encoding="utf-8")

    assert "npm and PyPI packages that make SCBE usable" in page
    assert 'href="packages/scbe-aethermoore.html"' in page
    assert 'href="packages/scbe-aethermoore-cli.html"' in page
    assert 'href="packages/scbe-agent-bus.html"' in page
    assert 'href="packages/scbe-bookforge.html"' in page
    assert 'href="bookforge-publishing-kit.html"' in page
    assert "npm install scbe-aethermoore" in page
    assert "npm install -g scbe-aethermoore-cli" in page
    assert "pip install scbe-agent-bus" in page
    assert "pip install scbe-bookforge" in page


def test_live_package_pages_include_registry_links_and_versions() -> None:
    core = (DOCS / "packages" / "scbe-aethermoore.html").read_text(encoding="utf-8")
    cli = (DOCS / "packages" / "scbe-aethermoore-cli.html").read_text(encoding="utf-8")
    bus = (DOCS / "packages" / "scbe-agent-bus.html").read_text(encoding="utf-8")

    assert "https://www.npmjs.com/package/scbe-aethermoore" in core
    assert "https://pypi.org/project/scbe-aethermoore/" in core
    assert "npm: 4.1.0" in core
    assert "PyPI: 4.1.3" in core
    assert "governance abacus" in core
    assert "https://www.npmjs.com/package/scbe-aethermoore-cli" in cli
    assert "scbe-aethermoore-cli 4.4.0" in cli
    assert "scbe abacus run --d-h 0.1 --pd 0 --json" in cli
    assert "https://www.npmjs.com/package/scbe-agent-bus" in bus
    assert "https://pypi.org/project/scbe-agent-bus/" in bus
    assert "npm: 0.3.1" in bus
    assert "PyPI: 0.3.0" in bus
    assert "hosted-credential gating" in bus


def test_bookforge_page_is_marked_publish_pending_without_dead_pypi_link() -> None:
    page = (DOCS / "packages" / "scbe-bookforge.html").read_text(encoding="utf-8")

    assert "scbe-bookforge" in page
    assert "publish pending" in page.lower()
    assert "pip install scbe-bookforge" in page
    assert "../bookforge-publishing-kit.html" in page
    assert "https://pypi.org/project/scbe-bookforge/" not in page


def test_package_pages_are_discoverable_to_search_vercel_and_homepage() -> None:
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    vercelignore = (REPO_ROOT / ".vercelignore").read_text(encoding="utf-8")
    ignore_build = (REPO_ROOT / "scripts" / "vercel" / "ignore-build.cjs").read_text(encoding="utf-8")
    homepage = (DOCS / "index.html").read_text(encoding="utf-8")

    for path in [
        "packages.html",
        "packages/scbe-aethermoore.html",
        "packages/scbe-aethermoore-cli.html",
        "packages/scbe-agent-bus.html",
        "packages/scbe-bookforge.html",
        "bookforge-publishing-kit.html",
    ]:
        assert f"https://aethermoore.com/SCBE-AETHERMOORE/{path}" in sitemap

    assert "!docs/packages.html" in vercelignore
    assert "!docs/packages/**" in vercelignore
    assert "'docs/packages.html'" in ignore_build
    assert "'docs/packages'" in ignore_build
    assert 'href="packages.html"' in homepage
