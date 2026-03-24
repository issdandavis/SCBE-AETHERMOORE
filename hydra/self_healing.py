"""HYDRA Self-Healing Mesh
========================

Service health monitoring with circuit breakers, ordered fallback chains,
error classification, and decision traces.

Patterns sourced from AI Workflow Architect + SCBE governance.
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
# Circuit Breaker
# ═══════════════════════════════════════════════════════════

class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal — requests pass through
    OPEN = "open"           # Tripped — requests blocked
    HALF_OPEN = "half_open" # Testing — one request allowed


@dataclass
class CircuitBreaker:
    """Trip after N failures, reset after cooldown."""
    failure_threshold: int = 3
    cooldown_seconds: float = 60.0
    failure_count: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: float = 0.0
    last_success_time: float = 0.0

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_success_time = time.time()

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN — allow one test request
        return True


# ═══════════════════════════════════════════════════════════
# Error Classification
# ═══════════════════════════════════════════════════════════

class ErrorClass(str, Enum):
    RETRYABLE = "retryable"     # Timeout, network, 5xx
    AUTH = "auth"               # 401/403, bad token
    NOT_FOUND = "not_found"     # 404, missing resource
    PERMANENT = "permanent"     # Config error, bad code


def classify_error(error: Exception) -> ErrorClass:
    msg = str(error).lower()
    if any(k in msg for k in ["timeout", "timed out", "connection", "503", "502", "429"]):
        return ErrorClass.RETRYABLE
    if any(k in msg for k in ["401", "403", "unauthorized", "forbidden", "auth", "token"]):
        return ErrorClass.AUTH
    if any(k in msg for k in ["404", "not found", "no such"]):
        return ErrorClass.NOT_FOUND
    return ErrorClass.PERMANENT


# ═══════════════════════════════════════════════════════════
# Decision Trace
# ═══════════════════════════════════════════════════════════

@dataclass
class DecisionTrace:
    """Record of a heal/resolve decision for audit."""
    service: str
    action: str
    confidence: float
    reason: str
    timestamp: float = field(default_factory=time.time)
    success: Optional[bool] = None


# ═══════════════════════════════════════════════════════════
# Service Definition
# ═══════════════════════════════════════════════════════════

@dataclass
class ServiceDef:
    """A monitored service with health check and fallback chain."""
    name: str
    category: str
    check: Callable[[], bool]
    fallbacks: List[Callable[[], bool]] = field(default_factory=list)
    circuit: CircuitBreaker = field(default_factory=CircuitBreaker)
    last_check: float = 0.0
    last_latency_ms: float = 0.0
    status: str = "unknown"
    error_class: Optional[ErrorClass] = None
    traces: List[DecisionTrace] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Self-Healing Mesh
# ═══════════════════════════════════════════════════════════

class SelfHealingMesh:
    """Monitors services, detects failures, heals via fallback chains."""

    def __init__(self):
        self.services: Dict[str, ServiceDef] = {}
        self.traces: List[DecisionTrace] = []

    def register(
        self,
        name: str,
        category: str,
        check: Callable[[], bool],
        fallbacks: Optional[List[Callable[[], bool]]] = None,
    ):
        self.services[name] = ServiceDef(
            name=name,
            category=category,
            check=check,
            fallbacks=fallbacks or [],
        )

    def check(self, name: str) -> Tuple[str, float]:
        """Check a single service. Returns (status, latency_ms)."""
        svc = self.services.get(name)
        if not svc:
            return ("not_registered", 0.0)

        if not svc.circuit.allow_request():
            svc.status = "circuit_open"
            return ("circuit_open", 0.0)

        start = time.time()
        try:
            ok = svc.check()
            latency = (time.time() - start) * 1000
            svc.last_latency_ms = latency
            svc.last_check = time.time()
            if ok:
                svc.circuit.record_success()
                svc.status = "up"
                svc.error_class = None
                return ("up", latency)
            else:
                svc.circuit.record_failure()
                svc.status = "down"
                return ("down", latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            svc.last_latency_ms = latency
            svc.last_check = time.time()
            svc.error_class = classify_error(e)
            svc.circuit.record_failure()
            svc.status = "error"
            return ("error", latency)

    def heal(self, name: str) -> bool:
        """Attempt to heal a service via its fallback chain."""
        svc = self.services.get(name)
        if not svc:
            return False

        for i, fallback in enumerate(svc.fallbacks):
            trace = DecisionTrace(
                service=name,
                action=f"fallback_{i}",
                confidence=1.0 / (1 + i),  # Decreasing confidence per fallback
                reason=f"Attempting fallback {i} for {name}",
            )
            try:
                ok = fallback()
                trace.success = ok
                svc.traces.append(trace)
                self.traces.append(trace)
                if ok:
                    svc.circuit.record_success()
                    svc.status = "healed"
                    return True
            except Exception:
                trace.success = False
                svc.traces.append(trace)
                self.traces.append(trace)

        return False

    def check_all(self) -> Dict[str, Tuple[str, float]]:
        """Check all services. Returns {name: (status, latency_ms)}."""
        results = {}
        for name in self.services:
            results[name] = self.check(name)
        return results

    def heal_all(self) -> Dict[str, bool]:
        """Attempt to heal all down/error services."""
        healed = {}
        for name, svc in self.services.items():
            if svc.status in ("down", "error", "circuit_open"):
                healed[name] = self.heal(name)
        return healed

    def status_report(self) -> str:
        """Generate a human-readable status report."""
        lines = ["HYDRA Self-Healing Mesh Status", "=" * 40]
        by_cat: Dict[str, List[ServiceDef]] = {}
        for svc in self.services.values():
            by_cat.setdefault(svc.category, []).append(svc)

        total = len(self.services)
        up = sum(1 for s in self.services.values() if s.status == "up")

        for cat, svcs in sorted(by_cat.items()):
            lines.append(f"\n  {cat}:")
            for s in svcs:
                icon = {"up": "+", "down": "X", "error": "!", "healed": "~",
                        "circuit_open": "O", "unknown": "?"}.get(s.status, "?")
                lat = f"{s.last_latency_ms:.0f}ms" if s.last_latency_ms > 0 else ""
                cb = f" [{s.circuit.state.value}]" if s.circuit.state != CircuitState.CLOSED else ""
                lines.append(f"    [{icon}] {s.name:<25} {s.status:<15} {lat}{cb}")

        lines.append(f"\n  {up}/{total} services UP ({up/max(total,1)*100:.0f}%)")
        return "\n".join(lines)
