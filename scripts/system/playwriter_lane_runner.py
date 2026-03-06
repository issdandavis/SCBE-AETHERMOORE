#!/usr/bin/env python3
"""Playwriter-compatible lane runner with deterministic HTTP fallback.

Supports:
- navigate: set/refresh session URL
- title: fetch title for current URL
- snapshot: fetch compact page evidence for current URL
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "artifacts" / "page_evidence"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(session_id: str) -> Path:
    return EVIDENCE_DIR / f"playwriter-session-{session_id}.json"


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
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _write_evidence(session_id: str, task: str, payload: Dict[str, Any]) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    host = urllib.parse.urlparse(payload.get("url", "")).netloc.replace(":", "_") or "unknown"
    path = EVIDENCE_DIR / f"playwriter-{host}-{task}-session{session_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Playwriter lane task with deterministic fallback.")
    parser.add_argument("--session", required=True, help="Session ID (string/integer).")
    parser.add_argument("--task", required=True, choices=["navigate", "title", "snapshot"])
    parser.add_argument("--url", default="", help="Optional URL for navigate/title/snapshot.")
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
        artifact = _write_evidence(args.session, "navigate", evidence)
        evidence["artifact_path"] = str(artifact)
        print(json.dumps(evidence, indent=2))
        return 0

    if not target_url:
        print(json.dumps({"ok": False, "error": "No URL in session. Run navigate first or provide --url."}))
        return 1

    try:
        html, status = _fetch_html(target_url, timeout=args.timeout)
    except urllib.error.HTTPError as exc:
        payload = {
            "ok": False,
            "session_id": str(args.session),
            "task": args.task,
            "url": target_url,
            "error": f"http_error:{exc.code}",
            "timestamp": _utc_iso(),
        }
        artifact = _write_evidence(args.session, args.task, payload)
        payload["artifact_path"] = str(artifact)
        print(json.dumps(payload, indent=2))
        return 1
    except Exception as exc:
        payload = {
            "ok": False,
            "session_id": str(args.session),
            "task": args.task,
            "url": target_url,
            "error": str(exc),
            "timestamp": _utc_iso(),
        }
        artifact = _write_evidence(args.session, args.task, payload)
        payload["artifact_path"] = str(artifact)
        print(json.dumps(payload, indent=2))
        return 1

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
    artifact = _write_evidence(args.session, args.task, payload)
    payload["artifact_path"] = str(artifact)
    _save_state(args.session, {"session_id": str(args.session), "url": target_url, "updated_at": _utc_iso()})
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
