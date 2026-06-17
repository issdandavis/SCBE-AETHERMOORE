from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CATALOG = DOCS / "research" / "research_catalog.json"


def test_research_catalog_links_to_existing_topics_sources_and_outputs() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["schema"] == "aethermoore-research-catalog-v1"
    assert (DOCS / catalog["standard"]).exists()

    topics = {topic["id"] for topic in catalog["topics"]}
    assert {
        "space-systems",
        "materials-chemistry",
        "autonomy-swarms",
        "life-systems",
    } <= topics

    assert (DOCS / "research" / "index.html").exists()
    for topic in catalog["topics"]:
        assert (DOCS / "research" / "topics" / f"{topic['id']}.html").exists()

    for paper in catalog["papers"]:
        paper_topics = set(paper.get("topics", [paper["topic"]]))
        assert paper_topics <= topics
        assert (DOCS / paper["source_md"]).exists()
        assert (DOCS / paper["html"]).exists()
        if "pdf" in paper:
            assert (DOCS / paper["pdf"]).exists()
        assert paper["claim_boundary"]
        assert paper["abstract"]
        assert paper["grade"]
        assert paper["review_model"]
