"""
HYDRA Self-Healing Workflow
============================

Two planes:
  GOVERNANCE PLANE  — weights (phi-scaled Sacred Tongues, SCBE 14-layer)
  FUNCTION PLANE    — functions (browser, API, file I/O, training, inference)

Connected by a self-healing mesh that:
  1. Heartbeats every service on a schedule
  2. Detects failures and routes around them
  3. Uses Telegram for human-in-the-loop escalation
  4. Stores state across Drive/Obsidian/Notion
  5. Runs compute on Colab/Vertex/Cloud Run
  6. Tunnels AI-to-AI via secure sessions

Service Registry:
  NOTES     — Obsidian (local), Notion (cloud), Google Drive (cloud)
  COMPUTE   — Colab (free GPU), Vertex AI (prod GPU), Cloud Run (API)
  WORKFLOW  — n8n (self-hosted), Zapier (cloud)
  MESSAGING — Telegram (human), WebSocket (agent-to-agent)
  AI        — Claude API, ChatGPT API, HuggingFace Inference
  BROWSER   — Playwright (local), PlaywrightCloud (remote)
  STORAGE   — SQLite (Switchboard), Firebase, S3/GCS

Usage:
    from hydra.self_healing import SelfHealingMesh

    mesh = SelfHealingMesh()
    await mesh.boot()          # Heartbeat all services
    await mesh.run_workflow("research", {"goal": "..."})
    mesh.status()              # Show service health
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional


# ---------------------------------------------------------------------------
#  Service Health
# ---------------------------------------------------------------------------

class ServiceHealth(str, Enum):
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class ServiceCategory(str, Enum):
    NOTES = "notes"
    COMPUTE = "compute"
    WORKFLOW = "workflow"
    MESSAGING = "messaging"
    AI = "ai"
    BROWSER = "browser"
    STORAGE = "storage"


class CircuitState(str, Enum):
    """Per-service circuit breaker (from AI Workflow Architect retryService)."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing - skip requests
    HALF_OPEN = "half_open" # Testing recovery


# Retryable error patterns (from AI Workflow Architect)
RETRYABLE_PATTERNS = [
    re.compile(r"rate.?limit", re.I),
    re.compile(r"timeout", re.I),
    re.compile(r"5\d\d", re.I),
    re.compile(r"overloaded", re.I),
    re.compile(r"capacity", re.I),
    re.compile(r"temporarily", re.I),
    re.compile(r"ECONNRESET", re.I),
    re.compile(r"ETIMEDOUT", re.I),
]
NON_RETRYABLE_PATTERNS = [
    re.compile(r"auth", re.I),
    re.compile(r"invalid.?key", re.I),
    re.compile(r"permission", re.I),
    re.compile(r"not.?configured", re.I),
    re.compile(r"401|403", re.I),
]


def _is_retryable(error: str) -> bool:
    """Classify whether an error is worth retrying."""
    for pat in NON_RETRYABLE_PATTERNS:
        if pat.search(error):
            return False
    for pat in RETRYABLE_PATTERNS:
        if pat.search(error):
            return True
    return True  # Default: retry unknown errors


@dataclass
class DecisionTrace:
    """Structured audit of each heal/route decision (from AI Workflow Architect)."""
    timestamp: float
    service: str
    action: str  # heal_attempt, fallback_route, circuit_trip, circuit_reset, approval_wait
    confidence: float  # 0.0-1.0
    reasoning: str
    alternatives: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    resolved_to: str = ""


@dataclass
class ServiceNode:
    """One service in the mesh."""
    name: str
    category: ServiceCategory
    health: ServiceHealth = ServiceHealth.UNKNOWN
    url: str = ""
    last_check: float = 0.0
    last_ok: float = 0.0
    consecutive_failures: int = 0
    latency_ms: float = 0.0
    error: str = ""
    fallback: Optional[str] = None  # Name of primary fallback service
    fallback_chain: List[str] = field(default_factory=list)  # Ordered fallback list
    _check_fn: Optional[Callable] = field(default=None, repr=False)
    # Circuit breaker state (from AI Workflow Architect)
    circuit: CircuitState = CircuitState.CLOSED
    circuit_opened_at: float = 0.0
    circuit_cooldown_s: float = 60.0  # Seconds before half-open retry

    def is_alive(self) -> bool:
        return self.health in (ServiceHealth.UP, ServiceHealth.DEGRADED)

    @property
    def circuit_ready(self) -> bool:
        """True if circuit is closed or cooldown expired (half-open)."""
        if self.circuit == CircuitState.CLOSED:
            return True
        if self.circuit == CircuitState.OPEN:
            elapsed = time.time() - self.circuit_opened_at
            return elapsed >= self.circuit_cooldown_s
        return True  # half_open = allow one test request


