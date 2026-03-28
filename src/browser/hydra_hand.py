"""
HYDRA Hand — Multi-Headed Agentic Browser Squad
=================================================

Each HYDRA Head gets a "hand" of 5 browser fingers + 1 thumb (KO commander).
The 6 Sacred Tongues map to browser roles:

    KO (Thumb)  — Commander: orchestrates the squad, speaks results aloud
    AV (Index)  — Navigator: scouts URLs, follows links, discovers paths
    RU (Middle) — Policy:    checks safety, validates domains, blocks threats
    CA (Ring)   — Compute:   extracts data, runs JS, scrapes content
    UM (Pinky)  — Shadow:    stealth browsing, no fingerprints, incognito
    DR (Palm)   — Schema:    structures findings into knowledge graph nodes

Proximity model (how "close" a message/event feels):
    OWL    (async)     → email, background fetch     → AV tongue  (1.0s delay)
    KNOCK  (sync)      → direct request, needs reply  → CA tongue  (0.15s delay)
    ROCK   (interrupt) → urgent alert, threat detected → RU tongue  (0.0s delay)
    GHOST  (stealth)   → silent observation            → UM tongue  (0.3s delay)
    FORGE  (build)     → constructing output           → DR tongue  (0.5s delay)
    VOICE  (command)   → orchestrator decision          → KO tongue  (0.05s delay)

Features:
    - multi_action():       Send multiple fingers to different URLs in parallel
    - swarm_research():     Coordinate multiple hands across many queries
    - register_with_spine(): Plug into HydraSpine as a governed limb
    - ingest_to_mesh():     Auto-feed research results into SemanticMesh
    - Proximity throttling: ROCK fires instantly, OWL is gentle/slow

Usage:
    # Basic research
    hand = HydraHand(head_id="research-alpha")
    await hand.open()
    results = await hand.research("SCBE hyperbolic security competitors")
    await hand.close()

    # Multi-action dispatch
    async with HydraHand(head_id="multi") as hand:
        results = await hand.multi_action([
            {"tongue": "CA", "url": "https://arxiv.org", "action": "extract"},
            {"tongue": "AV", "url": "https://github.com", "action": "links"},
            {"tongue": "RU", "url": "https://example.com", "action": "navigate"},
        ])

    # Swarm research (multiple hands)
    async with HydraHand("alpha") as h1, HydraHand("beta") as h2:
        merged = await swarm_research([h1, h2], ["query A", "query B"])

    # Spine integration
    from hydra.spine import HydraSpine
    spine = HydraSpine()
    hand.register_with_spine(spine)

    # Mesh ingest
    nodes = await hand.ingest_to_mesh(results)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.browser.polly_vision import PollyVision, ObservationTier, PageObservation

logger = logging.getLogger("hydra-hand")


# ── Tongue Roles ─────────────────────────────────────────────────────


class Tongue(str, Enum):
    KO = "KO"  # Command / Orchestrate
    AV = "AV"  # Navigate / Scout
    RU = "RU"  # Policy / Safety
    CA = "CA"  # Compute / Extract
    UM = "UM"  # Shadow / Stealth
    DR = "DR"  # Schema / Structure


class Proximity(str, Enum):
    """How 'close' an event feels — maps to urgency."""

    OWL = "owl"  # Async background (email)
    KNOCK = "knock"  # Sync request (text message)
    ROCK = "rock"  # Interrupt/alert (repeated ping)
    GHOST = "ghost"  # Silent observation
    FORGE = "forge"  # Building/constructing
    VOICE = "voice"  # Command decision


TONGUE_PROXIMITY = {
    Tongue.AV: Proximity.OWL,
    Tongue.CA: Proximity.KNOCK,
    Tongue.RU: Proximity.ROCK,
    Tongue.UM: Proximity.GHOST,
    Tongue.DR: Proximity.FORGE,
    Tongue.KO: Proximity.VOICE,
}

# Phi-weighted priority (golden ratio scaling)
TONGUE_WEIGHT = {
    Tongue.KO: 1.000,
    Tongue.AV: 1.618,
    Tongue.RU: 2.618,
    Tongue.CA: 4.236,
    Tongue.UM: 6.854,
    Tongue.DR: 11.090,
}


# ── Finger (Single Browser Instance) ────────────────────────────────


@dataclass
class BrowsingResult:
    """Result from a single finger's action."""

    tongue: Tongue
    url: str
    title: str = ""
    text: str = ""
    links: List[str] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    risk_score: float = 0.0
    risk_decision: str = "ALLOW"
    metadata: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


