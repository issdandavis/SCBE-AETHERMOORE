"""
Harvard Dataverse Scraper — pulls research datasets from the open Dataverse API.

Free, no key needed. Rate limit: be polite (~1 req/sec).
"""

import time
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

DATAVERSE_API = "https://dataverse.harvard.edu/api"
RATE_LIMIT = 1.5


def search_datasets(query: str, limit: int = 20) -> list[KnowledgeChunk]:
    """Search Harvard Dataverse for datasets."""
    params = {
        "q": query,
        "type": "dataset",
        "per_page": limit,
    }
    url = f"{DATAVERSE_API}/search?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE research)"})

    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())

    chunks = []
    for item in data.get("data", {}).get("items", []):
        name = item.get("name", "Unknown")
        description = item.get("description", "")
        url_val = item.get("url", "")
        published_at = item.get("published_at", "")
        citation = item.get("citation", "")
        subjects = item.get("subjects", [])
        authors = item.get("authors", [])
        global_id = item.get("global_id", "")

        category = _categorize_dataverse(name, description, subjects)

        chunk = KnowledgeChunk(
            id="",
            source="harvard_dataverse",
            category=category,
            title=name,
            content=(
                f"# {name}\n\nAuthors: {', '.join(authors[:5])}\n"
                f"Published: {published_at}\nSubjects: {', '.join(subjects[:5])}\n"
                f"DOI: {global_id}\n\n{description[:3000]}\n\nCitation: {citation}"
            ),
            url=url_val,
            metadata={
                "dataverse_id": global_id,
                "subjects": subjects,
                "authors": authors,
                "file_count": item.get("fileCount", 0),
            },
        )
        chunks.append(chunk)

    return chunks


def _categorize_dataverse(name: str, description: str, subjects: list) -> str:
    """Map Dataverse results to knowledge categories."""
    text = (name + " " + description + " " + " ".join(subjects)).lower()
    if any(kw in text for kw in ["cryptograph", "security", "cyber"]):
        return "security"
    if any(kw in text for kw in ["geometry", "manifold", "topology", "mathematical"]):
        return "math"
    if any(kw in text for kw in ["artificial intelligence", "machine learning", "deep learning"]):
        return "ai"
    if any(kw in text for kw in ["quantum", "qubit"]):
        return "quantum"
    if any(kw in text for kw in ["language", "nlp", "text mining", "corpus"]):
        return "nlp"
    return "research"


DATAVERSE_RESEARCH_QUERIES = [
    "cryptography",
    "machine learning security",
    "hyperbolic embedding",
    "graph neural network",
    "natural language processing",
    "quantum computing",
    "blockchain",
    "adversarial machine learning",
]


def scrape_all_queries(max_per_query: int = 10) -> list[KnowledgeChunk]:
    """Run all SCBE-relevant Dataverse queries."""
    all_chunks = []
    for query in DATAVERSE_RESEARCH_QUERIES:
        print(f"  Searching Harvard Dataverse for '{query}'...")
        try:
            chunks = search_datasets(query, limit=max_per_query)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    chunks = scrape_all_queries(max_per_query=5)
    print(f"\nFound {len(chunks)} datasets from Harvard Dataverse")
    for c in chunks[:5]:
        print(f"  [{c.category}] {c.title[:80]}")
