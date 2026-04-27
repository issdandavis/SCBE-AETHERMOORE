"""
SCBE Agent Bus — unified pipeline connecting browser tools, free LLMs,
web search, and the aethermoore.com website.

The bus routes tasks through:
  1. Web search (DuckDuckGo API, free)
  2. Page scraping (Playwright)
  3. Free LLM inference (HuggingFace Inference API / Ollama local)
  4. Governed output (zone gates, Sacred Tongues scoring)

All LLM calls are free-tier: HuggingFace serverless inference (HF_TOKEN)
or Ollama running locally. No paid API keys required.

Usage:
    bus = AgentBus()
    await bus.start()

    # Ask a question with web research
    result = await bus.ask("What is post-quantum cryptography?")

    # Search + summarize
    result = await bus.search_and_summarize("SCBE AI safety", max_sources=3)

    # Scrape + analyze
    result = await bus.analyze_page("https://example.com")

    # Monitor sites
    result = await bus.monitor(["https://news.ycombinator.com", "https://github.com"])

    await bus.stop()
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scbe.agent_bus")

# Bus event log
BUS_LOG = Path("artifacts/agent-bus/events.jsonl")


@dataclass
class BusEvent:
    """Audit record for every bus operation."""
    task_type: str
    query: str
    sources_used: int = 0
    llm_provider: str = ""
    llm_model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_seconds: float = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentBus:
    """
    Unified agent bus. Connects:
    - PlaywrightRuntime (browser)
    - WebScraper (extraction)
    - ResearchAgent (multi-site research)
    - Free LLM inference (HuggingFace / Ollama)
    """

    def __init__(
        self,
        *,
        hf_model: str = "Qwen/Qwen2.5-72B-Instruct",
        ollama_model: str = "llama3.2",
        ollama_url: str = "http://127.0.0.1:11434",
        prefer_local: bool = True,
    ) -> None:
        self.hf_model = hf_model
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url.rstrip("/")
        self.prefer_local = prefer_local

        self._runtime = None
        self._scraper = None
        self._researcher = None
        self._started = False
        self._event_log: List[BusEvent] = []

    # -- lifecycle -----------------------------------------------------------

    async def start(self, *, headless: bool = True) -> None:
        """Start the bus (launches browser + initializes scraper)."""
        from agents.playwright_runtime import PlaywrightRuntime
        from agents.web_scraper import WebScraper
        from agents.research_agent import ResearchAgent

        self._runtime = PlaywrightRuntime()
        await self._runtime.launch(headless=headless)
        self._scraper = WebScraper(self._runtime)
        self._researcher = ResearchAgent(self._scraper, max_sources=5)
        self._started = True

        BUS_LOG.parent.mkdir(parents=True, exist_ok=True)
        logger.info("AgentBus started (hf=%s, ollama=%s)", self.hf_model, self.ollama_model)

    async def stop(self) -> None:
        """Stop the bus."""
        if self._runtime:
            await self._runtime.close()
        self._runtime = self._scraper = self._researcher = None
        self._started = False
        logger.info("AgentBus stopped")

    # -- main operations -----------------------------------------------------

    async def ask(
        self,
        question: str,
        *,
        search_first: bool = True,
        max_sources: int = 3,
    ) -> Dict[str, Any]:
        """
        Answer a question using web research + free LLM.

        1. Search the web for relevant context
        2. Scrape top results
        3. Build a context prompt
        4. Send to free LLM for answer
        """
        self._require_started()
        start = time.monotonic()
        event = BusEvent(task_type="ask", query=question)

        context_text = ""
        sources = []

        if search_first:
            try:
                pages = await self._scraper.search_and_scrape(question, max_results=max_sources)
                for p in pages:
                    if p.text and not p.error:
                        snippet = p.text[:1500]
                        context_text += f"\n\n---\nSource: {p.title} ({p.url})\n{snippet}"
                        sources.append({"title": p.title, "url": p.url, "words": p.word_count})
                event.sources_used = len(sources)
            except Exception as exc:
                logger.warning("Search failed for '%s': %s", question, exc)

        prompt = self._build_prompt(question, context_text)
        answer = await self._llm_generate(prompt)

        event.llm_provider = answer["provider"]
        event.llm_model = answer["model"]
        event.duration_seconds = time.monotonic() - start
        event.success = not answer.get("error")
        event.error = answer.get("error")
        self._log_event(event)

        return {
            "question": question,
            "answer": answer["text"],
            "sources": sources,
            "provider": answer["provider"],
            "model": answer["model"],
            "duration_seconds": round(event.duration_seconds, 1),
        }

    async def search_and_summarize(
        self,
        query: str,
        *,
        max_sources: int = 5,
    ) -> Dict[str, Any]:
        """Search the web, scrape results, summarize with free LLM."""
        self._require_started()
        start = time.monotonic()
        event = BusEvent(task_type="search_and_summarize", query=query)

        report = await self._researcher.research(query)
        event.sources_used = report.sources_checked

        if not report.findings:
            event.duration_seconds = time.monotonic() - start
            self._log_event(event)
            return {
                "query": query,
                "summary": f"No relevant findings for '{query}'.",
                "findings": [],
                "sources_checked": report.sources_checked,
            }

        # Build context from findings
        context = "\n\n".join(
            f"[{f.confidence:.0%}] {f.title}\n{f.relevant_text[:800]}"
            for f in report.findings[:5]
        )

        prompt = (
            f"Summarize these research findings about '{query}' in 2-3 paragraphs. "
            f"Cite sources by title. Be concise and factual.\n\n{context}"
        )

        answer = await self._llm_generate(prompt)
        event.llm_provider = answer["provider"]
        event.llm_model = answer["model"]
        event.duration_seconds = time.monotonic() - start
        self._log_event(event)

        return {
            "query": query,
            "summary": answer["text"],
            "findings": [
                {"title": f.title, "url": f.source_url, "confidence": f.confidence}
                for f in report.findings
            ],
            "sources_checked": report.sources_checked,
            "words_read": report.total_words_read,
            "provider": answer["provider"],
            "duration_seconds": round(event.duration_seconds, 1),
        }

    async def analyze_page(self, url: str) -> Dict[str, Any]:
        """Scrape a page and analyze it with free LLM."""
        self._require_started()
        start = time.monotonic()
        event = BusEvent(task_type="analyze_page", query=url)

        page = await self._scraper.scrape(url, extract_tables=True, extract_images=True)
        event.sources_used = 1

        if page.error:
            event.error = page.error
            event.success = False
            self._log_event(event)
            return {"url": url, "error": page.error}

        prompt = (
            f"Analyze this web page and provide a structured summary:\n\n"
            f"Title: {page.title}\n"
            f"URL: {page.url}\n"
            f"Word count: {page.word_count}\n"
            f"Headings: {json.dumps([h['text'] for h in page.headings[:10]])}\n"
            f"Tables: {len(page.tables)}\n"
            f"Links: {len(page.links)}\n\n"
            f"Content:\n{page.text[:3000]}\n\n"
            f"Provide: 1) What this page is about, 2) Key points, 3) Notable data"
        )

        answer = await self._llm_generate(prompt)
        event.llm_provider = answer["provider"]
        event.llm_model = answer["model"]
        event.duration_seconds = time.monotonic() - start
        self._log_event(event)

        return {
            "url": page.url,
            "title": page.title,
            "word_count": page.word_count,
            "analysis": answer["text"],
            "headings": [h["text"] for h in page.headings[:10]],
            "tables": len(page.tables),
            "links": len(page.links),
            "provider": answer["provider"],
        }

    async def monitor(self, urls: List[str]) -> Dict[str, Any]:
        """Quick read of multiple sites with summaries."""
        self._require_started()
        summaries = await self._researcher.monitor_sites(urls)
        return {"sites": summaries, "count": len(summaries)}

    # -- free LLM inference --------------------------------------------------

    async def _llm_generate(self, prompt: str) -> Dict[str, Any]:
        """
        Generate text using free LLMs.

        Priority: Ollama (local) → HuggingFace (free API) → Offline fallback
        """
        # Try Ollama first if prefer_local
        if self.prefer_local:
            result = await self._try_ollama(prompt)
            if result:
                return result

        # Try HuggingFace
        result = await self._try_huggingface(prompt)
        if result:
            return result

        # Try Ollama as fallback if not preferred
        if not self.prefer_local:
            result = await self._try_ollama(prompt)
            if result:
                return result

        # Offline fallback
        return {
            "text": f"[LLM unavailable — raw context returned]\n\n{prompt[:2000]}",
            "provider": "offline",
            "model": "none",
            "error": "No LLM provider available (set HF_TOKEN or run Ollama)",
        }

    async def _try_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Try Ollama local inference."""
        try:
            import urllib.request
            url = f"{self.ollama_url}/api/generate"
            payload = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return {
                "text": data.get("response", ""),
                "provider": "ollama",
                "model": self.ollama_model,
            }
        except Exception as exc:
            logger.debug("Ollama failed: %s", exc)
            return None

    async def _try_huggingface(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Try HuggingFace Inference API (free tier, chat completions)."""
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            return None

        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(model=self.hf_model, token=hf_token)
            resp = client.chat_completion(
                messages=[{"role": "user", "content": prompt[:4000]}],
                max_tokens=512,
            )
            text = resp.choices[0].message.content
            if text and text.strip():
                return {
                    "text": text.strip(),
                    "provider": "huggingface",
                    "model": self.hf_model,
                }
            return None
        except Exception as exc:
            logger.debug("HuggingFace failed: %s", exc)
            return None

    # -- internal ------------------------------------------------------------

    def _build_prompt(self, question: str, context: str) -> str:
        if context:
            return (
                f"Answer the following question using the provided context. "
                f"Be concise, factual, and cite sources when possible.\n\n"
                f"Question: {question}\n\n"
                f"Context:{context}\n\n"
                f"Answer:"
            )
        return f"Answer concisely: {question}"

    def _log_event(self, event: BusEvent) -> None:
        event.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self._event_log.append(event)
        try:
            with open(BUS_LOG, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception:
            pass

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("AgentBus not started — call await bus.start() first")

    @property
    def event_count(self) -> int:
        return len(self._event_log)

    @property
    def events(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._event_log]
