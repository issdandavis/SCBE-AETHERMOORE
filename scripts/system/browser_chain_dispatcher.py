#!/usr/bin/env python3
"""Simple browser lane dispatcher for SCBE browser skills.

Provides a lightweight registry that maps domains/tasks to browser tentacles.
This module intentionally stays dependency-light so automation can run even
without Playwriter/Playwright extension connectivity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse


_AUTO_TASKS = {"", "auto", "default"}
_GENERIC_NAVIGATION_TASKS = {"browse", "navigate", "open", "view"}
_SEARCH_HINT_KEYS = (
    "query",
    "search",
    "search_query",
    "keywords",
    "repo_query",
    "model_query",
    "dataset_query",
    "space_query",
    "product_query",
    "collection_query",
    "page_query",
    "workspace_query",
)
_RESEARCH_HINT_KEYS = (
    "research",
    "research_goal",
    "research_query",
    "paper_query",
    "paper_id",
    "paper_ids",
    "arxiv_id",
    "arxiv_ids",
    "category",
)
_LOCAL_PREVIEW_HOSTS = {
    "0.0.0.0",
    "10.0.2.2",
    "127.0.0.1",
    "host.docker.internal",
    "localhost",
}
_LOCAL_PREVIEW_SUFFIXES = (".internal", ".local", ".localhost", ".test")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_domain(domain: str) -> str:
    cleaned = domain.strip().lower()
    if not cleaned:
        return ""

    candidate = cleaned if "://" in cleaned else f"https://{cleaned}"
    parsed = urlparse(candidate)
    return (parsed.netloc or parsed.path).strip().lower().strip("/")


def _host_without_port(domain: str) -> str:
    normalized = _normalize_domain(domain)
    host = normalized.rsplit("@", 1)[-1]
    if not host:
        return ""
    if host.startswith("[") and "]" in host:
        return host.split("]", 1)[0] + "]"
    if ":" in host and host.count(":") == 1:
        return host.split(":", 1)[0]
    return host


def _value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _payload_has_hint(payload: Dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(_value_present(payload.get(key)) for key in keys)


def _is_local_preview_host(host: str) -> bool:
    check = host.strip().lower()
    if not check:
        return False
    if check in _LOCAL_PREVIEW_HOSTS:
        return True
    return check.endswith(_LOCAL_PREVIEW_SUFFIXES)


def _make_assignment_id(domain: str, task: str, tentacle_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha1(f"{domain}|{task}|{tentacle_id}".encode("utf-8")).hexdigest()[:6]
    return f"bc-{stamp}-{digest}"


@dataclass
class BrowserTentacle:
    tentacle_id: str
    domain_patterns: List[str]
    default_task: str = "navigate"
    execution_engine: str = "playwriter"
    tags: List[str] = field(default_factory=list)
    search_default_task: str = ""
    research_default_task: str = ""
    local_preview: bool = False
    task_engines: Dict[str, str] = field(default_factory=dict)

    def matches(self, domain: str) -> bool:
        host = _host_without_port(domain)
        if self.local_preview and _is_local_preview_host(host):
            return True

        return any(
            host == pattern or host.endswith(f".{pattern}")
            for pattern in (pat.strip().lower() for pat in self.domain_patterns if pat.strip())
        )


class BrowserChainDispatcher:
    def __init__(self) -> None:
        self._tentacles: List[BrowserTentacle] = []

    def register_tentacle(self, tentacle: BrowserTentacle) -> None:
        self._tentacles.append(tentacle)

    def _resolve_task(self, tentacle: BrowserTentacle, requested_task: str, payload: Dict[str, Any]) -> tuple[str, str]:
        search_hint = _payload_has_hint(payload, _SEARCH_HINT_KEYS)
        research_hint = _payload_has_hint(payload, _RESEARCH_HINT_KEYS)

        if requested_task in _AUTO_TASKS:
            if research_hint and tentacle.research_default_task:
                return tentacle.research_default_task, "payload_research_hint"
            if search_hint and tentacle.search_default_task:
                return tentacle.search_default_task, "payload_search_hint"
            return tentacle.default_task, "tentacle_default"

        if requested_task in _GENERIC_NAVIGATION_TASKS:
            if tentacle.local_preview:
                return tentacle.default_task, "preview_default"
            if research_hint and tentacle.research_default_task:
                return tentacle.research_default_task, "payload_research_hint"
            if search_hint and tentacle.search_default_task:
                return tentacle.search_default_task, "payload_search_hint"
            return requested_task, "explicit"

        if requested_task == "search" and research_hint and tentacle.research_default_task:
            return tentacle.research_default_task, "payload_research_hint"

        return requested_task, "explicit"

    def _resolve_engine(self, tentacle: BrowserTentacle, requested_engine: str, task_type: str) -> tuple[str, str]:
        if requested_engine and requested_engine != "auto":
            return requested_engine, "payload_override"
        if task_type in tentacle.task_engines:
            return tentacle.task_engines[task_type], "task_default"
        return tentacle.execution_engine, "tentacle_default"

    def assign_task(self, domain: str, task_type: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        requested_engine = str(payload.get("engine", "")).strip().lower()
        domain_norm = _normalize_domain(domain)
        host_norm = _host_without_port(domain_norm)
        requested_task = task_type.strip().lower() if task_type else ""

        selected = next((t for t in self._tentacles if t.matches(domain_norm)), None)
        if selected is None:
            selected = BrowserTentacle(
                tentacle_id="tentacle-generic",
                domain_patterns=[host_norm or domain_norm or "unknown"],
                default_task="navigate",
                execution_engine="playwriter",
                tags=["generic"],
            )

        resolved_task, task_source = self._resolve_task(selected, requested_task, payload)
        resolved_engine, engine_source = self._resolve_engine(selected, requested_engine, resolved_task)
        assignment_id = _make_assignment_id(domain_norm or host_norm or "unknown", resolved_task, selected.tentacle_id)

        return {
            "ok": True,
            "assignment_id": assignment_id,
            "assigned_at": _utc_iso(),
            "domain": domain_norm,
            "host": host_norm,
            "requested_task_type": requested_task or "auto",
            "task_type": resolved_task,
            "task_source": task_source,
            "tentacle_id": selected.tentacle_id,
            "execution_engine": resolved_engine,
            "engine_source": engine_source,
            "tentacle": asdict(selected),
            "payload": payload,
        }


def build_default_fleet() -> List[BrowserTentacle]:
    return [
        BrowserTentacle(
            tentacle_id="tentacle-preview-dr",
            domain_patterns=["localhost", "127.0.0.1", "0.0.0.0", "10.0.2.2", "host.docker.internal"],
            default_task="preview",
            execution_engine="playwright",
            tags=["preview", "local", "smoke", "dev"],
            local_preview=True,
            task_engines={
                "navigate": "playwright",
                "preview": "playwright",
            },
        ),
        BrowserTentacle(
            tentacle_id="tentacle-arxiv-um",
            domain_patterns=["arxiv.org"],
            default_task="research",
            execution_engine="playwright",
            tags=["research", "papers", "metadata", "evidence"],
            search_default_task="research",
            research_default_task="research",
            task_engines={
                "navigate": "playwright",
                "research": "playwright",
                "search": "playwright",
            },
        ),
        BrowserTentacle(
            tentacle_id="tentacle-web-search-um",
            domain_patterns=["duckduckgo.com", "html.duckduckgo.com"],
            default_task="search",
            execution_engine="playwriter",
            tags=["search", "web", "evidence"],
            search_default_task="search",
            research_default_task="research",
            task_engines={
                "research": "playwright",
                "search": "playwright",
            },
        ),
        BrowserTentacle(
            tentacle_id="tentacle-huggingface-ca",
            domain_patterns=["hf.co", "huggingface.co"],
            default_task="search",
            execution_engine="playwriter",
            tags=["models", "datasets", "spaces", "research"],
            search_default_task="search",
            research_default_task="research",
            task_engines={
                "research": "playwright",
                "search": "playwright",
            },
        ),
        BrowserTentacle(
            tentacle_id="tentacle-github-ko",
            domain_patterns=["github.com"],
            default_task="navigate",
            execution_engine="playwriter",
            tags=["repo", "pr", "issues", "search"],
            search_default_task="search",
        ),
        BrowserTentacle(
            tentacle_id="tentacle-notion-av",
            domain_patterns=["notion.so", "www.notion.so"],
            default_task="navigate",
            execution_engine="playwriter",
            tags=["workspace", "knowledge", "search"],
            search_default_task="search",
        ),
        BrowserTentacle(
            tentacle_id="tentacle-shopify-ru",
            domain_patterns=["shopify.com", "myshopify.com"],
            default_task="navigate",
            execution_engine="playwriter",
            tags=["commerce", "admin", "catalog", "search"],
            search_default_task="search",
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch browser tasks to SCBE tentacles.")
    parser.add_argument("--domain", required=True, help="Target domain, e.g. arxiv.org")
    parser.add_argument("--task", default="auto", help="Task type, e.g. auto/research/search/navigate")
    parser.add_argument("--engine", default="auto", help="Execution engine (playwriter/playwright/auto)")
    parser.add_argument("--payload-json", default="", help="Optional JSON payload for assignment context")
    args = parser.parse_args()

    payload: Dict[str, Any] = {}
    if args.engine.strip() and args.engine.strip().lower() != "auto":
        payload["engine"] = args.engine
    if args.payload_json.strip():
        try:
            extra = json.loads(args.payload_json)
            if isinstance(extra, dict):
                payload.update(extra)
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": f"invalid payload JSON: {exc}"}))
            return 1

    dispatcher = BrowserChainDispatcher()
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    result = dispatcher.assign_task(domain=args.domain, task_type=args.task, payload=payload)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
