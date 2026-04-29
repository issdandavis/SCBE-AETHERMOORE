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
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("scbe.agent_bus")

BUS_LOG = Path("artifacts/agent-bus/events.jsonl")
SCHEMA_VERSION = "1.0.0"

RETRY_BASE_SECONDS = 1.0
RETRY_MAX_ATTEMPTS = 5
RETRY_CAP_SECONDS = 30.0
BREAKER_FAIL_THRESHOLD = 4
BREAKER_COOLDOWN_SECONDS = 60.0
HTTP_TIMEOUT_SECONDS = 60.0


class CircuitBreaker:
    """Three-state breaker: closed → open (after N consecutive fails) → half-open (single probe) → closed."""

    def __init__(
        self,
        name: str,
        fail_threshold: int = BREAKER_FAIL_THRESHOLD,
        cooldown: float = BREAKER_COOLDOWN_SECONDS,
    ) -> None:
        self.name = name
        self.fail_threshold = fail_threshold
        self.cooldown = cooldown
        self.consecutive_failures = 0
        self.opened_at: Optional[float] = None
        self.half_open_in_flight = False

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if (time.monotonic() - self.opened_at) >= self.cooldown:
            return "half_open"
        return "open"

    def allow(self) -> bool:
        s = self.state
        if s == "closed":
            return True
        if s == "open":
            return False
        if self.half_open_in_flight:
            return False
        self.half_open_in_flight = True
        return True

    def record_success(self) -> None:
        if self.opened_at is not None:
            logger.info("breaker[%s] closed after probe success", self.name)
        self.consecutive_failures = 0
        self.opened_at = None
        self.half_open_in_flight = False

    def record_failure(self) -> None:
        self.half_open_in_flight = False
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.fail_threshold and self.opened_at is None:
            self.opened_at = time.monotonic()
            logger.warning(
                "breaker[%s] OPEN after %d consecutive failures (cooldown %ss)",
                self.name,
                self.consecutive_failures,
                self.cooldown,
            )


