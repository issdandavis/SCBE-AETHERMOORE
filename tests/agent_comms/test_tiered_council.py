"""Tests for the tiered council orchestrator.

All adapter behavior is mocked so tests are deterministic and have no network deps.
"""

from __future__ import annotations

import pytest

from src.agent_comms.tiered_council import (
    CostTier,
    CouncilCall,
    CouncilProvider,
    TieredCouncil,
    keyword_rubric,
    length_floor_rubric,
)


def _provider(
    id_: str, tier: CostTier, available: bool = True, in_c: float = 0.0, out_c: float = 0.0
) -> CouncilProvider:
    return CouncilProvider(
        id=id_,
        tier=tier,
        family="remote-openai-compatible" if tier != CostTier.LOCAL_FREE else "local-openai-compatible",
        cents_per_1k_in=in_c,
        cents_per_1k_out=out_c,
        available=available,
        reason="ok" if available else "missing_env",
    )


def _call(provider_id: str, response: str, cents: float = 0.0, error: str | None = None) -> CouncilCall:
    return CouncilCall(
        provider_id=provider_id,
        prompt_tokens=10,
        completion_tokens=20,
        cents=cents,
        duration_ms=5.0,
        response=response,
        error=error,
    )


def make_adapter(responses: dict[str, CouncilCall]):
    """Adapter that returns the pre-recorded CouncilCall for each provider id."""

    def _adapter(provider_id: str, _prompt: str, _opts: dict) -> CouncilCall:
        if provider_id not in responses:
            raise RuntimeError(f"unknown provider in test: {provider_id}")
        return responses[provider_id]

    return _adapter


def test_solves_at_local_free_tier_when_rubric_passes() -> None:
    providers = [
        _provider("ollama", CostTier.LOCAL_FREE),
        _provider("haiku", CostTier.CHEAP_PAID, in_c=0.1, out_c=0.4),
    ]
    answer = "The sum of one and two is three. " * 3  # > 40 chars
    adapter = make_adapter({"ollama": _call("ollama", answer, cents=0.0)})

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(40),
        team_size_per_tier=1,
    )
    result = council.solve(task="what is one plus two", budget_cents=10.0)

    assert result.solved is True
    assert result.final_tier == CostTier.LOCAL_FREE
    assert result.total_cents == 0.0
    assert "three" in result.final_answer
    # never escalated past tier 0
    assert all(att.tier <= CostTier.LOCAL_FREE for att in result.attempts if att.skipped_reason is None)


def test_escalates_when_local_tier_fails_rubric() -> None:
    providers = [
        _provider("ollama", CostTier.LOCAL_FREE),
        _provider("groq", CostTier.REMOTE_FREE),
        _provider("haiku", CostTier.CHEAP_PAID, in_c=0.1, out_c=0.4),
    ]
    adapter = make_adapter(
        {
            "ollama": _call("ollama", "x"),  # too short, fails rubric
            "groq": _call("groq", "Detailed correct response with enough length to pass the rubric easily."),
        }
    )

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(40),
        team_size_per_tier=1,
    )
    result = council.solve(task="explain something", budget_cents=10.0)

    assert result.solved is True
    assert result.final_tier == CostTier.REMOTE_FREE
    assert result.total_cents == 0.0  # both tiers were free
    # escalation path shows tier0 fail, tier1 pass
    joined = " | ".join(result.escalation_path)
    assert "tier0" in joined
    assert "tier1" in joined


def test_budget_skip_prevents_paid_tier() -> None:
    providers = [
        _provider("ollama", CostTier.LOCAL_FREE),
        _provider("haiku", CostTier.CHEAP_PAID, in_c=10.0, out_c=10.0),  # high estimate
    ]
    adapter = make_adapter(
        {
            "ollama": _call("ollama", "x"),  # fails rubric
            "haiku": _call("haiku", "would-be-paid-answer", cents=5.0),
        }
    )

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(40),
        team_size_per_tier=1,
        est_in_tokens=1000,
        est_out_tokens=1000,
    )
    result = council.solve(task="task", budget_cents=0.5)

    assert result.solved is False
    # haiku tier should be skipped due to budget; final answer falls back to last attempted (ollama)
    skips = [a for a in result.attempts if a.skipped_reason and "budget_would_exceed" in a.skipped_reason]
    assert len(skips) >= 1
    # only the local tier was actually run -> 0 cents spent
    assert result.total_cents == 0.0


