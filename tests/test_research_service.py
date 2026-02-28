"""Tests for the Research Connector Service and new source adapters.

Covers:
  - Semantic Scholar source adapter
  - CrossRef source adapter
  - ORCID source adapter
  - ResearchConnectorService (tiered filtration, dedup, scoring)
"""

from __future__ import annotations

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List, Optional

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.obsidian_researcher.source_adapter import (
    IngestionResult,
    SourceAdapter,
    SourceType,
)
from agents.obsidian_researcher.sources.orcid_source import ORCIDSource
from agents.obsidian_researcher.sources.semantic_scholar_source import SemanticScholarSource
from agents.obsidian_researcher.sources.crossref_source import CrossRefSource
from agents.obsidian_researcher.research_service import (
    ResearchConnectorService,
    Tier,
    ScoredResult,
    SearchReport,
    HealthReport,
    _TIER_TRUST,
    _TIER_THRESHOLD,
)


# ==========================================================================
# Mock data
# ==========================================================================

MOCK_S2_SEARCH_RESPONSE = {
    "total": 2,
    "data": [
        {
            "paperId": "abc123",
            "title": "Hyperbolic Geometry for AI Safety",
            "abstract": "We propose a hyperbolic cost model for adversarial behavior.",
            "year": 2025,
            "citationCount": 42,
            "influentialCitationCount": 5,
            "referenceCount": 30,
            "fieldsOfStudy": ["Computer Science"],
            "authors": [
                {"authorId": "1", "name": "Issac Davis"},
                {"authorId": "2", "name": "Claude AI"},
            ],
            "externalIds": {"DOI": "10.1234/hyp-safety", "ArXiv": "2501.12345"},
            "url": "https://www.semanticscholar.org/paper/abc123",
            "venue": "NeurIPS",
            "publicationDate": "2025-12-01",
            "openAccessPdf": {"url": "https://arxiv.org/pdf/2501.12345"},
            "tldr": {"text": "Hyperbolic cost scaling makes adversarial AI infeasible."},
        },
        {
            "paperId": "def456",
            "title": "Post-Quantum Cryptography Survey",
            "abstract": "A survey of PQC algorithms.",
            "year": 2024,
            "citationCount": 100,
            "influentialCitationCount": 15,
            "referenceCount": 80,
            "fieldsOfStudy": ["Computer Science", "Mathematics"],
            "authors": [{"authorId": "3", "name": "Alice Crypto"}],
            "externalIds": {"DOI": "10.5678/pqc-survey"},
            "url": "https://www.semanticscholar.org/paper/def456",
            "venue": "IEEE S&P",
            "publicationDate": "2024-05-15",
            "openAccessPdf": None,
            "tldr": None,
        },
    ],
}

MOCK_CROSSREF_SEARCH_RESPONSE = {
    "status": "ok",
    "message": {
        "total-results": 1,
        "items": [
            {
                "DOI": "10.1234/hyp-safety",
                "title": ["Hyperbolic Geometry for AI Safety"],
                "author": [
                    {"given": "Issac", "family": "Davis"},
                ],
                "published-print": {"date-parts": [[2025, 12, 1]]},
                "abstract": "We propose a hyperbolic cost model.",
                "container-title": ["NeurIPS Proceedings"],
                "publisher": "MIT Press",
                "type": "journal-article",
                "is-referenced-by-count": 42,
                "references-count": 30,
                "subject": ["Computer Science", "AI Safety"],
                "ISSN": ["1234-5678"],
                "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
            }
        ],
    },
}

MOCK_ORCID_WORKS_RESPONSE = {
    "group": [
        {
            "work-summary": [
                {
                    "title": {"title": {"value": "SCBE: Symphonic Cipher Governance"}},
                    "type": "JOURNAL_ARTICLE",
                    "publication-date": {
                        "year": {"value": "2026"},
                        "month": {"value": "01"},
                    },
                    "external-ids": {
                        "external-id": [
                            {"external-id-type": "doi", "external-id-value": "10.9999/scbe"},
                        ]
                    },
                    "put-code": 12345,
                    "journal-title": {"value": "AI Safety Journal"},
                    "url": {"value": "https://example.com/scbe"},
                }
            ]
        }
    ]
}

MOCK_ORCID_PROFILE_RESPONSE = {
    "person": {
        "name": {
            "given-names": {"value": "Issac"},
            "family-name": {"value": "Davis"},
        },
        "emails": {"email": [{"email": "test@example.com"}]},
    }
}


