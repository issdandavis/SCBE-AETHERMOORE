#!/usr/bin/env python3
"""Unified AetherBrowser search entrypoint.

Routes site-specific search tasks through SCBE-owned browser/nav scripts
instead of dropping the operator into an external browser workflow first.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "system"
DEFAULT_SURFACE_TO_DOMAIN = {
    "github": "github.com",
    "arxiv": "arxiv.org",
    "notion": "www.notion.so",
    "huggingface": "huggingface.co",
    "web": "html.duckduckgo.com",
}


def _load_module(module_name: str, script_name: str):
    script_path = SCRIPTS_DIR / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _default_vault_path() -> Optional[str]:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        config_path = Path(appdata) / "Obsidian" / "obsidian.json"
    else:
        config_path = Path.home() / "AppData" / "Roaming" / "Obsidian" / "obsidian.json"
    if not config_path.exists():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    vaults = payload.get("vaults", {})
    if not isinstance(vaults, dict):
        return None
    for meta in vaults.values():
        if not isinstance(meta, dict):
            continue
        raw_path = str(meta.get("path", "")).strip()
        if raw_path and Path(raw_path).exists():
            return raw_path
    return None


def _resolve_vault_path(vault: Optional[str], save_to_live_vault: bool) -> Optional[str]:
    if vault:
        cleaned = vault.strip()
        if cleaned:
            return cleaned
    if save_to_live_vault:
        return _default_vault_path()
    return None


def _search_huggingface_api(query: str, max_results: int = 5, save_to_vault: Optional[str] = None) -> List[Dict[str, Any]]:
    import urllib.parse
    import urllib.request

    url = f"https://huggingface.co/api/models?search={urllib.parse.quote_plus(query)}&limit={max_results}"
    results: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SCBE-AetherBrowser/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for item in data[:max_results]:
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            results.append(
                {
                    "title": model_id,
                    "description": (item.get("pipeline_tag") or "")[:120],
                    "link": f"https://huggingface.co/{model_id}",
                    "downloads": item.get("downloads", 0),
                    "likes": item.get("likes", 0),
                    "type": "models",
                }
            )
    except Exception:
        return []

    if save_to_vault and results:
        safe_query = query.replace(" ", "_")[:40]
        note_path = Path(save_to_vault) / f"huggingface_{safe_query}.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        with note_path.open("w", encoding="utf-8") as handle:
            handle.write(f"# Hugging Face Search: {query}\n\n")
            for item in results:
                handle.write(f"## {item['title']}\n\n")
                if item.get("description"):
                    handle.write(f"{item['description']}\n\n")
                handle.write(f"[Link]({item['link']})\n\n")
                handle.write("---\n\n")

    return results


def _search_web_via_playwriter(query: str, max_results: int = 5, save_to_vault: Optional[str] = None) -> List[Dict[str, Any]]:
    runner_path = SCRIPTS_DIR / "playwriter_lane_runner.py"
    session_id = f"ab-search-{abs(hash(query)) % 100000}"
    command = [
        sys.executable,
        str(runner_path),
        "--session",
        session_id,
        "--task",
        "search-evidence",
        "--query",
        query,
        "--max-results",
        str(max(1, int(max_results))),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return []

    payload = json.loads(completed.stdout)
    results = list(payload.get("results", []))
    if save_to_vault and results:
        safe_query = query.replace(" ", "_")[:40]
        note_path = Path(save_to_vault) / f"web_{safe_query}.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        with note_path.open("w", encoding="utf-8") as handle:
            handle.write(f"# Web Search: {query}\n\n")
            for item in results:
                handle.write(f"## {item['title']}\n\n")
                if item.get("snippet"):
                    handle.write(f"{item['snippet']}\n\n")
                handle.write(f"[Link]({item['url']})\n\n")
                handle.write("---\n\n")
    return results


def _dispatch_search(
    surface: str,
    query: str,
    max_results: int,
    use_browser: bool,
    vault_path: Optional[str],
) -> List[Dict[str, Any]]:
    surface_norm = surface.strip().lower()
    if surface_norm == "github":
        module = _load_module("aetherbrowser_github_nav", "aetherbrowser_github_nav.py")
        fn: Callable[..., List[Dict[str, Any]]] = (
            module.nav_github_playwright if use_browser else module.nav_github_api_fallback
        )
        return fn(query, max_results, "repositories", vault_path)
    if surface_norm == "arxiv":
        module = _load_module("aetherbrowser_arxiv_nav", "aetherbrowser_arxiv_nav.py")
        fn = module.nav_arxiv_playwright if use_browser else module.nav_arxiv_api_fallback
        return fn(query, max_results, vault_path)
    if surface_norm == "notion":
        module = _load_module("aetherbrowser_notion_nav", "aetherbrowser_notion_nav.py")
        fn = module.nav_notion_playwright if use_browser else module.search_notion_api
        results = fn(query, max_results, vault_path) if use_browser else fn(query, max_results)
        if not use_browser and vault_path and results:
            module._save_to_vault(results, query, vault_path)
        return results
    if surface_norm == "huggingface":
        nav_path = SCRIPTS_DIR / "aetherbrowser_huggingface_nav.py"
        if nav_path.exists():
            module = _load_module("aetherbrowser_huggingface_nav", "aetherbrowser_huggingface_nav.py")
            fn = module.nav_huggingface_playwright if use_browser else module.nav_huggingface_api_fallback
            return fn(query, max_results=max_results, search_type="models", save_to_vault=vault_path)
        return _search_huggingface_api(query, max_results, vault_path)
    if surface_norm == "web":
        return _search_web_via_playwriter(query, max_results, vault_path)
    raise ValueError(f"Unsupported surface '{surface_norm}'")


def _route_assignment(surface: str) -> Dict[str, Any]:
    dispatcher = _load_module("browser_chain_dispatcher", "browser_chain_dispatcher.py")
    fleet = dispatcher.BrowserChainDispatcher()
    for tentacle in dispatcher.build_default_fleet():
        fleet.register_tentacle(tentacle)
    domain = DEFAULT_SURFACE_TO_DOMAIN[surface]
    return fleet.assign_task(domain, "research", {"engine": "playwriter", "surface": surface})


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SCBE-owned browser-first search tasks.")
    parser.add_argument("surface", choices=sorted(DEFAULT_SURFACE_TO_DOMAIN.keys()))
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max", type=int, default=5, help="Max results")
    parser.add_argument("--browser", action="store_true", help="Prefer Playwright browser mode when available")
    parser.add_argument("--vault", default="", help="Explicit Obsidian vault path for result notes")
    parser.add_argument("--save-to-live-vault", action="store_true", help="Resolve the currently open Obsidian vault and save a note there")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    vault_path = _resolve_vault_path(args.vault, args.save_to_live_vault)
    assignment = _route_assignment(args.surface)
    results = _dispatch_search(args.surface, args.query, max(1, args.max), args.browser, vault_path)
    payload = {
        "ok": True,
        "surface": args.surface,
        "query": args.query,
        "max_results": max(1, args.max),
        "assignment": assignment,
        "saved_to_vault": vault_path,
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"[AetherBrowser] {args.surface} :: {args.query}")
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
