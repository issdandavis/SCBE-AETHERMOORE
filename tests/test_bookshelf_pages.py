from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"


def test_bookshelf_catalog_points_to_real_pages_and_assets() -> None:
    catalog = json.loads((DOCS / "books.json").read_text(encoding="utf-8"))

    assert catalog["schema"] == "aethermoore-bookshelf-v1"
    assert catalog["books"], "bookshelf catalog should not be empty"

    for book in catalog["books"]:
        assert (DOCS / book["page"]).exists(), book["page"]
        assert (DOCS / book["cover"]).exists(), book["cover"]
        assert book["title"]
        assert book["author"] == "Issac Daniel Davis"
        assert book["formats"]
        assert book["reader_fit"]
        assert book["process"]


def test_bookshelf_catalog_matches_current_kdp_statuses() -> None:
    catalog = json.loads((DOCS / "books.json").read_text(encoding="utf-8"))
    books = {book["id"]: book for book in catalog["books"]}

    miracle_formats = {fmt["name"]: fmt for fmt in books["miracle-memory"]["formats"]}
    assert miracle_formats["Kindle eBook"]["status"] == "In review"
    assert miracle_formats["Kindle eBook"]["price_usd"] == "5.99"
    assert miracle_formats["Kindle eBook"]["kdp_select"] is True
    assert miracle_formats["Kindle eBook"]["last_modified"] == "2026-05-13"
    assert miracle_formats["Paperback"]["status"] == "In review"
    assert miracle_formats["Paperback"]["price_usd"] == "16.99"
    assert miracle_formats["Paperback"]["last_modified"] == "2026-05-13"
    assert miracle_formats["Hardcover"]["status"] == "Not created"
    assert miracle_formats["Hardcover"]["available"] is False

    six_formats = {fmt["name"]: fmt for fmt in books["six-tongues-protocol"]["formats"]}
    assert six_formats["Kindle eBook"]["status"] == "Live"
    assert six_formats["Kindle eBook"]["price_usd"] == "4.99"
    assert six_formats["Kindle eBook"]["asin"] == "B0GSSFQD9G"
    assert six_formats["Kindle eBook"]["submitted"] == "2026-03-16"
    assert six_formats["Kindle eBook"]["kdp_select"] is True
    assert six_formats["Paperback"]["status"] == "Live"
    assert six_formats["Paperback"]["price_usd"] == "22.99"
    assert six_formats["Paperback"]["asin"] == "B0GSW8CLC6"
    assert six_formats["Paperback"]["submitted"] == "2026-03-17"
    assert six_formats["Hardcover"]["status"] == "Draft"
    assert six_formats["Hardcover"]["last_modified"] == "2026-03-18"
    assert six_formats["Hardcover"]["available"] is False


def test_bookshelf_hub_links_each_book_page_and_process_lane() -> None:
    page = (DOCS / "books.html").read_text(encoding="utf-8")

    assert "AetherMoore Bookshelf" in page
    assert 'href="books/miracle-memory.html"' in page
    assert 'href="books/six-tongues-protocol.html"' in page
    assert "Publishing Process" in page
    assert "static/books/miracle-memory-cover.png" in page
    assert "static/books/six-tongues-cover.jpg" in page
    assert "May 13, 2026 update" in page
    assert "submitted March 16, 2026" in page
    assert "draft, last modified March 18, 2026" in page


def test_six_tongues_page_uses_live_amazon_asins() -> None:
    page = (DOCS / "books" / "six-tongues-protocol.html").read_text(encoding="utf-8")

    assert "The Six Tongues Protocol" in page
    assert "https://www.amazon.com/dp/B0GSSFQD9G" in page
    assert "https://www.amazon.com/dp/B0GSW8CLC6" in page
    assert "ASIN B0GSSFQD9G" in page
    assert "ASIN B0GSW8CLC6" in page
    assert "enrolled in KDP Select" in page
    assert "Submitted March 16, 2026" in page
    assert "Submitted March 17, 2026" in page
    assert "Last modified March 18, 2026" in page


def test_miracle_memory_page_marks_kdp_review_without_fake_purchase_link() -> None:
    page = (DOCS / "books" / "miracle-memory.html").read_text(encoding="utf-8")

    assert "The Miracle Was The Memory" in page
    assert "KDP review" in page
    assert "$5.99 USD" in page
    assert "$16.99 USD" in page
    assert "Amazon link coming after review" in page
    assert "Last modified May 13, 2026" in page
    assert "Hardcover:</strong> not created yet" in page
    assert "amazon.com/dp/" not in page.lower()


def test_bookshelf_routes_are_discoverable_to_search_and_vercel() -> None:
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    vercelignore = (REPO_ROOT / ".vercelignore").read_text(encoding="utf-8")
    ignore_build = (REPO_ROOT / "scripts" / "vercel" / "ignore-build.cjs").read_text(encoding="utf-8")
    homepage = (DOCS / "index.html").read_text(encoding="utf-8")

    assert "https://aethermoore.com/SCBE-AETHERMOORE/books.html" in sitemap
    assert "https://aethermoore.com/SCBE-AETHERMOORE/books/miracle-memory.html" in sitemap
    assert "https://aethermoore.com/SCBE-AETHERMOORE/books/six-tongues-protocol.html" in sitemap
    assert "!docs/books.html" in vercelignore
    assert "!docs/books/**" in vercelignore
    assert "'docs/books.html'" in ignore_build
    assert "'docs/books'" in ignore_build
    assert 'href="books.html"' in homepage
