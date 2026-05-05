"""Tiered council orchestrator for budget-bounded multi-provider LLM dispatch.

Routes a task through cost tiers (local free -> remote free -> cheap paid -> premium paid),
optionally running an MoA-style team of free models with a supervisor synthesis at each
tier, and only escalates when the rubric score fails the threshold or the prior tier
errored. Caller sets `budget_cents`; the council never crosses it.

The orchestrator is provider-agnostic: callers inject an adapter that knows how to call
each provider id and report (text, tokens, cents). This module does not import
huggingface_hub, anthropic, openai, or any other client SDK -- those live in the
adapters in src/aetherbrowser/provider_executor.py and src/agent_comms/harness_providers.py.

Pattern reference: matches polly_client.py's per-attempt trace shape but generalizes
beyond code generation to any text task. The team-mode synthesis follows the
Mixture-of-Agents pattern (Wang 2024): N candidates from peer models, then a single
supervisor pass that produces the consolidated answer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Iterable, Sequence

SCHEMA_VERSION = "scbe_tiered_council_v1"


class CostTier(IntEnum):
    LOCAL_FREE = 0
    REMOTE_FREE = 1
    CHEAP_PAID = 2
    PREMIUM_PAID = 3


PRICING_TIER_TO_COST_TIER: dict[str, CostTier] = {
    "free-local": CostTier.LOCAL_FREE,
    "free-tier": CostTier.REMOTE_FREE,
    "free-tier-or-paid": CostTier.REMOTE_FREE,
    "paid-or-free-credits": CostTier.REMOTE_FREE,
    "paid-low-cost": CostTier.CHEAP_PAID,
    "membership-credits": CostTier.CHEAP_PAID,
    "paid": CostTier.PREMIUM_PAID,
    "unknown": CostTier.PREMIUM_PAID,
}


@dataclass(frozen=True)
class CouncilProvider:
    id: str
    tier: CostTier
    family: str
    cents_per_1k_in: float
    cents_per_1k_out: float
    available: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": int(self.tier),
            "family": self.family,
            "cents_per_1k_in": self.cents_per_1k_in,
            "cents_per_1k_out": self.cents_per_1k_out,
            "available": self.available,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CouncilCall:
    provider_id: str
    prompt_tokens: int
    completion_tokens: int
    cents: float
    duration_ms: float
    response: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.response.strip() != ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cents": self.cents,
            "duration_ms": self.duration_ms,
            "response": self.response,
            "error": self.error,
            "ok": self.ok,
        }


@dataclass(frozen=True)
class TierAttempt:
    tier: CostTier
    members: tuple[CouncilCall, ...]
    synthesis_call: CouncilCall | None
    rubric_score: float
    rubric_passed: bool
    skipped_reason: str | None = None

    @property
    def best_response(self) -> str:
        if self.synthesis_call is not None and self.synthesis_call.ok:
            return self.synthesis_call.response
        good = [m for m in self.members if m.ok]
        if good:
            return max(good, key=lambda m: len(m.response)).response
        return ""

    @property
    def cents(self) -> float:
        total = sum(m.cents for m in self.members)
        if self.synthesis_call is not None:
            total += self.synthesis_call.cents
        return total

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": int(self.tier),
            "members": [m.to_dict() for m in self.members],
            "synthesis_call": self.synthesis_call.to_dict() if self.synthesis_call else None,
            "rubric_score": self.rubric_score,
            "rubric_passed": self.rubric_passed,
            "skipped_reason": self.skipped_reason,
            "best_response": self.best_response,
            "cents": self.cents,
        }


@dataclass(frozen=True)
class CouncilSolution:
    schema_version: str
    task: str
    final_answer: str
    final_tier: CostTier | None
    total_cents: float
    budget_cents: float
    rubric_threshold: float
    attempts: tuple[TierAttempt, ...]
    escalation_path: tuple[str, ...]
    solved: bool
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task": self.task,
            "final_answer": self.final_answer,
            "final_tier": int(self.final_tier) if self.final_tier is not None else None,
            "total_cents": self.total_cents,
            "budget_cents": self.budget_cents,
            "rubric_threshold": self.rubric_threshold,
            "attempts": [a.to_dict() for a in self.attempts],
            "escalation_path": list(self.escalation_path),
            "solved": self.solved,
            "note": self.note,
        }


# Adapter contract: caller supplies a callable that, given (provider_id, prompt, options),
# returns a CouncilCall. The council never imports SDKs directly.
ProviderAdapter = Callable[[str, str, dict[str, Any]], CouncilCall]

# Rubric contract: pure function (task, candidate) -> score in [0, 1].
RubricFn = Callable[[str, str], float]


def length_floor_rubric(min_chars: int = 40) -> RubricFn:
    """Default rubric: passes if the candidate has more than min_chars of non-whitespace.

    Intentionally cheap and naive; production callers should pass a domain-specific
    rubric (regex match, JSON-schema validate, downstream test pass, etc.).
    """

    def _score(_task: str, candidate: str) -> float:
        body = candidate.strip()
        if not body:
            return 0.0
        chars = len(body)
        if chars < min_chars:
            return chars / max(1, min_chars)
        return 1.0

    return _score


def keyword_rubric(*required_keywords: str) -> RubricFn:
    """Score by fraction of required keywords present (case-insensitive)."""

    keys = tuple(k.lower() for k in required_keywords if k)

    def _score(_task: str, candidate: str) -> float:
        if not keys:
            return 1.0
        haystack = candidate.lower()
        hits = sum(1 for k in keys if k in haystack)
        return hits / len(keys)

    return _score


def _group_by_tier(
    providers: Sequence[CouncilProvider],
) -> dict[CostTier, list[CouncilProvider]]:
    grouped: dict[CostTier, list[CouncilProvider]] = {tier: [] for tier in CostTier}
    for p in providers:
        if p.available:
            grouped[p.tier].append(p)
    return grouped


def _estimate_call_cents(provider: CouncilProvider, est_in_tokens: int, est_out_tokens: int) -> float:
    return provider.cents_per_1k_in * (est_in_tokens / 1000.0) + provider.cents_per_1k_out * (est_out_tokens / 1000.0)


@dataclass
class TieredCouncil:
    providers: Sequence[CouncilProvider]
    adapter: ProviderAdapter
    rubric: RubricFn = field(default_factory=lambda: length_floor_rubric())
    rubric_threshold: float = 0.7
    team_size_per_tier: int = 3
    synthesizer_provider_id: str | None = None
    est_in_tokens: int = 800
    est_out_tokens: int = 400
    synthesis_prefix: str = (
        "You are the supervisor for a council of peer models. The user task and the "
        "peer responses are below. Synthesize a single best answer. Prefer the most "
        "factually grounded peer; correct any contradictions; do not invent new claims.\n\n"
    )

    def solve(
        self,
        *,
        task: str,
        budget_cents: float,
        max_tier: CostTier = CostTier.PREMIUM_PAID,
        adapter_options: dict[str, Any] | None = None,
    ) -> CouncilSolution:
        """Run the tiered cascade. Stop at the first tier where rubric passes."""

        grouped = _group_by_tier(self.providers)
        attempts: list[TierAttempt] = []
        escalation_path: list[str] = []
        total_cents = 0.0
        last_attempt: TierAttempt | None = None

        for tier in CostTier:
            if tier > max_tier:
                break

            tier_providers = grouped[tier]
            if not tier_providers:
                attempts.append(
                    TierAttempt(
                        tier=tier,
                        members=(),
                        synthesis_call=None,
                        rubric_score=0.0,
                        rubric_passed=False,
                        skipped_reason="no_available_providers_at_tier",
                    )
                )
                escalation_path.append(f"tier{int(tier)}:no_providers")
                continue

            members = tier_providers[: max(1, self.team_size_per_tier)]
            est_member_cents = sum(_estimate_call_cents(p, self.est_in_tokens, self.est_out_tokens) for p in members)

            synthesizer = self._pick_synthesizer(tier, members, grouped)
            est_synth_cents = (
                _estimate_call_cents(synthesizer, self.est_in_tokens, self.est_out_tokens)
                if (synthesizer is not None and len(members) > 1)
                else 0.0
            )

            est_tier_cents = est_member_cents + est_synth_cents
            if total_cents + est_tier_cents > budget_cents and tier > CostTier.LOCAL_FREE:
                attempts.append(
                    TierAttempt(
                        tier=tier,
                        members=(),
                        synthesis_call=None,
                        rubric_score=0.0,
                        rubric_passed=False,
                        skipped_reason=(
                            f"budget_would_exceed:est={est_tier_cents:.4f}c "
                            f"spent={total_cents:.4f}c budget={budget_cents:.4f}c"
                        ),
                    )
                )
                escalation_path.append(f"tier{int(tier)}:budget_skip")
                continue

            member_calls = self._run_members(task, members, adapter_options or {})
            tier_cents = sum(c.cents for c in member_calls)

            synthesis_call: CouncilCall | None = None
            if len(member_calls) > 1 and synthesizer is not None and any(c.ok for c in member_calls):
                synthesis_prompt = self._build_synthesis_prompt(task, member_calls)
                synthesis_call = self._safe_call(
                    synthesizer.id,
                    synthesis_prompt,
                    adapter_options or {},
                )
                tier_cents += synthesis_call.cents

            total_cents += tier_cents

            best = self._best_text(member_calls, synthesis_call)
            score = self.rubric(task, best)
            passed = score >= self.rubric_threshold and bool(best.strip())

            attempt = TierAttempt(
                tier=tier,
                members=tuple(member_calls),
                synthesis_call=synthesis_call,
                rubric_score=score,
                rubric_passed=passed,
                skipped_reason=None,
            )
            attempts.append(attempt)
            escalation_path.append(f"tier{int(tier)}:score={score:.2f}:passed={passed}:cents={tier_cents:.4f}")
            last_attempt = attempt

            if passed:
                return CouncilSolution(
                    schema_version=SCHEMA_VERSION,
                    task=task,
                    final_answer=best,
                    final_tier=tier,
                    total_cents=total_cents,
                    budget_cents=budget_cents,
                    rubric_threshold=self.rubric_threshold,
                    attempts=tuple(attempts),
                    escalation_path=tuple(escalation_path),
                    solved=True,
                    note=f"rubric_passed_at_tier_{int(tier)}",
                )

        final_answer = last_attempt.best_response if last_attempt is not None else ""
        return CouncilSolution(
            schema_version=SCHEMA_VERSION,
            task=task,
            final_answer=final_answer,
            final_tier=last_attempt.tier if last_attempt is not None else None,
            total_cents=total_cents,
            budget_cents=budget_cents,
            rubric_threshold=self.rubric_threshold,
            attempts=tuple(attempts),
            escalation_path=tuple(escalation_path),
            solved=False,
            note="rubric_never_passed_or_no_tier_available",
        )

    def _run_members(
        self,
        task: str,
        members: Sequence[CouncilProvider],
        adapter_options: dict[str, Any],
    ) -> list[CouncilCall]:
        calls: list[CouncilCall] = []
        for provider in members:
            calls.append(self._safe_call(provider.id, task, adapter_options))
        return calls

    def _safe_call(
        self,
        provider_id: str,
        prompt: str,
        adapter_options: dict[str, Any],
    ) -> CouncilCall:
        started = time.monotonic()
        try:
            call = self.adapter(provider_id, prompt, adapter_options)
            return call
        except Exception as exc:  # noqa: BLE001 -- adapter contract: surface error in CouncilCall
            elapsed = (time.monotonic() - started) * 1000.0
            return CouncilCall(
                provider_id=provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                cents=0.0,
                duration_ms=elapsed,
                response="",
                error=f"{type(exc).__name__}:{exc}",
            )

    def _pick_synthesizer(
        self,
        tier: CostTier,
        tier_members: Sequence[CouncilProvider],
        grouped: dict[CostTier, list[CouncilProvider]],
    ) -> CouncilProvider | None:
        if self.synthesizer_provider_id:
            for p in self.providers:
                if p.id == self.synthesizer_provider_id and p.available:
                    return p
        # default: cheapest available provider at the same tier that is not already a member
        member_ids = {m.id for m in tier_members}
        candidates = [p for p in grouped[tier] if p.id not in member_ids]
        if candidates:
            return min(candidates, key=lambda p: p.cents_per_1k_out)
        # fall back to the cheapest member itself
        if tier_members:
            return min(tier_members, key=lambda p: p.cents_per_1k_out)
        return None

    def _build_synthesis_prompt(self, task: str, member_calls: Sequence[CouncilCall]) -> str:
        peer_text_parts = []
        for idx, call in enumerate(member_calls, start=1):
            if call.ok:
                peer_text_parts.append(f"[peer {idx} :: {call.provider_id}]\n{call.response}")
        peer_text = "\n\n".join(peer_text_parts) if peer_text_parts else "(no peers responded)"
        return f"{self.synthesis_prefix}USER TASK:\n{task}\n\nPEER RESPONSES:\n{peer_text}\n\nFINAL ANSWER:\n"

    @staticmethod
    def _best_text(member_calls: Sequence[CouncilCall], synthesis_call: CouncilCall | None) -> str:
        if synthesis_call is not None and synthesis_call.ok:
            return synthesis_call.response
        good = [c for c in member_calls if c.ok]
        if good:
            return max(good, key=lambda c: len(c.response)).response
        return ""


def providers_from_harness_registry(
    registry: dict[str, Any],
    *,
    cost_estimates: dict[str, tuple[float, float]] | None = None,
    families_to_include: Iterable[str] | None = None,
) -> list[CouncilProvider]:
    """Adapt the harness_providers.provider_registry() output into CouncilProvider list.

    `registry` is the dict returned by harness_providers.provider_registry().
    `cost_estimates` maps provider_id -> (cents_per_1k_in, cents_per_1k_out). Missing
    entries default to 0 for free tiers, 0.1c/0.4c for cheap paid, 1c/3c for premium.
    """

    cost_estimates = cost_estimates or {}
    out: list[CouncilProvider] = []
    for provider_id, harness in registry.items():
        if families_to_include is not None and harness.family not in tuple(families_to_include):
            continue
        tier = PRICING_TIER_TO_COST_TIER.get(harness.pricing_tier, CostTier.PREMIUM_PAID)
        if provider_id in cost_estimates:
            in_c, out_c = cost_estimates[provider_id]
        elif tier == CostTier.LOCAL_FREE or tier == CostTier.REMOTE_FREE:
            in_c, out_c = (0.0, 0.0)
        elif tier == CostTier.CHEAP_PAID:
            in_c, out_c = (0.1, 0.4)
        else:
            in_c, out_c = (1.0, 3.0)
        token = harness.token() if hasattr(harness, "token") else None
        available = bool(token)
        reason = "ok" if available else "missing_token_or_local_unreachable"
        out.append(
            CouncilProvider(
                id=provider_id,
                tier=tier,
                family=harness.family,
                cents_per_1k_in=in_c,
                cents_per_1k_out=out_c,
                available=available,
                reason=reason,
            )
        )
    return out


__all__ = [
    "SCHEMA_VERSION",
    "CostTier",
    "CouncilProvider",
    "CouncilCall",
    "TierAttempt",
    "CouncilSolution",
    "TieredCouncil",
    "ProviderAdapter",
    "RubricFn",
    "length_floor_rubric",
    "keyword_rubric",
    "providers_from_harness_registry",
    "PRICING_TIER_TO_COST_TIER",
]