async def _retry_with_backoff(
    fn: Callable[[], Awaitable[Any]],
    *,
    breaker: CircuitBreaker,
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    base: float = RETRY_BASE_SECONDS,
    cap: float = RETRY_CAP_SECONDS,
    is_rate_limit: Callable[[BaseException], bool] = lambda e: False,
) -> Optional[Any]:
    """Run `fn` with exponential backoff + jitter, gated by `breaker`.

    Returns None if breaker is open or all attempts fail.
    """
    if not breaker.allow():
        logger.debug("breaker[%s] blocked call (state=%s)", breaker.name, breaker.state)
        return None

    last_exc: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = await fn()
            breaker.record_success()
            return result
        except BaseException as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            # honor rate-limit signals with longer backoff
            multiplier = 4.0 if is_rate_limit(exc) else 2.0
            sleep_for = min(cap, base * (multiplier ** (attempt - 1)))
            sleep_for *= 0.5 + random.random()  # full jitter in [0.5x, 1.5x]
            logger.debug(
                "retry[%s] attempt %d/%d failed (%s); sleeping %.2fs",
                breaker.name,
                attempt,
                max_attempts,
                exc.__class__.__name__,
                sleep_for,
            )
            await asyncio.sleep(sleep_for)

    breaker.record_failure()
    logger.warning("retry[%s] exhausted after %d attempts: %s", breaker.name, max_attempts, last_exc)
    return None


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
    breaker_state: Dict[str, str] = field(default_factory=dict)

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
        browser_mode: str = "headless",
        agent_id: str = "agent-bus-default",
        sign_events: bool = True,
        write_to_ledger: bool = True,
    ) -> None:
        self.hf_model = hf_model
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url.rstrip("/")
        self.prefer_local = prefer_local
        self.browser_mode = browser_mode
        self.agent_id = agent_id
        self.sign_events = sign_events
        self.write_to_ledger = write_to_ledger

        self._runtime = None
        self._scraper = None
        self._researcher = None
        self._backend = None
        self._signer = None
        self._ledger_bridge = None
        self._started = False
        self._event_log: List[BusEvent] = []
        self._http: Optional[Any] = None  # httpx.AsyncClient
        self._ollama_breaker = CircuitBreaker("ollama")
        self._hf_breaker = CircuitBreaker("huggingface")

    # -- lifecycle -----------------------------------------------------------

    async def start(self, *, headless: bool = True) -> None:
        """Start the bus (launches browser backend + scraper + HTTP + identity + ledger)."""
        from agents.web_scraper import WebScraper
        from agents.research_agent import ResearchAgent
        from agents.agent_bus_browser import make_backend

        try:
            import httpx

            self._http = httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
        except ImportError:
            logger.warning("httpx not installed — Ollama calls will be unavailable")
            self._http = None

        self._backend = make_backend(self.browser_mode)
        # "headed" mode forces visible browser; other modes honor caller's headless flag
        backend_headless = False if self.browser_mode == "headed" else headless
        await self._backend.launch(headless=backend_headless)
        self._runtime = self._backend.runtime
        self._scraper = WebScraper(self._runtime)
        self._researcher = ResearchAgent(self._scraper, max_sources=5)

        if self.sign_events:
            from agents.agent_bus_signing import EventSigner

            self._signer = EventSigner(self.agent_id)
            self._signer.initialize()

        if self.write_to_ledger:
            from agents.agent_bus_ledger import LedgerBridge

            self._ledger_bridge = LedgerBridge(self.agent_id)
            self._ledger_bridge.initialize()

        self._started = True
        BUS_LOG.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "AgentBus started (mode=%s, hf=%s, ollama=%s, signing=%s, ledger=%s)",
            self.browser_mode,
            self.hf_model,
            self.ollama_model,
            self._signer.algorithm if self._signer else "off",
            "on" if (self._ledger_bridge and self._ledger_bridge._ledger) else "off",
        )

    async def stop(self) -> None:
        """Stop the bus."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        if self._backend is not None:
            await self._backend.close()
            self._backend = None
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
        event.tokens_in = int(answer.get("tokens_in", 0) or 0)
        event.tokens_out = int(answer.get("tokens_out", 0) or 0)
        event.duration_seconds = time.monotonic() - start
        event.success = not answer.get("error")
        event.error = answer.get("error")
        event.breaker_state = self._breaker_snapshot()
        self._log_event(event)

        return {
            "question": question,
            "answer": answer["text"],
            "sources": sources,
            "provider": answer["provider"],
            "model": answer["model"],
            "tokens_in": event.tokens_in,
            "tokens_out": event.tokens_out,
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
        context = "\n\n".join(f"[{f.confidence:.0%}] {f.title}\n{f.relevant_text[:800]}" for f in report.findings[:5])

        prompt = (
            f"Summarize these research findings about '{query}' in 2-3 paragraphs. "
            f"Cite sources by title. Be concise and factual.\n\n{context}"
        )

        answer = await self._llm_generate(prompt)
        event.llm_provider = answer["provider"]
        event.llm_model = answer["model"]
        event.tokens_in = int(answer.get("tokens_in", 0) or 0)
        event.tokens_out = int(answer.get("tokens_out", 0) or 0)
        event.duration_seconds = time.monotonic() - start
        event.breaker_state = self._breaker_snapshot()
        self._log_event(event)

        return {
            "query": query,
            "summary": answer["text"],
            "findings": [{"title": f.title, "url": f.source_url, "confidence": f.confidence} for f in report.findings],
            "sources_checked": report.sources_checked,
            "words_read": report.total_words_read,
            "provider": answer["provider"],
            "tokens_in": event.tokens_in,
            "tokens_out": event.tokens_out,
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
        event.tokens_in = int(answer.get("tokens_in", 0) or 0)
        event.tokens_out = int(answer.get("tokens_out", 0) or 0)
        event.duration_seconds = time.monotonic() - start
        event.breaker_state = self._breaker_snapshot()
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
            "tokens_in": event.tokens_in,
            "tokens_out": event.tokens_out,
        }

    async def monitor(self, urls: List[str]) -> Dict[str, Any]:
        """Quick read of multiple sites with summaries."""
        self._require_started()
        summaries = await self._researcher.monitor_sites(urls)
        return {"sites": summaries, "count": len(summaries)}

    # -- team coordination ---------------------------------------------------

    # -- self-training -------------------------------------------------------

    def measure_performance(self) -> Optional[Dict[str, Any]]:
        """Compute a rolling perf window over recent events. Returns None if no data."""
        from agents.agent_bus_training import TrainingTrigger

        perf = TrainingTrigger().measure()
        if perf is None:
            return None
        return {
            "total": perf.total,
            "successes": perf.successes,
            "failures": perf.failures,
            "success_rate": round(perf.success_rate, 3),
            "avg_duration": round(perf.avg_duration, 2),
            "avg_tokens_out": round(perf.avg_tokens_out, 1),
            "breaker_open_count": perf.breaker_open_count,
            "needs_training": perf.needs_training,
        }

    async def maybe_train(self, *, dry_run: bool = False) -> Dict[str, Any]:
        """If recent perf is below threshold, trigger a self-training run.

        Returns {triggered: bool, perf: ..., report: ...}. Conservative by
        default: dry_run=True just reports what would happen.
        """
        from agents.agent_bus_training import TrainingTrigger

        trigger = TrainingTrigger()
        perf = trigger.measure()
        if perf is None:
            return {"triggered": False, "reason": "no_events"}
        if not trigger.should_trigger(perf):
            return {"triggered": False, "perf": perf.__dict__}
        report = trigger.trigger(perf, dry_run=dry_run)
        return {"triggered": True, "perf": perf.__dict__, "report": report}

    # -- self-extension ------------------------------------------------------

    @property
    def tools(self):
        """Lazy-init tool registry, available even before `start()` is called."""
        if not hasattr(self, "_tools") or self._tools is None:
            from agents.agent_bus_extensions import ToolRegistry

            self._tools = ToolRegistry()
        return self._tools

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        """Invoke a registered tool by name."""
        return await self.tools.call(name, **kwargs)

    async def generate_tool(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, str]] = None,
        *,
        attempts: int = 3,
    ) -> bool:
        """Use the bus's LLM to write a new tool, validate it, register it.

        Returns True on success. The generated source is persisted under
        agents/generated_tools/<name>.py.
        """
        self._require_started()
        from agents.agent_bus_extensions import ToolGenerator, ToolSpec

        spec = ToolSpec(name=name, description=description, parameters=parameters or {})
        gen = ToolGenerator(self, self.tools)
        return await gen.generate(spec, attempts=attempts)

    # -- team coordination ---------------------------------------------------

    async def team_decide(
        self,
        action: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        action_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ask the swarm for Byzantine consensus on an action.

        Only meaningful when browser_mode='swarm'; in other modes returns
        an automatic ALLOW so callers don't have to branch on mode.
        """
        self._require_started()
        from agents.agent_bus_team import TeamCoordinator

        if self.browser_mode != "swarm":
            return {"decision": "ALLOW", "votes": [], "confidence": 1.0, "reason": "non_swarm_mode"}
        coord = TeamCoordinator(self._backend)
        return await coord.team_decide(action_id or action, action, context)

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
        """Try Ollama local inference (async via httpx, retried, breaker-gated)."""
        if self._http is None:
            return None

        url = f"{self.ollama_url}/api/generate"
        payload = {"model": self.ollama_model, "prompt": prompt, "stream": False}

        async def _call() -> Dict[str, Any]:
            resp = await self._http.post(url, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.json()

        data = await _retry_with_backoff(
            _call,
            breaker=self._ollama_breaker,
            is_rate_limit=lambda e: getattr(e, "response", None) is not None
            and getattr(e.response, "status_code", 0) == 429,
        )
        if data is None:
            return None

        return {
            "text": data.get("response", ""),
            "provider": "ollama",
            "model": self.ollama_model,
            "tokens_in": int(data.get("prompt_eval_count", 0) or 0),
            "tokens_out": int(data.get("eval_count", 0) or 0),
        }

    async def _try_huggingface(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Try HuggingFace Inference API (sync SDK wrapped in to_thread, retried, breaker-gated)."""
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            return None

        def _is_rate_limit(exc: BaseException) -> bool:
            msg = str(exc).lower()
            return "429" in msg or "rate" in msg and "limit" in msg

        async def _call() -> Any:
            from huggingface_hub import InferenceClient

            def _sync_call() -> Any:
                client = InferenceClient(model=self.hf_model, token=hf_token, timeout=HTTP_TIMEOUT_SECONDS)
                return client.chat_completion(
                    messages=[{"role": "user", "content": prompt[:4000]}],
                    max_tokens=512,
                )

            return await asyncio.to_thread(_sync_call)

        resp = await _retry_with_backoff(
            _call,
            breaker=self._hf_breaker,
            is_rate_limit=_is_rate_limit,
        )
        if resp is None:
            return None

        try:
            text = resp.choices[0].message.content
        except (AttributeError, IndexError) as exc:
            logger.warning("HF response shape unexpected: %s", exc)
            return None
        if not text or not text.strip():
            return None

        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
        tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0

        return {
            "text": text.strip(),
            "provider": "huggingface",
            "model": self.hf_model,
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
        }

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

        record = event.to_dict()
        if self._signer is not None:
            sig, pk, alg = self._signer.sign(record)
            record["_sig"] = sig
            record["_pubkey"] = pk
            record["_sig_alg"] = alg
            record["_agent_id"] = self.agent_id
            record["_schema_version"] = SCHEMA_VERSION

        try:
            BUS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(BUS_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as exc:
            logger.warning("could not append to %s: %s", BUS_LOG, exc)

        if self._ledger_bridge is not None:
            self._ledger_bridge.write_event(
                task_type=event.task_type,
                action=event.task_type,
                target=event.query[:200],
                payload=record,
                decision="ALLOW" if event.success else "ERROR",
                score=None,
            )

    def _breaker_snapshot(self) -> Dict[str, str]:
        return {
            "ollama": self._ollama_breaker.state,
            "huggingface": self._hf_breaker.state,
        }

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("AgentBus not started — call await bus.start() first")

    @property
    def event_count(self) -> int:
        return len(self._event_log)

    @property
    def events(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._event_log]