@dataclass
class Finger:
    """One headless browser instance with a tongue role."""

    tongue: Tongue
    browser: Any = None  # Playwright browser instance
    page: Any = None  # Current page
    active: bool = False
    action_count: int = 0
    blocked_count: int = 0
    vision: Optional[PollyVision] = None  # Polly Vision observation window

    @property
    def proximity(self) -> Proximity:
        return TONGUE_PROXIMITY[self.tongue]

    @property
    def weight(self) -> float:
        return TONGUE_WEIGHT[self.tongue]

    async def open(self, playwright_instance):
        """Launch this finger's browser."""
        launch_args = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        }

        # UM (Shadow) gets extra stealth
        if self.tongue == Tongue.UM:
            launch_args["args"].extend(
                [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--incognito",
                ]
            )

        self.browser = await playwright_instance.chromium.launch(**launch_args)

        context_args = {}
        if self.tongue == Tongue.UM:
            context_args["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        context = await self.browser.new_context(**context_args)
        self.page = await context.new_page()
        self.active = True
        logger.info(
            "[%s] Finger opened (%s mode)", self.tongue.value, self.proximity.value
        )

    async def close(self):
        """Shut down this finger's browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
            self.active = False

    async def navigate(self, url: str, timeout: int = 15000) -> BrowsingResult:
        """Navigate to URL and return result."""
        start = time.monotonic()
        try:
            response = await self.page.goto(
                url, timeout=timeout, wait_until="domcontentloaded"
            )
            title = await self.page.title()
            self.action_count += 1
            return BrowsingResult(
                tongue=self.tongue,
                url=url,
                title=title,
                metadata={"status": response.status if response else 0},
                elapsed_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return BrowsingResult(
                tongue=self.tongue,
                url=url,
                metadata={"error": str(e)},
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

    async def extract_text(self, selector: str = "body") -> str:
        """Extract text content from current page."""
        try:
            el = await self.page.query_selector(selector)
            if el:
                return await el.inner_text()
            return ""
        except Exception:
            return ""

    async def extract_links(self) -> List[str]:
        """Extract all links from current page."""
        try:
            links = await self.page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.href).filter(h => h.startsWith('http'))",
            )
            return links[:100]  # Cap at 100
        except Exception:
            return []

    async def screenshot(self, path: str) -> str:
        """Take a screenshot of current page."""
        await self.page.screenshot(path=path, full_page=True)
        self.action_count += 1
        return path

    async def run_js(self, script: str) -> Any:
        """Execute JavaScript on current page."""
        return await self.page.evaluate(script)

    async def observe(
        self, force_screenshot: bool = False, reason: str = ""
    ) -> Optional[PageObservation]:
        """Observe the current page through PollyVision.

        Returns a PageObservation with accessibility tree, interactive
        elements, and optionally a screenshot — depending on the vision tier.
        Returns None if vision is not attached or page is unavailable.
        """
        if not self.vision or not self.page:
            return None
        return await self.vision.observe(
            self.page, force_screenshot=force_screenshot, reason=reason
        )


# ── Domain Safety (RU Finger's Job) ─────────────────────────────────

# Blocked domains (RU finger checks these)
BLOCKED_DOMAINS = {
    "malware.com",
    "phishing.example",
    "evil.corp",
}

# Trusted domains (bypass deep scanning)
TRUSTED_DOMAINS = {
    "github.com",
    "huggingface.co",
    "arxiv.org",
    "scholar.google.com",
    "stackoverflow.com",
    "docs.python.org",
    "pypi.org",
    "en.wikipedia.org",
    "developer.mozilla.org",
}


def check_domain_safety(url: str) -> tuple[str, float]:
    """Quick domain check. Returns (decision, risk_score)."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.lower()

    if any(blocked in domain for blocked in BLOCKED_DOMAINS):
        return "DENY", 1.0
    if any(trusted in domain for trusted in TRUSTED_DOMAINS):
        return "ALLOW", 0.0
    # Unknown domain — quarantine for review
    return "QUARANTINE", 0.5


# ── The Hand (Squad of 5 Fingers + Thumb) ────────────────────────────


class HydraHand:
    """
    A squad of 6 headless browsers, one per Sacred Tongue.

    The KO (thumb) orchestrates research tasks by:
    1. AV scouts URLs and discovers paths
    2. RU checks each URL for safety
    3. CA extracts data from approved URLs
    4. UM handles anything needing stealth
    5. DR structures findings into mesh-ready format
    6. KO synthesizes and returns the final result
    """

    def __init__(
        self,
        head_id: str = "default",
        vision_tier: ObservationTier = ObservationTier.TIER_2,
    ):
        self.head_id = head_id
        self.vision_tier = vision_tier
        self.fingers: Dict[Tongue, Finger] = {
            t: Finger(tongue=t, vision=PollyVision(tier=vision_tier)) for t in Tongue
        }
        self._playwright = None
        self._open = False

    async def open(self):
        """Open all fingers (launch 6 browser instances)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run:\n"
                "  pip install playwright && playwright install chromium"
            )

        self._playwright = await async_playwright().__aenter__()

        # Open all fingers in parallel
        await asyncio.gather(*[f.open(self._playwright) for f in self.fingers.values()])
        self._open = True
        logger.info("[%s] Hand opened — 6 fingers active", self.head_id)

    async def close(self):
        """Close all fingers."""
        await asyncio.gather(*[f.close() for f in self.fingers.values()])
        if self._playwright:
            await self._playwright.__aexit__(None, None, None)
            self._playwright = None
        self._open = False
        logger.info("[%s] Hand closed", self.head_id)

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *args):
        await self.close()

    def finger(self, tongue: Tongue) -> Finger:
        return self.fingers[tongue]

    # ── Research Pipeline ────────────────────────────────────────────

    async def research(
        self,
        query: str,
        max_urls: int = 5,
        search_engine: str = "https://www.google.com/search?q=",
    ) -> Dict[str, Any]:
        """
        Full research pipeline using all 6 fingers:

        1. AV navigates to search engine, discovers URLs
        2. RU checks each URL for safety
        3. CA extracts content from safe URLs (parallel)
        4. UM handles any quarantined URLs via stealth
        5. DR structures everything into a research report
        6. KO returns the synthesized result
        """
        start = time.monotonic()
        report = {
            "query": query,
            "head_id": self.head_id,
            "urls_discovered": [],
            "urls_safe": [],
            "urls_blocked": [],
            "urls_quarantined": [],
            "extractions": [],
            "structured": {},
            "elapsed_ms": 0,
        }

        # Step 1: AV scouts — find URLs
        av = self.finger(Tongue.AV)
        search_url = search_engine + query.replace(" ", "+")
        await av.navigate(search_url)
        all_links = await av.extract_links()

        # Filter to likely-useful links (skip google internals, etc.)
        candidate_urls = [
            link
            for link in all_links
            if not any(
                skip in link
                for skip in [
                    "google.com/search",
                    "accounts.google",
                    "support.google",
                    "maps.google",
                    "translate.google",
                    "webcache.google",
                ]
            )
        ][
            : max_urls * 2
        ]  # Get extras in case some are blocked

        report["urls_discovered"] = candidate_urls

        # Step 2: RU checks safety
        safe_urls = []
        for url in candidate_urls:
            decision, risk = check_domain_safety(url)
            if decision == "ALLOW":
                safe_urls.append(url)
                report["urls_safe"].append(url)
            elif decision == "DENY":
                report["urls_blocked"].append(url)
            else:
                report["urls_quarantined"].append(url)

            if len(safe_urls) >= max_urls:
                break

        # Step 3: CA extracts from safe URLs (with PollyVision perception)
        ca = self.finger(Tongue.CA)
        extractions = []
        for url in safe_urls[:max_urls]:
            nav_result = await ca.navigate(url)
            if nav_result.metadata.get("status", 0) == 200 or nav_result.title:
                # Use PollyVision observation when available (structured perception)
                obs = await ca.observe(reason=f"research:{query[:40]}")
                if obs:
                    extractions.append(
                        {
                            "url": url,
                            "title": obs.title or nav_result.title,
                            "text": obs.accessibility_tree[:2000],
                            "page_summary": obs.page_summary,
                            "element_count": obs.element_count,
                            "has_screenshot": obs.has_screenshot,
                            "content_hash": obs.content_hash,
                            "token_estimate": obs.token_estimate,
                            "elapsed_ms": nav_result.elapsed_ms + obs.elapsed_ms,
                        }
                    )
                else:
                    # Fallback: blind text extraction
                    text = await ca.extract_text()
                    extractions.append(
                        {
                            "url": url,
                            "title": nav_result.title,
                            "text": text[:2000],
                            "elapsed_ms": nav_result.elapsed_ms,
                        }
                    )

        report["extractions"] = extractions

        # Step 4: UM handles quarantined URLs via stealth (if any)
        if report["urls_quarantined"]:
            um = self.finger(Tongue.UM)
            for url in report["urls_quarantined"][:2]:  # Max 2 stealth visits
                nav_result = await um.navigate(url)
                if nav_result.title:
                    obs = await um.observe(reason="stealth-quarantined")
                    if obs:
                        extractions.append(
                            {
                                "url": url,
                                "title": obs.title or nav_result.title,
                                "text": obs.accessibility_tree[:1000],
                                "page_summary": obs.page_summary,
                                "source": "stealth",
                                "content_hash": obs.content_hash,
                                "elapsed_ms": nav_result.elapsed_ms + obs.elapsed_ms,
                            }
                        )
                    else:
                        text = await um.extract_text()
                        extractions.append(
                            {
                                "url": url,
                                "title": nav_result.title,
                                "text": text[:1000],
                                "source": "stealth",
                                "elapsed_ms": nav_result.elapsed_ms,
                            }
                        )

        # Step 5: DR structures into knowledge-ready format
        structured = {
            "topic": query,
            "sources": len(extractions),
            "key_findings": [],
            "mesh_nodes": [],
        }

        for ext in extractions:
            # Create a mesh-ready node descriptor
            node_hash = hashlib.sha256(ext["url"].encode()).hexdigest()[:12]
            structured["mesh_nodes"].append(
                {
                    "id": f"research_{node_hash}",
                    "label": ext["title"][:100] if ext["title"] else ext["url"][:100],
                    "content": ext["text"][:500],
                    "source_url": ext["url"],
                    "node_type": "SOURCE",
                }
            )

        report["structured"] = structured
        report["elapsed_ms"] = (time.monotonic() - start) * 1000

        logger.info(
            "[%s] Research complete: %d sources, %.0fms",
            self.head_id,
            len(extractions),
            report["elapsed_ms"],
        )
        return report

    async def research_and_funnel(
        self,
        query: str,
        max_urls: int = 5,
        topics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Research a query and automatically push findings to cloud storage.

        Combines research() + ResearchFunnel.push() in one call.
        Findings go to local JSONL, Notion (if configured), and HuggingFace (if configured).
        """
        from src.browser.research_funnel import ResearchFunnel

        report = await self.research(query, max_urls=max_urls)
        funnel = ResearchFunnel()
        receipt = await funnel.push(report, topics=topics)
        report["funnel_receipt"] = {
            "run_id": receipt.run_id,
            "local_path": receipt.local_path,
            "notion_url": receipt.notion_url,
            "hf_committed": receipt.hf_committed,
            "errors": receipt.errors,
        }
        return report

    # ── Status ───────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Hand status summary."""
        return {
            "head_id": self.head_id,
            "open": self._open,
            "fingers": {
                t.value: {
                    "active": f.active,
                    "proximity": f.proximity.value,
                    "weight": f.weight,
                    "actions": f.action_count,
                    "blocked": f.blocked_count,
                }
                for t, f in self.fingers.items()
            },
        }

    # ── Proximity-Based Throttling ────────────────────────────────────

    @staticmethod
    def _throttle_delay(proximity: Proximity) -> float:
        """Return delay in seconds based on proximity urgency.

        OWL actions are slow/gentle (background fetch).
        ROCK actions are fast/urgent (threat response).

        Mapping:
            ROCK   -> 0.0s   (immediate, urgent alert)
            VOICE  -> 0.05s  (orchestrator, near-instant)
            KNOCK  -> 0.15s  (sync request, brief pause)
            GHOST  -> 0.3s   (stealth, deliberate pacing)
            FORGE  -> 0.5s   (building, measured pace)
            OWL    -> 1.0s   (async background, gentle)
        """
        return {
            Proximity.ROCK: 0.0,
            Proximity.VOICE: 0.05,
            Proximity.KNOCK: 0.15,
            Proximity.GHOST: 0.3,
            Proximity.FORGE: 0.5,
            Proximity.OWL: 1.0,
        }.get(proximity, 0.2)

    # ── Multi-Action Dispatch ─────────────────────────────────────────

    async def multi_action(self, tasks: List[dict]) -> List[BrowsingResult]:
        """Send multiple fingers to different URLs simultaneously.

        Each task dict specifies which tongue/finger to use and what to do:
            {
                "tongue": "CA",       # Sacred Tongue to use (KO/AV/RU/CA/UM/DR)
                "url": "https://...", # Target URL
                "action": "extract",  # Action: navigate | extract | screenshot | links | js
                "selector": "body",   # CSS selector (for extract action)
                "script": "...",      # JavaScript (for js action)
                "screenshot_path": "...",  # File path (for screenshot action)
            }

        All tasks run in parallel, respecting proximity-based throttling.
        RU (ROCK proximity) tasks fire immediately; OWL tasks are gentle.

        Returns a list of BrowsingResult, one per task.
        """
        if not self._open:
            raise RuntimeError("Hand not open. Call await hand.open() first.")

        async def _run_task(task: dict) -> BrowsingResult:
            tongue_str = task.get("tongue", "CA").upper()
            try:
                tongue = Tongue(tongue_str)
            except ValueError:
                return BrowsingResult(
                    tongue=Tongue.CA,
                    url=task.get("url", ""),
                    metadata={"error": f"Unknown tongue: {tongue_str}"},
                )

            finger = self.fingers[tongue]
            if not finger.active:
                return BrowsingResult(
                    tongue=tongue,
                    url=task.get("url", ""),
                    metadata={"error": f"Finger {tongue_str} not active"},
                )

            # Proximity-based throttle: OWL waits longer, ROCK fires immediately
            delay = self._throttle_delay(finger.proximity)
            if delay > 0:
                await asyncio.sleep(delay)

            url = task.get("url", "")
            action = task.get("action", "navigate").lower()
            start = time.monotonic()

            # RU policy check first (unless this IS the RU finger)
            if tongue != Tongue.RU and url:
                decision, risk = check_domain_safety(url)
                if decision == "DENY":
                    finger.blocked_count += 1
                    return BrowsingResult(
                        tongue=tongue,
                        url=url,
                        risk_score=risk,
                        risk_decision="DENY",
                        metadata={"blocked": True},
                        elapsed_ms=(time.monotonic() - start) * 1000,
                    )

            # Navigate to URL if needed
            if url:
                nav = await finger.navigate(url)
                if nav.metadata.get("error"):
                    return nav

            # Execute the requested action
            result = BrowsingResult(tongue=tongue, url=url)

            if action == "extract":
                selector = task.get("selector", "body")
                result.text = await finger.extract_text(selector)
                result.title = await finger.page.title() if finger.page else ""
            elif action == "links":
                result.links = await finger.extract_links()
                result.title = await finger.page.title() if finger.page else ""
            elif action == "screenshot":
                path = task.get("screenshot_path", f"screenshot_{tongue_str}.png")
                result.screenshot_path = await finger.screenshot(path)
            elif action == "js":
                script = task.get("script", "document.title")
                js_result = await finger.run_js(script)
                result.metadata["js_result"] = js_result
            else:
                # Default: just navigate (already done above)
                result.title = await finger.page.title() if finger.page else ""

            result.elapsed_ms = (time.monotonic() - start) * 1000
            return result

        # Fire all tasks in parallel
        results = await asyncio.gather(
            *[_run_task(t) for t in tasks],
            return_exceptions=True,
        )

        # Convert exceptions to BrowsingResult
        final: List[BrowsingResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                tongue_str = tasks[i].get("tongue", "CA").upper()
                try:
                    tongue = Tongue(tongue_str)
                except ValueError:
                    tongue = Tongue.CA
                final.append(
                    BrowsingResult(
                        tongue=tongue,
                        url=tasks[i].get("url", ""),
                        metadata={"error": str(r)},
                    )
                )
            else:
                final.append(r)

        logger.info(
            "[%s] multi_action complete: %d tasks, %d successful",
            self.head_id,
            len(tasks),
            sum(1 for r in final if not r.metadata.get("error")),
        )
        return final

    # ── HydraSpine Integration ────────────────────────────────────────

    def register_with_spine(self, spine) -> str:
        """Register this hand as a limb on a HydraSpine.

        The HydraSpine expects limbs with `limb_id` and `limb_type`
        attributes, plus an async `execute()` method.  This method
        wraps the hand in a thin adapter and calls `spine.connect_limb()`.

        Args:
            spine: A HydraSpine instance (from hydra.spine).

        Returns:
            The limb_id assigned by the spine.
        """
        adapter = _HandLimbAdapter(self)
        return spine.connect_limb(adapter)

    # ── Mesh Ingest ───────────────────────────────────────────────────

    async def ingest_to_mesh(
        self,
        results: Dict[str, Any],
        mesh=None,
        db_path: str = "semantic_mesh.db",
    ) -> list:
        """Ingest research results into the SemanticMesh knowledge graph.

        Takes the output of `research()` or `swarm_research()` and feeds
        each extraction as a governed node into the SemanticMesh.

        Args:
            results: Dict from research() containing "structured"/"extractions".
            mesh: Optional pre-existing SemanticMesh instance.
                  If None, attempts to import and create one.
            db_path: Database path for SemanticMesh (used only if mesh is None).

        Returns:
            A list of dicts, each with "node_id", "label", "source_url".
        """
        # Resolve or create mesh
        if mesh is None:
            try:
                from src.mcp_server.semantic_mesh import SemanticMesh

                mesh = SemanticMesh(db_path)
            except ImportError:
                logger.warning("SemanticMesh not available; skipping ingest")
                return []

        ingested = []
        mesh_nodes = results.get("structured", {}).get("mesh_nodes", [])
        extractions = results.get("extractions", [])

        # Merge mesh_nodes and extractions for comprehensive coverage
        items_to_ingest = []

        for node in mesh_nodes:
            items_to_ingest.append(
                {
                    "content": node.get("content", ""),
                    "label": node.get("label", ""),
                    "source_url": node.get("source_url", ""),
                    "node_type": node.get("node_type", "SOURCE"),
                }
            )

        # Also ingest any extractions not already represented
        existing_urls = {item["source_url"] for item in items_to_ingest}
        for ext in extractions:
            if ext.get("url") not in existing_urls:
                items_to_ingest.append(
                    {
                        "content": ext.get("text", "")[:500],
                        "label": ext.get("title", ext.get("url", ""))[:100],
                        "source_url": ext.get("url", ""),
                        "node_type": "SOURCE",
                    }
                )

        # Collect node IDs for cross-linking
        created_ids = []

        for item in items_to_ingest:
            try:
                result = mesh.ingest(
                    content=item["content"],
                    node_type=item["node_type"],
                    label=item["label"],
                    source=f"hydra-hand:{self.head_id}",
                    connect_to=created_ids[-3:] if created_ids else None,
                )
                node_id = result.get("node_id", "")
                created_ids.append(node_id)
                ingested.append(
                    {
                        "node_id": node_id,
                        "label": item["label"],
                        "source_url": item["source_url"],
                    }
                )
            except Exception as e:
                logger.warning("Mesh ingest failed for %s: %s", item["label"][:30], e)

        logger.info(
            "[%s] Mesh ingest: %d nodes created from %d items",
            self.head_id,
            len(ingested),
            len(items_to_ingest),
        )
        return ingested


# ── Hand-to-Limb Adapter (for HydraSpine integration) ────────────────


class _HandLimbAdapter:
    """Thin adapter that lets a HydraHand register as a HydraLimb.

    The HydraSpine.connect_limb() method expects objects with:
        - limb_id: str
        - limb_type: str
        - execute(action, target, params) -> dict  (async)

    This adapter translates spine execute() calls into finger actions.
    """

    limb_type = "hydra_hand"

    def __init__(self, hand: HydraHand):
        self.hand = hand
        self.limb_id = f"hand-{hand.head_id}"

    async def execute(
        self, action: str, target: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route spine execute calls to appropriate finger actions."""
        tongue_str = params.get("tongue", "CA").upper()
        try:
            tongue = Tongue(tongue_str)
        except ValueError:
            tongue = Tongue.CA

        finger = self.hand.fingers.get(tongue)
        if not finger or not finger.active:
            return {"success": False, "error": f"Finger {tongue_str} not active"}

        # Proximity-based throttle
        delay = HydraHand._throttle_delay(finger.proximity)
        if delay > 0:
            await asyncio.sleep(delay)

        if action == "navigate":
            result = await finger.navigate(target)
            return {
                "success": not result.metadata.get("error"),
                "title": result.title,
                "url": target,
                "elapsed_ms": result.elapsed_ms,
                "tongue": tongue_str,
            }
        elif action == "extract" or action == "get_content":
            selector = params.get("selector", "body")
            text = await finger.extract_text(selector)
            return {"success": True, "text": text[:2000], "tongue": tongue_str}
        elif action == "screenshot":
            path = params.get("path", f"screenshot_{tongue_str}.png")
            await finger.screenshot(path)
            return {"success": True, "path": path, "tongue": tongue_str}
        elif action == "links":
            links = await finger.extract_links()
            return {"success": True, "links": links, "tongue": tongue_str}
        elif action == "js":
            script = params.get("script", "document.title")
            js_result = await finger.run_js(script)
            return {"success": True, "result": js_result, "tongue": tongue_str}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def activate(self) -> bool:
        if not self.hand._open:
            await self.hand.open()
        return True

    async def deactivate(self) -> None:
        await self.hand.close()


# ── Swarm Research (multi-hand coordination) ──────────────────────────


async def swarm_research(
    hands: List[HydraHand],
    queries: List[str],
    max_urls_per_query: int = 3,
    merge_strategy: str = "interleave",
) -> dict:
    """Distribute research queries across multiple HydraHands and merge results.

    This is the multi-hand coordination layer: each hand is a full
    6-finger squad, and this function distributes queries round-robin
    across all available hands, runs them in parallel, then merges.

    Args:
        hands: List of open HydraHand instances.
        queries: List of search queries to research.
        max_urls_per_query: Max URLs to extract per query.
        merge_strategy: How to merge results:
            - "interleave": Round-robin merge of extractions.
            - "concatenate": Simple concatenation.
            - "deduplicate": Concatenate and remove duplicate URLs.

    Returns:
        A merged research dict with:
        - "queries": list of original queries
        - "hands_used": number of hands
        - "per_query": list of individual research results
        - "merged_extractions": combined extractions
        - "merged_mesh_nodes": combined mesh-ready nodes
        - "total_sources": total extraction count
        - "elapsed_ms": wall-clock time
    """
    if not hands:
        return {"error": "No hands provided", "queries": queries}

    start = time.monotonic()

    # Assign queries round-robin to hands
    assignments: Dict[int, List[str]] = {i: [] for i in range(len(hands))}
    for qi, query in enumerate(queries):
        hand_idx = qi % len(hands)
        assignments[hand_idx].append(query)

    # Run all research tasks in parallel
    async def _research_batch(
        hand: HydraHand, batch_queries: List[str]
    ) -> List[Dict[str, Any]]:
        results = []
        for q in batch_queries:
            try:
                r = await hand.research(q, max_urls=max_urls_per_query)
                results.append(r)
            except Exception as e:
                results.append(
                    {
                        "query": q,
                        "head_id": hand.head_id,
                        "error": str(e),
                        "extractions": [],
                        "structured": {"mesh_nodes": []},
                    }
                )
        return results

    all_tasks = []
    for hand_idx, batch in assignments.items():
        if batch:
            all_tasks.append(_research_batch(hands[hand_idx], batch))

    batch_results = await asyncio.gather(*all_tasks, return_exceptions=True)

    # Flatten results
    per_query: List[Dict[str, Any]] = []
    for batch in batch_results:
        if isinstance(batch, Exception):
            per_query.append(
                {
                    "error": str(batch),
                    "extractions": [],
                    "structured": {"mesh_nodes": []},
                }
            )
        else:
            per_query.extend(batch)

    # Merge extractions
    all_extractions = []
    all_mesh_nodes = []
    for r in per_query:
        all_extractions.extend(r.get("extractions", []))
        all_mesh_nodes.extend(r.get("structured", {}).get("mesh_nodes", []))

    if merge_strategy == "deduplicate":
        seen_urls = set()
        deduped = []
        for ext in all_extractions:
            url = ext.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append(ext)
        all_extractions = deduped

        seen_node_urls = set()
        deduped_nodes = []
        for node in all_mesh_nodes:
            url = node.get("source_url", "")
            if url not in seen_node_urls:
                seen_node_urls.add(url)
                deduped_nodes.append(node)
        all_mesh_nodes = deduped_nodes
    elif merge_strategy == "interleave":
        # Interleave extractions from different queries
        by_query: List[List[dict]] = [r.get("extractions", []) for r in per_query]
        interleaved = []
        max_len = max((len(lst) for lst in by_query), default=0)
        for i in range(max_len):
            for lst in by_query:
                if i < len(lst):
                    interleaved.append(lst[i])
        all_extractions = interleaved

    elapsed = (time.monotonic() - start) * 1000

    logger.info(
        "swarm_research complete: %d queries across %d hands, %d sources, %.0fms",
        len(queries),
        len(hands),
        len(all_extractions),
        elapsed,
    )

    return {
        "queries": queries,
        "hands_used": len(hands),
        "per_query": per_query,
        "merged_extractions": all_extractions,
        "merged_mesh_nodes": all_mesh_nodes,
        "total_sources": len(all_extractions),
        "elapsed_ms": elapsed,
    }


# ── CLI Demo ─────────────────────────────────────────────────────────


async def _demo():
    """Quick demo of the HYDRA Hand."""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("  HYDRA Hand — Multi-Headed Browser Squad Demo")
    print("=" * 60 + "\n")

    async with HydraHand(head_id="demo-alpha") as hand:
        print("Hand status:", hand.status())
        print()

        # Research something
        result = await hand.research("SCBE hyperbolic AI safety", max_urls=3)

        print(f"Query: {result['query']}")
        print(f"URLs discovered: {len(result['urls_discovered'])}")
        print(f"URLs safe: {len(result['urls_safe'])}")
        print(f"URLs blocked: {len(result['urls_blocked'])}")
        print(f"Extractions: {len(result['extractions'])}")
        print(f"Time: {result['elapsed_ms']:.0f}ms")
        print()

        for ext in result["extractions"]:
            print(f"  [{ext.get('source', 'direct')}] {ext['title'][:60]}")
            print(f"    {ext['url'][:80]}")
            print()

        print(f"Mesh nodes ready: {len(result['structured']['mesh_nodes'])}")


if __name__ == "__main__":
    asyncio.run(_demo())
