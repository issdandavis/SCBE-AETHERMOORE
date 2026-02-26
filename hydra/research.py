"""
HYDRA research orchestration.

Phase 1 goals:
- Headless, cloud-deployable multi-agent web research.
- Reuse existing HYDRA primitives (providers, limbs, switchboard).
- Coordinate decomposition, discovery, browse/extract, and synthesis.
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

import httpx

from .limbs import MultiTabBrowserLimb
from .llm_providers import LLMProvider, create_provider
from .switchboard import Switchboard


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


@dataclass
class ResearchConfig:
    """Config for the research orchestrator."""

    mode: str = "local"  # local | cloud | httpx
    provider_order: List[str] = field(default_factory=lambda: ["claude", "gpt", "gemini"])
    decompose_provider: Optional[str] = None
    synthesis_provider: Optional[str] = None

    max_subtasks: int = 5
    discovery_per_subtask: int = 3
    extract_max_chars: int = 8000
    request_timeout_sec: int = 20

    local_max_tabs: int = 4
    browser_backend: str = "playwright"

    switchboard_role: str = "researcher"
    cloud_poll_interval_sec: float = 0.5
    cloud_wait_timeout_sec: int = 120

    use_hf_summarizer: bool = False
    hf_model_name: str = "facebook/bart-large-cnn"


@dataclass
class ResearchSubTask:
    """LLM-generated sub-task for parallel research."""

    subtask_id: str
    title: str
    search_query: str
    urls: List[str] = field(default_factory=list)


@dataclass
class ResearchSource:
    """Extracted source record."""

    subtask_id: str
    url: str
    title: str = ""
    excerpt: str = ""
    chars: int = 0
    status: str = "ok"
    provider: str = ""
    error: Optional[str] = None


@dataclass
class ResearchReport:
    """Final research output."""

    query: str
    summary: str
    synthesis: str
    sources: List[ResearchSource]
    subtasks: List[ResearchSubTask]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "summary": self.summary,
            "synthesis": self.synthesis,
            "sources": [asdict(s) for s in self.sources],
            "subtasks": [asdict(s) for s in self.subtasks],
            "metadata": self.metadata,
        }


def html_to_text(raw_html: str, max_chars: int = 8000) -> str:
    """Convert HTML-ish text to compact plain text."""
    if not raw_html:
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    except Exception:
        # Lightweight fallback for environments without bs4/lxml.
        text = re.sub(r"<[^>]+>", " ", raw_html)

    compact = " ".join(text.split())
    return compact[: max(1, int(max_chars))]


def _safe_json_loads(text: str) -> Any:
    """Parse JSON from plain text or fenced markdown blocks."""
    text = (text or "").strip()
    if not text:
        return None

    candidates: List[str] = [text]
    match = _JSON_FENCE_RE.search(text)
    if match:
        candidates.insert(0, match.group(1).strip())

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last attempt: find first array/object block.
    for start_char, end_char in (("[", "]"), ("{", "}")):
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start >= 0 and end > start:
            chunk = text[start : end + 1]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue

    return None


class ResearchOrchestrator:
    """Orchestrates multi-agent web research using HYDRA primitives."""

    def __init__(
        self,
        config: Optional[ResearchConfig] = None,
        *,
        switchboard: Optional[Switchboard] = None,
        browser_limb: Optional[MultiTabBrowserLimb] = None,
        providers: Optional[Dict[str, LLMProvider]] = None,
        hf_summarizer: Optional[Any] = None,
    ):
        self.config = config or ResearchConfig()
        self.switchboard = switchboard
        self.browser_limb = browser_limb
        self.providers = providers or self._build_providers(self.config.provider_order)
        self.hf_summarizer = hf_summarizer

        if not self.providers:
            raise RuntimeError("No LLM providers available for research orchestration")

        self._decompose_provider_name = self._pick_provider_name(self.config.decompose_provider)
        self._synthesis_provider_name = self._pick_provider_name(self.config.synthesis_provider)

    def _pick_provider_name(self, preferred: Optional[str]) -> str:
        if preferred:
            key = preferred.strip().lower()
            if key in self.providers:
                return key
        return next(iter(self.providers.keys()))

    def _build_providers(self, names: Sequence[str]) -> Dict[str, LLMProvider]:
        out: Dict[str, LLMProvider] = {}
        for name in names:
            key = str(name).strip().lower()
            if not key or key in out:
                continue
            try:
                out[key] = create_provider(key)
            except Exception:
                continue
        return out

    async def close(self) -> None:
        """Cleanup resources owned by the orchestrator."""
        if self.browser_limb is not None:
            try:
                await self.browser_limb.deactivate()
            except Exception:
                pass

    async def research(self, query: str) -> ResearchReport:
        """Run full research pipeline for a query."""
        started = time.time()

        subtasks = await self._decompose_query(query)
        subtasks = await self._ensure_discovery(subtasks)

        jobs = self._flatten_subtask_jobs(subtasks)
        mode = self.config.mode.strip().lower()
        if mode == "cloud":
            if not self.switchboard:
                raise RuntimeError("Cloud mode requires a configured Switchboard")
            sources = await self._browse_cloud(jobs)
        elif mode == "httpx":
            sources = await self._browse_httpx(jobs)
        else:
            sources = await self._browse_local(jobs)

        if self.config.use_hf_summarizer:
            await self._compress_sources_with_hf(sources)

        synthesis, provider_summaries = await self._synthesize(query, subtasks, sources)
        summary = self._build_summary(query, subtasks, sources, synthesis)

        return ResearchReport(
            query=query,
            summary=summary,
            synthesis=synthesis,
            sources=sources,
            subtasks=subtasks,
            metadata={
                "mode": self.config.mode,
                "providers_active": sorted(self.providers.keys()),
                "decompose_provider": self._decompose_provider_name,
                "synthesis_provider": self._synthesis_provider_name,
                "provider_summaries": provider_summaries,
                "source_count": len(sources),
                "elapsed_ms": round((time.time() - started) * 1000.0, 2),
            },
        )

    async def _decompose_query(self, query: str) -> List[ResearchSubTask]:
        provider = self.providers[self._decompose_provider_name]
        prompt = (
            "Decompose the research query into 2-5 parallel subtasks. "
            "Return strict JSON array with objects: "
            "{title, search_query, urls}. "
            "Only include urls if highly confident. "
            f"\nQuery: {query}"
        )

        raw_text = ""
        try:
            response = await provider.complete(prompt)
            raw_text = response.text
        except Exception:
            raw_text = ""

        parsed = _safe_json_loads(raw_text)
        subtasks: List[ResearchSubTask] = []

        if isinstance(parsed, list):
            for idx, item in enumerate(parsed, start=1):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or f"Subtask {idx}").strip()
                search_query = str(item.get("search_query") or query).strip()
                urls = [str(u).strip() for u in item.get("urls", []) if str(u).strip()] if isinstance(item.get("urls"), list) else []
                subtasks.append(
                    ResearchSubTask(
                        subtask_id=f"subtask-{idx}",
                        title=title,
                        search_query=search_query,
                        urls=urls,
                    )
                )

        # Deterministic fallback if provider output is missing/unparseable.
        if len(subtasks) < 2:
            subtasks = [
                ResearchSubTask("subtask-1", "Core overview", query, []),
                ResearchSubTask("subtask-2", "Recent updates", f"{query} latest", []),
            ]

        return subtasks[: max(1, int(self.config.max_subtasks))]

    async def _ensure_discovery(self, subtasks: List[ResearchSubTask]) -> List[ResearchSubTask]:
        out: List[ResearchSubTask] = []
        for subtask in subtasks:
            urls = [u for u in subtask.urls if self._looks_like_url(u)]
            if not urls:
                discovered = await self._discover_urls(subtask.search_query)
                urls = [u for u in discovered if self._looks_like_url(u)]
            if not urls:
                # Keep task without URLs so synthesis still includes it.
                urls = []
            out.append(
                ResearchSubTask(
                    subtask_id=subtask.subtask_id,
                    title=subtask.title,
                    search_query=subtask.search_query,
                    urls=urls,
                )
            )
        return out

    async def _discover_urls(self, search_query: str) -> List[str]:
        query = quote_plus(search_query)
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        timeout = httpx.Timeout(self.config.request_timeout_sec)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(rss_url, headers={"User-Agent": "HYDRA-Research/1.0"})
                response.raise_for_status()
        except Exception:
            return []

        links: List[str] = []
        try:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                link = (item.findtext("link") or "").strip()
                if link:
                    links.append(link)
                if len(links) >= max(1, int(self.config.discovery_per_subtask)):
                    break
        except Exception:
            return []

        dedup: List[str] = []
        seen: set[str] = set()
        for link in links:
            if link not in seen:
                dedup.append(link)
                seen.add(link)
        return dedup

    def _flatten_subtask_jobs(self, subtasks: Iterable[ResearchSubTask]) -> List[Tuple[str, str, str]]:
        jobs: List[Tuple[str, str, str]] = []
        for subtask in subtasks:
            for url in subtask.urls:
                jobs.append((subtask.subtask_id, subtask.title, url))
        return jobs

    async def _browse_local(self, jobs: List[Tuple[str, str, str]]) -> List[ResearchSource]:
        if not jobs:
            return []

        if self.browser_limb is None:
            self.browser_limb = MultiTabBrowserLimb(
                backend_type=self.config.browser_backend,
                max_tabs=max(1, int(self.config.local_max_tabs)),
            )
            await self.browser_limb.activate()

        sources: List[ResearchSource] = []
        max_tabs = max(1, int(self.config.local_max_tabs))

        for start in range(0, len(jobs), max_tabs):
            chunk = jobs[start : start + max_tabs]
            nav_commands = [{"action": "navigate", "target": url} for _, _, url in chunk]
            nav_results = await self.browser_limb.execute_parallel(nav_commands)

            fetch_commands: List[Dict[str, Any]] = []
            mapping: List[Tuple[str, str, str]] = []

            for (subtask_id, title, url), nav in zip(chunk, nav_results):
                if not isinstance(nav, dict) or not nav.get("success"):
                    sources.append(
                        ResearchSource(
                            subtask_id=subtask_id,
                            title=title,
                            url=url,
                            status="error",
                            error=str(nav.get("error") if isinstance(nav, dict) else "navigate failed"),
                        )
                    )
                    continue

                fetch_commands.append(
                    {
                        "action": "get_content",
                        "target": "",
                        "tab_id": nav.get("tab_id"),
                    }
                )
                mapping.append((subtask_id, title, url))

            if not fetch_commands:
                continue

            fetch_results = await self.browser_limb.execute_parallel(fetch_commands)
            for (subtask_id, title, url), fetched in zip(mapping, fetch_results):
                payload = fetched if isinstance(fetched, dict) else {}
                data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
                raw = str(data.get("preview") or "")
                text = html_to_text(raw, max_chars=self.config.extract_max_chars)

                sources.append(
                    ResearchSource(
                        subtask_id=subtask_id,
                        title=title,
                        url=url,
                        excerpt=text,
                        chars=len(text),
                        status="ok" if payload.get("success") else "error",
                        error=None if payload.get("success") else str(payload.get("error") or "fetch failed"),
                    )
                )

        return sources

    async def _browse_httpx(self, jobs: List[Tuple[str, str, str]]) -> List[ResearchSource]:
        """Lightweight HTTP-only fetching -- no browser, ~5 MB vs ~300 MB per Chromium tab."""
        if not jobs:
            return []

        timeout = httpx.Timeout(self.config.request_timeout_sec)
        sources: List[ResearchSource] = []

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HydraResearch/1.0)"},
        ) as client:

            async def _fetch(subtask_id: str, title: str, url: str) -> ResearchSource:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    text = html_to_text(resp.text, max_chars=self.config.extract_max_chars)
                    return ResearchSource(
                        subtask_id=subtask_id, title=title, url=str(resp.url),
                        excerpt=text, chars=len(text), status="ok", provider="httpx",
                    )
                except Exception as exc:
                    return ResearchSource(
                        subtask_id=subtask_id, title=title, url=url,
                        status="error", error=str(exc), provider="httpx",
                    )

            results = await asyncio.gather(*[_fetch(sid, t, u) for sid, t, u in jobs])
            sources.extend(results)

        return sources

    async def _browse_cloud(self, jobs: List[Tuple[str, str, str]]) -> List[ResearchSource]:
        if not jobs:
            return []
        if self.switchboard is None:
            raise RuntimeError("Cloud browsing requested but no switchboard is configured")

        task_to_job: Dict[str, Tuple[str, str, str]] = {}
        for subtask_id, title, url in jobs:
            queued = self.switchboard.enqueue_task(
                role=self.config.switchboard_role,
                payload={
                    "action": "research_fetch",
                    "target": url,
                    "params": {
                        "subtask_id": subtask_id,
                        "title": title,
                        "max_chars": int(self.config.extract_max_chars),
                    },
                },
                dedupe_key=f"research::{subtask_id}::{url}",
                priority=80,
            )
            task_to_job[str(queued["task_id"])] = (subtask_id, title, url)

        task_rows = await self._wait_for_cloud_tasks(task_to_job.keys())
        out: List[ResearchSource] = []

        for task_id, row in task_rows.items():
            subtask_id, title, url = task_to_job[task_id]
            status = str(row.get("status", "failed"))
            result = row.get("result") if isinstance(row.get("result"), dict) else {}

            if status == "done":
                text = str(result.get("text") or "")
                out.append(
                    ResearchSource(
                        subtask_id=subtask_id,
                        title=title,
                        url=str(result.get("url") or url),
                        excerpt=text[: self.config.extract_max_chars],
                        chars=len(text),
                        status="ok",
                        provider="cloud-worker",
                    )
                )
            else:
                out.append(
                    ResearchSource(
                        subtask_id=subtask_id,
                        title=title,
                        url=url,
                        status="error",
                        error=str(row.get("error_text") or "worker failed"),
                        provider="cloud-worker",
                    )
                )

        return out

    async def _wait_for_cloud_tasks(self, task_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        pending = {str(tid) for tid in task_ids}
        done: Dict[str, Dict[str, Any]] = {}
        deadline = time.time() + max(1, int(self.config.cloud_wait_timeout_sec))

        while pending and time.time() < deadline:
            rows = self._fetch_task_rows(pending)
            for task_id, row in rows.items():
                status = str(row.get("status") or "")
                if status in {"done", "failed"}:
                    done[task_id] = row
                    pending.discard(task_id)
            if pending:
                await asyncio.sleep(max(0.05, float(self.config.cloud_poll_interval_sec)))

        for task_id in sorted(pending):
            done[task_id] = {
                "task_id": task_id,
                "status": "failed",
                "error_text": "timeout waiting for cloud worker",
                "result": {},
            }
        return done

    def _fetch_task_rows(self, task_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        ids = [str(t) for t in task_ids if str(t).strip()]
        if not ids:
            return {}
        if self.switchboard is None:
            return {}

        placeholders = ",".join("?" for _ in ids)
        sql = (
            "SELECT task_id, status, result_json, error_text "
            f"FROM tasks WHERE task_id IN ({placeholders})"
        )

        out: Dict[str, Dict[str, Any]] = {}
        try:
            with self.switchboard._connect() as conn:  # intentionally reuses switchboard DB connection config
                rows = conn.execute(sql, tuple(ids)).fetchall()
        except sqlite3.Error:
            return out

        for row in rows:
            task_id = str(row["task_id"])
            result: Dict[str, Any] = {}
            raw_result = row["result_json"]
            if raw_result:
                try:
                    parsed = json.loads(str(raw_result))
                    if isinstance(parsed, dict):
                        result = parsed
                except json.JSONDecodeError:
                    result = {}

            out[task_id] = {
                "task_id": task_id,
                "status": str(row["status"]),
                "result": result,
                "error_text": row["error_text"],
            }

        return out

    async def _compress_sources_with_hf(self, sources: List[ResearchSource]) -> None:
        if not sources:
            return

        if self.hf_summarizer is None:
            try:
                from .hf_summarizer import HFSummarizer

                self.hf_summarizer = HFSummarizer(model_name=self.config.hf_model_name)
            except Exception:
                self.hf_summarizer = None

        if self.hf_summarizer is None:
            return

        async def _compress(source: ResearchSource) -> None:
            if source.status != "ok" or not source.excerpt.strip():
                return
            try:
                summary = await self.hf_summarizer.summarize_async(source.excerpt)
                source.excerpt = summary[: self.config.extract_max_chars]
                source.chars = len(source.excerpt)
                source.provider = "hf-bart"
            except Exception:
                # Non-fatal: keep original source excerpt.
                return

        await asyncio.gather(*[_compress(source) for source in sources])

    async def _synthesize(
        self,
        query: str,
        subtasks: List[ResearchSubTask],
        sources: List[ResearchSource],
    ) -> Tuple[str, Dict[str, str]]:
        context_lines: List[str] = []
        for source in sources:
            if source.status != "ok":
                continue
            context_lines.append(
                f"- [{source.subtask_id}] {source.url}\n"
                f"  excerpt: {source.excerpt[:1200]}"
            )

        context_blob = "\n".join(context_lines) if context_lines else "No valid sources were fetched."
        subtasks_blob = "\n".join(
            [f"- {s.subtask_id}: {s.title} ({s.search_query})" for s in subtasks]
        )

        prompt = (
            "You are a research synthesis agent. Use only provided source excerpts. "
            "Return clear findings, caveats, and a source-backed summary.\n\n"
            f"Query: {query}\n"
            f"Subtasks:\n{subtasks_blob}\n\n"
            f"Source excerpts:\n{context_blob}\n"
        )

        async def _run_provider(name: str, provider: LLMProvider) -> Tuple[str, str]:
            try:
                response = await provider.complete(prompt)
                return name, response.text.strip()
            except Exception as exc:
                return name, f"provider_error: {exc}"

        provider_runs = [_run_provider(name, provider) for name, provider in self.providers.items()]
        results = await asyncio.gather(*provider_runs)
        provider_summaries = {name: text for name, text in results}

        primary_text = provider_summaries.get(self._synthesis_provider_name, "")
        if not primary_text:
            primary_text = next(iter(provider_summaries.values()), "")

        return primary_text, provider_summaries

    def _build_summary(
        self,
        query: str,
        subtasks: List[ResearchSubTask],
        sources: List[ResearchSource],
        synthesis: str,
    ) -> str:
        ok_count = len([s for s in sources if s.status == "ok"])
        err_count = len([s for s in sources if s.status != "ok"])

        first_line = synthesis.strip().splitlines()[0].strip() if synthesis.strip() else ""
        if not first_line:
            first_line = f"Research completed for '{query}'."

        return (
            f"{first_line} "
            f"Subtasks: {len(subtasks)}. Sources fetched: {ok_count}. "
            f"Source failures: {err_count}."
        )

    @staticmethod
    def _looks_like_url(value: str) -> bool:
        v = str(value or "").strip().lower()
        return v.startswith("http://") or v.startswith("https://")
