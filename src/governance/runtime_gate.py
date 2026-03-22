"""Runtime Governance Gate — The actual thing between intent and execution.
=========================================================================

This sits between an LLM producing a tool call and the tool executing.
Every action passes through here. No exceptions.

Decisions:
  ALLOW     — execute normally
  DENY      — block, return fail-to-noise
  QUARANTINE — hold for review, log, do not execute yet
  REROUTE   — redirect to a safer alternative action

The gate computes:
  1. Tongue coordinates from the action description
  2. Spin vector relative to session centroid
  3. Harmonic cost from Poincare distance
  4. Cross-check: spin + cost + tongue balance → decision

This is not a filter. It's a cost function. Safe actions are cheap.
Dangerous actions are expensive. Impossible actions cost infinity.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PHI = 1.618033988749895
PI = math.pi
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_WEIGHTS = tuple(PHI ** k for k in range(6))
WORD_RE = re.compile(r"[A-Za-z0-9_']+")


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    REROUTE = "REROUTE"


@dataclass
class GateResult:
    """What the gate returns for every action."""
    decision: Decision
    cost: float
    spin_magnitude: int
    tongue_coords: List[float]
    signals: List[str]
    reroute_to: Optional[str] = None
    noise: Optional[bytes] = None  # fail-to-noise: deterministic noise on DENY
    # Audit
    action_hash: str = ""
    timestamp: float = 0.0
    session_query_count: int = 0
    cumulative_cost: float = 0.0


def _fail_to_noise(action_hash: str, length: int = 32) -> bytes:
    """Generate deterministic noise from the action hash.

    Same input always produces same noise (reproducible for audit).
    The noise looks random but is derived from the denied action —
    if someone asks 'what did the system output?', the answer is
    'noise derived from the hash of what was blocked', which is
    auditable without revealing the blocked content.
    """
    h = hashlib.sha256(f"fail-to-noise:{action_hash}".encode()).digest()
    noise = bytearray()
    block = h
    while len(noise) < length:
        block = hashlib.sha256(block).digest()
        noise.extend(block)
    return bytes(noise[:length])


@dataclass
class RerouteRule:
    """Maps dangerous action patterns to safer alternatives."""
    pattern: str
    replacement: str
    reason: str


# Default reroute table — dangerous actions → safe alternatives
DEFAULT_REROUTES: List[RerouteRule] = [
    RerouteRule("file.*read.*/etc/passwd", "file_read_denied", "system file access blocked"),
    RerouteRule("http.*external.*send", "log_intent_only", "external data send → log only"),
    RerouteRule("execute.*shell|exec.*command|os\\.system", "sandbox_execute", "shell exec → sandboxed"),
    RerouteRule("delete.*all|drop.*table|rm.*-rf", "soft_delete", "destructive op → soft delete"),
    RerouteRule("api.*key|secret|token|password", "redact_and_log", "credential access → redacted"),
    RerouteRule("send.*email|post.*slack|publish", "queue_for_review", "external publish → review queue"),
]


class RuntimeGate:
    """The gate. Every action goes through here.

    Maintains session state:
      - Running centroid of tongue coordinates
      - Cumulative cost (tracks drift over conversation)
      - Query count (tracks volume)
      - Immune memory (known attack hashes)
      - Reflex table (known safe action hashes)
    """

    def __init__(
        self,
        *,
        cost_allow: float = 10.0,
        cost_quarantine: float = 50.0,
        cost_deny: float = 500.0,
        spin_quarantine: int = 5,
        spin_deny: int = 6,
        cumulative_cost_quarantine: float = 200.0,
        cumulative_cost_deny: float = 1000.0,
        reroute_rules: Optional[List[RerouteRule]] = None,
    ):
        # Thresholds
        self.cost_allow = cost_allow
        self.cost_quarantine = cost_quarantine
        self.cost_deny = cost_deny
        self.spin_quarantine = spin_quarantine
        self.spin_deny = spin_deny
        self.cumulative_cost_quarantine = cumulative_cost_quarantine
        self.cumulative_cost_deny = cumulative_cost_deny

        # Reroute table
        self._reroute_rules = reroute_rules or DEFAULT_REROUTES
        self._reroute_patterns = [
            (re.compile(r.pattern, re.IGNORECASE), r) for r in self._reroute_rules
        ]

        # Session state
        self._centroid: Optional[np.ndarray] = None
        self._centroid_count: int = 0
        self._cumulative_cost: float = 0.0
        self._query_count: int = 0
        self._immune: set = set()       # known attack hashes → instant DENY
        self._reflex: dict = {}         # known safe hashes → instant ALLOW
        self._audit_log: List[GateResult] = []

    # ------------------------------------------------------------------ #
    #  Tongue coordinate extraction
    # ------------------------------------------------------------------ #

    def _text_to_coords(self, text: str) -> List[float]:
        words = WORD_RE.findall(text)
        wc = len(words)
        chars = max(len(text), 1)
        unique = len(set(w.lower() for w in words))
        digits = sum(c.isdigit() for c in text)
        upper = sum(c.isupper() for c in text)
        punct = sum(c in ".,;:!?-_/()[]{}@#$%^&*" for c in text)
        urls = len(re.findall(r"https?://", text))

        return [
            min(1.0, 0.2 + 0.4 * (upper / chars) * 5 + 0.15 * (urls > 0)),
            min(1.0, wc / 600.0),
            min(1.0, unique / max(wc, 1)),
            min(1.0, (digits / chars) * 10),
            min(1.0, (upper / chars) * 5),
            min(1.0, (punct / chars) * 8),
        ]

    # ------------------------------------------------------------------ #
    #  Spin quantization
    # ------------------------------------------------------------------ #

    def _spin(self, coords: List[float], threshold: float = 0.05) -> Tuple[Tuple[int, ...], int]:
        if self._centroid is None:
            centroid = [0.4, 0.2, 0.5, 0.1, 0.2, 0.3]
        else:
            centroid = self._centroid.tolist()

        spins = []
        for l in range(6):
            diff = coords[l] - centroid[l]
            if diff > threshold:
                spins.append(1)
            elif diff < -threshold:
                spins.append(-1)
            else:
                spins.append(0)
        return tuple(spins), sum(abs(s) for s in spins)

    # ------------------------------------------------------------------ #
    #  Cost computation
    # ------------------------------------------------------------------ #

    def _harmonic_cost(self, coords: List[float]) -> float:
        if self._centroid is None:
            centroid = np.array([0.4, 0.2, 0.5, 0.1, 0.2, 0.3])
        else:
            centroid = self._centroid

        tc = np.array(coords)
        weights = np.array(TONGUE_WEIGHTS)
        weighted_dist = float(np.sqrt(np.sum(weights * (tc - centroid) ** 2)))
        d_star = min(weighted_dist, 5.0)  # clamp to avoid overflow
        return PI ** (PHI * d_star)

    # ------------------------------------------------------------------ #
    #  Reroute check
    # ------------------------------------------------------------------ #

    def _check_reroute(self, action_text: str) -> Optional[RerouteRule]:
        for pattern, rule in self._reroute_patterns:
            if pattern.search(action_text):
                return rule
        return None

    # ------------------------------------------------------------------ #
    #  Centroid update
    # ------------------------------------------------------------------ #

    def _update_centroid(self, coords: List[float]) -> None:
        tc = np.array(coords)
        if self._centroid is None:
            self._centroid = tc.copy()
            self._centroid_count = 1
        else:
            n = self._centroid_count + 1
            self._centroid = self._centroid * ((n - 1) / n) + tc / n
            self._centroid_count = n

    # ------------------------------------------------------------------ #
    #  THE GATE
    # ------------------------------------------------------------------ #

    def evaluate(self, action_text: str, tool_name: str = "") -> GateResult:
        """Evaluate an action. Returns ALLOW, DENY, QUARANTINE, or REROUTE.

        This is the function that sits between intent and execution.
        """
        self._query_count += 1
        ts = time.time()
        action_hash = hashlib.blake2s(
            action_text.encode("utf-8", errors="replace"), digest_size=8
        ).hexdigest()

        # ---- Fast paths (O(1)) ----

        full_text = f"{tool_name} {action_text}" if tool_name else action_text

        # ---- Reroute ALWAYS checks first (pattern match, not cost-based) ----
        reroute_rule = self._check_reroute(full_text)
        if reroute_rule is not None:
            coords = self._text_to_coords(full_text)
            result = GateResult(
                decision=Decision.REROUTE, cost=0.0,
                spin_magnitude=0, tongue_coords=coords,
                signals=[f"reroute_match({reroute_rule.pattern})"],
                reroute_to=reroute_rule.replacement,
                action_hash=action_hash, timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # Auto-calibrate: first 5 actions build the centroid (assumed clean)
        # This is the "incubation" period — the system learns what normal looks like
        if self._query_count <= 5 and action_hash not in self._immune:
            coords = self._text_to_coords(full_text)
            self._update_centroid(coords)
            self._cumulative_cost += 1.0  # nominal cost during calibration
            result = GateResult(
                decision=Decision.ALLOW, cost=1.0,
                spin_magnitude=0, tongue_coords=coords,
                signals=["calibrating"],
                action_hash=action_hash, timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # Immune memory: known attack → instant DENY + noise
        if action_hash in self._immune:
            result = GateResult(
                decision=Decision.DENY, cost=float("inf"),
                spin_magnitude=6, tongue_coords=[0.0] * 6,
                signals=["immune_memory_hit"],
                noise=_fail_to_noise(action_hash),
                action_hash=action_hash, timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # Reflex table: known safe → instant ALLOW
        if action_hash in self._reflex:
            result = GateResult(
                decision=Decision.ALLOW, cost=1.0,
                spin_magnitude=0, tongue_coords=[0.5] * 6,
                signals=["reflex_hit"],
                action_hash=action_hash, timestamp=ts,
                session_query_count=self._query_count,
                cumulative_cost=self._cumulative_cost,
            )
            self._audit_log.append(result)
            return result

        # ---- Full evaluation ----

        full_text = f"{tool_name} {action_text}" if tool_name else action_text
        coords = self._text_to_coords(full_text)
        spins, magnitude = self._spin(coords)
        cost = self._harmonic_cost(coords)

        self._update_centroid(coords)
        self._cumulative_cost += cost

        signals: List[str] = []

        # ---- Cost-based decision ----

        # Per-action cost
        if cost > self.cost_deny:
            signals.append(f"cost_deny({cost:.1f}>{self.cost_deny})")
        elif cost > self.cost_quarantine:
            signals.append(f"cost_quarantine({cost:.1f}>{self.cost_quarantine})")
        elif cost > self.cost_allow:
            signals.append(f"cost_elevated({cost:.1f}>{self.cost_allow})")

        # Spin magnitude
        if magnitude >= self.spin_deny:
            signals.append(f"spin_deny(mag={magnitude})")
        elif magnitude >= self.spin_quarantine:
            signals.append(f"spin_quarantine(mag={magnitude})")

        # Cumulative cost (session-level drift detection)
        if self._cumulative_cost > self.cumulative_cost_deny:
            signals.append(f"cumulative_deny({self._cumulative_cost:.1f}>{self.cumulative_cost_deny})")
        elif self._cumulative_cost > self.cumulative_cost_quarantine:
            signals.append(f"cumulative_quarantine({self._cumulative_cost:.1f}>{self.cumulative_cost_quarantine})")

        # ---- Decision logic ----

        decision = Decision.ALLOW
        noise = None

        # Any DENY signal → DENY + fail-to-noise
        if any("deny" in s for s in signals):
            decision = Decision.DENY
            self._immune.add(action_hash)  # learn this attack
            noise = _fail_to_noise(action_hash)

        # 2+ QUARANTINE signals → QUARANTINE
        elif sum(1 for s in signals if "quarantine" in s) >= 2:
            decision = Decision.QUARANTINE

        # 1 QUARANTINE signal → still QUARANTINE (conservative)
        elif any("quarantine" in s for s in signals):
            decision = Decision.QUARANTINE

        # Cost elevated but no quarantine signals → ALLOW with warning
        elif any("elevated" in s for s in signals):
            decision = Decision.ALLOW
            signals.append("allow_with_warning")

        # Clean → learn as safe reflex
        if decision == Decision.ALLOW and not signals:
            self._reflex[action_hash] = True

        result = GateResult(
            decision=decision, cost=cost,
            spin_magnitude=magnitude, tongue_coords=coords,
            signals=signals,
            noise=noise if decision == Decision.DENY else None,
            action_hash=action_hash, timestamp=ts,
            session_query_count=self._query_count,
            cumulative_cost=self._cumulative_cost,
        )
        self._audit_log.append(result)
        return result

    # ------------------------------------------------------------------ #
    #  Session management
    # ------------------------------------------------------------------ #

    def reset_session(self) -> None:
        """Reset session state (keep immune memory and reflexes)."""
        self._centroid = None
        self._centroid_count = 0
        self._cumulative_cost = 0.0
        self._query_count = 0
        self._audit_log = []

    def stats(self) -> Dict[str, Any]:
        decisions = {}
        for r in self._audit_log:
            decisions[r.decision.value] = decisions.get(r.decision.value, 0) + 1
        return {
            "query_count": self._query_count,
            "cumulative_cost": round(self._cumulative_cost, 2),
            "immune_signatures": len(self._immune),
            "reflex_entries": len(self._reflex),
            "decisions": decisions,
            "audit_log_size": len(self._audit_log),
        }