# ---------------------------------------------------------------------------
#  Self-Healing Mesh
# ---------------------------------------------------------------------------

class SelfHealingMesh:
    """Monitors all services, detects failures, routes around them.

    The two planes:
      GOVERNANCE PLANE: SCBE API (Cloud Run) — decisions have weights
      FUNCTION PLANE: Everything else — actions are functions, not weights

    Self-healing rules:
      1. If a service fails 3x, switch to its fallback
      2. If Telegram is up, alert the human
      3. If a note service fails, try the next one (Obsidian -> Notion -> Drive)
      4. If compute fails, fall back (Vertex -> Colab -> local)
      5. If AI fails, try another provider (Claude -> GPT -> HF -> local)
      6. Every 60s, retry downed services to see if they recovered
    """

    # Circuit breaker threshold (from AI Workflow Architect: 5 failures)
    CIRCUIT_FAILURE_THRESHOLD = 5
    # Confidence below this triggers approval wait (from AI Workflow Architect: 0.7)
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self):
        self.services: Dict[str, ServiceNode] = {}
        self.heal_log: List[Dict[str, Any]] = []
        self.decision_traces: List[DecisionTrace] = []
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._register_all_services()

    def _register_all_services(self) -> None:
        """Register all known services with their health checks and fallbacks.

        Ordered fallback chains (from AI Workflow Architect retryService.ts):
        Each service has a priority-ordered list of alternatives.
        """

        # --- NOTES ---
        self._add("obsidian", ServiceCategory.NOTES,
                   fallback="notion",
                   fallback_chain=["notion", "google_drive"],
                   check=self._check_obsidian)
        self._add("notion", ServiceCategory.NOTES,
                   url="https://api.notion.com/v1/users/me",
                   fallback="google_drive",
                   fallback_chain=["google_drive", "obsidian"],
                   check=self._check_notion)
        self._add("google_drive", ServiceCategory.NOTES,
                   fallback="obsidian",
                   fallback_chain=["obsidian", "notion"],
                   check=self._check_google_drive)

        # --- COMPUTE ---
        self._add("colab", ServiceCategory.COMPUTE,
                   url=os.environ.get("COLAB_API_URL", ""),
                   fallback="vertex",
                   fallback_chain=["vertex", "cloud_run"],
                   check=self._check_url_health)
        self._add("vertex", ServiceCategory.COMPUTE,
                   fallback="cloud_run",
                   fallback_chain=["cloud_run", "colab"],
                   check=self._check_vertex)
        self._add("cloud_run", ServiceCategory.COMPUTE,
                   url="https://scbe-api-956103948282.us-central1.run.app/v1/health",
                   fallback="colab",
                   fallback_chain=["colab", "vertex"],
                   check=self._check_url_health)

        # --- WORKFLOW ---
        self._add("n8n", ServiceCategory.WORKFLOW,
                   url=os.environ.get("N8N_BRIDGE_URL", "http://127.0.0.1:8001") + "/health",
                   fallback="zapier",
                   fallback_chain=["zapier"],
                   check=self._check_url_health)
        self._add("zapier", ServiceCategory.WORKFLOW,
                   fallback="n8n",
                   fallback_chain=["n8n"],
                   check=self._check_zapier)

        # --- MESSAGING ---
        self._add("telegram", ServiceCategory.MESSAGING,
                   url=f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', '')}/getMe",
                   fallback="websocket",
                   fallback_chain=["websocket"],
                   check=self._check_url_health)
        self._add("websocket", ServiceCategory.MESSAGING,
                   fallback="telegram",
                   fallback_chain=["telegram"],
                   check=self._check_websocket)

        # --- AI PROVIDERS (ordered like Workflow Architect's FALLBACK_CHAINS) ---
        self._add("claude", ServiceCategory.AI,
                   fallback="chatgpt",
                   fallback_chain=["chatgpt", "huggingface"],
                   check=self._check_claude)
        self._add("chatgpt", ServiceCategory.AI,
                   fallback="huggingface",
                   fallback_chain=["claude", "huggingface"],
                   check=self._check_chatgpt)
        self._add("huggingface", ServiceCategory.AI,
                   url="https://huggingface.co/api/whoami-v2",
                   fallback="claude",
                   fallback_chain=["claude", "chatgpt"],
                   check=self._check_hf)

        # --- BROWSER ---
        self._add("playwright_local", ServiceCategory.BROWSER,
                   fallback="playwright_cloud",
                   fallback_chain=["playwright_cloud"],
                   check=self._check_playwright)
        self._add("playwright_cloud", ServiceCategory.BROWSER,
                   fallback="playwright_local",
                   fallback_chain=["playwright_local"],
                   check=self._check_playwright_cloud)

        # --- STORAGE ---
        self._add("switchboard", ServiceCategory.STORAGE,
                   fallback="firebase",
                   fallback_chain=["firebase"],
                   check=self._check_switchboard)
        self._add("firebase", ServiceCategory.STORAGE,
                   fallback="switchboard",
                   fallback_chain=["switchboard"],
                   check=self._check_firebase)

    def _add(self, name: str, category: ServiceCategory,
             url: str = "", fallback: str = None,
             fallback_chain: List[str] = None,
             check: Callable = None) -> None:
        self.services[name] = ServiceNode(
            name=name, category=category, url=url,
            fallback=fallback,
            fallback_chain=fallback_chain or [],
            _check_fn=check,
        )

    # ------------------------------------------------------------------
    #  Boot & Heartbeat
    # ------------------------------------------------------------------

    async def boot(self) -> Dict[str, str]:
        """Heartbeat all services and return their health."""
        results = {}
        tasks = []
        names = []

        for name, svc in self.services.items():
            names.append(name)
            tasks.append(self._check_service(name))

        done = await asyncio.gather(*tasks, return_exceptions=True)
        for i, name in enumerate(names):
            svc = self.services[name]
            results[name] = svc.health.value

        self._running = True
        # Start background heartbeat
        if not self._heartbeat_task or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        return results

    async def shutdown(self) -> None:
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def _heartbeat_loop(self) -> None:
        """Re-check all services every 60 seconds. Retry downed ones."""
        while self._running:
            await asyncio.sleep(60)
            for name in list(self.services.keys()):
                await self._check_service(name)

            # Self-heal: retry downed services
            for name, svc in self.services.items():
                if svc.health == ServiceHealth.DOWN and svc.consecutive_failures >= 3:
                    await self._attempt_heal(name)

    async def _check_service(self, name: str) -> ServiceHealth:
        """Run the health check for a single service with circuit breaker."""
        svc = self.services.get(name)
        if not svc:
            return ServiceHealth.UNKNOWN

        # Circuit breaker: skip check if circuit is open and cooldown not expired
        if svc.circuit == CircuitState.OPEN and not svc.circuit_ready:
            return svc.health

        # If cooldown expired, move to half-open for a test request
        if svc.circuit == CircuitState.OPEN and svc.circuit_ready:
            svc.circuit = CircuitState.HALF_OPEN

        t0 = time.time()
        svc.last_check = t0

        try:
            if svc._check_fn:
                health = await svc._check_fn(svc)
            else:
                health = ServiceHealth.UNKNOWN

            svc.latency_ms = round((time.time() - t0) * 1000, 1)
            svc.health = health

            if health in (ServiceHealth.UP, ServiceHealth.DEGRADED):
                svc.last_ok = time.time()
                svc.consecutive_failures = 0
                svc.error = ""
                # Reset circuit on success
                if svc.circuit != CircuitState.CLOSED:
                    self._trace(svc.name, "circuit_reset", 1.0,
                                f"Service recovered after {svc.circuit.value}")
                    svc.circuit = CircuitState.CLOSED
            else:
                svc.consecutive_failures += 1
                self._maybe_trip_circuit(svc)

        except Exception as e:
            svc.health = ServiceHealth.DOWN
            svc.error = str(e)[:200]
            svc.consecutive_failures += 1
            svc.latency_ms = round((time.time() - t0) * 1000, 1)
            self._maybe_trip_circuit(svc)

        return svc.health

    def _maybe_trip_circuit(self, svc: ServiceNode) -> None:
        """Open circuit breaker after threshold failures."""
        if svc.consecutive_failures >= self.CIRCUIT_FAILURE_THRESHOLD:
            if svc.circuit != CircuitState.OPEN:
                svc.circuit = CircuitState.OPEN
                svc.circuit_opened_at = time.time()
                self._trace(svc.name, "circuit_trip", 0.1,
                            f"Tripped after {svc.consecutive_failures} failures: {svc.error[:80]}",
                            alternatives=svc.fallback_chain)

    def _trace(self, service: str, action: str, confidence: float,
               reasoning: str, alternatives: List[str] = None,
               resolved_to: str = "") -> None:
        """Record a structured decision trace (from AI Workflow Architect)."""
        self.decision_traces.append(DecisionTrace(
            timestamp=time.time(),
            service=service,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives or [],
            resolved_to=resolved_to,
        ))

    # ------------------------------------------------------------------
    #  Self-Healing
    # ------------------------------------------------------------------

    async def _attempt_heal(self, name: str) -> None:
        """Try to heal a downed service using ordered fallback chain."""
        svc = self.services[name]
        event = {
            "time": time.time(),
            "service": name,
            "action": "heal_attempt",
            "failures": svc.consecutive_failures,
            "retryable": _is_retryable(svc.error),
        }

        # Non-retryable errors (auth, permission) = don't bother with fallback
        if not _is_retryable(svc.error):
            event["resolution"] = "non_retryable_error"
            self._trace(name, "heal_attempt", 0.2,
                        f"Non-retryable: {svc.error[:80]}")
            self.heal_log.append(event)
            return

        # Walk the ordered fallback chain (from AI Workflow Architect)
        for fb_name in svc.fallback_chain:
            fb = self.services.get(fb_name)
            if fb and fb.is_alive() and fb.circuit_ready:
                event["resolution"] = f"routed to fallback: {fb_name}"
                confidence = 1.0 - (svc.fallback_chain.index(fb_name) * 0.2)
                self._trace(name, "fallback_route", max(confidence, 0.3),
                            f"Routed {name} -> {fb_name}",
                            alternatives=svc.fallback_chain,
                            resolved_to=fb_name)
                self.heal_log.append(event)
                return

        # Legacy single-fallback as last resort
        if svc.fallback and svc.fallback in self.services:
            fb = self.services[svc.fallback]
            if fb.is_alive():
                event["resolution"] = f"routed to fallback: {svc.fallback}"
                self.heal_log.append(event)
                return

        # Alert via Telegram if available
        tg = self.services.get("telegram")
        if tg and tg.is_alive():
            await self._telegram_alert(
                f"HEAL: {name} down ({svc.consecutive_failures} failures). "
                f"Error: {svc.error[:100]}"
            )
            event["alerted"] = "telegram"

        self._trace(name, "heal_attempt", 0.1,
                    f"All fallbacks exhausted for {name}")
        self.heal_log.append(event)

    async def _telegram_alert(self, text: str) -> None:
        """Send an alert via Telegram bot."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            return
        # We don't know the chat_id here — would need to be configured
        # For now, just log it
        print(f"[HEAL-ALERT] {text}")

    def get_best_service(self, category: ServiceCategory) -> Optional[ServiceNode]:
        """Get the best available service in a category.

        Follows the fallback chain until it finds one that's UP.
        """
        candidates = [s for s in self.services.values()
                       if s.category == category and s.is_alive()]
        if not candidates:
            return None
        # Prefer lowest latency
        return min(candidates, key=lambda s: s.latency_ms)

    def resolve(self, name: str) -> Optional[ServiceNode]:
        """Resolve a service, following ordered fallback chain if DOWN.

        Uses the ordered fallback_chain first (from AI Workflow Architect),
        then falls back to the legacy single-pointer chain.
        """
        svc = self.services.get(name)
        if not svc:
            return None
        if svc.is_alive() and svc.circuit_ready:
            return svc

        # Walk ordered fallback chain first
        for fb_name in svc.fallback_chain:
            fb = self.services.get(fb_name)
            if fb and fb.is_alive() and fb.circuit_ready:
                return fb

        # Legacy single-pointer chain (max depth 5)
        visited = {name}
        current = svc
        for _ in range(5):
            if not current.fallback or current.fallback in visited:
                break
            visited.add(current.fallback)
            fb = self.services.get(current.fallback)
            if fb and fb.is_alive() and fb.circuit_ready:
                return fb
            if fb:
                current = fb

        return None  # Everything down

    # ------------------------------------------------------------------
    #  Workflow execution
    # ------------------------------------------------------------------

    async def run_workflow(self, workflow_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a self-healing workflow.

        The workflow adapts to which services are available:
          - If n8n is up, use it for orchestration
          - If n8n is down, fall back to Zapier
          - If both down, run steps directly via HYDRA limbs
          - Notes go to whichever note service is UP
          - Compute goes to whichever compute is available
        """
        result = {
            "workflow": workflow_type,
            "started": time.time(),
            "steps": [],
            "services_used": [],
        }

        if workflow_type == "research":
            return await self._wf_research(params, result)
        elif workflow_type == "train":
            return await self._wf_train(params, result)
        elif workflow_type == "publish":
            return await self._wf_publish(params, result)
        elif workflow_type == "health_report":
            return await self._wf_health_report(result)
        else:
            result["error"] = f"Unknown workflow: {workflow_type}"
            return result

    async def _wf_research(self, params: Dict[str, Any], result: Dict) -> Dict:
        """Research workflow: browse -> extract -> save to notes -> summarize."""
        goal = params.get("goal", "")

        # Step 1: Browse (function plane)
        browser = self.resolve("playwright_local")
        result["steps"].append({
            "step": "browse",
            "service": browser.name if browser else "NONE",
            "alive": browser.is_alive() if browser else False,
        })

        # Step 2: AI summarize (function plane)
        ai = self.get_best_service(ServiceCategory.AI)
        result["steps"].append({
            "step": "summarize",
            "service": ai.name if ai else "NONE",
            "alive": ai.is_alive() if ai else False,
        })

        # Step 3: Save to notes (function plane)
        notes = self.get_best_service(ServiceCategory.NOTES)
        result["steps"].append({
            "step": "save_notes",
            "service": notes.name if notes else "NONE",
            "alive": notes.is_alive() if notes else False,
        })

        # Step 4: Alert via messaging (function plane)
        msg = self.get_best_service(ServiceCategory.MESSAGING)
        result["steps"].append({
            "step": "notify",
            "service": msg.name if msg else "NONE",
            "alive": msg.is_alive() if msg else False,
        })

        result["services_used"] = list({s["service"] for s in result["steps"] if s["service"] != "NONE"})
        result["completed"] = time.time()
        return result

    async def _wf_train(self, params: Dict[str, Any], result: Dict) -> Dict:
        """Training workflow: load data -> govern -> train -> push to HF."""
        tongue = params.get("tongue", "KO")

        compute = self.get_best_service(ServiceCategory.COMPUTE)
        result["steps"].append({
            "step": "select_compute",
            "service": compute.name if compute else "NONE",
            "tongue": tongue,
        })

        # Governance check (weight plane)
        gov = self.resolve("cloud_run")
        result["steps"].append({
            "step": "governance_check",
            "service": gov.name if gov else "NONE",
            "plane": "GOVERNANCE (weights)",
        })

        # Train (function plane)
        result["steps"].append({
            "step": "train",
            "service": compute.name if compute else "local",
            "plane": "FUNCTION",
        })

        # Push to HF (function plane)
        hf = self.resolve("huggingface")
        result["steps"].append({
            "step": "push_to_hf",
            "service": hf.name if hf else "NONE",
        })

        result["services_used"] = list({s["service"] for s in result["steps"] if s.get("service") != "NONE"})
        result["completed"] = time.time()
        return result

    async def _wf_publish(self, params: Dict[str, Any], result: Dict) -> Dict:
        """Publish workflow: draft -> govern -> post via n8n/Zapier."""
        workflow = self.get_best_service(ServiceCategory.WORKFLOW)
        ai = self.get_best_service(ServiceCategory.AI)
        msg = self.get_best_service(ServiceCategory.MESSAGING)

        result["steps"] = [
            {"step": "draft", "service": ai.name if ai else "NONE"},
            {"step": "govern", "service": "cloud_run", "plane": "GOVERNANCE"},
            {"step": "publish", "service": workflow.name if workflow else "NONE"},
            {"step": "notify", "service": msg.name if msg else "NONE"},
        ]
        result["completed"] = time.time()
        return result

    async def _wf_health_report(self, result: Dict) -> Dict:
        """Generate a full health report of all services."""
        for name, svc in self.services.items():
            await self._check_service(name)

        result["report"] = {}
        for cat in ServiceCategory:
            services = [s for s in self.services.values() if s.category == cat]
            result["report"][cat.value] = [
                {
                    "name": s.name,
                    "health": s.health.value,
                    "latency_ms": s.latency_ms,
                    "failures": s.consecutive_failures,
                    "fallback": s.fallback,
                    "error": s.error[:100] if s.error else "",
                }
                for s in services
            ]

        alive = sum(1 for s in self.services.values() if s.is_alive())
        total = len(self.services)
        result["summary"] = {
            "alive": alive,
            "total": total,
            "health_pct": round(alive / total * 100, 1) if total else 0,
        }
        result["heal_log_size"] = len(self.heal_log)
        result["completed"] = time.time()
        return result

    # ------------------------------------------------------------------
    #  Health Check Implementations
    # ------------------------------------------------------------------

    async def _check_url_health(self, svc: ServiceNode) -> ServiceHealth:
        """Generic URL health check."""
        if not svc.url:
            return ServiceHealth.UNKNOWN
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(svc.url, headers={"User-Agent": "HYDRA-Mesh/1.0"})
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8)
            )
            if resp.status < 400:
                return ServiceHealth.UP
            return ServiceHealth.DEGRADED
        except Exception as e:
            svc.error = str(e)[:200]
            return ServiceHealth.DOWN

    async def _check_obsidian(self, svc: ServiceNode) -> ServiceHealth:
        """Check if Obsidian vaults are accessible (local filesystem)."""
        from pathlib import Path
        vault1 = Path(r"C:\Users\issda\OneDrive\Dropbox\Izack Realmforge")
        vault2 = Path(r"C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder")
        ctx = vault1 / "AI Workspace" / "_context.md"

        if ctx.exists():
            return ServiceHealth.UP
        if vault1.exists() or vault2.exists():
            return ServiceHealth.DEGRADED
        return ServiceHealth.DOWN

    async def _check_notion(self, svc: ServiceNode) -> ServiceHealth:
        """Check Notion API."""
        token = os.environ.get("NOTION_TOKEN", "")
        if not token:
            return ServiceHealth.DOWN
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                },
            )
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8)
            )
            return ServiceHealth.UP if resp.status == 200 else ServiceHealth.DEGRADED
        except Exception:
            return ServiceHealth.DOWN

    async def _check_google_drive(self, svc: ServiceNode) -> ServiceHealth:
        """Check if Google Drive credentials exist."""
        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if creds and os.path.exists(creds):
            return ServiceHealth.UP
        # Check for default gcloud auth
        gcloud_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
        if os.path.exists(gcloud_path):
            return ServiceHealth.DEGRADED  # Exists but might be expired
        return ServiceHealth.DOWN

    async def _check_vertex(self, svc: ServiceNode) -> ServiceHealth:
        """Check Vertex AI availability."""
        try:
            from google.cloud import aiplatform
            return ServiceHealth.UP
        except ImportError:
            return ServiceHealth.DOWN

    async def _check_zapier(self, svc: ServiceNode) -> ServiceHealth:
        """Check if any Zapier webhooks are configured."""
        has_webhooks = any(k.startswith("ZAPIER_WEBHOOK_") for k in os.environ)
        return ServiceHealth.UP if has_webhooks else ServiceHealth.DOWN

    async def _check_claude(self, svc: ServiceNode) -> ServiceHealth:
        """Check Claude API key."""
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        return ServiceHealth.UP if key else ServiceHealth.DOWN

    async def _check_chatgpt(self, svc: ServiceNode) -> ServiceHealth:
        """Check OpenAI API key."""
        key = os.environ.get("OPENAI_API_KEY", "")
        return ServiceHealth.UP if key else ServiceHealth.DOWN

    async def _check_hf(self, svc: ServiceNode) -> ServiceHealth:
        """Check HuggingFace token."""
        token = os.environ.get("HF_TOKEN", "")
        if not token:
            return ServiceHealth.DOWN
        try:
            loop = asyncio.get_event_loop()
            req = urllib.request.Request(
                "https://huggingface.co/api/whoami-v2",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8)
            )
            return ServiceHealth.UP if resp.status == 200 else ServiceHealth.DEGRADED
        except Exception:
            return ServiceHealth.DOWN

    async def _check_playwright(self, svc: ServiceNode) -> ServiceHealth:
        """Check if Playwright is installed."""
        try:
            import playwright
            return ServiceHealth.UP
        except ImportError:
            return ServiceHealth.DOWN

    async def _check_playwright_cloud(self, svc: ServiceNode) -> ServiceHealth:
        """Check remote Playwright workers."""
        workers = [v for k, v in os.environ.items() if k.startswith("PW_WORKER_")]
        return ServiceHealth.UP if workers else ServiceHealth.DOWN

    async def _check_websocket(self, svc: ServiceNode) -> ServiceHealth:
        """Check if WebSocket libraries available."""
        try:
            import websockets
            return ServiceHealth.UP
        except ImportError:
            return ServiceHealth.DOWN

    async def _check_switchboard(self, svc: ServiceNode) -> ServiceHealth:
        """Check SQLite switchboard."""
        from pathlib import Path
        db = Path("artifacts/hydra/switchboard.db")
        if db.exists():
            return ServiceHealth.UP
        return ServiceHealth.DEGRADED  # Will be created on first use

    async def _check_firebase(self, svc: ServiceNode) -> ServiceHealth:
        """Check Firebase credentials."""
        creds = os.environ.get("FIREBASE_CREDENTIALS", "")
        if creds:
            return ServiceHealth.UP
        return ServiceHealth.DOWN

    # ------------------------------------------------------------------
    #  Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Full mesh status with circuit breaker info."""
        by_cat = {}
        for cat in ServiceCategory:
            services = [s for s in self.services.values() if s.category == cat]
            by_cat[cat.value] = {
                "services": {
                    s.name: {
                        "health": s.health.value,
                        "circuit": s.circuit.value,
                        "latency_ms": s.latency_ms,
                        "failures": s.consecutive_failures,
                    }
                    for s in services
                },
                "best": (self.get_best_service(cat) or ServiceNode(name="NONE", category=cat)).name,
            }

        alive = sum(1 for s in self.services.values() if s.is_alive())
        circuits_open = sum(1 for s in self.services.values() if s.circuit == CircuitState.OPEN)
        return {
            "running": self._running,
            "alive": alive,
            "total": len(self.services),
            "health_pct": round(alive / len(self.services) * 100, 1),
            "circuits_open": circuits_open,
            "categories": by_cat,
            "heal_events": len(self.heal_log),
            "decision_traces": len(self.decision_traces),
        }

    def status_text(self) -> str:
        """Human-readable status."""
        s = self.status()
        lines = [
            f"HYDRA Self-Healing Mesh",
            f"=======================",
            f"Health: {s['alive']}/{s['total']} services ({s['health_pct']}%)",
            f"Circuits open: {s['circuits_open']}",
            f"Heal events: {s['heal_events']}  |  Decision traces: {s['decision_traces']}",
            f"",
        ]
        for cat_name, cat_data in s["categories"].items():
            lines.append(f"  {cat_name.upper():12s} (best: {cat_data['best']})")
            for svc_name, svc_info in cat_data["services"].items():
                health = svc_info["health"]
                circuit = svc_info["circuit"]
                icon = {"UP": "+", "DEGRADED": "~", "DOWN": "X", "UNKNOWN": "?"}[health]
                circ = f" [OPEN]" if circuit == "open" else ""
                lat = f" {svc_info['latency_ms']}ms" if svc_info['latency_ms'] > 0 else ""
                lines.append(f"    [{icon}] {svc_name}{circ}{lat}")
        return "\n".join(lines)
