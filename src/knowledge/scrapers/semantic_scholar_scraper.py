"""
Semantic Scholar Scraper — citation graphs, related papers, author networks.

Free API, no key needed. Rate limited to 100 req/5min.
"""

import time
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

S2_API = "https://api.semanticscholar.org/graph/v1"
RATE_LIMIT = 1


def search_papers(
    query: str, limit: int = 20, fields: str = "title,abstract,authors,year,url,citationCount"
) -> list[KnowledgeChunk]:
    """Search Semantic Scholar for papers."""
    params = urlencode({"query": query, "limit": limit, "fields": fields})
    url = f"{S2_API}/paper/search?{params}"

    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())

    chunks = []
    for paper in data.get("data", []):
        authors = [a.get("name", "") for a in paper.get("authors", [])]
        abstract = paper.get("abstract", "") or ""
        title = paper.get("title", "Unknown")
        year = paper.get("year", "")
        citations = paper.get("citationCount", 0)

        chunk = KnowledgeChunk(
            id="",
            source="semantic_scholar",
            category="research",
            title=title,
            content=f"# {title}\n\nAuthors: {', '.join(authors)}\nYear: {year}\nCitations: {citations}\n\n{abstract}",
            url=paper.get("url", ""),
            metadata={
                "s2_paper_id": paper.get("paperId", ""),
                "year": year,
                "citation_count": citations,
                "authors": authors,
            },
        )
        chunks.append(chunk)

    return chunks


def get_citations(paper_id: str, limit: int = 20) -> list[KnowledgeChunk]:
    """Get papers that cite a given paper — follow the knowledge graph."""
    url = f"{S2_API}/paper/{paper_id}/citations?fields=title,abstract,authors,year,url&limit={limit}"
    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0"})

    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())

    chunks = []
    for entry in data.get("data", []):
        paper = entry.get("citingPaper", {})
        if not paper.get("title"):
            continue

        authors = [a.get("name", "") for a in paper.get("authors", [])]
        chunk = KnowledgeChunk(
            id="",
            source="semantic_scholar",
            category="citations",
            title=paper.get("title", ""),
            content=(
                f"# {paper.get('title', '')}\n\nAuthors: {', '.join(authors)}\n"
                f"Year: {paper.get('year', '')}\n\n{paper.get('abstract', '') or ''}"
            ),
            url=paper.get("url", ""),
            metadata={
                "s2_paper_id": paper.get("paperId", ""),
                "citing_paper_id": paper_id,
            },
        )
        chunks.append(chunk)

    return chunks


SCBE_RESEARCH_QUERIES = [
    "hyperbolic geometry AI safety",
    "Poincare ball embedding neural network",
    "post-quantum cryptography lattice",
    "multi-agent governance consensus",
    "sacred geometry tokenization",
    "geometric deep learning hyperbolic",
    "adversarial robustness exponential cost",
    "blockchain memory distributed ledger AI",
    "RAG retrieval augmented generation security",
    "autonomous agent containment",
]


def scrape_all_queries(max_per_query: int = 10) -> list[KnowledgeChunk]:
    """Run all SCBE-relevant research queries."""
    all_chunks = []
    for query in SCBE_RESEARCH_QUERIES:
        print(f"  Searching S2 for '{query}'...")
        chunks = search_papers(query, limit=max_per_query)
        all_chunks.extend(chunks)
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    chunks = scrape_all_queries(max_per_query=5)
    print(f"\nFound {len(chunks)} papers")
    for c in chunks[:5]:
        print(f"  [{c.metadata.get('citation_count', 0)} cites] {c.title[:80]}")
