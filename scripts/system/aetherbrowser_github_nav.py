"""
AetherBrowser GitHub Navigation — Playwright-based GitHub search with Obsidian export.

Maps to: $aetherbrowser-github-nav
Integrates with: HYDRA canvas BROWSER_NAV steps, cross-talk, Obsidian vault

Usage:
    python aetherbrowser_github_nav.py "SCBE AI safety"
    python aetherbrowser_github_nav.py "AI governance" --type repositories --max 10
    python aetherbrowser_github_nav.py "topic" --vault "C:\\path\\to\\vault"
    python aetherbrowser_github_nav.py "topic" --json
"""

import json
import os
import sys
from argparse import ArgumentParser
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


def nav_github_playwright(
    query: str,
    max_results: int = 5,
    search_type: str = "repositories",
    save_to_vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Navigate GitHub via Playwright, search, extract results."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Falling back to GitHub API.", file=sys.stderr)
        return nav_github_api_fallback(query, max_results, search_type, save_to_vault)

    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            url = f"https://github.com/search?q={quote_plus(query)}&type={search_type}"
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)

            if search_type == "repositories":
                # Modern GitHub search results
                items = page.query_selector_all("[data-testid='results-list'] > div")
                if not items:
                    # Fallback selector
                    items = page.query_selector_all(".search-title a")

                for item in items[:max_results]:
                    link_el = item.query_selector("a[href*='/']")
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href") or ""
                    title = link_el.inner_text().strip()
                    if not href.startswith("http"):
                        href = "https://github.com" + href

                    desc_el = item.query_selector("p, span.topic-tag")
                    desc = desc_el.inner_text().strip() if desc_el else ""

                    results.append({
                        "title": title,
                        "description": desc[:300],
                        "link": href,
                        "type": search_type,
                    })
            else:
                # Generic extraction for other types
                links = page.query_selector_all("a.Link--primary")
                for link_el in links[:max_results]:
                    href = link_el.get_attribute("href") or ""
                    title = link_el.inner_text().strip()
                    if not href.startswith("http"):
                        href = "https://github.com" + href
                    results.append({
                        "title": title,
                        "description": "",
                        "link": href,
                        "type": search_type,
                    })

        except Exception as exc:
            print(f"Browser error: {exc}", file=sys.stderr)
        finally:
            browser.close()

    if save_to_vault and results:
        _save_to_vault(results, query, save_to_vault, search_type)

    return results


def nav_github_api_fallback(
    query: str,
    max_results: int = 5,
    search_type: str = "repositories",
    save_to_vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fallback: use GitHub REST API (no Playwright needed)."""
    import urllib.request

    url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&per_page={max_results}"
    results: List[Dict[str, Any]] = []

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "HYDRA-AetherBrowser/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data.get("items", [])[:max_results]:
            results.append({
                "title": item.get("full_name", ""),
                "description": (item.get("description") or "")[:300],
                "link": item.get("html_url", ""),
                "stars": item.get("stargazers_count", 0),
                "type": search_type,
            })
    except Exception as exc:
        print(f"API error: {exc}", file=sys.stderr)

    if save_to_vault and results:
        _save_to_vault(results, query, save_to_vault, search_type)

    return results


def _save_to_vault(results: List[Dict[str, Any]], query: str, vault_path: str, search_type: str):
    """Save results to Obsidian vault as Markdown note."""
    safe_query = query.replace(" ", "_")[:40]
    note_path = os.path.join(vault_path, f"github_{safe_query}_{search_type}.md")
    os.makedirs(os.path.dirname(note_path), exist_ok=True)

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(f"# GitHub Search: {query} ({search_type})\n\n")
        for r in results:
            stars = f" ({r['stars']} stars)" if r.get("stars") else ""
            f.write(f"## {r['title']}{stars}\n\n")
            if r.get("description"):
                f.write(f"{r['description']}\n\n")
            f.write(f"[Link]({r['link']})\n\n---\n\n")

    print(f"Saved to {note_path}", file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description="AetherBrowser GitHub navigation.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--max", type=int, default=5, help="Max results.")
    parser.add_argument("--type", default="repositories", help="Search type: repositories, users, issues, code.")
    parser.add_argument("--vault", default=None, help="Obsidian vault path to save note.")
    parser.add_argument("--json", action="store_true", help="JSON output for HYDRA piping.")
    parser.add_argument("--no-browser", action="store_true", help="Skip Playwright, use API only.")
    args = parser.parse_args()

    if args.no_browser:
        results = nav_github_api_fallback(args.query, args.max, args.type, args.vault)
    else:
        results = nav_github_playwright(args.query, args.max, args.type, args.vault)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n[GitHub] {len(results)} {args.type} for: {args.query}")
        for i, r in enumerate(results, 1):
            stars = f" ({r.get('stars', '?')} stars)" if r.get("stars") else ""
            print(f"  {i}. {r['title']}{stars}")
            if r.get("description"):
                print(f"     {r['description'][:80]}")
            print(f"     {r['link']}")
        print()
