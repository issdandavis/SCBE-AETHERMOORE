"""
AetherBrowser Notion Navigation — Notion API + optional Playwright browser.

Maps to: $aetherbrowser-notion-nav
Integrates with: HYDRA canvas BROWSER_NAV steps, knowledge pipeline, Obsidian vault

Usage:
    python aetherbrowser_notion_nav.py search "SCBE governance"
    python aetherbrowser_notion_nav.py search "sacred eggs" --max 10
    python aetherbrowser_notion_nav.py search "topic" --vault "C:\\path\\to\\vault" --json
"""

import json
import os
import sys
from argparse import ArgumentParser
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


def _get_notion_token() -> str:
    """Resolve Notion token from environment or .env files."""
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if token:
        return token

    # Check .env.connector.oauth
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "connector_oauth", ".env.connector.oauth")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("NOTION_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    return ""


def search_notion_api(query: str, max_results: int = 10, page_size: int = 20) -> List[Dict[str, Any]]:
    """Search Notion workspace via API."""
    import urllib.request

    token = _get_notion_token()
    if not token:
        print(
            "Warning: No NOTION_TOKEN found. Set it in env or config/connector_oauth/.env.connector.oauth",
            file=sys.stderr,
        )
        return []

    url = "https://api.notion.com/v1/search"
    payload = json.dumps(
        {
            "query": query,
            "page_size": min(page_size, 100),
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    results: List[Dict[str, Any]] = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data.get("results", [])[:max_results]:
            obj_type = item.get("object", "unknown")
            title = ""

            # Extract title based on object type
            if obj_type == "page":
                props = item.get("properties", {})
                for _prop_name, prop_val in props.items():
                    if prop_val.get("type") == "title":
                        title_arr = prop_val.get("title", [])
                        title = "".join(t.get("plain_text", "") for t in title_arr)
                        break
                if not title:
                    title = item.get("url", "Untitled page")
            elif obj_type == "database":
                title_arr = item.get("title", [])
                title = "".join(t.get("plain_text", "") for t in title_arr)

            results.append(
                {
                    "id": item.get("id", ""),
                    "type": obj_type,
                    "title": title or "Untitled",
                    "url": item.get("url", ""),
                    "last_edited": item.get("last_edited_time", ""),
                }
            )
    except Exception as exc:
        print(f"Notion API error: {exc}", file=sys.stderr)

    return results


def nav_notion_playwright(
    query: str, max_results: int = 5, save_to_vault: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Navigate Notion via Playwright (requires login)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Using API only.", file=sys.stderr)
        return search_notion_api(query, max_results)

    # For Notion, the API is generally better than browser scraping
    # since Notion requires auth. Use API as primary, browser as visual fallback.
    results = search_notion_api(query, max_results)

    if save_to_vault and results:
        _save_to_vault(results, query, save_to_vault)

    return results


def _save_to_vault(results: List[Dict[str, Any]], query: str, vault_path: str):
    """Save results to Obsidian vault as Markdown note."""
    safe_query = query.replace(" ", "_")[:40]
    note_path = os.path.join(vault_path, f"notion_{safe_query}.md")
    os.makedirs(os.path.dirname(note_path), exist_ok=True)

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(f"# Notion Search: {query}\n\n")
        for r in results:
            f.write(f"## {r['title']} ({r['type']})\n\n")
            if r.get("url"):
                f.write(f"[Open in Notion]({r['url']})\n\n")
            if r.get("last_edited"):
                f.write(f"*Last edited: {r['last_edited']}*\n\n")
            f.write("---\n\n")

    print(f"Saved to {note_path}", file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description="AetherBrowser Notion navigation.")
    parser.add_argument("command", nargs="?", default="search", help="Command: search")
    parser.add_argument("query", nargs="?", default="", help="Search query.")
    parser.add_argument("--max", type=int, default=10, help="Max results.")
    parser.add_argument("--vault", default=None, help="Obsidian vault path to save note.")
    parser.add_argument("--json", action="store_true", help="JSON output.")
    parser.add_argument("--browser", action="store_true", help="Use Playwright browser (default: API only).")
    args = parser.parse_args()

    if not args.query:
        print("Usage: python aetherbrowser_notion_nav.py search 'query'")
        sys.exit(1)

    if args.browser:
        results = nav_notion_playwright(args.query, args.max, args.vault)
    else:
        results = search_notion_api(args.query, args.max)
        if args.vault and results:
            _save_to_vault(results, args.query, args.vault)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n[Notion] {len(results)} results for: {args.query}")
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['type']}] {r['title']}")
            if r.get("url"):
                print(f"     {r['url']}")
        print()
