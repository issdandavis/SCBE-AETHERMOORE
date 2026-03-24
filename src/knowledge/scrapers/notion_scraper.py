"""
Notion Scraper — pulls all SCBE pages from the Notion workspace.

Uses the Notion API to search and fetch pages, then converts
them into KnowledgeChunks for the funnel.
"""

import os
import json
import time
from urllib.request import urlopen, Request

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from src.knowledge.funnel import KnowledgeChunk

NOTION_API = "https://api.notion.com/v1"
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
RATE_LIMIT = 0.35  # seconds between requests

# Category mapping based on page title keywords
CATEGORY_MAP = {
    "sacred egg": "sacred-eggs",
    "geoseed": "geoseed",
    "geoseal": "geoseal",
    "hydra": "hydra",
    "phdm": "phdm",
    "tongue": "tongues",
    "tokenizer": "tongues",
    "axiom": "axioms",
    "theorem": "theorems",
    "governance": "governance",
    "patent": "patent",
    "marketing": "marketing",
    "demo": "demo",
    "deployment": "deployment",
    "architecture": "architecture",
    "browser": "browser",
    "swarm": "swarm",
    "hyperbolic": "math",
    "poincar": "math",
    "manifold": "math",
    "spiralverse": "lore",
    "story": "lore",
    "chapter": "lore",
}


def _api_request(endpoint: str, method: str = "GET", body: dict = None) -> dict:
    """Make a Notion API request."""
    url = f"{NOTION_API}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def categorize_page(title: str) -> str:
    """Map a page title to a knowledge category."""
    title_lower = title.lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in title_lower:
            return cat
    return "scbe-general"


def search_pages(query: str = "", max_results: int = 100) -> list[dict]:
    """Search Notion workspace for pages."""
    results = []
    has_more = True
    start_cursor = None

    while has_more and len(results) < max_results:
        body = {"page_size": min(100, max_results - len(results))}
        if query:
            body["query"] = query
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = _api_request("search", method="POST", body=body)
        results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        start_cursor = resp.get("next_cursor")
        time.sleep(RATE_LIMIT)

    return results


def fetch_page_blocks(page_id: str) -> str:
    """Fetch all blocks from a page and return as text."""
    blocks = []
    has_more = True
    start_cursor = None

    while has_more:
        endpoint = f"blocks/{page_id}/children"
        if start_cursor:
            endpoint += f"?start_cursor={start_cursor}"

        resp = _api_request(endpoint)
        for block in resp.get("results", []):
            text = _extract_block_text(block)
            if text:
                blocks.append(text)

        has_more = resp.get("has_more", False)
        start_cursor = resp.get("next_cursor")
        time.sleep(RATE_LIMIT)

    return "\n".join(blocks)


def _extract_block_text(block: dict) -> str:
    """Extract text content from a Notion block."""
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    if "rich_text" in block_data:
        return "".join(rt.get("plain_text", "") for rt in block_data["rich_text"])
    elif block_type == "code":
        code_text = "".join(rt.get("plain_text", "") for rt in block_data.get("rich_text", []))
        lang = block_data.get("language", "")
        return f"```{lang}\n{code_text}\n```"
    elif block_type == "equation":
        return f"$${block_data.get('expression', '')}$$"

    return ""


def _extract_title(page: dict) -> str:
    """Extract page title from Notion page object."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            return "".join(rt.get("plain_text", "") for rt in prop.get("title", []))
    return "Untitled"


def scrape_workspace(queries: list[str] = None, fetch_content: bool = True) -> list[KnowledgeChunk]:
    """Scrape the entire Notion workspace into KnowledgeChunks."""
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN not set")
        return []

    if queries is None:
        queries = ["SCBE", "Sacred", "GeoSeed", "HYDRA", "Spiralverse", "governance", "theorem"]

    all_pages = {}
    for q in queries:
        print(f"  Searching Notion for '{q}'...")
        pages = search_pages(q)
        for page in pages:
            page_id = page.get("id", "")
            if page_id and page_id not in all_pages:
                all_pages[page_id] = page

    print(f"  Found {len(all_pages)} unique pages")

    chunks = []
    for page_id, page in all_pages.items():
        title = _extract_title(page)
        url = page.get("url", "")
        created = page.get("created_time", "")
        category = categorize_page(title)

        content = title
        if fetch_content:
            try:
                content = fetch_page_blocks(page_id)
                if not content:
                    content = title
            except Exception as e:
                print(f"  Warning: Could not fetch blocks for '{title}': {e}")
                content = title

        chunk = KnowledgeChunk(
            id="",
            source="notion",
            category=category,
            title=title,
            content=f"# {title}\n\n{content}",
            url=url,
            timestamp=created,
            metadata={
                "notion_id": page_id,
                "page_type": page.get("object", "page"),
                "parent_type": page.get("parent", {}).get("type", ""),
            },
        )
        chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    chunks = scrape_workspace(fetch_content=False)
    print(f"\nScraped {len(chunks)} pages from Notion")
    for c in chunks[:10]:
        print(f"  [{c.category}] {c.title[:80]}")
