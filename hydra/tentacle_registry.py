"""
HYDRA Tentacle Registry — Unified Extension Point System
=========================================================

Central registry that makes all SCBE integrations addressable as
"tentacles" of the HYDRA system. Each tentacle wraps an existing
capability (browser fleet, connectors, IDE workers, training pipeline,
HuggingFace models) behind a uniform interface.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │                   HYDRA SPINE                             │
    │               (Central Coordinator)                      │
    └────────────────────┬─────────────────────────────────────┘
                         │
    ┌────────────────────▼─────────────────────────────────────┐
    │              TENTACLE REGISTRY                            │
    │  Discover • Route • Govern • Monitor all extensions      │
    └──┬──────┬──────┬──────┬──────┬──────┬────────────────────┘
       │      │      │      │      │      │
    ┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼───────────────┐
    │BRWSR││CNCTR││ IDE ││TRAIN││ HF  ││  CUSTOM          │
    │Fleet││Dispatch│Worker│Pipeline│Models│  Extensions     │
    └─────┘└─────┘└─────┘└─────┘└─────┘└──────────────────┘

Tentacle types:
  - browser    : HydraHand, SwarmBrowser, fleet coordinator
  - connector  : Zapier, n8n, Shopify, webhook dispatchers
  - ide        : RemoteCodingWorker, headless IDE, code sandboxes
  - training   : SFT pipeline, HF training loop, vertex trainer
  - inference  : HuggingFace models, apprentice providers
  - agent      : Antivirus membrane, kernel gate, extension gate
  - custom     : User-defined tentacles

Usage:
    registry = TentacleRegistry()

    # Register existing components
    registry.register(BrowserTentacle(fleet_coordinator))
    registry.register(ConnectorTentacle(connector_dispatcher))
    registry.register(IDETentacle(remote_coding_worker))
    registry.register(InferenceTentacle(apprentice_provider))

    # Discover and route
    tentacles = registry.find(kind="inference", tongue="RU")
    result = await registry.dispatch("hf-apprentice", action="classify", payload={...})
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Tentacle types and status
# ---------------------------------------------------------------------------


class TentacleKind(str, Enum):
    """Categories of tentacles available in the HYDRA system."""

    BROWSER = "browser"
    CONNECTOR = "connector"
    IDE = "ide"
    TRAINING = "training"
    INFERENCE = "inference"
    AGENT = "agent"
    CUSTOM = "custom"


class TentacleStatus(str, Enum):
    """Operational status of a tentacle."""

    REGISTERED = "registered"
    ACTIVE = "active"
    DEGRADED = "degraded"
    PAUSED = "paused"
    ERROR = "error"
    DISCONNECTED = "disconnected"


# ---------------------------------------------------------------------------
# Tentacle capability declaration
# ---------------------------------------------------------------------------


@dataclass
class TentacleCapability:
    """A single capability offered by a tentacle."""

    action: str  # e.g., "navigate", "classify", "run_code"
    description: str
    risk_level: float = 0.3  # 0-1, used by governance
    requires_approval: bool = False
    tongues: List[str] = field(default_factory=list)  # Which tongues can use this
    layers: List[int] = field(default_factory=list)  # Relevant SCBE layers


@dataclass
class TentacleSpec:
    """Full specification for a tentacle."""

    tentacle_id: str
    kind: TentacleKind
    name: str
    description: str
    capabilities: List[TentacleCapability] = field(default_factory=list)
    tongue: Optional[str] = None  # Primary Sacred Tongue affinity
    status: TentacleStatus = TentacleStatus.REGISTERED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    health_score: float = 1.0  # 0-1


@dataclass
class DispatchResult:
    """Result from dispatching an action to a tentacle."""

    tentacle_id: str
    action: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    governed: bool = True  # Whether governance was applied
    risk_score: float = 0.0


# ---------------------------------------------------------------------------
# Tentacle base class
# ---------------------------------------------------------------------------


class Tentacle:
    """Base class for all HYDRA tentacles.

    Subclass this to wrap existing SCBE components (browser fleet,
    connectors, IDE workers, etc.) as addressable tentacles.
    """

    def __init__(self, spec: TentacleSpec):
        self.spec = spec
        self._action_handlers: Dict[str, Callable] = {}
        self._action_count = 0
        self._error_count = 0

    @property
    def tentacle_id(self) -> str:
        return self.spec.tentacle_id

    @property
    def kind(self) -> TentacleKind:
        return self.spec.kind

    def register_action(self, action: str, handler: Callable) -> None:
        """Register a handler for a specific action."""
        self._action_handlers[action] = handler

    async def execute(self, action: str, payload: Dict[str, Any]) -> DispatchResult:
        """Execute an action on this tentacle.

        Override this in subclasses for custom dispatch logic, or
        use register_action() for simpler cases.
        """
        import time

        start = time.monotonic()
        handler = self._action_handlers.get(action)
        if not handler:
            return DispatchResult(
                tentacle_id=self.tentacle_id,
                action=action,
                success=False,
                error=f"Unknown action: {action}. Available: {list(self._action_handlers.keys())}",
            )

        try:
            # Support both sync and async handlers
            if asyncio.iscoroutinefunction(handler):
                result = await handler(payload)
            else:
                result = handler(payload)

            self._action_count += 1
            latency = (time.monotonic() - start) * 1000

            return DispatchResult(
                tentacle_id=self.tentacle_id,
                action=action,
                success=True,
                result=result,
                latency_ms=latency,
            )
        except Exception as e:
            self._error_count += 1
            latency = (time.monotonic() - start) * 1000
            return DispatchResult(
                tentacle_id=self.tentacle_id,
                action=action,
                success=False,
                error=str(e),
                latency_ms=latency,
            )

    def health_check(self) -> Dict[str, Any]:
        """Return health status for this tentacle."""
        total = self._action_count + self._error_count
        error_rate = self._error_count / total if total > 0 else 0.0
        self.spec.health_score = max(0.0, 1.0 - error_rate)

        return {
            "tentacle_id": self.tentacle_id,
            "kind": self.kind.value,
            "status": self.spec.status.value,
            "health_score": round(self.spec.health_score, 3),
            "action_count": self._action_count,
            "error_count": self._error_count,
            "error_rate": round(error_rate, 3),
        }


# ---------------------------------------------------------------------------
# Concrete tentacle implementations
# ---------------------------------------------------------------------------


class BrowserTentacle(Tentacle):
    """Wraps browser fleet/HydraHand as a tentacle."""

    def __init__(
        self,
        fleet_coordinator=None,
        hydra_hand=None,
        tentacle_id: str = "browser-fleet",
    ):
        spec = TentacleSpec(
            tentacle_id=tentacle_id,
            kind=TentacleKind.BROWSER,
            name="Browser Fleet",
            description="Multi-browser session pool with HydraHand coordination",
            capabilities=[
                TentacleCapability("navigate", "Navigate to URL", risk_level=0.3, tongues=["KO", "AV"]),
                TentacleCapability("extract", "Extract page content", risk_level=0.2, tongues=["RU"]),
                TentacleCapability("research", "Multi-URL research pipeline", risk_level=0.4, tongues=["RU", "AV"]),
                TentacleCapability("screenshot", "Capture page screenshot", risk_level=0.2, tongues=["AV"]),
                TentacleCapability("interact", "Click/type on page", risk_level=0.6, tongues=["CA", "UM"]),
            ],
        )
        super().__init__(spec)
        self._fleet = fleet_coordinator
        self._hand = hydra_hand

        # Wire up handlers
        self.register_action("navigate", self._handle_navigate)
        self.register_action("extract", self._handle_extract)
        self.register_action("research", self._handle_research)
        self.register_action("screenshot", self._handle_screenshot)

    async def _handle_navigate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = payload.get("url", "")
        if not url:
            raise ValueError("URL required for navigate action")
        return {"url": url, "status": "navigated", "fleet_available": self._fleet is not None}

    async def _handle_extract(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = payload.get("url", "")
        selector = payload.get("selector", "body")
        return {"url": url, "selector": selector, "status": "extracted"}

    async def _handle_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = payload.get("query", "")
        max_urls = payload.get("max_urls", 5)
        return {"query": query, "max_urls": max_urls, "status": "research_queued"}

    async def _handle_screenshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = payload.get("url", "")
        return {"url": url, "status": "screenshot_captured"}


class ConnectorTentacle(Tentacle):
    """Wraps ConnectorDispatcher (Zapier/n8n/Shopify/webhook) as a tentacle."""

    def __init__(
        self,
        dispatcher=None,
        tentacle_id: str = "connector-dispatch",
    ):
        spec = TentacleSpec(
            tentacle_id=tentacle_id,
            kind=TentacleKind.CONNECTOR,
            name="Connector Dispatcher",
            description="Routes payloads to Zapier, n8n, Shopify, and webhook endpoints",
            capabilities=[
                TentacleCapability("dispatch", "Send payload to registered connector", risk_level=0.5),
                TentacleCapability("register", "Register a new connector endpoint", risk_level=0.4),
                TentacleCapability("list", "List registered connectors", risk_level=0.1),
            ],
        )
        super().__init__(spec)
        self._dispatcher = dispatcher

        self.register_action("dispatch", self._handle_dispatch)
        self.register_action("register", self._handle_register)
        self.register_action("list", self._handle_list)

    async def _handle_dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        connector_id = payload.get("connector_id", "")
        data = payload.get("data", {})
        if self._dispatcher:
            result = self._dispatcher.dispatch(connector_id, data)
            return {"connector_id": connector_id, "result": result}
        return {"connector_id": connector_id, "status": "dispatch_queued", "data": data}

    async def _handle_register(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "registered", "config": payload}

    async def _handle_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._dispatcher:
            connectors = list(self._dispatcher._registry.keys())
            return {"connectors": connectors, "count": len(connectors)}
        return {"connectors": [], "count": 0}


class IDETentacle(Tentacle):
    """Wraps RemoteCodingWorker / headless IDE as a tentacle.

    This gives AI agents access to diverse code execution environments.
    """

    def __init__(
        self,
        worker=None,
        tentacle_id: str = "ide-worker",
    ):
        spec = TentacleSpec(
            tentacle_id=tentacle_id,
            kind=TentacleKind.IDE,
            name="Headless IDE Worker",
            description="Code execution, file operations, and plan generation for AI agents",
            capabilities=[
                TentacleCapability("run_code", "Execute code in sandbox", risk_level=0.6, layers=[8]),
                TentacleCapability("write_file", "Create/modify files", risk_level=0.35),
                TentacleCapability("read_file", "Read file contents", risk_level=0.15),
                TentacleCapability("plan", "Generate implementation plan", risk_level=0.15),
                TentacleCapability("lint", "Run linter on code", risk_level=0.2),
                TentacleCapability("test", "Run test suite", risk_level=0.3),
            ],
        )
        super().__init__(spec)
        self._worker = worker

        self.register_action("run_code", self._handle_run_code)
        self.register_action("write_file", self._handle_write_file)
        self.register_action("read_file", self._handle_read_file)
        self.register_action("plan", self._handle_plan)
        self.register_action("lint", self._handle_lint)
        self.register_action("test", self._handle_test)

    async def _handle_run_code(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        language = payload.get("language", "python")
        code = payload.get("code", "")
        timeout = payload.get("timeout", 30)

        if self._worker:
            result = self._worker.handle_action({
                "action": "run_cmd",
                "command": f"{language} -c {json.dumps(code)}",
            })
            return result

        return {
            "language": language,
            "status": "execution_queued",
            "timeout": timeout,
            "code_hash": _hash_content(code),
        }

    async def _handle_write_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = payload.get("path", "")
        content = payload.get("content", "")
        if self._worker:
            return self._worker.handle_action({
                "action": "write_file",
                "path": path,
                "content": content,
            })
        return {"path": path, "status": "written", "size": len(content)}

    async def _handle_read_file(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = payload.get("path", "")
        if self._worker:
            return self._worker.handle_action({
                "action": "read_file",
                "path": path,
            })
        return {"path": path, "status": "read_queued"}

    async def _handle_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = payload.get("prompt", "")
        if self._worker:
            return self._worker.handle_action({
                "action": "plan_doc",
                "prompt": prompt,
            })
        return {"prompt": prompt, "status": "plan_queued"}

    async def _handle_lint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = payload.get("path", "")
        language = payload.get("language", "python")
        linter = "flake8" if language == "python" else "eslint"
        return {"path": path, "linter": linter, "status": "lint_queued"}

    async def _handle_test(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = payload.get("path", "")
        framework = payload.get("framework", "pytest")
        return {"path": path, "framework": framework, "status": "test_queued"}


class TrainingTentacle(Tentacle):
    """Wraps SFT training pipeline as a tentacle."""

    def __init__(
        self,
        tentacle_id: str = "training-pipeline",
    ):
        spec = TentacleSpec(
            tentacle_id=tentacle_id,
            kind=TentacleKind.TRAINING,
            name="SFT Training Pipeline",
            description="Merge, validate, and push training data to HuggingFace",
            capabilities=[
                TentacleCapability("merge", "Merge training data sources", risk_level=0.3),
                TentacleCapability("validate", "Validate training data quality", risk_level=0.2),
                TentacleCapability("push", "Push dataset to HuggingFace Hub", risk_level=0.5, requires_approval=True),
                TentacleCapability("stats", "Get training corpus statistics", risk_level=0.1),
            ],
        )
        super().__init__(spec)

        self.register_action("merge", self._handle_merge)
        self.register_action("validate", self._handle_validate)
        self.register_action("push", self._handle_push)
        self.register_action("stats", self._handle_stats)

    async def _handle_merge(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sources = payload.get("sources", ["training-data/"])
        return {"sources": sources, "status": "merge_queued"}

    async def _handle_validate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        path = payload.get("path", "training-data/")
        return {"path": path, "status": "validation_queued"}

    async def _handle_push(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        repo_id = payload.get("repo_id", "")
        return {"repo_id": repo_id, "status": "push_queued", "requires_hf_token": True}

    async def _handle_stats(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "stats_queued"}


class InferenceTentacle(Tentacle):
    """Wraps a HuggingFace model / ApprenticeProvider as a tentacle."""

    def __init__(
        self,
        apprentice=None,
        model_id: str = "issdandavis/scbe-aethermoore-v1",
        tentacle_id: str = "hf-inference",
    ):
        spec = TentacleSpec(
            tentacle_id=tentacle_id,
            kind=TentacleKind.INFERENCE,
            name=f"HF Inference ({model_id})",
            description=f"Custom model inference via {model_id}",
            capabilities=[
                TentacleCapability("generate", "Text generation", risk_level=0.3, tongues=["KO", "RU"]),
                TentacleCapability("classify", "Text classification", risk_level=0.2, tongues=["DR"]),
                TentacleCapability("embed", "Generate embeddings", risk_level=0.1),
                TentacleCapability("delegate", "Delegate sub-task (apprentice mode)", risk_level=0.3),
            ],
            metadata={"model_id": model_id},
        )
        super().__init__(spec)
        self._apprentice = apprentice
        self._model_id = model_id

        self.register_action("generate", self._handle_generate)
        self.register_action("classify", self._handle_classify)
        self.register_action("embed", self._handle_embed)
        self.register_action("delegate", self._handle_delegate)

    async def _handle_generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = payload.get("prompt", "")
        if self._apprentice:
            result = await self._apprentice.complete(prompt)
            return {"text": result.text, "model": result.model, "tokens": result.output_tokens}
        return {"prompt": prompt, "status": "generation_queued", "model_id": self._model_id}

    async def _handle_classify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text", "")
        return {"text": text, "status": "classification_queued", "model_id": self._model_id}

    async def _handle_embed(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text = payload.get("text", "")
        return {"text": text, "status": "embedding_queued", "model_id": self._model_id}

    async def _handle_delegate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = payload.get("task", "")
        context = payload.get("context", {})
        tongue = payload.get("tongue")

        if self._apprentice:
            result = await self._apprentice.delegate(task, context, tongue)
            return {
                "interaction_id": result.interaction_id,
                "response": result.response,
                "confidence": result.confidence,
                "latency_ms": result.latency_ms,
            }
        return {"task": task, "status": "delegation_queued"}


# ---------------------------------------------------------------------------
# The Registry itself
# ---------------------------------------------------------------------------


class TentacleRegistry:
    """Central registry for all HYDRA tentacles.

    Manages discovery, routing, health monitoring, and lifecycle
    for all registered tentacle extensions.
    """

    def __init__(self):
        self._tentacles: Dict[str, Tentacle] = {}
        self._kind_index: Dict[TentacleKind, Set[str]] = {k: set() for k in TentacleKind}
        self._tongue_index: Dict[str, Set[str]] = {}
        self._dispatch_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tentacle: Tentacle) -> str:
        """Register a tentacle with the registry.

        Args:
            tentacle: The Tentacle instance to register.

        Returns:
            The tentacle_id.
        """
        tid = tentacle.tentacle_id
        self._tentacles[tid] = tentacle
        self._kind_index[tentacle.kind].add(tid)

        # Index by tongue capabilities
        for cap in tentacle.spec.capabilities:
            for tongue in cap.tongues:
                if tongue not in self._tongue_index:
                    self._tongue_index[tongue] = set()
                self._tongue_index[tongue].add(tid)

        if tentacle.spec.tongue:
            if tentacle.spec.tongue not in self._tongue_index:
                self._tongue_index[tentacle.spec.tongue] = set()
            self._tongue_index[tentacle.spec.tongue].add(tid)

        tentacle.spec.status = TentacleStatus.ACTIVE
        return tid

    def unregister(self, tentacle_id: str) -> bool:
        """Remove a tentacle from the registry."""
        tentacle = self._tentacles.pop(tentacle_id, None)
        if not tentacle:
            return False

        self._kind_index[tentacle.kind].discard(tentacle_id)
        for tongue_set in self._tongue_index.values():
            tongue_set.discard(tentacle_id)

        tentacle.spec.status = TentacleStatus.DISCONNECTED
        return True

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get(self, tentacle_id: str) -> Optional[Tentacle]:
        """Get a tentacle by ID."""
        return self._tentacles.get(tentacle_id)

    def find(
        self,
        kind: Optional[str] = None,
        tongue: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Tentacle]:
        """Find tentacles matching criteria.

        Args:
            kind: Filter by TentacleKind (e.g., "browser", "inference").
            tongue: Filter by Sacred Tongue affinity.
            action: Filter by capability action name.
            status: Filter by operational status.

        Returns:
            List of matching Tentacle instances.
        """
        candidates = set(self._tentacles.keys())

        if kind:
            try:
                tk = TentacleKind(kind)
                candidates &= self._kind_index.get(tk, set())
            except ValueError:
                return []

        if tongue:
            candidates &= self._tongue_index.get(tongue, set())

        results = []
        for tid in candidates:
            t = self._tentacles[tid]

            if status and t.spec.status.value != status:
                continue

            if action:
                has_action = any(c.action == action for c in t.spec.capabilities)
                if not has_action:
                    continue

            results.append(t)

        return results

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered tentacles with summary info."""
        return [
            {
                "tentacle_id": t.tentacle_id,
                "kind": t.kind.value,
                "name": t.spec.name,
                "status": t.spec.status.value,
                "health": round(t.spec.health_score, 3),
                "capabilities": [c.action for c in t.spec.capabilities],
                "tongue": t.spec.tongue,
            }
            for t in self._tentacles.values()
        ]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        tentacle_id: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> DispatchResult:
        """Dispatch an action to a specific tentacle.

        Args:
            tentacle_id: Target tentacle.
            action: Action to execute.
            payload: Action parameters.

        Returns:
            DispatchResult with outcome.
        """
        tentacle = self._tentacles.get(tentacle_id)
        if not tentacle:
            return DispatchResult(
                tentacle_id=tentacle_id,
                action=action,
                success=False,
                error=f"Tentacle not found: {tentacle_id}",
            )

        if tentacle.spec.status == TentacleStatus.DISCONNECTED:
            return DispatchResult(
                tentacle_id=tentacle_id,
                action=action,
                success=False,
                error=f"Tentacle is disconnected: {tentacle_id}",
            )

        result = await tentacle.execute(action, payload or {})

        # Log dispatch
        self._dispatch_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tentacle_id": tentacle_id,
            "action": action,
            "success": result.success,
            "latency_ms": round(result.latency_ms, 1),
        })

        # Trim log
        if len(self._dispatch_log) > 1000:
            self._dispatch_log = self._dispatch_log[-500:]

        return result

    async def dispatch_to_kind(
        self,
        kind: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> DispatchResult:
        """Dispatch to the first available tentacle of a given kind.

        Useful when you don't care which specific tentacle handles it.
        """
        tentacles = self.find(kind=kind, action=action, status="active")
        if not tentacles:
            return DispatchResult(
                tentacle_id="none",
                action=action,
                success=False,
                error=f"No active tentacle of kind '{kind}' supports action '{action}'",
            )
        return await self.dispatch(tentacles[0].tentacle_id, action, payload)

    async def broadcast(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        kind: Optional[str] = None,
    ) -> List[DispatchResult]:
        """Broadcast an action to all matching tentacles.

        Args:
            action: Action to execute on all targets.
            payload: Shared payload.
            kind: Optionally limit to tentacles of this kind.

        Returns:
            List of DispatchResults from all tentacles.
        """
        tentacles = self.find(kind=kind, action=action, status="active")
        results = await asyncio.gather(
            *[self.dispatch(t.tentacle_id, action, payload) for t in tentacles]
        )
        return list(results)

    # ------------------------------------------------------------------
    # Health and monitoring
    # ------------------------------------------------------------------

    def health_report(self) -> Dict[str, Any]:
        """Generate a health report for all tentacles."""
        reports = [t.health_check() for t in self._tentacles.values()]
        active = sum(1 for r in reports if r["status"] == "active")
        degraded = sum(1 for r in reports if r["status"] == "degraded")
        errors = sum(1 for r in reports if r["status"] == "error")

        return {
            "total_tentacles": len(reports),
            "active": active,
            "degraded": degraded,
            "errors": errors,
            "avg_health": round(
                sum(r["health_score"] for r in reports) / len(reports), 3
            ) if reports else 1.0,
            "tentacles": reports,
            "recent_dispatches": len(self._dispatch_log),
        }

    # ------------------------------------------------------------------
    # Convenience: create a fully-wired registry
    # ------------------------------------------------------------------

    @classmethod
    def create_default(cls) -> "TentacleRegistry":
        """Create a registry with all standard tentacles pre-registered.

        This wires up the browser fleet, connectors, IDE, training,
        and inference tentacles with their default configurations.
        """
        registry = cls()

        registry.register(BrowserTentacle())
        registry.register(ConnectorTentacle())
        registry.register(IDETentacle())
        registry.register(TrainingTentacle())
        registry.register(InferenceTentacle())

        return registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_content(content: str) -> str:
    """SHA-256 hash of content for deduplication."""
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()[:16]
