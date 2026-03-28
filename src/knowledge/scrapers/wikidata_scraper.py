"""
Wikidata Scraper — structured knowledge from the Wikidata SPARQL endpoint.

Pulls entities, relationships, and properties for SCBE-relevant concepts.
Free, no key needed. Rate limit: ~5 req/min for SPARQL.
"""

import time
import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
RATE_LIMIT = 2.0


def search_entities(query: str, limit: int = 20) -> list[KnowledgeChunk]:
    """Search Wikidata entities by label."""
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "limit": limit,
        "format": "json",
    }
    url = f"{WIKIDATA_API}?{urlencode(params)}"
    req = Request(
        url, headers={"User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE research)"}
    )

    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())

    chunks = []
    for entity in data.get("search", []):
        entity_id = entity.get("id", "")
        label = entity.get("label", "Unknown")
        description = entity.get("description", "")
        url_val = entity.get("concepturi", f"https://www.wikidata.org/wiki/{entity_id}")

        chunk = KnowledgeChunk(
            id="",
            source="wikidata",
            category="research",
            title=f"{label} ({entity_id})",
            content=(
                f"# {label}\n\nWikidata ID: {entity_id}\n"
                f"Description: {description}\n\n"
                "Structured knowledge entity from Wikidata."
            ),
            url=url_val,
            metadata={
                "wikidata_id": entity_id,
                "description": description,
            },
        )
        chunks.append(chunk)

    return chunks


def sparql_query(query: str) -> list[dict]:
    """Run a SPARQL query against Wikidata."""
    params = {"query": query, "format": "json"}
    url = f"{WIKIDATA_SPARQL}?{urlencode(params)}"
    req = Request(
        url,
        headers={
            "User-Agent": "AetherBrowser/1.0 (SCBE-AETHERMOORE research)",
            "Accept": "application/sparql-results+json",
        },
    )

    with urlopen(req, timeout=60) as response:
        data = json.loads(response.read())

    return data.get("results", {}).get("bindings", [])


def get_concept_graph(concept: str, limit: int = 20) -> list[KnowledgeChunk]:
    """Get related entities for a concept via SPARQL."""
    sparql = f"""
    SELECT ?item ?itemLabel ?itemDescription WHERE {{
      ?item rdfs:label "{concept}"@en .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT {limit}
    """
    try:
        results = sparql_query(sparql)
    except Exception:
        return []

    chunks = []
    for r in results:
        item_uri = r.get("item", {}).get("value", "")
        label = r.get("itemLabel", {}).get("value", "Unknown")
        desc = r.get("itemDescription", {}).get("value", "")
        entity_id = item_uri.split("/")[-1] if "/" in item_uri else ""

        chunk = KnowledgeChunk(
            id="",
            source="wikidata",
            category="research",
            title=f"{label} ({entity_id})",
            content=f"# {label}\n\nWikidata: {entity_id}\n{desc}\n\nSource: Wikidata SPARQL knowledge graph.",
            url=item_uri,
            metadata={"wikidata_id": entity_id, "sparql_concept": concept},
        )
        chunks.append(chunk)

    return chunks


WIKIDATA_RESEARCH_QUERIES = [
    "hyperbolic geometry",
    "Poincare disk model",
    "post-quantum cryptography",
    "AI alignment",
    "sacred geometry",
    "golden ratio",
    "blockchain consensus",
    "multi-agent system",
    "lattice-based cryptography",
    "retrieval-augmented generation",
]


def scrape_all_queries(max_per_query: int = 10) -> list[KnowledgeChunk]:
    """Run all SCBE-relevant Wikidata searches."""
    all_chunks = []
    for query in WIKIDATA_RESEARCH_QUERIES:
        print(f"  Searching Wikidata for '{query}'...")
        try:
            chunks = search_entities(query, limit=max_per_query)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(RATE_LIMIT)
    return all_chunks


if __name__ == "__main__":
    chunks = scrape_all_queries(max_per_query=5)
    print(f"\nFound {len(chunks)} entities from Wikidata")
    for c in chunks[:5]:
        print(f"  [{c.category}] {c.title[:80]}")
