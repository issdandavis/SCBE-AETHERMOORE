"""
arXiv Scraper — pulls papers from cs.AI, cs.CR, cs.CL, math.DG, quant-ph.

Feeds into the Knowledge Funnel as KnowledgeChunks.
Protected by antivirus gate before deposit.
"""

import time
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

ARXIV_API = "https://export.arxiv.org/api/query"
RATE_LIMIT = 3  # seconds between requests

# Categories we care about
CATEGORIES = {
    "cs.AI": "ai",
    "cs.CR": "security",
    "cs.CL": "nlp",
    "cs.LG": "machine-learning",
    "math.DG": "geometry",
    "quant-ph": "quantum",
    "cs.MA": "multi-agent",
    "cs.DC": "distributed",
}


def search_arxiv(query: str, category: str = "cs.AI", max_results: int = 20) -> list[KnowledgeChunk]:
    """Search arXiv and return KnowledgeChunks."""
    params = {
        "search_query": f"cat:{category} AND all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urlencode(params)}"

    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE)"})
    with urlopen(req, timeout=30) as response:
        data = response.read()

    root = ET.fromstring(data)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    chunks = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        id_el = entry.find("atom:id", ns)

        title = title_el.text.strip().replace("\n", " ") if title_el is not None else "Unknown"
        summary = summary_el.text.strip() if summary_el is not None else ""
        published = published_el.text.strip() if published_el is not None else ""
        arxiv_url = id_el.text.strip() if id_el is not None else ""

        # Extract authors
        authors = []
        for author in entry.findall("atom:author/atom:name", ns):
            authors.append(author.text)

        mapped_cat = CATEGORIES.get(category, "research")

        chunk = KnowledgeChunk(
            id="",
            source="arxiv",
            category=mapped_cat,
            title=title,
            content=f"# {title}\n\nAuthors: {', '.join(authors)}\nPublished: {published}\n\n{summary}",
            url=arxiv_url,
            timestamp=published,
            metadata={
                "authors": authors,
                "arxiv_category": category,
                "arxiv_id": arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else "",
            },
        )
        chunks.append(chunk)

    return chunks


def scrape_all_categories(query: str, max_per_cat: int = 10) -> list[KnowledgeChunk]:
    """Scrape all SCBE-relevant arXiv categories."""
    all_chunks = []
    for cat in CATEGORIES:
        print(f"  Scraping arXiv {cat} for '{query}'...")
        chunks = search_arxiv(query, category=cat, max_results=max_per_cat)
        all_chunks.extend(chunks)
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "hyperbolic geometry AI safety"
    chunks = scrape_all_categories(query, max_per_cat=5)
    print(f"\nFound {len(chunks)} papers across all categories")
    for c in chunks[:5]:
        print(f"  [{c.category}] {c.title[:80]}")
