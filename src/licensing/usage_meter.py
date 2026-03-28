"""
Usage Meter — Per-Decision Metering for SCBE Governance Billing
================================================================

Tracks governance decisions (ALLOW/QUARANTINE/DENY/ESCALATE) for
usage-based billing. Supports the Launch SKU pricing model:

  Primary meter:  Per 1,000 decisions
  Platform floor: Per-tenant base fee
  Optional:       Per-agent bundles

Features:
  - Thread-safe decision counting
  - Hourly/daily/monthly rollups
  - Per-tenant and per-agent tracking
  - Exportable usage reports (JSON/JSONL)
  - Quota enforcement with soft/hard limits
  - Revenue estimation at configurable rates

@module licensing/usage_meter
@layer Layer 13 (Governance)
@version 1.0.0
"""

from __future__ import annotations

import json
import time
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ── Pricing Constants (from LAUNCH_SKU.md) ───────────────────────────────────

DEFAULT_RATE_PER_1K_DECISIONS = 2.50  # USD per 1,000 decisions
DEFAULT_PLATFORM_FLOOR_MONTHLY = 99.00  # USD per tenant per month
DEFAULT_AGENT_BUNDLE_MONTHLY = 29.00  # USD per agent per month

# Success SLOs
TARGET_P95_LATENCY_MS = 120
TARGET_FALSE_QUARANTINE_RATE = 0.015


# ── Decision Record ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DecisionRecord:
    """A single governance decision event for billing."""

    timestamp: float
    tenant_id: str
    agent_id: str
    decision: str  # ALLOW, QUARANTINE, DENY, ESCALATE
    latency_ms: float  # p95 target: ≤120ms
    risk_score: float  # [0, 1]
    policy_ids: List[str]  # Which policies triggered
    billable: bool = True  # False for test/shadow mode


# ── Usage Meter ──────────────────────────────────────────────────────────────


