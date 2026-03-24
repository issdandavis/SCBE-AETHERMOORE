"""
Library of Congress Scraper — pulls from LOC's free JSON API.

Covers: digitized books, manuscripts, maps, photos, legislation, newspaper archives.
No API key needed. Rate limit: be polite (~1 req/sec).
"""

import time
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

LOC_API = "https://www.loc.gov"
RATE_LIMIT = 1.5


def search_loc(query: str, collection: str = "", limit: int = 25) -> list[KnowledgeChunk]:
    """Search Library of Congress collections."""
    params = {"q": query, "fo": "json", "c": limit, "sp": 1}
    if collection:
        url = f"{LOC_API}/{collection}/?{urlencode(params)}"
    else:
        url = f"{LOC_API}/search/?{urlencode(params)}"

    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE research)"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())

    chunks = []
    for result in data.get("results", []):
        title = result.get("title", "Unknown")
        description = result.get("description", [""])
        if isinstance(description, list):
            description = " ".join(description)

        subjects = result.get("subject", [])
        if isinstance(subjects, list):
            subjects = subjects[:10]

        dates = result.get("date", "")
        item_url = result.get("url", "") or result.get("id", "")
        contributors = result.get("contributor", [])

        category = _categorize_loc(title, subjects)

        chunk = KnowledgeChunk(
            id="",
            source="library_of_congress",
            category=category,
            title=title,
            content=f"# {title}\n\nContributors: {', '.join(contributors[:5]) if contributors else 'N/A'}\nDate: {dates}\nSubjects: {', '.join(subjects[:5])}\n\n{description[:3000]}",
            url=item_url,
            metadata={
                "loc_collection": collection,
                "subjects": subjects[:10],
                "dates": dates,
                "original_format": result.get("original_format", []),
            },
        )
        chunks.append(chunk)

    return chunks


def _categorize_loc(title: str, subjects: list) -> str:
    """Map LOC results to knowledge categories."""
    text = (title + " " + " ".join(subjects)).lower()
    if any(kw in text for kw in ["cryptograph", "cipher", "encryption", "security"]):
        return "security"
    if any(kw in text for kw in ["geometry", "manifold", "topology", "mathematical"]):
        return "math"
    if any(kw in text for kw in ["artificial intelligence", "machine learning", "neural"]):
        return "ai"
    if any(kw in text for kw in ["quantum", "physics"]):
        return "quantum"
    if any(kw in text for kw in ["govern", "law", "policy", "regulation", "patent"]):
        return "governance"
    if any(kw in text for kw in ["language", "linguistic", "tokeniz"]):
        return "nlp"
    return "research"


LOC_RESEARCH_QUERIES = [
    "cryptography history",
    "hyperbolic geometry",
    "artificial intelligence safety",
    "quantum computing",
    "network security protocols",
    "sacred geometry mathematics",
    "distributed systems consensus",
    "post-quantum cryptography",
]

LOC_COLLECTIONS = [
    "manuscripts",
    "maps",
    "newspapers",
]


def scrape_all_queries(max_per_query: int = 10) -> list[KnowledgeChunk]:
    """Run all SCBE-relevant LOC queries."""
    all_chunks = []
    for query in LOC_RESEARCH_QUERIES:
        print(f"  Searching LOC for '{query}'...")
        try:
            chunks = search_loc(query, limit=max_per_query)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    chunks = scrape_all_queries(max_per_query=5)
    print(f"\nFound {len(chunks)} items from Library of Congress")
    for c in chunks[:5]:
        print(f"  [{c.category}] {c.title[:80]}")
