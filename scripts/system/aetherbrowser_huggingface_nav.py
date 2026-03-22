"""
AetherBrowser Hugging Face Navigation - browser-first repo discovery with API fallback.

Maps to: $aetherbrowser-huggingface-nav
Integrates with: HYDRA browser lane discovery, Obsidian vault export, JSON piping

Usage:
    python aetherbrowser_huggingface_nav.py "vision transformer"
    python aetherbrowser_huggingface_nav.py "reasoning" --type datasets --max 10
    python aetherbrowser_huggingface_nav.py "leaderboard" --type all --vault "C:\\path\\to\\vault"
    python aetherbrowser_huggingface_nav.py "diffusion" --json --no-browser
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from argparse import ArgumentParser
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus


HF_ROOT = "https://huggingface.co"
SURFACE_CONFIGS: Dict[str, Dict[str, str]] = {
    "models": {
        "label": "models",
        "web_path": "/models",
        "api_path": "/api/models",
        "repo_prefix": "",
    },
    "datasets": {
        "label": "datasets",
        "web_path": "/datasets",
        "api_path": "/api/datasets",
        "repo_prefix": "datasets/",
    },
    "spaces": {
        "label": "spaces",
        "web_path": "/spaces",
        "api_path": "/api/spaces",
        "repo_prefix": "spaces/",
    },
}
MODEL_RESERVED_ROOTS = {
    "models",
    "datasets",
    "spaces",
    "tasks",
    "docs",
    "blog",
    "join",
    "login",
    "pricing",
    "settings",
    "organizations",
}


def _surface_plan(search_type: str) -> List[Dict[str, str]]:
    normalized = (search_type or "models").strip().lower()
    if normalized == "all":
        return [
            SURFACE_CONFIGS["models"],
            SURFACE_CONFIGS["datasets"],
            SURFACE_CONFIGS["spaces"],
        ]
    if normalized not in SURFACE_CONFIGS:
        raise ValueError(f"Unsupported Hugging Face search type: {search_type}")
    return [SURFACE_CONFIGS[normalized]]


def _load_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


def _build_search_url(surface: Dict[str, str], query: str) -> str:
    return f"{HF_ROOT}{surface['web_path']}?search={quote_plus(query)}"


def _build_api_url(surface: Dict[str, str], query: str, max_results: int) -> str:
    limit = max(1, int(max_results))
    return f"{HF_ROOT}{surface['api_path']}?search={quote_plus(query)}&limit={limit}"


def _normalize_repo_id(raw_value: Any) -> str:
    return str(raw_value or "").strip().strip("/")


def _build_repo_link(surface: Dict[str, str], repo_id: str) -> str:
    if not repo_id:
        return ""
    prefix = surface["repo_prefix"]
    return f"{HF_ROOT}/{prefix}{repo_id}".rstrip("/")


def _normalize_api_result(item: Dict[str, Any], surface: Dict[str, str]) -> Optional[Dict[str, Any]]:
    repo_id = _normalize_repo_id(item.get("id") or item.get("modelId") or item.get("name"))
    if not repo_id:
        return None

    description = ""
    for candidate in (
        item.get("description"),
        item.get("pipeline_tag"),
        item.get("task"),
        item.get("sdk"),
    ):
        if candidate:
            description = str(candidate).strip()
            break

    result: Dict[str, Any] = {
        "title": repo_id,
        "description": description[:320],
        "link": _build_repo_link(surface, repo_id),
        "type": surface["label"],
        "source": "api",
    }

    for key in ("author", "likes", "downloads", "pipeline_tag", "sdk"):
        if key in item and item.get(key) not in (None, ""):
            result[key] = item[key]

    return result


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "HYDRA-AetherBrowser-HF/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_browser_results(page: Any, surface_type: str, max_results: int) -> List[Dict[str, Any]]:
    evaluator = """
    ([surfaceType, limit, reservedRoots]) => {
      const anchors = Array.from(document.querySelectorAll("main a[href], article a[href], section a[href], a[href]"));
      const seen = new Set();
      const rows = [];

      const isMatch = (href) => {
        if (!href.startsWith("/")) return false;
        const path = href.split("?")[0].split("#")[0];
        const parts = path.split("/").filter(Boolean);
        if (surfaceType === "models") {
          return parts.length === 2 && !reservedRoots.includes(parts[0]);
        }
        return parts.length === 3 && parts[0] === surfaceType;
      };

      for (const anchor of anchors) {
        const href = anchor.getAttribute("href") || "";
        if (!isMatch(href)) continue;
        const link = new URL(href, location.origin).toString();
        if (seen.has(link)) continue;

        const title = (anchor.textContent || "").replace(/\\s+/g, " ").trim() || link;
        const card = anchor.closest("article, li, div");
        let description = "";
        if (card) {
          description = (card.textContent || "").replace(/\\s+/g, " ").trim();
          if (description.startsWith(title)) {
            description = description.slice(title.length).trim();
          }
        }

        rows.push({
          title,
          description: description.slice(0, 320),
          link,
          type: surfaceType,
          source: "playwright",
        });
        seen.add(link);
        if (rows.length >= limit) break;
      }
      return rows;
    }
    """
    return list(
        page.evaluate(evaluator, [surface_type, max(1, int(max_results)), sorted(MODEL_RESERVED_ROOTS)])
    )


def _dedupe_results(results: List[Dict[str, Any]], max_results: int) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for row in results:
        link = str(row.get("link", "")).strip()
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(row)
        if len(deduped) >= max_results:
            break
    return deduped


def _safe_query_fragment(query: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in query.strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")[:48] or "search"


def _save_to_vault(
    results: List[Dict[str, Any]],
    query: str,
    vault_path: str,
    search_type: str,
) -> str:
    safe_query = _safe_query_fragment(query)
    note_path = os.path.join(vault_path, f"huggingface_{safe_query}_{search_type}.md")
    os.makedirs(os.path.dirname(note_path), exist_ok=True)

    with open(note_path, "w", encoding="utf-8") as handle:
        handle.write(f"# Hugging Face Search: {query} ({search_type})\n\n")
        for row in results:
            handle.write(f"## [{row['type']}] {row['title']}\n\n")
            if row.get("description"):
                handle.write(f"{row['description']}\n\n")
            if row.get("likes") is not None:
                handle.write(f"- Likes: {row['likes']}\n")
            if row.get("downloads") is not None:
                handle.write(f"- Downloads: {row['downloads']}\n")
            if row.get("source"):
                handle.write(f"- Source: {row['source']}\n")
            handle.write(f"- Link: {row['link']}\n\n---\n\n")

    print(f"Saved to {note_path}", file=sys.stderr)
    return note_path


def nav_huggingface_api_fallback(
    query: str,
    max_results: int = 5,
    search_type: str = "models",
    save_to_vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    try:
        for surface in _surface_plan(search_type):
            payload = _fetch_json(_build_api_url(surface, query, max_results))
            if not isinstance(payload, list):
                continue
            for item in payload:
                normalized = _normalize_api_result(item, surface)
                if normalized is not None:
                    results.append(normalized)
    except Exception as exc:
        print(f"Hugging Face API error: {exc}", file=sys.stderr)

    results = _dedupe_results(results, max(1, int(max_results)))
    if save_to_vault and results:
        _save_to_vault(results, query, save_to_vault, search_type)
    return results


def nav_huggingface_playwright(
    query: str,
    max_results: int = 5,
    search_type: str = "models",
    save_to_vault: Optional[str] = None,
) -> List[Dict[str, Any]]:
    sync_playwright = _load_sync_playwright()
    if sync_playwright is None:
        print("Playwright not installed. Falling back to Hugging Face API.", file=sys.stderr)
        return nav_huggingface_api_fallback(query, max_results, search_type, save_to_vault)

    results: List[Dict[str, Any]] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                for surface in _surface_plan(search_type):
                    if len(results) >= max_results:
                        break
                    page.goto(_build_search_url(surface, query), timeout=20000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    remaining = max(1, int(max_results) - len(results))
                    results.extend(_extract_browser_results(page, surface["label"], remaining))
            finally:
                browser.close()
    except Exception as exc:
        print(f"Browser error: {exc}", file=sys.stderr)
        return nav_huggingface_api_fallback(query, max_results, search_type, save_to_vault)

    results = _dedupe_results(results, max(1, int(max_results)))
    if not results:
        return nav_huggingface_api_fallback(query, max_results, search_type, save_to_vault)

    if save_to_vault:
        _save_to_vault(results, query, save_to_vault, search_type)
    return results


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="AetherBrowser Hugging Face navigation.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--max", type=int, default=5, help="Max results.")
    parser.add_argument(
        "--type",
        default="models",
        choices=["models", "datasets", "spaces", "all"],
        help="Search surface.",
    )
    parser.add_argument("--vault", default=None, help="Obsidian vault path to save note.")
    parser.add_argument("--json", action="store_true", help="JSON output.")
    parser.add_argument("--no-browser", action="store_true", help="Skip Playwright, use API only.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.no_browser:
        results = nav_huggingface_api_fallback(args.query, args.max, args.type, args.vault)
    else:
        results = nav_huggingface_playwright(args.query, args.max, args.type, args.vault)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print(f"\n[Hugging Face] {len(results)} {args.type} results for: {args.query}")
    for index, row in enumerate(results, 1):
        print(f"  {index}. [{row['type']}] {row['title']}")
        if row.get("description"):
            print(f"     {row['description'][:100]}")
        print(f"     {row['link']}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
