"""
Internet Archive Scraper — pulls from archive.org's free search API.

Covers: books, texts, software, audio, video, web pages.
No API key needed. Rate limit: be polite (~1 req/sec).
"""

import time
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

IA_API = "https://archive.org"
RATE_LIMIT = 1.0


def search_archive(query: str, media_type: str = "texts", limit: int = 25) -> list[KnowledgeChunk]:
    """Search Internet Archive."""
    params = {
        "q": f"{query} AND mediatype:{media_type}",
        "output": "json",
        "rows": limit,
        "fl[]": "identifier,title,description,creator,date,subject,downloads",
    }
    url = f"{IA_API}/advancedsearch.php?{urlencode(params, doseq=True)}"

    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE research)"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())

    chunks = []
    for doc in data.get("response", {}).get("docs", []):
        identifier = doc.get("identifier", "")
        title = doc.get("title", "Unknown")
        if isinstance(title, list):
            title = title[0]
        description = doc.get("description", "")
        if isinstance(description, list):
            description = " ".join(description)
        creator = doc.get("creator", "")
        if isinstance(creator, list):
            creator = ", ".join(creator)
        date = doc.get("date", "")
        subjects = doc.get("subject", [])
        if isinstance(subjects, str):
            subjects = [subjects]
        downloads = doc.get("downloads", 0)

        category = _categorize_ia(title, description, subjects)

        chunk = KnowledgeChunk(
            id="",
            source="internet_archive",
            category=category,
            title=title,
            content=f"# {title}\n\nCreator: {creator}\nDate: {date}\nDownloads: {downloads}\nSubjects: {', '.join(subjects[:5])}\n\n{str(description)[:3000]}",
            url=f"https://archive.org/details/{identifier}",
            metadata={
                "ia_identifier": identifier,
                "media_type": media_type,
                "downloads": downloads,
                "subjects": subjects[:10],
            },
        )
        chunks.append(chunk)

    return chunks


def _categorize_ia(title: str, description: str, subjects: list) -> str:
    """Map IA results to knowledge categories."""
    text = (title + " " + str(description) + " " + " ".join(subjects)).lower()
    if any(kw in text for kw in ["cryptograph", "cipher", "encryption"]):
        return "security"
    if any(kw in text for kw in ["geometry", "manifold", "topology", "hyperbolic"]):
        return "math"
    if any(kw in text for kw in ["artificial intelligence", "machine learning", "neural network"]):
        return "ai"
    if any(kw in text for kw in ["quantum", "qubit"]):
        return "quantum"
    if any(kw in text for kw in ["governance", "policy", "regulation"]):
        return "governance"
    return "research"


IA_RESEARCH_QUERIES = [
    "hyperbolic geometry",
    "post-quantum cryptography",
    "AI safety alignment",
    "sacred geometry",
    "distributed consensus protocols",
    "tokenization natural language",
    "neural network security",
    "blockchain memory",
]


def scrape_all_queries(max_per_query: int = 10) -> list[KnowledgeChunk]:
    """Run all SCBE-relevant IA queries."""
    all_chunks = []
    for query in IA_RESEARCH_QUERIES:
        print(f"  Searching Internet Archive for '{query}'...")
        try:
            chunks = search_archive(query, limit=max_per_query)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    chunks = scrape_all_queries(max_per_query=5)
    print(f"\nFound {len(chunks)} items from Internet Archive")
    for c in chunks[:5]:
        print(f"  [{c.category}] {c.title[:80]}")
