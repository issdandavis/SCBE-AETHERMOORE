"""Real-provider dispatch for the TieredCouncil orchestrator.

Wires `src.agent_comms.tiered_council.TieredCouncil` to the OpenAI-compatible chat
endpoints already registered in `src.agent_comms.harness_providers`. Used as the
`tiered_council` dispatch_provider in `scripts/scbe-system-cli.py agentbus run`.

This module deliberately keeps the HTTP transport in one place (`_HttpFn`) so tests
can inject a fake transport without monkey-patching urllib globally.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from src.agent_comms import harness_providers as _harness
from src.agent_comms.tiered_council import (
    CostTier,
    CouncilCall,
    CouncilProvider,
    CouncilSolution,
    PRICING_TIER_TO_COST_TIER,
    RubricFn,
    TieredCouncil,
    length_floor_rubric,
)

SCHEMA_VERSION = "scbe_tiered_council_dispatch_v1"


# Coarse cost estimates in cents per 1K tokens. Production callers should override
# via `cost_overrides`. These are used only for pre-call budget gating; the actual
# `cents` reported in each CouncilCall is computed from the provider's response.
DEFAULT_COST_ESTIMATES_CENTS_PER_1K: dict[str, tuple[float, float]] = {
    "ollama": (0.0, 0.0),
    "lmstudio": (0.0, 0.0),
    "vllm": (0.0, 0.0),
    "llamacpp": (0.0, 0.0),
    "textgenwebui": (0.0, 0.0),
    "tabbyapi": (0.0, 0.0),
    "groq": (0.0, 0.0),
    "cerebras": (0.0, 0.0),
    "sambanova": (0.0, 0.0),
    "gemini": (0.0, 0.0),
    "huggingface": (0.0, 0.0),
    "nvidia": (0.0, 0.0),
    "together": (0.005, 0.015),
    "deepseek": (0.014, 0.028),
    "kimi": (0.06, 0.06),
    "kimi_code": (0.06, 0.06),
    "moonshot": (0.06, 0.06),
    "mistral": (0.04, 0.12),
    "fireworks": (0.02, 0.08),
    "xai": (0.5, 1.5),
    "openrouter": (0.1, 0.4),
    "openai": (0.15, 0.6),
}


_HttpFn = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


def _default_http(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


@dataclass
class CouncilDispatchConfig:
    rubric: RubricFn | None = None
    rubric_threshold: float = 0.7
    team_size_per_tier: int = 2
    synthesizer_provider_id: str | None = None
    max_tier: CostTier = CostTier.PREMIUM_PAID
    request_timeout_s: float = 30.0
    max_response_tokens: int = 512
    temperature: float = 0.2
    families_to_include: tuple[str, ...] | None = None
    cost_overrides: Mapping[str, tuple[float, float]] | None = None


def build_council_providers(
    *,
    families_to_include: Sequence[str] | None = None,
    cost_overrides: Mapping[str, tuple[float, float]] | None = None,
    registry_provider: Callable[[], dict[str, _harness.HarnessProvider]] = _harness.provider_registry,
) -> list[CouncilProvider]:
    """Build CouncilProviders from the live harness_providers registry.

    A provider is `available=True` only when its api key env vars are present (or it
    is local with no auth). Tier mapping comes from `pricing_tier`. Cost estimates
    fall through DEFAULT_COST_ESTIMATES_CENTS_PER_1K, overridable via cost_overrides.
    """

    registry = registry_provider()
    overrides = dict(DEFAULT_COST_ESTIMATES_CENTS_PER_1K)
    if cost_overrides:
        overrides.update(cost_overrides)

    out: list[CouncilProvider] = []
    for provider_id, harness in registry.items():
        if families_to_include is not None and harness.family not in tuple(families_to_include):
            continue
        tier = PRICING_TIER_TO_COST_TIER.get(harness.pricing_tier, CostTier.PREMIUM_PAID)
        in_c, out_c = overrides.get(
            provider_id,
            (0.0, 0.0) if tier <= CostTier.REMOTE_FREE else (1.0, 3.0),
        )
        token = harness.token()
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


def make_openai_compat_adapter(
    *,
    config: CouncilDispatchConfig,
    http: _HttpFn = _default_http,
    registry_provider: Callable[[], dict[str, _harness.HarnessProvider]] = _harness.provider_registry,
) -> Callable[[str, str, dict[str, Any]], CouncilCall]:
    """Build an adapter that calls OpenAI-compatible chat completions for any harness provider id."""

    def _adapter(provider_id: str, prompt: str, options: dict[str, Any]) -> CouncilCall:
        registry = registry_provider()
        harness = registry.get(provider_id)
        if harness is None:
            return CouncilCall(
                provider_id=provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                cents=0.0,
                duration_ms=0.0,
                response="",
                error=f"unknown_harness_provider:{provider_id}",
            )

        token = harness.token()
        if token is None:
            return CouncilCall(
                provider_id=provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                cents=0.0,
                duration_ms=0.0,
                response="",
                error="missing_credentials",
            )

        model = (options.get("model") if isinstance(options, dict) else None) or harness.default_model
        url = harness.chat_url
        headers: dict[str, str] = {}
        if token != "local-no-auth":
            headers["Authorization"] = f"Bearer {token}"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(options.get("max_tokens", config.max_response_tokens)),
            "temperature": float(options.get("temperature", config.temperature)),
        }

        started = time.monotonic()
        try:
            data = http(url, payload, headers, config.request_timeout_s)
        except HTTPError as exc:
            elapsed = (time.monotonic() - started) * 1000.0
            try:
                body_snippet = exc.read().decode("utf-8", errors="replace")[:240]
            except Exception:  # noqa: BLE001
                body_snippet = ""
            return CouncilCall(
                provider_id=provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                cents=0.0,
                duration_ms=elapsed,
                response="",
                error=f"http_{exc.code}:{body_snippet}",
            )
        except URLError as exc:
            elapsed = (time.monotonic() - started) * 1000.0
            return CouncilCall(
                provider_id=provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                cents=0.0,
                duration_ms=elapsed,
                response="",
                error=f"url_unreachable:{exc.reason}",
            )
        except TimeoutError:
            elapsed = (time.monotonic() - started) * 1000.0
            return CouncilCall(
                provider_id=provider_id,
                prompt_tokens=0,
                completion_tokens=0,
                cents=0.0,
                duration_ms=elapsed,
                response="",
                error="provider_timeout",
            )
        except Exception as exc:  # noqa: BLE001
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

        elapsed = (time.monotonic() - started) * 1000.0
        text, prompt_tokens, completion_tokens = _extract_openai_chat_response(data)

        # Cost: prefer authoritative numbers from the council provider definition
        cost_estimates = DEFAULT_COST_ESTIMATES_CENTS_PER_1K.get(provider_id, (0.0, 0.0))
        in_rate, out_rate = cost_estimates
        cents = (prompt_tokens / 1000.0) * in_rate + (completion_tokens / 1000.0) * out_rate

        return CouncilCall(
            provider_id=provider_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cents=cents,
            duration_ms=elapsed,
            response=text,
            error=None if text.strip() else "empty_response",
        )

    return _adapter


def _extract_openai_chat_response(data: dict[str, Any]) -> tuple[str, int, int]:
    text = ""
    prompt_tokens = 0
    completion_tokens = 0
    if not isinstance(data, dict):
        return text, prompt_tokens, completion_tokens
    choices = data.get("choices") or []
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            if not text and isinstance(first.get("text"), str):
                text = first["text"]
    usage = data.get("usage")
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    return text, prompt_tokens, completion_tokens


def dispatch_tiered_council(
    *,
    task: str,
    budget_cents: float,
    config: CouncilDispatchConfig | None = None,
    http: _HttpFn = _default_http,
    registry_provider: Callable[[], dict[str, _harness.HarnessProvider]] = _harness.provider_registry,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a TieredCouncil over real harness providers, return an agentbus-shaped payload."""

    config = config or CouncilDispatchConfig()
    rubric = config.rubric or length_floor_rubric()

    providers = build_council_providers(
        families_to_include=config.families_to_include,
        cost_overrides=config.cost_overrides,
        registry_provider=registry_provider,
    )
    adapter = make_openai_compat_adapter(
        config=config,
        http=http,
        registry_provider=registry_provider,
    )

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=rubric,
        rubric_threshold=config.rubric_threshold,
        team_size_per_tier=config.team_size_per_tier,
        synthesizer_provider_id=config.synthesizer_provider_id,
    )

    solution = council.solve(
        task=task,
        budget_cents=budget_cents,
        max_tier=config.max_tier,
    )

    return _format_dispatch_payload(solution, metadata=metadata)


