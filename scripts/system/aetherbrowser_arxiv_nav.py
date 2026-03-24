"""
AetherBrowser arXiv Navigation — Playwright-based arXiv browser with Obsidian export.

Maps to: $aetherbrowser-arxiv-nav
Fallback for: hydra arxiv (when API limits hit or dynamic content needed)
Integrates with: HYDRA canvas BROWSER_NAV steps, cross-talk, Obsidian vault

Usage:
    python aetherbrowser_arxiv_nav.py "AI swarm governance"
    python aetherbrowser_arxiv_nav.py "chladni modes" --max 10
    python aetherbrowser_arxiv_nav.py "quantum error correction" --vault "C:\\path\\to\\vault"
    python aetherbrowser_arxiv_nav.py "topic" --json
"""

import json
import os
import sys
from argparse import ArgumentParser
from typing import Any, Dict, List, Optional


def nav_arxiv_playwright(query: str, max_results: int = 5, save_to_vault: Optional[str] = None) -> List[Dict[str, Any]]:
    """Navigate arXiv via Playwright, search query, extract results."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Falling back to HYDRA arxiv API.", file=sys.stderr)
        return nav_arxiv_api_fallback(query, max_results, save_to_vault)

    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            search_url = f"https://arxiv.org/search/?query={query.replace(' ', '+')}&searchtype=all"
            page.goto(search_url, timeout=15000)
            page.wait_for_selector("li.arxiv-result", timeout=10000)

            items = page.query_selector_all("li.arxiv-result")
            for item in items[:max_results]:
                title_el = item.query_selector("p.title")
                title = title_el.inner_text().strip() if title_el else "N/A"

                abs_el = item.query_selector("span.abstract-full")
                if not abs_el:
                    abs_el = item.query_selector("span.abstract-short")
                abstract = abs_el.inner_text().strip() if abs_el else ""
                abstract = abstract.replace("\n", " ").strip()
                if abstract.endswith("Less"):
                    abstract = abstract[:-4].strip()

                link_el = item.query_selector("p.list-title a")
                link = link_el.get_attribute("href") if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://arxiv.org" + link

                arxiv_id = ""
                if link:
                    arxiv_id = link.split("/abs/")[-1] if "/abs/" in link else ""

                results.append(
                    {
                        "arxiv_id": arxiv_id,
                        "title": title,
                        "abstract": abstract[:500],
                        "link": link,
                    }
                )
        except Exception as exc:
            print(f"Browser error: {exc}", file=sys.stderr)
        finally:
            browser.close()

    if save_to_vault and results:
        _save_to_vault(results, query, save_to_vault, "arxiv")

    return results


def nav_arxiv_api_fallback(
    query: str, max_results: int = 5, save_to_vault: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fallback: use arXiv API (no Playwright needed)."""
    import urllib.request
    import xml.etree.ElementTree as ET

    url = f"http://export.arxiv.org/api/query?search_query=all:{query.replace(' ', '+')}&max_results={max_results}"
    results: List[Dict[str, Any]] = []

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
            abstract = (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")
            link = ""
            for lnk in entry.findall("atom:link", ns):
                if lnk.get("title") == "pdf":
                    link = lnk.get("href", "")
                    break
            if not link:
                link_el = entry.find("atom:id", ns)
                link = link_el.text if link_el is not None else ""

            arxiv_id = link.split("/abs/")[-1] if "/abs/" in link else ""

            results.append(
                {
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "abstract": abstract[:500],
                    "link": link,
                }
            )
    except Exception as exc:
        print(f"API error: {exc}", file=sys.stderr)

    if save_to_vault and results:
        _save_to_vault(results, query, save_to_vault, "arxiv")

    return results


def _save_to_vault(results: List[Dict[str, Any]], query: str, vault_path: str, source: str):
    """Save results to Obsidian vault as Markdown note."""
    safe_query = query.replace(" ", "_")[:40]
    note_path = os.path.join(vault_path, f"{source}_{safe_query}.md")
    os.makedirs(os.path.dirname(note_path), exist_ok=True)

    with open(note_path, "w", encoding="utf-8") as f:
        f.write(f"# {source.title()} Search: {query}\n\n")
        for r in results:
            f.write(f"## {r['title']}\n\n")
            if r.get("abstract"):
                f.write(f"{r['abstract']}\n\n")
            if r.get("link"):
                f.write(f"[Link]({r['link']})\n\n")
            f.write("---\n\n")

    print(f"Saved to {note_path}", file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description="AetherBrowser arXiv navigation.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--max", type=int, default=5, help="Max results.")
    parser.add_argument("--vault", default=None, help="Obsidian vault path to save note.")
    parser.add_argument("--json", action="store_true", help="JSON output for HYDRA piping.")
    parser.add_argument("--no-browser", action="store_true", help="Skip Playwright, use API only.")
    args = parser.parse_args()

    if args.no_browser:
        results = nav_arxiv_api_fallback(args.query, args.max, args.vault)
    else:
        results = nav_arxiv_playwright(args.query, args.max, args.vault)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n[arXiv] {len(results)} results for: {args.query}")
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['arxiv_id']}] {r['title'][:80]}")
            if r.get("link"):
                print(f"     {r['link']}")
        print()
