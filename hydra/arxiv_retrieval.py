"""
HYDRA arXiv Retrieval
=====================

AI-to-AI retrieval helpers for arXiv metadata.

Design goals:
- Deterministic retrieval packets for agent handoff
- Standards-only dependencies (httpx + stdlib XML)
- arXiv API etiquette support (optional request delay)
"""

from __future__ import annotations

import hashlib
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


class ArxivAPIError(RuntimeError):
    """Raised when arXiv API returns malformed or error responses."""


@dataclass(frozen=True)
class ArxivPaper:
    """Normalized arXiv paper metadata."""

    arxiv_id: str
    title: str
    summary: str
    authors: List[str]
    categories: List[str]
    primary_category: Optional[str]
    published: Optional[str]
    updated: Optional[str]
    abs_url: str
    pdf_url: Optional[str]
    comment: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArxivSearchResult:
    """Search result with metadata and papers."""

    query: str
    start: int
    max_results: int
    total_results: int
    papers: List[ArxivPaper]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "start": self.start,
            "max_results": self.max_results,
            "total_results": self.total_results,
            "papers": [p.to_dict() for p in self.papers],
        }


class ArxivClient:
    """
    Thin client for arXiv Atom API.

    Notes:
    - API docs: https://info.arxiv.org/help/api/user-manual.html
    - arXiv requests a polite delay for repeated calls.
    """

    def __init__(
        self,
        api_url: str = ARXIV_API_URL,
        timeout_seconds: float = 20.0,
        min_delay_seconds: float = 3.0,
        user_agent: Optional[str] = None,
    ) -> None:
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.min_delay_seconds = min_delay_seconds
        self.user_agent = user_agent or os.getenv(
            "ARXIV_USER_AGENT",
            "SCBE-AETHERMOORE-HYDRA/1.0 (+https://sites.google.com/view/aethermoorcommandcenter)",
        )
        self._last_request_ts = 0.0

    def search(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        start: int = 0,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        raw_query: bool = False,
    ) -> ArxivSearchResult:
        if not query.strip():
            raise ValueError("query must not be empty")
        if start < 0:
            raise ValueError("start must be >= 0")
        if max_results <= 0:
            raise ValueError("max_results must be > 0")

        normalized_query = query.strip()
        search_query = normalized_query if raw_query else f"all:{normalized_query}"
        if category:
            search_query = f"{search_query}+AND+cat:{category}"

        params = {
            "search_query": search_query,
            "start": str(start),
            "max_results": str(max_results),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        xml_text = self._fetch_xml(params)
        total, papers = self._parse_feed(xml_text)
        return ArxivSearchResult(
            query=normalized_query,
            start=start,
            max_results=max_results,
            total_results=total,
            papers=papers,
        )

    def fetch_by_ids(self, ids: List[str]) -> List[ArxivPaper]:
        cleaned_ids = [self._clean_id(x) for x in ids if x and x.strip()]
        if not cleaned_ids:
            raise ValueError("ids must contain at least one arXiv id")
        params = {"id_list": ",".join(cleaned_ids)}
        xml_text = self._fetch_xml(params)
        _, papers = self._parse_feed(xml_text)
        return papers

    def _fetch_xml(self, params: Dict[str, str]) -> str:
        self._respect_rate_limit()
        headers = {"User-Agent": self.user_agent}
        response = httpx.get(
            self.api_url,
            params=params,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        self._last_request_ts = time.monotonic()
        response.raise_for_status()
        return response.text

    def _respect_rate_limit(self) -> None:
        if self.min_delay_seconds <= 0:
            return
        now = time.monotonic()
        wait_for = self.min_delay_seconds - (now - self._last_request_ts)
        if wait_for > 0:
            time.sleep(wait_for)

    def _parse_feed(self, xml_text: str) -> tuple[int, List[ArxivPaper]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ArxivAPIError(f"unable to parse arXiv response: {exc}") from exc

        title = self._find_text(root, "atom:title")
        summary = self._find_text(root, "atom:summary")
        if title and "error" in title.lower():
            raise ArxivAPIError(summary or "arXiv API returned an error feed")

        total_raw = self._find_text(root, "opensearch:totalResults")
        total = int(total_raw) if total_raw and total_raw.isdigit() else 0

        papers: List[ArxivPaper] = []
        for entry in root.findall("atom:entry", ARXIV_NS):
            paper = self._parse_entry(entry)
            if paper:
                papers.append(paper)
        return total, papers

    def _parse_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        id_url = self._find_text(entry, "atom:id")
        if not id_url:
            return None
        arxiv_id = self._clean_id(id_url)
        title = self._normalize_whitespace(self._find_text(entry, "atom:title") or "")
        summary = self._normalize_whitespace(self._find_text(entry, "atom:summary") or "")
        published = self._find_text(entry, "atom:published")
        updated = self._find_text(entry, "atom:updated")
        comment = self._find_text(entry, "arxiv:comment")

        authors: List[str] = []
        for a in entry.findall("atom:author", ARXIV_NS):
            name = self._find_text(a, "atom:name")
            if name:
                authors.append(name)

        categories = [c.attrib.get("term", "") for c in entry.findall("atom:category", ARXIV_NS)]
        categories = [c for c in categories if c]
        primary_category_node = entry.find("arxiv:primary_category", ARXIV_NS)
        primary_category = None
        if primary_category_node is not None:
            primary_category = primary_category_node.attrib.get("term")

        abs_url = id_url
        pdf_url = None
        for link in entry.findall("atom:link", ARXIV_NS):
            href = link.attrib.get("href", "")
            rel = link.attrib.get("rel", "")
            title_attr = link.attrib.get("title", "")
            type_attr = link.attrib.get("type", "")
            if rel == "alternate" and href:
                abs_url = href
            if title_attr == "pdf" or type_attr == "application/pdf" or href.endswith(".pdf"):
                pdf_url = href

        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )

    @staticmethod
    def _find_text(node: ET.Element, path: str) -> Optional[str]:
        target = node.find(path, ARXIV_NS)
        if target is None or target.text is None:
            return None
        return target.text.strip()

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def _clean_id(value: str) -> str:
        text = value.strip()
        if "/abs/" in text:
            text = text.split("/abs/", 1)[1]
        if "/pdf/" in text:
            text = text.split("/pdf/", 1)[1]
        if text.endswith(".pdf"):
            text = text[:-4]
        return text


class AI2AIRetrievalService:
    """
    Service layer for agent-to-agent handoff packets from arXiv.
    """

    def __init__(self, client: Optional[ArxivClient] = None, librarian: Optional[Any] = None) -> None:
        self.client = client or ArxivClient()
        self.librarian = librarian

    def retrieve_arxiv_packet(
        self,
        *,
        requester: str,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5,
        remember: bool = True,
        raw_query: bool = False,
    ) -> Dict[str, Any]:
        result = self.client.search(
            query=query,
            category=category,
            max_results=max_results,
            raw_query=raw_query,
        )
        generated_at = datetime.now(timezone.utc).isoformat()
        ids = ",".join(p.arxiv_id for p in result.papers)
        packet_id = hashlib.sha256(f"{requester}|{query}|{ids}|{generated_at}".encode("utf-8")).hexdigest()[:16]
        packet = {
            "packet_id": packet_id,
            "source": "arxiv",
            "requester": requester,
            "query": result.query,
            "category": category,
            "generated_at": generated_at,
            "total_results": result.total_results,
            "returned_results": len(result.papers),
            "papers": [p.to_dict() for p in result.papers],
            "hints_for_next_agent": [
                "Rank by abstract relevance and novelty.",
                "Extract methods, baselines, and datasets.",
                "Draft a related-work matrix before writing.",
            ],
        }
        if remember and self.librarian is not None:
            keywords = [query] + ([category] if category else [])
            self.librarian.remember(
                key=f"arxiv_packet:{packet_id}",
                value=packet,
                category="research.arxiv",
                importance=0.8,
                keywords=keywords,
            )
        return packet

    @staticmethod
    def build_related_work_outline(packet: Dict[str, Any]) -> str:
        lines = [
            "# Related Work Outline",
            "",
            f"- Packet: `{packet.get('packet_id', 'unknown')}`",
            f"- Query: `{packet.get('query', '')}`",
            f"- Retrieved: `{packet.get('returned_results', 0)}` papers",
            "",
        ]
        for idx, paper in enumerate(packet.get("papers", []), start=1):
            authors = ", ".join(paper.get("authors", [])[:3])
            cats = ", ".join(paper.get("categories", [])[:3])
            lines.append(
                f"{idx}. **{paper.get('title', '').strip()}** "
                f"({paper.get('arxiv_id', '')})"
            )
            if authors:
                lines.append(f"   Authors: {authors}")
            if cats:
                lines.append(f"   Categories: {cats}")
            if paper.get("summary"):
                lines.append(f"   Summary: {paper['summary'][:420]}...")
            if paper.get("pdf_url"):
                lines.append(f"   PDF: {paper['pdf_url']}")
        return "\n".join(lines) + "\n"
