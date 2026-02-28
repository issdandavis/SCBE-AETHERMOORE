#!/usr/bin/env python3
"""
Agent Marketplace — Autonomous AI Agent Service with Profit Algorithm.

AI agents find clients, quote jobs, collect pre-payment, execute work,
and bill the remainder.  Every job guarantees minimum $1 profit.

Pricing Formula:
    pre_payment = estimated_token_cost + $5
    final_bill  = actual_cost + profit_margin(time, complexity, knowledge)
    profit_margin = max($1, target_profit - sunk_cost_recovery)

Revenue flows through Stripe / CashApp / Ko-fi via webhook connectors.

@module fleet/agent_marketplace
@layer Layer 13 (governance), Layer 5 (cost scaling)
@version 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

# Token cost estimates (USD per 1K tokens, approximate)
TOKEN_COSTS: Dict[str, float] = {
    "claude-opus":    0.075,    # $75 / 1M input
    "claude-sonnet":  0.015,    # $15 / 1M input
    "claude-haiku":   0.001,    # $1 / 1M input
    "gpt-4o":         0.005,    # $5 / 1M input
    "gpt-4o-mini":    0.00015,  # $0.15 / 1M input
    "gemini-flash":   0.0005,   # $0.50 / 1M input
    "gemini-pro":     0.00125,  # $1.25 / 1M input
    "ollama-local":   0.0,      # free (electricity only)
    "huggingface":    0.001,    # varies, ~$1/1M
    "grok":           0.005,    # $5 / 1M
}

# Minimum profit floor — never go below this
MIN_PROFIT_USD = 1.00
# Target profit per job
TARGET_PROFIT_USD = 5.00
# Maximum markup multiplier for complex/high-value work
MAX_MARKUP = 10.0

# Payment provider configurations
STRIPE_API_KEY_ENV = "STRIPE_SECRET_KEY"
CASHAPP_TAG_ENV = "CASHAPP_TAG"


# ═══════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════

class JobStatus(str, Enum):
    QUOTED = "quoted"
    PREPAID = "prepaid"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELIVERED = "delivered"
    PAID = "paid"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class JobCategory(str, Enum):
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    FEATURE_BUILD = "feature_build"
    RESEARCH = "research"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_WRITING = "content_writing"
    SECURITY_AUDIT = "security_audit"
    GOVERNANCE_SCAN = "governance_scan"
    TRAINING_DATA = "training_data"
    AUTOMATION = "automation"
    CONSULTATION = "consultation"
    CUSTOM = "custom"


# Complexity multipliers for profit calculation
CATEGORY_COMPLEXITY: Dict[str, float] = {
    "code_review":      1.0,
    "bug_fix":          1.5,
    "feature_build":    2.5,
    "research":         2.0,
    "data_analysis":    1.5,
    "content_writing":  1.0,
    "security_audit":   3.0,
    "governance_scan":  2.5,
    "training_data":    1.5,
    "automation":       2.0,
    "consultation":     2.0,
    "custom":           2.0,
}


@dataclass
class Client:
    """A registered client in the marketplace."""
    client_id: str
    name: str
    email: str = ""
    payment_method: str = "stripe"  # stripe | cashapp | kofi | manual
    payment_id: str = ""            # Stripe customer ID, CashApp tag, etc.
    total_spent: float = 0.0
    jobs_completed: int = 0
    trust_level: float = 1.0        # [0, 2] — affects pricing (loyal = cheaper)
    registered_at: float = field(default_factory=time.time)


@dataclass
class JobQuote:
    """A price quote for a job."""
    quote_id: str
    job_id: str
    estimated_tokens: int
    estimated_cost: float           # raw token cost
    pre_payment: float              # what client pays upfront
    estimated_total: float          # full estimated price
    profit_target: float            # expected profit
    model_plan: str                 # which model(s) to use
    valid_until: float              # quote expiry timestamp
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class Job:
    """A marketplace job from submission to payment."""
    job_id: str
    client_id: str
    category: JobCategory
    title: str
    description: str
    status: JobStatus = JobStatus.QUOTED
    quote: Optional[JobQuote] = None

    # Execution tracking
    tokens_used: int = 0
    actual_cost: float = 0.0
    time_started: float = 0.0
    time_completed: float = 0.0
    execution_minutes: float = 0.0

    # Payment tracking
    pre_payment_received: float = 0.0
    final_bill: float = 0.0
    profit: float = 0.0
    payment_status: str = "pending"  # pending | pre_paid | invoiced | paid

    # Deliverables
    deliverables: List[str] = field(default_factory=list)
    result_summary: str = ""

    # Metadata
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Profit Algorithm
# ═══════════════════════════════════════════════════════════════

def calculate_profit_margin(
    actual_cost: float,
    execution_minutes: float,
    category: str,
    knowledge_growth: float = 0.0,
    client_trust: float = 1.0,
) -> Dict[str, float]:
    """Calculate profit margin for a completed job.

    The algorithm ensures:
    - Minimum $1 profit on ANY job (even if it cost $0.001 in tokens)
    - Target $5 profit for standard jobs
    - No maximum — high-value work earns more
    - Loyal clients get better rates (higher trust = lower markup)

    Formula:
        base_profit = max(MIN_PROFIT, TARGET_PROFIT * complexity)
        time_factor = log2(1 + minutes) * 0.5  (longer = more value)
        knowledge_factor = knowledge_growth * 2.0  (learning = value)
        loyalty_discount = 1.0 / client_trust  (higher trust = lower price)

        profit = base_profit * time_factor * (1 + knowledge_factor) * loyalty_discount
        profit = max(MIN_PROFIT, profit)  # NEVER below $1
    """
    complexity = CATEGORY_COMPLEXITY.get(category, 2.0)

    # Base profit: complexity-weighted target
    base_profit = max(MIN_PROFIT_USD, TARGET_PROFIT_USD * complexity / 2.0)

    # Time factor: longer jobs create more value (log scale, not linear)
    time_factor = max(0.5, math.log2(1 + execution_minutes) * 0.5)

    # Knowledge factor: if the agent learned something reusable, it's worth more
    knowledge_factor = 1.0 + (knowledge_growth * 2.0)

    # Loyalty discount: repeat clients pay less (trust ranges 1.0-2.0)
    loyalty_discount = 1.0 / max(0.5, client_trust)

    # Raw profit calculation
    raw_profit = base_profit * time_factor * knowledge_factor * loyalty_discount

    # Apply bounds
    profit = max(MIN_PROFIT_USD, raw_profit)

    # Profit-to-cost ratio check: don't charge 100x the actual cost
    if actual_cost > 0:
        max_total = actual_cost * MAX_MARKUP
        if profit > max_total:
            profit = max(MIN_PROFIT_USD, max_total)

    return {
        "profit": round(profit, 2),
        "base_profit": round(base_profit, 2),
        "time_factor": round(time_factor, 4),
        "knowledge_factor": round(knowledge_factor, 4),
        "loyalty_discount": round(loyalty_discount, 4),
        "complexity": complexity,
        "actual_cost": round(actual_cost, 4),
        "total_bill": round(actual_cost + profit, 2),
    }


def estimate_tokens(description: str, category: str) -> int:
    """Estimate how many tokens a job will require.

    Rough heuristics based on job category:
    - Code review: ~2K tokens per 100 lines
    - Bug fix: ~5K tokens (investigation + fix)
    - Feature build: ~10K-50K tokens
    - Research: ~8K tokens
    - Content writing: ~3K tokens per page
    """
    base_tokens = {
        "code_review":      2000,
        "bug_fix":          5000,
        "feature_build":    20000,
        "research":         8000,
        "data_analysis":    5000,
        "content_writing":  3000,
        "security_audit":   15000,
        "governance_scan":  10000,
        "training_data":    5000,
        "automation":       10000,
        "consultation":     3000,
        "custom":           5000,
    }
    base = base_tokens.get(category, 5000)

    # Scale by description length (longer description = more complex job)
    desc_words = len(description.split())
    if desc_words > 100:
        base = int(base * 1.5)
    if desc_words > 300:
        base = int(base * 2.0)

    return base


def select_model(category: str, budget: float) -> str:
    """Select the best model for a job category and budget.

    Strategy:
    - Security/governance: use Claude Sonnet (accurate, trustworthy)
    - Code work: use Claude Haiku or local Ollama (fast, cheap)
    - Content: use GPT-4o-mini (good writing, cheap)
    - Research: use Gemini Flash (fast, good at search)
    - If budget is tiny: always use cheapest option
    """
    if budget < 0.10:
        return "ollama-local"

    model_map = {
        "code_review":      "claude-haiku",
        "bug_fix":          "claude-sonnet",
        "feature_build":    "claude-sonnet",
        "research":         "gemini-flash",
        "data_analysis":    "gemini-pro",
        "content_writing":  "gpt-4o-mini",
        "security_audit":   "claude-sonnet",
        "governance_scan":  "claude-sonnet",
        "training_data":    "claude-haiku",
        "automation":       "claude-haiku",
        "consultation":     "claude-sonnet",
        "custom":           "claude-haiku",
    }
    return model_map.get(category, "claude-haiku")


# ═══════════════════════════════════════════════════════════════
# Payment Helpers
# ═══════════════════════════════════════════════════════════════

def create_stripe_payment_intent(
    amount_cents: int,
    client_email: str,
    job_id: str,
    description: str,
) -> Dict[str, Any]:
    """Create a Stripe PaymentIntent for pre-payment or final billing.

    Requires STRIPE_SECRET_KEY env var.
    Returns payment intent details or mock if Stripe unavailable.
    """
    stripe_key = os.environ.get(STRIPE_API_KEY_ENV, "").strip()
    if not stripe_key:
        return {
            "status": "mock",
            "payment_intent_id": f"pi_mock_{job_id[:8]}",
            "amount_cents": amount_cents,
            "note": "Set STRIPE_SECRET_KEY to enable real payments",
        }

    try:
        import urllib.request

        payload = json.dumps({
            "amount": amount_cents,
            "currency": "usd",
            "receipt_email": client_email,
            "description": description,
            "metadata[job_id]": job_id,
        }).encode()

        # Stripe uses form-encoded, not JSON
        form_data = "&".join(
            f"{k}={v}" for k, v in {
                "amount": str(amount_cents),
                "currency": "usd",
                "receipt_email": client_email,
                "description": description,
                f"metadata[job_id]": job_id,
            }.items()
        ).encode()

        req = urllib.request.Request(
            "https://api.stripe.com/v1/payment_intents",
            data=form_data,
            headers={
                "Authorization": f"Bearer {stripe_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


# ═══════════════════════════════════════════════════════════════
# AgentMarketplace
# ═══════════════════════════════════════════════════════════════

class AgentMarketplace:
    """Autonomous agent service marketplace.

    Flow:
        1. Client submits job description
        2. System generates quote (estimated tokens + profit)
        3. Client pre-pays (covers expected cost + $5 profit)
        4. Agent executes the work
        5. System calculates final bill (actual cost + profit algorithm)
        6. If final < pre-payment: refund difference
        7. If final > pre-payment: invoice remainder
        8. Deliver results

    Revenue model:
        - $1 minimum profit per job (floor)
        - $5 target profit for standard jobs
        - No maximum — complex work earns proportionally more
        - $1 in 10 minutes = $6/hr automated = free money
    """

    def __init__(self) -> None:
        self.clients: Dict[str, Client] = {}
        self.jobs: Dict[str, Job] = {}
        self.revenue_log: List[Dict[str, Any]] = []
        self.total_revenue: float = 0.0
        self.total_profit: float = 0.0
        self.total_jobs_completed: int = 0

    # ── Client Management ────────────────────────────────────

    def register_client(
        self,
        name: str,
        email: str = "",
        payment_method: str = "stripe",
        payment_id: str = "",
    ) -> Client:
        """Register a new client."""
        cid = f"client-{uuid.uuid4().hex[:10]}"
        client = Client(
            client_id=cid,
            name=name,
            email=email,
            payment_method=payment_method,
            payment_id=payment_id,
        )
        self.clients[cid] = client
        return client

    # ── Job Submission & Quoting ─────────────────────────────

    def submit_job(
        self,
        client_id: str,
        category: str,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Submit a new job and auto-generate a quote."""
        if client_id not in self.clients:
            raise ValueError(f"Unknown client: {client_id}")

        cat = JobCategory(category) if category in [e.value for e in JobCategory] else JobCategory.CUSTOM
        jid = f"job-{uuid.uuid4().hex[:10]}"

        job = Job(
            job_id=jid,
            client_id=client_id,
            category=cat,
            title=title,
            description=description,
            metadata=metadata or {},
        )

        # Auto-generate quote
        job.quote = self._generate_quote(job)
        self.jobs[jid] = job
        return job

    def _generate_quote(self, job: Job) -> JobQuote:
        """Generate a price quote for a job."""
        est_tokens = estimate_tokens(job.description, job.category.value)
        model = select_model(job.category.value, budget=50.0)
        cost_per_1k = TOKEN_COSTS.get(model, 0.005)
        est_cost = (est_tokens / 1000.0) * cost_per_1k

        # Pre-payment: estimated cost + target profit
        pre_payment = est_cost + TARGET_PROFIT_USD

        # Round up to nearest $0.50 for clean pricing
        pre_payment = math.ceil(pre_payment * 2) / 2.0
        pre_payment = max(pre_payment, MIN_PROFIT_USD + 1.0)  # at least $2

        complexity = CATEGORY_COMPLEXITY.get(job.category.value, 2.0)
        est_total = est_cost + (TARGET_PROFIT_USD * complexity / 2.0)

        return JobQuote(
            quote_id=f"quote-{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            estimated_tokens=est_tokens,
            estimated_cost=round(est_cost, 4),
            pre_payment=round(pre_payment, 2),
            estimated_total=round(est_total, 2),
            profit_target=round(TARGET_PROFIT_USD * complexity / 2.0, 2),
            model_plan=model,
            valid_until=time.time() + 3600,  # 1 hour expiry
            breakdown={
                "token_estimate": est_tokens,
                "cost_per_1k": cost_per_1k,
                "raw_token_cost": round(est_cost, 4),
                "profit_target": round(TARGET_PROFIT_USD * complexity / 2.0, 2),
                "pre_payment": round(pre_payment, 2),
                "model": model,
            },
        )

    # ── Payment ──────────────────────────────────────────────

    def accept_quote(self, job_id: str) -> Dict[str, Any]:
        """Client accepts a quote — triggers pre-payment collection."""
        job = self.jobs.get(job_id)
        if not job or not job.quote:
            return {"error": "Job or quote not found"}

        client = self.clients.get(job.client_id)
        if not client:
            return {"error": "Client not found"}

        # Create payment intent
        amount_cents = int(job.quote.pre_payment * 100)
        payment = create_stripe_payment_intent(
            amount_cents=amount_cents,
            client_email=client.email,
            job_id=job.job_id,
            description=f"SCBE Agent: {job.title} (pre-payment)",
        )

        return {
            "job_id": job.job_id,
            "pre_payment": job.quote.pre_payment,
            "payment": payment,
            "next_step": "Once payment confirms, job moves to IN_PROGRESS",
        }

    def confirm_prepayment(self, job_id: str, amount: float) -> Dict[str, Any]:
        """Confirm that pre-payment was received (webhook callback)."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}

        job.pre_payment_received = amount
        job.status = JobStatus.PREPAID
        job.payment_status = "pre_paid"

        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "pre_payment_received": amount,
            "ready_for_execution": True,
        }

    # ── Job Execution ────────────────────────────────────────

    def start_job(self, job_id: str) -> Dict[str, Any]:
        """Mark a job as in-progress. Called when agent begins work."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        if job.status not in (JobStatus.PREPAID, JobStatus.QUOTED):
            return {"error": f"Job in wrong state: {job.status.value}"}

        job.status = JobStatus.IN_PROGRESS
        job.time_started = time.time()

        return {
            "job_id": job.job_id,
            "status": "in_progress",
            "started_at": job.time_started,
        }

    def log_tokens(self, job_id: str, tokens: int, cost: float) -> None:
        """Log token usage during execution."""
        job = self.jobs.get(job_id)
        if job:
            job.tokens_used += tokens
            job.actual_cost += cost

    def complete_job(
        self,
        job_id: str,
        result_summary: str,
        deliverables: Optional[List[str]] = None,
        knowledge_growth: float = 0.0,
    ) -> Dict[str, Any]:
        """Complete a job — calculate final bill and profit.

        Args:
            job_id: the job to complete
            result_summary: what was delivered
            deliverables: list of file paths, URLs, etc.
            knowledge_growth: [0, 1] how much the agent learned (reusable knowledge)
        """
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}

        client = self.clients.get(job.client_id)
        client_trust = client.trust_level if client else 1.0

        job.time_completed = time.time()
        job.execution_minutes = (job.time_completed - job.time_started) / 60.0 if job.time_started else 0.0
        job.status = JobStatus.COMPLETED
        job.result_summary = result_summary
        job.deliverables = deliverables or []

        # ── THE PROFIT ALGORITHM ──
        margin = calculate_profit_margin(
            actual_cost=job.actual_cost,
            execution_minutes=job.execution_minutes,
            category=job.category.value,
            knowledge_growth=knowledge_growth,
            client_trust=client_trust,
        )

        job.profit = margin["profit"]
        job.final_bill = margin["total_bill"]

        # Payment reconciliation
        balance = job.final_bill - job.pre_payment_received
        if balance <= 0:
            # Client overpaid — owe refund
            payment_action = "refund"
            refund_amount = abs(balance)
        else:
            # Client owes more
            payment_action = "invoice_remainder"
            refund_amount = 0.0

        # Update totals
        self.total_revenue += job.final_bill
        self.total_profit += job.profit
        self.total_jobs_completed += 1

        if client:
            client.total_spent += job.final_bill
            client.jobs_completed += 1
            # Loyalty growth: trust increases with each completed job
            client.trust_level = min(2.0, client.trust_level + 0.05)

        # Revenue log
        self.revenue_log.append({
            "job_id": job.job_id,
            "client_id": job.client_id,
            "category": job.category.value,
            "actual_cost": job.actual_cost,
            "profit": job.profit,
            "total_bill": job.final_bill,
            "pre_payment": job.pre_payment_received,
            "balance": round(balance, 2),
            "tokens_used": job.tokens_used,
            "execution_minutes": round(job.execution_minutes, 2),
            "timestamp": time.time(),
        })
        if len(self.revenue_log) > 1000:
            self.revenue_log = self.revenue_log[-1000:]

        return {
            "job_id": job.job_id,
            "status": "completed",
            "result_summary": result_summary,
            "deliverables": job.deliverables,
            "billing": {
                "actual_token_cost": round(job.actual_cost, 4),
                "tokens_used": job.tokens_used,
                "execution_minutes": round(job.execution_minutes, 2),
                "profit": job.profit,
                "final_bill": job.final_bill,
                "pre_payment_received": job.pre_payment_received,
                "balance": round(balance, 2),
                "payment_action": payment_action,
                "refund_amount": round(refund_amount, 2) if refund_amount else None,
            },
            "margin_breakdown": margin,
        }

    # ── Status & Analytics ───────────────────────────────────

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get full status of a job."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        return {
            "job_id": job.job_id,
            "title": job.title,
            "category": job.category.value,
            "status": job.status.value,
            "tokens_used": job.tokens_used,
            "actual_cost": round(job.actual_cost, 4),
            "pre_payment": job.pre_payment_received,
            "final_bill": job.final_bill,
            "profit": job.profit,
            "created_at": job.created_at,
        }

    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Overall marketplace analytics."""
        active_jobs = sum(1 for j in self.jobs.values() if j.status == JobStatus.IN_PROGRESS)
        avg_profit = self.total_profit / max(1, self.total_jobs_completed)
        hourly_rate = 0.0
        if self.revenue_log:
            total_minutes = sum(e.get("execution_minutes", 0) for e in self.revenue_log)
            if total_minutes > 0:
                hourly_rate = (self.total_profit / total_minutes) * 60

        return {
            "total_clients": len(self.clients),
            "total_jobs": len(self.jobs),
            "active_jobs": active_jobs,
            "completed_jobs": self.total_jobs_completed,
            "total_revenue": round(self.total_revenue, 2),
            "total_profit": round(self.total_profit, 2),
            "average_profit_per_job": round(avg_profit, 2),
            "effective_hourly_rate": round(hourly_rate, 2),
            "revenue_log_size": len(self.revenue_log),
        }

    def get_revenue_report(self, last_n: int = 20) -> Dict[str, Any]:
        """Revenue report for recent jobs."""
        recent = self.revenue_log[-last_n:]
        return {
            "period_revenue": round(sum(e["total_bill"] for e in recent), 2),
            "period_profit": round(sum(e["profit"] for e in recent), 2),
            "period_jobs": len(recent),
            "entries": recent,
        }