def _mock_urlopen_factory(response_data: Any):
    """Create a mock urlopen context manager returning JSON data."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ==========================================================================
# Semantic Scholar Tests
# ==========================================================================


class TestSemanticScholarSource(unittest.TestCase):
    """Tests for the Semantic Scholar source adapter."""

    def setUp(self):
        self.source = SemanticScholarSource({"limit": 10})

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_fetch_returns_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_S2_SEARCH_RESPONSE)
        results = self.source.fetch("hyperbolic AI safety")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Hyperbolic Geometry for AI Safety")
        self.assertEqual(results[0].source_type, SourceType.SEMANTIC_SCHOLAR)

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_fetch_extracts_authors(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_S2_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        self.assertIn("Issac Davis", results[0].authors)
        self.assertIn("Claude AI", results[0].authors)

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_fetch_extracts_identifiers(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_S2_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        ids = results[0].identifiers
        self.assertEqual(ids["doi"], "10.1234/hyp-safety")
        self.assertEqual(ids["arxiv_id"], "2501.12345")
        self.assertEqual(ids["s2_paper_id"], "abc123")

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_fetch_extracts_metadata(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_S2_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        meta = results[0].metadata
        self.assertEqual(meta["citation_count"], 42)
        self.assertEqual(meta["venue"], "NeurIPS")
        self.assertEqual(meta["year"], 2025)

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_fetch_by_id(self, mock_urlopen):
        paper = MOCK_S2_SEARCH_RESPONSE["data"][0]
        mock_urlopen.return_value = _mock_urlopen_factory(paper)
        result = self.source.fetch_by_id("abc123")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Hyperbolic Geometry for AI Safety")

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_fetch_empty_query(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory({"data": []})
        results = self.source.fetch("")
        self.assertEqual(len(results), 0)

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_health_check(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(
            {"data": [{"title": "test"}]}
        )
        self.assertTrue(self.source.health_check())

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_tldr_as_summary(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_S2_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        self.assertEqual(
            results[0].summary,
            "Hyperbolic cost scaling makes adversarial AI infeasible.",
        )

    @patch("agents.obsidian_researcher.sources.semantic_scholar_source.urllib.request.urlopen")
    def test_tags_include_fields_and_venue(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_S2_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        tags = results[0].tags
        self.assertIn("semantic_scholar", tags)
        self.assertIn("field:Computer Science", tags)
        self.assertIn("venue:NeurIPS", tags)


# ==========================================================================
# CrossRef Tests
# ==========================================================================


class TestCrossRefSource(unittest.TestCase):
    """Tests for the CrossRef source adapter."""

    def setUp(self):
        self.source = CrossRefSource({"rows": 10})

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_fetch_returns_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_CROSSREF_SEARCH_RESPONSE)
        results = self.source.fetch("hyperbolic AI safety")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Hyperbolic Geometry for AI Safety")
        self.assertEqual(results[0].source_type, SourceType.CROSSREF)

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_fetch_extracts_doi(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_CROSSREF_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        self.assertEqual(results[0].identifiers["doi"], "10.1234/hyp-safety")

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_fetch_extracts_authors(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_CROSSREF_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        self.assertIn("Issac Davis", results[0].authors)

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_fetch_metadata(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_CROSSREF_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        meta = results[0].metadata
        self.assertEqual(meta["journal"], "NeurIPS Proceedings")
        self.assertEqual(meta["publisher"], "MIT Press")
        self.assertEqual(meta["citation_count"], 42)

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_fetch_by_doi(self, mock_urlopen):
        work = MOCK_CROSSREF_SEARCH_RESPONSE["message"]["items"][0]
        mock_urlopen.return_value = _mock_urlopen_factory(
            {"status": "ok", "message": work}
        )
        result = self.source.fetch_by_id("10.1234/hyp-safety")
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Hyperbolic Geometry for AI Safety")

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_fetch_by_doi_url(self, mock_urlopen):
        work = MOCK_CROSSREF_SEARCH_RESPONSE["message"]["items"][0]
        mock_urlopen.return_value = _mock_urlopen_factory(
            {"status": "ok", "message": work}
        )
        result = self.source.fetch_by_id("https://doi.org/10.1234/hyp-safety")
        self.assertIsNotNone(result)

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_health_check(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(
            {"status": "ok", "message": {"items": []}}
        )
        self.assertTrue(self.source.health_check())

    @patch("agents.obsidian_researcher.sources.crossref_source.urllib.request.urlopen")
    def test_tags_include_type_and_subject(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_CROSSREF_SEARCH_RESPONSE)
        results = self.source.fetch("test")
        tags = results[0].tags
        self.assertIn("crossref", tags)
        self.assertIn("type:journal-article", tags)
        self.assertIn("subject:Computer Science", tags)


# ==========================================================================
# ORCID Tests
# ==========================================================================


class TestORCIDSource(unittest.TestCase):
    """Tests for the ORCID source adapter."""

    def setUp(self):
        self.source = ORCIDSource({"orcid_id": "0009-0002-3936-9369"})

    @patch("agents.obsidian_researcher.sources.orcid_source.urllib.request.urlopen")
    def test_fetch_works(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_ORCID_WORKS_RESPONSE)
        works = self.source.fetch_works()
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0]["title"], "SCBE: Symphonic Cipher Governance")

    @patch("agents.obsidian_researcher.sources.orcid_source.urllib.request.urlopen")
    def test_fetch_profile(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_ORCID_PROFILE_RESPONSE)
        profile = self.source.fetch_profile()
        self.assertIsNotNone(profile)
        self.assertEqual(profile["name"], "Issac Davis")
        self.assertEqual(profile["orcid_id"], "0009-0002-3936-9369")

    @patch("agents.obsidian_researcher.sources.orcid_source.urllib.request.urlopen")
    def test_fetch_returns_ingestion_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_ORCID_WORKS_RESPONSE)
        results = self.source.fetch("")  # Empty query = all works
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], IngestionResult)
        self.assertEqual(results[0].title, "SCBE: Symphonic Cipher Governance")

    @patch("agents.obsidian_researcher.sources.orcid_source.urllib.request.urlopen")
    def test_fetch_extracts_external_ids(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_ORCID_WORKS_RESPONSE)
        works = self.source.fetch_works()
        self.assertEqual(works[0]["external_ids"]["doi"], "10.9999/scbe")

    @patch("agents.obsidian_researcher.sources.orcid_source.urllib.request.urlopen")
    def test_fetch_filters_by_query(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_ORCID_WORKS_RESPONSE)
        results = self.source.fetch("nonexistent-query")
        self.assertEqual(len(results), 0)

    @patch("agents.obsidian_researcher.sources.orcid_source.urllib.request.urlopen")
    def test_health_check(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_factory(MOCK_ORCID_PROFILE_RESPONSE)
        self.assertTrue(self.source.health_check())


# ==========================================================================
# Research Connector Service Tests
# ==========================================================================


class _MockAdapter(SourceAdapter):
    """Deterministic mock source for service testing."""

    def __init__(self, source_type: SourceType, results: List[IngestionResult], healthy: bool = True):
        super().__init__(source_type=source_type, config={})
        self._results = results
        self._healthy = healthy

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        return [r for r in self._results if query.lower() in r.title.lower() or not query]

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        for r in self._results:
            if identifier in r.identifiers.values():
                return r
        return None

    def health_check(self) -> bool:
        return self._healthy


def _make_result(title: str, source_type: SourceType, **kwargs) -> IngestionResult:
    return IngestionResult(
        source_type=source_type,
        raw_content=kwargs.get("raw", title),
        title=title,
        authors=kwargs.get("authors", []),
        url=kwargs.get("url", ""),
        timestamp=kwargs.get("timestamp", ""),
        identifiers=kwargs.get("identifiers", {}),
        tags=kwargs.get("tags", []),
        metadata=kwargs.get("metadata", {}),
        summary=kwargs.get("summary", title),
    )


class TestResearchConnectorService(unittest.TestCase):
    """Tests for the tiered research service."""

    def _make_service(self) -> ResearchConnectorService:
        """Create a service with mock adapters for each tier."""
        service = ResearchConnectorService.__new__(ResearchConnectorService)
        service._config = {}
        service._sources = {}

        # Tier 1 — Academic
        service._sources["semantic_scholar"] = (
            _MockAdapter(SourceType.SEMANTIC_SCHOLAR, [
                _make_result(
                    "Hyperbolic AI Safety", SourceType.SEMANTIC_SCHOLAR,
                    identifiers={"doi": "10.1234/test", "arxiv_id": "2501.12345"},
                    metadata={"citation_count": 50},
                ),
                _make_result(
                    "Post-Quantum Crypto", SourceType.SEMANTIC_SCHOLAR,
                    identifiers={"doi": "10.5678/pqc"},
                    metadata={"citation_count": 100},
                ),
            ]),
            Tier.ACADEMIC,
        )
        service._sources["crossref"] = (
            _MockAdapter(SourceType.CROSSREF, [
                _make_result(
                    "Hyperbolic AI Safety", SourceType.CROSSREF,
                    identifiers={"doi": "10.1234/test"},
                    metadata={"citation_count": 50},
                ),
            ]),
            Tier.ACADEMIC,
        )

        # Tier 2 — Professional
        service._sources["github"] = (
            _MockAdapter(SourceType.GITHUB, [
                _make_result("SCBE-AETHERMOORE repo", SourceType.GITHUB),
            ]),
            Tier.PROFESSIONAL,
        )

        # Tier 3 — General
        service._sources["web_page"] = (
            _MockAdapter(SourceType.WEB_PAGE, [
                _make_result("Random blog about AI safety", SourceType.WEB_PAGE),
            ]),
            Tier.GENERAL,
        )

        # Tier 4 — Community
        service._sources["reddit"] = (
            _MockAdapter(SourceType.REDDIT, [
                _make_result("Reddit post about AI safety", SourceType.REDDIT),
            ]),
            Tier.COMMUNITY,
        )

        return service

    def test_registered_sources(self):
        service = self._make_service()
        sources = service.registered_sources
        self.assertIn("semantic_scholar", sources)
        self.assertEqual(sources["semantic_scholar"], 1)
        self.assertEqual(sources["reddit"], 4)

    def test_search_all_tiers(self):
        service = self._make_service()
        report = service.search("AI safety")
        self.assertIsInstance(report, SearchReport)
        self.assertGreater(report.total_raw, 0)
        self.assertGreater(len(report.results), 0)

    def test_search_academic_only(self):
        service = self._make_service()
        report = service.search("Hyperbolic", tiers=[1])
        # Should only have academic results
        for sr in report.results:
            self.assertEqual(sr.tier, Tier.ACADEMIC)

    def test_search_specific_sources(self):
        service = self._make_service()
        report = service.search("", sources=["github"])
        self.assertEqual(report.sources_queried, ["github"])
        for sr in report.results:
            self.assertEqual(sr.source_name, "github")

    def test_tier_trust_scores(self):
        service = self._make_service()
        report = service.search("")
        for sr in report.results:
            self.assertEqual(sr.trust_score, _TIER_TRUST[sr.tier])

    def test_deduplication(self):
        service = self._make_service()
        # "Hyperbolic AI Safety" appears in both semantic_scholar and crossref
        report = service.search("Hyperbolic", deduplicate=True)
        titles = [sr.result.title for sr in report.results]
        # Should not have exact duplicates
        self.assertEqual(len(titles), len(set(t.lower().strip() for t in titles)))

    def test_no_deduplication(self):
        service = self._make_service()
        report = service.search("Hyperbolic", deduplicate=False)
        # Could have duplicates from S2 and CrossRef
        self.assertGreaterEqual(report.total_raw, 2)

    def test_min_score_filter(self):
        service = self._make_service()
        report = service.search("", min_score=0.9)
        for sr in report.results:
            self.assertGreaterEqual(sr.composite_score, 0.9)

    def test_max_results_limit(self):
        service = self._make_service()
        report = service.search("", max_results=2)
        self.assertLessEqual(len(report.results), 2)

    def test_search_report_structure(self):
        service = self._make_service()
        report = service.search("test")
        self.assertEqual(report.query, "test")
        self.assertIsInstance(report.elapsed_ms, float)
        self.assertIsInstance(report.tiers_searched, list)
        self.assertIsInstance(report.sources_queried, list)

    def test_search_academic_convenience(self):
        service = self._make_service()
        report = service.search_academic("Hyperbolic")
        self.assertEqual(report.tiers_searched, [1])

    def test_search_all_convenience(self):
        service = self._make_service()
        report = service.search_all("")
        self.assertEqual(sorted(report.tiers_searched), [1, 2, 3, 4])

    def test_results_sorted_by_composite_score(self):
        service = self._make_service()
        report = service.search("")
        scores = [sr.composite_score for sr in report.results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_health_report(self):
        service = self._make_service()
        health = service.health_report()
        self.assertIsInstance(health, HealthReport)
        self.assertGreater(health.total_healthy, 0)
        self.assertIn("semantic_scholar", health.sources)

    def test_resolve_doi(self):
        service = self._make_service()
        result = service.resolve_doi("10.1234/test")
        self.assertIsNotNone(result)
        self.assertIn("10.1234/test", result.identifiers.values())

    def test_to_jsonl_export(self):
        service = self._make_service()
        report = service.search("")
        jsonl = service.to_jsonl(report)
        lines = jsonl.strip().split("\n")
        self.assertEqual(len(lines), len(report.results))
        for line in lines:
            entry = json.loads(line)
            self.assertIn("title", entry)
            self.assertIn("tier", entry)
            self.assertIn("composite", entry)

    def test_scoring_boosts_doi_identifiers(self):
        """Results with DOI/arXiv should get relevance boost."""
        service = self._make_service()
        report = service.search("Hyperbolic AI Safety")
        # S2 result has both DOI and arXiv
        s2_results = [sr for sr in report.results if sr.source_name == "semantic_scholar"]
        if s2_results:
            self.assertGreater(s2_results[0].relevance_score, 0.0)

    def test_scoring_boosts_citations(self):
        """Results with high citation count should get relevance boost."""
        service = self._make_service()
        report = service.search("Post-Quantum Crypto")
        pqc_results = [
            sr for sr in report.results
            if "Post-Quantum" in sr.result.title
        ]
        if pqc_results:
            self.assertGreater(pqc_results[0].relevance_score, 0.0)

    def test_community_tier_filtered_by_default(self):
        """Community sources need higher composite score to pass."""
        service = self._make_service()
        report = service.search("unrelated query terms not in any title")
        # Reddit results with 0 relevance should be filtered at 0.5 threshold
        reddit_results = [sr for sr in report.results if sr.source_name == "reddit"]
        for rr in reddit_results:
            self.assertGreaterEqual(rr.composite_score, _TIER_THRESHOLD[Tier.COMMUNITY])

    def test_error_handling_source_failure(self):
        """Service should handle source failures gracefully."""
        service = self._make_service()
        # Replace github with a failing adapter
        class _FailAdapter(SourceAdapter):
            def __init__(self):
                super().__init__(source_type=SourceType.GITHUB, config={})
            def fetch(self, query, **kw):
                raise RuntimeError("API down")
            def fetch_by_id(self, id):
                return None

        service._sources["github"] = (_FailAdapter(), Tier.PROFESSIONAL)
        report = service.search("")
        self.assertGreater(len(report.errors), 0)
        self.assertIn("github", report.errors[0])

    def test_empty_service(self):
        """Service with no sources should return empty results."""
        service = ResearchConnectorService.__new__(ResearchConnectorService)
        service._config = {}
        service._sources = {}
        report = service.search("test")
        self.assertEqual(len(report.results), 0)
        self.assertEqual(report.total_raw, 0)


class TestTierConstants(unittest.TestCase):
    """Verify tier configuration."""

    def test_trust_scores_decrease_by_tier(self):
        self.assertGreater(_TIER_TRUST[Tier.ACADEMIC], _TIER_TRUST[Tier.PROFESSIONAL])
        self.assertGreater(_TIER_TRUST[Tier.PROFESSIONAL], _TIER_TRUST[Tier.GENERAL])
        self.assertGreater(_TIER_TRUST[Tier.GENERAL], _TIER_TRUST[Tier.COMMUNITY])

    def test_thresholds_increase_by_tier(self):
        self.assertLessEqual(_TIER_THRESHOLD[Tier.ACADEMIC], _TIER_THRESHOLD[Tier.PROFESSIONAL])
        self.assertLessEqual(_TIER_THRESHOLD[Tier.PROFESSIONAL], _TIER_THRESHOLD[Tier.GENERAL])
        self.assertLessEqual(_TIER_THRESHOLD[Tier.GENERAL], _TIER_THRESHOLD[Tier.COMMUNITY])

    def test_all_tiers_have_trust(self):
        for tier in Tier:
            self.assertIn(tier, _TIER_TRUST)

    def test_all_tiers_have_threshold(self):
        for tier in Tier:
            self.assertIn(tier, _TIER_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