def test_team_mode_runs_synthesizer_when_multiple_members() -> None:
    providers = [
        _provider("ollama_a", CostTier.LOCAL_FREE),
        _provider("ollama_b", CostTier.LOCAL_FREE),
        _provider("ollama_c", CostTier.LOCAL_FREE),
    ]
    adapter = make_adapter(
        {
            "ollama_a": _call("ollama_a", "answer A is short"),
            "ollama_b": _call("ollama_b", "answer B is also short"),
            "ollama_c": _call(
                "ollama_c",
                "synthesized answer combining A and B with extra detail required to pass rubric",
            ),
        }
    )

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=keyword_rubric("synthesized", "combining"),
        rubric_threshold=0.5,
        team_size_per_tier=2,
    )
    result = council.solve(task="combine answers", budget_cents=10.0)

    assert result.solved is True
    assert result.final_tier == CostTier.LOCAL_FREE
    tier0 = [a for a in result.attempts if a.tier == CostTier.LOCAL_FREE and a.skipped_reason is None][0]
    assert len(tier0.members) == 2
    assert tier0.synthesis_call is not None
    assert tier0.synthesis_call.provider_id == "ollama_c"
    assert "synthesized" in result.final_answer


def test_unavailable_providers_skip_to_next_tier() -> None:
    providers = [
        _provider("ollama", CostTier.LOCAL_FREE, available=False),
        _provider("groq", CostTier.REMOTE_FREE),
    ]
    adapter = make_adapter({"groq": _call("groq", "remote free answer that is plenty long enough.")})

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(40),
        team_size_per_tier=1,
    )
    result = council.solve(task="task", budget_cents=10.0)

    assert result.solved is True
    assert result.final_tier == CostTier.REMOTE_FREE
    skipped = [a for a in result.attempts if a.skipped_reason == "no_available_providers_at_tier"]
    assert any(a.tier == CostTier.LOCAL_FREE for a in skipped)


def test_adapter_exception_recorded_as_call_error_does_not_break_cascade() -> None:
    providers = [
        _provider("ollama", CostTier.LOCAL_FREE),
        _provider("groq", CostTier.REMOTE_FREE),
    ]

    def adapter(provider_id: str, _prompt: str, _opts: dict) -> CouncilCall:
        if provider_id == "ollama":
            raise ConnectionError("ollama unreachable")
        return _call(provider_id, "remote free answer that is plenty long enough.")

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(40),
        team_size_per_tier=1,
    )
    result = council.solve(task="task", budget_cents=10.0)

    assert result.solved is True
    assert result.final_tier == CostTier.REMOTE_FREE
    tier0 = [a for a in result.attempts if a.tier == CostTier.LOCAL_FREE and a.skipped_reason is None][0]
    assert any(m.error and "ConnectionError" in m.error for m in tier0.members)


def test_max_tier_caps_escalation() -> None:
    providers = [
        _provider("ollama", CostTier.LOCAL_FREE),
        _provider("opus", CostTier.PREMIUM_PAID, in_c=10.0, out_c=30.0),
    ]
    adapter = make_adapter(
        {
            "ollama": _call("ollama", "x"),  # fails rubric
            "opus": _call("opus", "premium answer that would pass rubric and cost a lot."),
        }
    )

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(40),
        team_size_per_tier=1,
    )
    result = council.solve(task="task", budget_cents=100.0, max_tier=CostTier.REMOTE_FREE)

    assert result.solved is False
    # premium tier never attempted
    premium_attempts = [a for a in result.attempts if a.tier == CostTier.PREMIUM_PAID]
    assert premium_attempts == []


def test_solution_to_dict_round_trips_basic_shape() -> None:
    providers = [_provider("ollama", CostTier.LOCAL_FREE)]
    adapter = make_adapter({"ollama": _call("ollama", "x" * 50)})

    council = TieredCouncil(
        providers=providers,
        adapter=adapter,
        rubric=length_floor_rubric(10),
        team_size_per_tier=1,
    )
    result = council.solve(task="ping", budget_cents=1.0)

    payload = result.to_dict()
    assert payload["schema_version"] == "scbe_tiered_council_v1"
    assert payload["solved"] is True
    assert payload["final_tier"] == int(CostTier.LOCAL_FREE)
    assert payload["total_cents"] == 0.0
    assert isinstance(payload["attempts"], list)
    assert payload["attempts"][0]["tier"] == int(CostTier.LOCAL_FREE)


@pytest.mark.parametrize(
    "candidate, expected_score",
    [
        ("", 0.0),
        ("short", pytest.approx(5 / 40)),
        ("a" * 40, 1.0),
        ("a" * 100, 1.0),
    ],
)
def test_length_floor_rubric_scores(candidate: str, expected_score: float) -> None:
    score = length_floor_rubric(40)("task", candidate)
    assert score == expected_score


def test_keyword_rubric_fraction() -> None:
    rubric = keyword_rubric("alpha", "beta", "gamma")
    assert rubric("task", "ALPHA only here") == pytest.approx(1 / 3)
    assert rubric("task", "alpha and beta and gamma") == 1.0
    assert rubric("task", "nothing relevant") == 0.0
    # empty keyword list -> always 1.0
    assert keyword_rubric()("task", "anything") == 1.0
