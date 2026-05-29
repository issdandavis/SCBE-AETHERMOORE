#!/usr/bin/env python3
"""
Research API Bus — single dispatcher for all configured free research APIs.

Usage:
    python scripts/research_api_bus.py --api arxiv --query "hyperbolic geometry" [--limit 5]

Available APIs:
    arxiv            arXiv preprint search (free, no key)
    semantic_scholar Semantic Scholar paper search (free, no key)
    openalex         OpenAlex scholarly works (free, no key, polite pool)
    crossref         CrossRef DOI/citation metadata (free, no key, polite pool)
    pubmed           PubMed biomedical literature (free, NCBI E-utilities)
    sam_gov          SAM.gov federal opportunities (SAM_GOV_API_KEY)
    uspto            USPTO patent applications (USPTO_ODP_API_KEY)
    hf_models        HuggingFace model hub (HF_TOKEN optional)
    github_repos     GitHub repository search (GITHUB_TOKEN recommended)

All outputs are JSON on stdout:
  {"ok": true, "api": "...", "count": N, "results": [...]}
  {"ok": false, "api": "...", "error": "...", "count": 0, "results": []}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Repo path setup so we can import internal clients
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CONTACT_EMAIL = "issdandavis7795@gmail.com"
_DEFAULT_LIMIT = 5
_TIMEOUT = 30


def _fetch_json(url: str, headers: Dict[str, str] | None = None, timeout: int = _TIMEOUT) -> Any:
    req = Request(url, headers={"User-Agent": f"SCBE-AetherMoore/1.0 ({_CONTACT_EMAIL})", **(headers or {})})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _result(api: str, results: List[dict]) -> dict:
    return {"ok": True, "api": api, "count": len(results), "results": results}


def _error(api: str, msg: str) -> dict:
    return {"ok": False, "api": api, "error": str(msg), "count": 0, "results": []}


# ---------------------------------------------------------------------------
# arXiv — free, no key required
# ---------------------------------------------------------------------------

def _search_arxiv(query: str, limit: int) -> dict:
    base = "https://export.arxiv.org/api/query"
    params = urlencode({"search_query": f"all:{query}", "max_results": limit, "sortBy": "relevance"})
    url = f"{base}?{params}"
    try:
        req = Request(url, headers={"User-Agent": f"SCBE-AetherMoore/1.0 ({_CONTACT_EMAIL})"})
        with urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode()
    except (HTTPError, URLError) as exc:
        return _error("arxiv", exc)

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return _error("arxiv", f"XML parse error: {exc}")

    results = []
    for entry in root.findall("atom:entry", ns):
        def text(tag: str) -> str:
            el = entry.find(f"atom:{{http://www.w3.org/2005/Atom}}{tag}", ns)
            return el.text.strip() if el is not None and el.text else ""

        arxiv_id_el = entry.find("{http://www.w3.org/2005/Atom}id")
        authors = [
            a.find("{http://www.w3.org/2005/Atom}name").text.strip()
            for a in entry.findall("{http://www.w3.org/2005/Atom}author")
            if a.find("{http://www.w3.org/2005/Atom}name") is not None
        ]
        results.append({
            "title": entry.findtext("{http://www.w3.org/2005/Atom}title", "").strip(),
            "authors": authors[:3],
            "summary": (entry.findtext("{http://www.w3.org/2005/Atom}summary", "") or "").strip()[:400],
            "published": entry.findtext("{http://www.w3.org/2005/Atom}published", "")[:10],
            "url": (arxiv_id_el.text or "").strip() if arxiv_id_el is not None else "",
        })
    return _result("arxiv", results)


# ---------------------------------------------------------------------------
# Semantic Scholar — free, no key required
# ---------------------------------------------------------------------------

def _search_semantic_scholar(query: str, limit: int) -> dict:
    fields = "title,authors,year,abstract,url,citationCount"
    params = urlencode({"query": query, "limit": limit, "fields": fields})
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    try:
        data = _fetch_json(url)
    except (HTTPError, URLError) as exc:
        return _error("semantic_scholar", exc)

    results = []
    for p in data.get("data", []):
        results.append({
            "title": p.get("title", ""),
            "authors": [a.get("name", "") for a in p.get("authors", [])[:3]],
            "year": p.get("year"),
            "abstract": (p.get("abstract") or "")[:400],
            "citations": p.get("citationCount", 0),
            "url": p.get("url", ""),
        })
    return _result("semantic_scholar", results)


# ---------------------------------------------------------------------------
# OpenAlex — free, no key (polite pool with email)
# ---------------------------------------------------------------------------

def _search_openalex(query: str, limit: int) -> dict:
    params = urlencode({"search": query, "per-page": limit, "mailto": _CONTACT_EMAIL})
    url = f"https://api.openalex.org/works?{params}"
    try:
        data = _fetch_json(url)
    except (HTTPError, URLError) as exc:
        return _error("openalex", exc)

    results = []
    for w in data.get("results", []):
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in w.get("authorships", [])[:3]
        ]
        results.append({
            "title": w.get("title", ""),
            "authors": authors,
            "year": w.get("publication_year"),
            "doi": w.get("doi", ""),
            "cited_by_count": w.get("cited_by_count", 0),
            "open_access": w.get("open_access", {}).get("is_oa", False),
            "url": w.get("id", ""),
        })
    return _result("openalex", results)


# ---------------------------------------------------------------------------
# CrossRef — free, no key (polite pool with email)
# ---------------------------------------------------------------------------

def _search_crossref(query: str, limit: int) -> dict:
    params = urlencode({"query": query, "rows": limit, "mailto": _CONTACT_EMAIL})
    url = f"https://api.crossref.org/works?{params}"
    try:
        data = _fetch_json(url)
    except (HTTPError, URLError) as exc:
        return _error("crossref", exc)

    results = []
    for item in data.get("message", {}).get("items", []):
        title = " ".join(item.get("title", []))
        authors = [
            f"{a.get('given','')} {a.get('family','')}".strip()
            for a in item.get("author", [])[:3]
        ]
        pub_date = item.get("published", {}).get("date-parts", [[None]])[0]
        results.append({
            "title": title,
            "authors": authors,
            "year": pub_date[0] if pub_date else None,
            "doi": item.get("DOI", ""),
            "publisher": item.get("publisher", ""),
            "type": item.get("type", ""),
            "url": item.get("URL", ""),
        })
    return _result("crossref", results)


# ---------------------------------------------------------------------------
# PubMed (NCBI E-utilities) — free, no key
# ---------------------------------------------------------------------------

def _search_pubmed(query: str, limit: int) -> dict:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    # Step 1: ESearch
    search_params = urlencode({"db": "pubmed", "term": query, "retmode": "json", "retmax": limit})
    try:
        search_data = _fetch_json(f"{base}/esearch.fcgi?{search_params}")
        ids = search_data.get("esearchresult", {}).get("idlist", [])
    except (HTTPError, URLError) as exc:
        return _error("pubmed", exc)

    if not ids:
        return _result("pubmed", [])

    # Step 2: ESummary
    time.sleep(0.35)  # NCBI rate limit courtesy
    summary_params = urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
    try:
        summary_data = _fetch_json(f"{base}/esummary.fcgi?{summary_params}")
    except (HTTPError, URLError) as exc:
        return _error("pubmed", f"esummary failed: {exc}")

    uids = summary_data.get("result", {}).get("uids", [])
    results = []
    for uid in uids:
        article = summary_data["result"].get(uid, {})
        authors = [a.get("name", "") for a in article.get("authors", [])[:3]]
        results.append({
            "title": article.get("title", ""),
            "authors": authors,
            "year": article.get("pubdate", "")[:4],
            "journal": article.get("source", ""),
            "pmid": uid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
        })
    return _result("pubmed", results)


# ---------------------------------------------------------------------------
# SAM.gov federal opportunities — SAM_GOV_API_KEY required
# ---------------------------------------------------------------------------

def _search_sam_gov(query: str, limit: int) -> dict:
    try:
        from api.darpa_prep.client import SamGovClient
        client = SamGovClient()
        raw = client.search_opportunities(query=query, limit=limit, active_only=True)
        normalized = [client.normalize_opportunity(item).model_dump() for item in raw]
    except ValueError as exc:
        return _error("sam_gov", f"Auth error: {exc}")
    except Exception as exc:
        return _error("sam_gov", str(exc))

    results = [
        {
            "title": r.get("title", ""),
            "agency": r.get("department_name", r.get("agency_name", "")),
            "type": r.get("opportunity_type", ""),
            "naics": r.get("naics", ""),
            "set_aside": r.get("set_aside_description", ""),
            "close_date": r.get("response_deadline", ""),
            "notice_id": r.get("notice_id", ""),
            "url": r.get("ui_link", ""),
        }
        for r in normalized
    ]
    return _result("sam_gov", results)


# ---------------------------------------------------------------------------
# USPTO Patent File Wrapper — USPTO_ODP_API_KEY required
# ---------------------------------------------------------------------------

def _search_uspto(query: str, limit: int) -> dict:
    api_key = os.getenv("USPTO_ODP_API_KEY", "").strip()
    if not api_key:
        return _error("uspto", "USPTO_ODP_API_KEY not set")

    params = urlencode({"q": query, "start": 0, "rows": limit})
    url = f"https://api.uspto.gov/api/v1/patent/applications/search?{params}"
    headers = {"X-API-KEY": api_key, "Accept": "application/json"}
    try:
        data = _fetch_json(url, headers=headers)
    except (HTTPError, URLError) as exc:
        return _error("uspto", exc)

    patents = data.get("results", data.get("patentBiblio", []))
    results = []
    for p in patents[:limit]:
        results.append({
            "title": p.get("inventionTitle", p.get("title", "")),
            "application_number": p.get("patentApplicationNumber", p.get("applicationNumber", "")),
            "filing_date": p.get("filingDate", ""),
            "status": p.get("applicationStatus", p.get("status", "")),
            "inventors": p.get("inventorNameArrayText", p.get("inventors", "")),
            "assignee": p.get("assigneeEntityName", p.get("assignee", "")),
        })
    return _result("uspto", results)


# ---------------------------------------------------------------------------
# HuggingFace model hub — HF_TOKEN optional
# ---------------------------------------------------------------------------

def _search_hf_models(query: str, limit: int) -> dict:
    params = urlencode({"search": query, "limit": limit, "sort": "downloads"})
    url = f"https://huggingface.co/api/models?{params}"
    token = os.getenv("HF_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        data = _fetch_json(url, headers=headers)
    except (HTTPError, URLError) as exc:
        return _error("hf_models", exc)

    results = []
    for m in data[:limit]:
        results.append({
            "model_id": m.get("id", ""),
            "author": m.get("author", ""),
            "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "pipeline_tag": m.get("pipeline_tag", ""),
            "tags": (m.get("tags") or [])[:5],
            "url": f"https://huggingface.co/{m.get('id', '')}",
        })
    return _result("hf_models", results)


# ---------------------------------------------------------------------------
# GitHub repository search — GITHUB_TOKEN recommended
# ---------------------------------------------------------------------------

def _search_github_repos(query: str, limit: int) -> dict:
    params = urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": min(limit, 30)})
    url = f"https://api.github.com/search/repositories?{params}"
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers: Dict[str, str] = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        data = _fetch_json(url, headers=headers)
    except HTTPError as exc:
        if exc.code == 403:
            return _error("github_repos", "Rate limited — set GITHUB_TOKEN for higher quota")
        return _error("github_repos", exc)
    except URLError as exc:
        return _error("github_repos", exc)

    results = []
    for r in data.get("items", [])[:limit]:
        results.append({
            "name": r.get("full_name", ""),
            "description": (r.get("description") or "")[:200],
            "stars": r.get("stargazers_count", 0),
            "language": r.get("language", ""),
            "topics": (r.get("topics") or [])[:5],
            "updated": r.get("updated_at", "")[:10],
            "url": r.get("html_url", ""),
        })
    return _result("github_repos", results)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_APIS = {
    "arxiv": _search_arxiv,
    "semantic_scholar": _search_semantic_scholar,
    "openalex": _search_openalex,
    "crossref": _search_crossref,
    "pubmed": _search_pubmed,
    "sam_gov": _search_sam_gov,
    "uspto": _search_uspto,
    "hf_models": _search_hf_models,
    "github_repos": _search_github_repos,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SCBE Research API Bus — dispatch search queries to free research APIs"
    )
    parser.add_argument("--api", required=True, choices=list(_APIS), help="API to query")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=_DEFAULT_LIMIT, help="Max results (default 5)")
    parser.add_argument("--json", action="store_true", default=True, help="Output JSON (always on)")
    parser.add_argument("--list-apis", action="store_true", help="Print available API names and exit")
    args = parser.parse_args()

    if args.list_apis:
        print(json.dumps({"apis": list(_APIS)}))
        return 0

    fn = _APIS[args.api]
    result = fn(args.query, args.limit)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