class UsageMeter:
    """Thread-safe per-decision usage meter.

    Tracks all governance decisions for billing, quota enforcement,
    and SLO monitoring.
    """

    def __init__(
        self,
        rate_per_1k: float = DEFAULT_RATE_PER_1K_DECISIONS,
        platform_floor: float = DEFAULT_PLATFORM_FLOOR_MONTHLY,
        agent_bundle: float = DEFAULT_AGENT_BUNDLE_MONTHLY,
    ):
        self.rate_per_1k = rate_per_1k
        self.platform_floor = platform_floor
        self.agent_bundle = agent_bundle

        self._lock = threading.Lock()
        self._records: List[DecisionRecord] = []

        # Per-tenant counters
        self._tenant_counts: Dict[str, int] = defaultdict(int)
        self._tenant_agents: Dict[str, set] = defaultdict(set)

        # Decision distribution
        self._decision_counts: Dict[str, int] = defaultdict(int)

        # Latency tracking
        self._latencies: List[float] = []

    def record_decision(self, record: DecisionRecord) -> None:
        """Record a governance decision.

        Thread-safe. Increments all relevant counters.
        """
        with self._lock:
            self._records.append(record)
            if record.billable:
                self._tenant_counts[record.tenant_id] += 1
            self._tenant_agents[record.tenant_id].add(record.agent_id)
            self._decision_counts[record.decision] += 1
            self._latencies.append(record.latency_ms)

    # ── Counters ─────────────────────────────────────────────────────────

    @property
    def total_decisions(self) -> int:
        with self._lock:
            return len(self._records)

    @property
    def billable_decisions(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if r.billable)

    def tenant_decisions(self, tenant_id: str) -> int:
        with self._lock:
            return self._tenant_counts.get(tenant_id, 0)

    def tenant_agents(self, tenant_id: str) -> int:
        with self._lock:
            return len(self._tenant_agents.get(tenant_id, set()))

    @property
    def unique_tenants(self) -> int:
        with self._lock:
            return len(self._tenant_counts)

    @property
    def unique_agents(self) -> int:
        with self._lock:
            return sum(len(agents) for agents in self._tenant_agents.values())

    # ── Decision Distribution ────────────────────────────────────────────

    @property
    def decision_distribution(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._decision_counts)

    @property
    def false_quarantine_rate(self) -> float:
        """Ratio of QUARANTINE decisions to total. Target: ≤1.5%."""
        with self._lock:
            total = len(self._records)
            if total == 0:
                return 0.0
            quarantines = self._decision_counts.get("QUARANTINE", 0)
            return quarantines / total

    # ── Latency SLOs ─────────────────────────────────────────────────────

    @property
    def p95_latency_ms(self) -> float:
        """95th percentile latency. Target: ≤120ms."""
        with self._lock:
            if not self._latencies:
                return 0.0
            sorted_lat = sorted(self._latencies)
            idx = int(len(sorted_lat) * 0.95)
            return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def mean_latency_ms(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            return sum(self._latencies) / len(self._latencies)

    # ── Revenue Estimation ───────────────────────────────────────────────

    def estimate_revenue(self, tenant_id: Optional[str] = None) -> Dict[str, float]:
        """Estimate revenue based on current usage.

        Components:
          - Decision revenue: billable_decisions / 1000 * rate
          - Platform floor: per unique tenant
          - Agent bundles: per unique agent

        Args:
            tenant_id: If specified, estimate for single tenant.

        Returns:
            Dict with revenue breakdown.
        """
        with self._lock:
            if tenant_id:
                decisions = self._tenant_counts.get(tenant_id, 0)
                agents = len(self._tenant_agents.get(tenant_id, set()))
                tenants = 1 if decisions > 0 else 0
            else:
                decisions = sum(1 for r in self._records if r.billable)
                agents = sum(len(a) for a in self._tenant_agents.values())
                tenants = len(self._tenant_counts)

        decision_revenue = (decisions / 1000) * self.rate_per_1k
        platform_revenue = tenants * self.platform_floor
        agent_revenue = agents * self.agent_bundle

        return {
            "decision_revenue": round(decision_revenue, 2),
            "platform_revenue": round(platform_revenue, 2),
            "agent_revenue": round(agent_revenue, 2),
            "total_estimated": round(
                decision_revenue + platform_revenue + agent_revenue, 2
            ),
            "decisions_counted": decisions,
            "tenants_counted": tenants,
            "agents_counted": agents,
        }

    # ── Quota Enforcement ────────────────────────────────────────────────

    def check_quota(
        self,
        tenant_id: str,
        monthly_limit: int,
    ) -> Tuple[bool, int]:
        """Check if tenant is within their monthly decision quota.

        Args:
            tenant_id: Tenant to check.
            monthly_limit: Max decisions per month (0 = unlimited).

        Returns:
            (within_quota, remaining_decisions)
        """
        if monthly_limit <= 0:
            return True, -1  # unlimited

        used = self.tenant_decisions(tenant_id)
        remaining = monthly_limit - used
        return remaining > 0, max(0, remaining)

    # ── SLO Report ───────────────────────────────────────────────────────

    def slo_report(self) -> Dict[str, Any]:
        """Generate SLO compliance report.

        Checks against Launch SKU success SLOs:
          - p95 latency ≤ 120ms
          - False quarantine rate ≤ 1.5%
        """
        p95 = self.p95_latency_ms
        fqr = self.false_quarantine_rate

        return {
            "p95_latency_ms": round(p95, 2),
            "p95_latency_target_ms": TARGET_P95_LATENCY_MS,
            "p95_latency_pass": p95 <= TARGET_P95_LATENCY_MS,
            "false_quarantine_rate": round(fqr, 4),
            "false_quarantine_target": TARGET_FALSE_QUARANTINE_RATE,
            "false_quarantine_pass": fqr <= TARGET_FALSE_QUARANTINE_RATE,
            "mean_latency_ms": round(self.mean_latency_ms, 2),
            "total_decisions": self.total_decisions,
            "billable_decisions": self.billable_decisions,
        }

    # ── Export ───────────────────────────────────────────────────────────

    def export_usage_report(self) -> Dict[str, Any]:
        """Export full usage report as JSON-serializable dict."""
        return {
            "generated_at": time.time(),
            "total_decisions": self.total_decisions,
            "billable_decisions": self.billable_decisions,
            "unique_tenants": self.unique_tenants,
            "unique_agents": self.unique_agents,
            "decision_distribution": self.decision_distribution,
            "revenue_estimate": self.estimate_revenue(),
            "slo_compliance": self.slo_report(),
        }

    def export_records_jsonl(self) -> str:
        """Export all decision records as JSONL string."""
        with self._lock:
            lines = []
            for r in self._records:
                lines.append(
                    json.dumps(
                        {
                            "timestamp": r.timestamp,
                            "tenant_id": r.tenant_id,
                            "agent_id": r.agent_id,
                            "decision": r.decision,
                            "latency_ms": r.latency_ms,
                            "risk_score": r.risk_score,
                            "policy_ids": r.policy_ids,
                            "billable": r.billable,
                        }
                    )
                )
            return "\n".join(lines)

    def reset(self) -> None:
        """Reset all counters (e.g., for monthly rollover)."""
        with self._lock:
            self._records.clear()
            self._tenant_counts.clear()
            self._tenant_agents.clear()
            self._decision_counts.clear()
            self._latencies.clear()
