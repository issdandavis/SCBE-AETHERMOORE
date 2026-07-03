"""
Cost metering + budget enforcement tests.

Covers agent_bus_cost (meter math, env rate overrides), the budget gate in
AgentBus._llm_generate, schema 1.1.0 acceptance of cost_usd events, and the
replay reader's cost aggregation.
"""

import json

import pytest

from agents.agent_bus import AgentBus
from agents.agent_bus_cost import (
    RATES_ENV_VAR,
    CostMeter,
    ProviderRates,
    load_rates,
)
from agents.agent_bus_replay import replay_log
from agents.agent_bus_schema import CURRENT_SCHEMA_VERSION, validate_event

PAID_RATES = {"huggingface": ProviderRates(usd_per_1k_in=0.30, usd_per_1k_out=1.20)}


class TestCostMeter:
    def test_price_math(self):
        meter = CostMeter(rates=PAID_RATES)
        # 2000 in @ $0.30/1k + 500 out @ $1.20/1k = 0.60 + 0.60
        assert meter.price("huggingface", 2000, 500) == pytest.approx(1.20)

    def test_unknown_provider_prices_at_zero(self):
        meter = CostMeter(rates=PAID_RATES)
        assert meter.price("mystery", 10_000, 10_000) == 0.0

    def test_charge_accumulates(self):
        meter = CostMeter(rates=PAID_RATES)
        meter.charge("huggingface", 1000, 0)
        meter.charge("huggingface", 1000, 0)
        assert meter.spent_usd == pytest.approx(0.60)

    def test_zero_budget_is_unbounded(self):
        meter = CostMeter(budget_usd=0.0, rates=PAID_RATES)
        meter.charge("huggingface", 1_000_000, 1_000_000)
        assert not meter.exceeded
        assert meter.remaining_usd is None

    def test_budget_trips_when_reached(self):
        meter = CostMeter(budget_usd=0.50, rates=PAID_RATES)
        assert not meter.exceeded
        meter.charge("huggingface", 2000, 0)  # $0.60
        assert meter.exceeded
        assert meter.remaining_usd == 0.0

    def test_remaining_headroom(self):
        meter = CostMeter(budget_usd=1.00, rates=PAID_RATES)
        meter.charge("huggingface", 1000, 0)  # $0.30
        assert meter.remaining_usd == pytest.approx(0.70)

    def test_default_providers_are_free(self):
        meter = CostMeter()
        assert meter.charge("ollama", 5000, 5000) == 0.0
        assert meter.charge("offline", 5000, 5000) == 0.0


class TestRatesEnv:
    def test_env_override(self):
        env = {RATES_ENV_VAR: json.dumps({"huggingface": {"in": 0.10, "out": 0.40}})}
        rates = load_rates(env)
        assert rates["huggingface"] == ProviderRates(0.10, 0.40)
        assert rates["ollama"] == ProviderRates()  # defaults preserved

    def test_malformed_json_falls_back_to_defaults(self):
        rates = load_rates({RATES_ENV_VAR: "{not json"})
        assert rates["huggingface"] == ProviderRates()

    def test_non_object_json_falls_back(self):
        rates = load_rates({RATES_ENV_VAR: "[1, 2]"})
        assert rates["ollama"] == ProviderRates()

    def test_malformed_entry_skipped_others_kept(self):
        env = {RATES_ENV_VAR: json.dumps({"bad": "nope", "good": {"in": 1.0, "out": 2.0}})}
        rates = load_rates(env)
        assert "bad" not in rates or rates.get("bad") == ProviderRates()
        assert rates["good"] == ProviderRates(1.0, 2.0)

    def test_missing_env_uses_defaults(self):
        assert load_rates({}).keys() >= {"ollama", "huggingface", "offline"}


class TestBudgetGate:
    @pytest.mark.asyncio
    async def test_llm_generate_refuses_when_budget_exceeded(self, monkeypatch):
        bus = AgentBus(budget_usd=0.01)
        bus.cost.spent_usd = 0.02  # already over

        async def _fail(*a, **k):  # providers must never be called
            raise AssertionError("provider called despite exceeded budget")

        monkeypatch.setattr(bus, "_try_ollama", _fail)
        monkeypatch.setattr(bus, "_try_huggingface", _fail)

        result = await bus._llm_generate("hello")
        assert result["provider"] == "budget"
        assert "budget_exceeded" in result["error"]
        assert result["cost_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_llm_generate_charges_offline_fallback(self, monkeypatch):
        bus = AgentBus(budget_usd=0.0)

        async def _none(*a, **k):
            return None

        monkeypatch.setattr(bus, "_try_ollama", _none)
        monkeypatch.setattr(bus, "_try_huggingface", _none)

        result = await bus._llm_generate("hello")
        assert result["provider"] == "offline"
        assert result["cost_usd"] == 0.0  # offline is free, but the field is present

    @pytest.mark.asyncio
    async def test_llm_generate_charges_provider_result(self, monkeypatch):
        bus = AgentBus(budget_usd=1.00)
        bus.cost.rates = dict(PAID_RATES)

        async def _hf(*a, **k):
            return {"text": "hi", "provider": "huggingface", "model": "m", "tokens_in": 1000, "tokens_out": 1000}

        async def _none(*a, **k):
            return None

        monkeypatch.setattr(bus, "_try_ollama", _none)
        monkeypatch.setattr(bus, "_try_huggingface", _hf)

        result = await bus._llm_generate("hello")
        assert result["cost_usd"] == pytest.approx(1.50)
        assert bus.cost.spent_usd == pytest.approx(1.50)
        assert bus.cost.exceeded  # next call would be gated


class TestSchemaCompat:
    def _event(self, **overrides):
        record = {
            "task_type": "ask",
            "query": "q",
            "timestamp": "2026-06-11T00:00:00+0000",
            "success": True,
            "_schema_version": CURRENT_SCHEMA_VERSION,
        }
        record.update(overrides)
        return record

    def test_current_version_is_1_1(self):
        assert CURRENT_SCHEMA_VERSION == "1.1.0"

    def test_event_with_cost_usd_validates(self):
        result = validate_event(self._event(cost_usd=0.0042))
        assert result.ok

    def test_legacy_1_0_0_event_without_cost_still_validates(self):
        result = validate_event(self._event(_schema_version="1.0.0"))
        assert result.ok
        assert not result.migrated  # additive minor needs no migration


class TestReplayCostAggregation:
    def test_replay_aggregates_cost_by_provider(self, tmp_path):
        log = tmp_path / "events.jsonl"
        events = [
            {
                "task_type": "ask",
                "query": "a",
                "timestamp": "2026-06-11T00:00:01+0000",
                "success": True,
                "llm_provider": "huggingface",
                "cost_usd": 0.25,
                "_schema_version": "1.1.0",
            },
            {
                "task_type": "ask",
                "query": "b",
                "timestamp": "2026-06-11T00:00:02+0000",
                "success": True,
                "llm_provider": "huggingface",
                "cost_usd": 0.50,
                "_schema_version": "1.1.0",
            },
            {  # legacy event without cost_usd prices at 0
                "task_type": "ask",
                "query": "c",
                "timestamp": "2026-06-11T00:00:03+0000",
                "success": True,
                "llm_provider": "ollama",
                "_schema_version": "1.0.0",
            },
        ]
        log.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

        report = replay_log(log)
        assert report["total_events"] == 3
        assert report["cost_usd"]["total"] == pytest.approx(0.75)
        assert report["cost_usd"]["by_provider"]["huggingface"] == pytest.approx(0.75)
        assert report["cost_usd"]["by_provider"]["ollama"] == 0.0