def _format_dispatch_payload(
    solution: CouncilSolution,
    *,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "council_schema_version": solution.schema_version,
        "solved": solution.solved,
        "final_tier": int(solution.final_tier) if solution.final_tier is not None else None,
        "final_answer": solution.final_answer,
        "total_cents": solution.total_cents,
        "budget_cents": solution.budget_cents,
        "rubric_threshold": solution.rubric_threshold,
        "escalation_path": list(solution.escalation_path),
        "attempts": [a.to_dict() for a in solution.attempts],
        "note": solution.note,
        "metadata": dict(metadata) if metadata else {},
    }


def truncated_payload_for_logging(payload: dict[str, Any], *, max_response_chars: int = 2000) -> dict[str, Any]:
    """Returns a copy of `payload` with very long response strings truncated.

    Useful when persisting a council result to a JSONL bus log without bloating disk.
    """

    out = dict(payload)
    final_answer = out.get("final_answer", "")
    if isinstance(final_answer, str) and len(final_answer) > max_response_chars:
        out["final_answer"] = (
            final_answer[:max_response_chars] + f"\n[truncated {len(final_answer) - max_response_chars} chars]"
        )
    out["attempts"] = [_truncate_attempt(a, max_response_chars) for a in out.get("attempts", [])]
    return out


def _truncate_attempt(attempt: dict[str, Any], max_chars: int) -> dict[str, Any]:
    out = dict(attempt)
    members = out.get("members", []) or []
    out["members"] = [_truncate_call(m, max_chars) for m in members]
    if out.get("synthesis_call") is not None:
        out["synthesis_call"] = _truncate_call(out["synthesis_call"], max_chars)
    if isinstance(out.get("best_response"), str) and len(out["best_response"]) > max_chars:
        out["best_response"] = out["best_response"][:max_chars] + "\n[truncated]"
    return out


def _truncate_call(call: dict[str, Any], max_chars: int) -> dict[str, Any]:
    out = dict(call)
    response = out.get("response")
    if isinstance(response, str) and len(response) > max_chars:
        out["response"] = response[:max_chars] + "\n[truncated]"
    return out


# Convenience for ad-hoc operator use: read SCBE_TIERED_COUNCIL_FAMILIES env var
def families_from_env() -> tuple[str, ...] | None:
    raw = os.getenv("SCBE_TIERED_COUNCIL_FAMILIES", "").strip()
    if not raw:
        return None
    return tuple(family.strip() for family in raw.split(",") if family.strip())


__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_COST_ESTIMATES_CENTS_PER_1K",
    "CouncilDispatchConfig",
    "build_council_providers",
    "make_openai_compat_adapter",
    "dispatch_tiered_council",
    "truncated_payload_for_logging",
    "families_from_env",
]
