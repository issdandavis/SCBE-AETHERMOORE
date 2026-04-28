from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents.research_agent import ResearchAgent


@dataclass
class FakePage:
    url: str
    title: str
    text: str
    word_count: int
    error: str | None = None
    headings: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    jsonld: list[dict[str, Any]] = field(default_factory=list)


class FakeScraper:
    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages

    async def search_and_scrape(self, *_args, **_kwargs) -> list[FakePage]:
        return self.pages


def test_research_report_tracks_source_outcomes_and_nonconstant_scores() -> None:
    pages = [
        FakePage(
            url="https://example.test/a",
            title="SCBE hyperbolic geometry governance",
            text="SCBE hyperbolic geometry AI governance " * 20,
            word_count=80,
        ),
        FakePage(
            url="https://example.test/b",
            title="AI governance notes",
            text="This source discusses AI governance and safety, with one mention of hyperbolic methods.",
            word_count=320,
        ),
        FakePage(
            url="https://example.test/c",
            title="Cooking",
            text="A short cooking note unrelated to the requested topic.",
            word_count=40,
        ),
    ]
    agent = ResearchAgent(FakeScraper(pages), max_sources=3, relevance_threshold=0.3)

    import asyncio

    report = asyncio.run(agent.research("SCBE hyperbolic geometry AI governance"))
    payload = report.to_dict()

    assert payload["sources_checked"] == 3
    assert len(payload["source_outcomes"]) == 3
    assert {row["status"] for row in payload["source_outcomes"]} == {"matched", "below_threshold"}
    assert payload["errors"] == []

    confidences = [finding["confidence"] for finding in payload["findings"]]
    assert len(confidences) == 2
    assert len(set(confidences)) == 2


def test_research_report_records_error_outcomes_without_silent_drop() -> None:
    pages = [
        FakePage(
            url="https://example.test/error",
            title="Broken",
            text="",
            word_count=0,
            error="provider_timeout",
        )
    ]
    agent = ResearchAgent(FakeScraper(pages), max_sources=1, relevance_threshold=0.3)

    import asyncio

    report = asyncio.run(agent.research("SCBE governance"))
    payload = report.to_dict()

    assert payload["findings"] == []
    assert payload["errors"] == ["https://example.test/error: provider_timeout"]
    assert payload["source_outcomes"] == [
        {
            "url": "https://example.test/error",
            "title": "Broken",
            "status": "error",
            "score": 0.0,
            "word_count": 0,
            "reason": "provider_timeout",
        }
    ]
