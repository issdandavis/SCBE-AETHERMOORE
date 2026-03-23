#!/usr/bin/env python3
"""Playwriter-compatible lane runner with deterministic HTTP fallback.

Supports:
- navigate: set/refresh session URL
- title: fetch title for current URL
- snapshot: fetch compact page evidence for current URL
- search-evidence: run a deterministic HTML search, select a result, and
  capture evidence for the selected page
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, Tuple

from scripts.system.html_text import html_to_text


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "page_evidence"
_SESSION_RE = re.compile(r"[^A-Za-z0-9._-]+")
DEFAULT_SEARCH_URL = "https://html.duckduckgo.com/html/"
_SEARCH_RESULT_ANCHOR_RE = re.compile(
    r'<a\b[^>]*class=["\'][^"\']*\bresult__a\b[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    flags=re.IGNORECASE | re.DOTALL,
)
_SEARCH_RESULT_SNIPPET_RE = re.compile(
    r'<(?:div|span|a)\b[^>]*class=["\'][^"\']*\bresult__snippet\b[^"\']*["\'][^>]*>(.*?)</(?:div|span|a)>',
    flags=re.IGNORECASE | re.DOTALL,
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(session_id: str) -> Path:
    safe_session = _SESSION_RE.sub("_", str(session_id)).strip("._-") or "session"
    return EVIDENCE_DIR / f"playwriter-session-{safe_session}.json"


def _load_state(session_id: str) -> Dict[str, Any]:
    path = _state_path(session_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(session_id: str, payload: Dict[str, Any]) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(session_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fetch_html(url: str, timeout: int) -> Tuple[str, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "scbe-playwriter-lane-runner/1.0"},
    )
    with urllib.request.urlopen(req, timeout=max(5, timeout)) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")
        return html, str(response.status)


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _extract_text_excerpt(html: str, max_chars: int = 1200) -> str:
    return html_to_text(html, max_chars=max_chars)


def _build_search_url(query: str) -> str:
    encoded = urllib.parse.urlencode({"q": query})
    return f"{DEFAULT_SEARCH_URL}?{encoded}"


def _clean_html_fragment(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _normalize_search_result_url(url: str) -> str:
    candidate = unescape(url).strip()
    if not candidate:
        return ""
    if candidate.startswith("//"):
        candidate = f"https:{candidate}"
    parsed = urllib.parse.urlparse(candidate)
    query = urllib.parse.parse_qs(parsed.query)
    encoded_target = query.get("uddg", [])
    if encoded_target:
        return urllib.parse.unquote(encoded_target[0]).strip()
    if parsed.scheme or parsed.netloc:
        return candidate
    return urllib.parse.urljoin(DEFAULT_SEARCH_URL, candidate)


def _extract_search_results(html: str, max_results: int = 5) -> list[Dict[str, Any]]:
    snippets = [
        _clean_html_fragment(raw)
        for raw in _SEARCH_RESULT_SNIPPET_RE.findall(html)
    ]
    results: list[Dict[str, Any]] = []
    for raw_url, raw_title in _SEARCH_RESULT_ANCHOR_RE.findall(html):
        title = _clean_html_fragment(raw_title)
        url = _normalize_search_result_url(raw_url)
        if not title or not url:
            continue
        index = len(results)
        results.append(
            {
                "rank": index + 1,
                "title": title,
                "url": url,
                "snippet": snippets[index] if index < len(snippets) else "",
            }
        )
        if len(results) >= max(1, max_results):
            break
    return results


def _write_evidence(session_id: str, task: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    host = urllib.parse.urlparse(payload.get("url", "")).netloc.replace(":", "_") or "unknown"
    path = EVIDENCE_DIR / f"playwriter-{host}-{task}-session{session_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _emit_payload(payload: Dict[str, Any], session_id: str, task: str, exit_code: int) -> int:
    artifact = _write_evidence(session_id, task, payload)
    payload["artifact_path"] = str(artifact)
    print(json.dumps(payload, indent=2))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Playwriter lane task with deterministic fallback.")
    parser.add_argument("--session", required=True, help="Session ID (string/integer).")
    parser.add_argument("--task", required=True, choices=["navigate", "title", "snapshot", "search-evidence"])
    parser.add_argument("--url", default="", help="Optional URL for navigate/title/snapshot.")
    parser.add_argument("--query", default="", help="Search query for search-evidence.")
    parser.add_argument("--result-index", type=int, default=0, help="Zero-based result index for search-evidence.")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum parsed search results for search-evidence.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    state = _load_state(args.session)
    target_url = args.url.strip() or str(state.get("url", "")).strip()
    if args.task == "navigate":
        if not target_url:
            print(json.dumps({"ok": False, "error": "navigate requires --url or existing session URL"}))
            return 1
        updated = {
            "session_id": str(args.session),
            "url": target_url,
            "updated_at": _utc_iso(),
        }
        _save_state(args.session, updated)
        evidence = {
            "ok": True,
            "session_id": str(args.session),
            "task": "navigate",
            "url": target_url,
            "timestamp": _utc_iso(),
        }
        return _emit_payload(evidence, str(args.session), "navigate", 0)

    if args.task == "search-evidence":
        query = args.query.strip()
        if not query:
            return _emit_payload(
                {
                    "ok": False,
                    "session_id": str(args.session),
                    "task": "search-evidence",
                    "url": "",
                    "error": "search-evidence requires --query",
                    "timestamp": _utc_iso(),
                },
                str(args.session),
                "search-evidence",
                1,
            )

        search_url = _build_search_url(query)
        try:
            search_html, search_status = _fetch_html(search_url, timeout=args.timeout)
            results = _extract_search_results(search_html, max_results=args.max_results)
            if not results:
                return _emit_payload(
                    {
                        "ok": False,
                        "session_id": str(args.session),
                        "task": "search-evidence",
                        "url": search_url,
                        "query": query,
                        "search_url": search_url,
                        "search_status_code": search_status,
                        "error": "no_search_results",
                        "timestamp": _utc_iso(),
                    },
                    str(args.session),
                    "search-evidence",
                    1,
                )
            if args.result_index < 0 or args.result_index >= len(results):
                return _emit_payload(
                    {
                        "ok": False,
                        "session_id": str(args.session),
                        "task": "search-evidence",
                        "url": search_url,
                        "query": query,
                        "search_url": search_url,
                        "search_status_code": search_status,
                        "results": results,
                        "error": f"result_index_out_of_range:{args.result_index}",
                        "timestamp": _utc_iso(),
                    },
                    str(args.session),
                    "search-evidence",
                    1,
                )

            selected = results[args.result_index]
            page_html, page_status = _fetch_html(selected["url"], timeout=args.timeout)
        except urllib.error.HTTPError as exc:
            return _emit_payload(
                {
                    "ok": False,
                    "session_id": str(args.session),
                    "task": "search-evidence",
                    "url": search_url,
                    "query": query,
                    "search_url": search_url,
                    "error": f"http_error:{exc.code}",
                    "timestamp": _utc_iso(),
                },
                str(args.session),
                "search-evidence",
                1,
            )
        except Exception as exc:
            return _emit_payload(
                {
                    "ok": False,
                    "session_id": str(args.session),
                    "task": "search-evidence",
                    "url": search_url,
                    "query": query,
                    "search_url": search_url,
                    "error": str(exc),
                    "timestamp": _utc_iso(),
                },
                str(args.session),
                "search-evidence",
                1,
            )

        title = _extract_title(page_html) or selected["title"]
        excerpt = _extract_text_excerpt(page_html)
        payload = {
            "ok": True,
            "session_id": str(args.session),
            "task": "search-evidence",
            "query": query,
            "search_url": search_url,
            "search_status_code": search_status,
            "selected_result_index": args.result_index,
            "selected_result": selected,
            "results": results,
            "url": selected["url"],
            "status_code": page_status,
            "title": title,
            "excerpt": excerpt,
            "char_count": len(excerpt),
            "timestamp": _utc_iso(),
        }
        _save_state(
            args.session,
            {
                "session_id": str(args.session),
                "url": selected["url"],
                "last_search_query": query,
                "last_search_url": search_url,
                "updated_at": _utc_iso(),
            },
        )
        return _emit_payload(payload, str(args.session), "search-evidence", 0)

    if not target_url:
        return _emit_payload(
            {
                "ok": False,
                "session_id": str(args.session),
                "task": args.task,
                "url": "",
                "error": "No URL in session. Run navigate first or provide --url.",
                "timestamp": _utc_iso(),
            },
            str(args.session),
            args.task,
            1,
        )

    try:
        html, status = _fetch_html(target_url, timeout=args.timeout)
    except urllib.error.HTTPError as exc:
        return _emit_payload(
            {
                "ok": False,
                "session_id": str(args.session),
                "task": args.task,
                "url": target_url,
                "error": f"http_error:{exc.code}",
                "timestamp": _utc_iso(),
            },
            str(args.session),
            args.task,
            1,
        )
    except Exception as exc:
        return _emit_payload(
            {
                "ok": False,
                "session_id": str(args.session),
                "task": args.task,
                "url": target_url,
                "error": str(exc),
                "timestamp": _utc_iso(),
            },
            str(args.session),
            args.task,
            1,
        )

    title = _extract_title(html)
    excerpt = _extract_text_excerpt(html)
    payload = {
        "ok": True,
        "session_id": str(args.session),
        "task": args.task,
        "url": target_url,
        "status_code": status,
        "title": title,
        "timestamp": _utc_iso(),
    }
    if args.task == "snapshot":
        payload["excerpt"] = excerpt
        payload["char_count"] = len(excerpt)
    _save_state(args.session, {"session_id": str(args.session), "url": target_url, "updated_at": _utc_iso()})
    return _emit_payload(payload, str(args.session), args.task, 0)


if __name__ == "__main__":
    raise SystemExit(main())
