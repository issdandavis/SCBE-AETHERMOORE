from src.fleet.octo_armor import Tentacle, TentacleThrottle


def test_cerebras_daily_cost_cap_blocks_after_budget(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    monkeypatch.setenv("SCBE_CEREBRAS_DAILY_BUDGET_USD", "1")
    monkeypatch.setenv("SCBE_EST_COST_PER_1K_CEREBRAS", "0.005")

    throttle = TentacleThrottle()
    assert throttle.can_use(Tentacle.CEREBRAS) is True

    # 250k tokens @ $0.005 / 1k => $1.25 estimated cost.
    throttle.record_use(Tentacle.CEREBRAS, tokens=250_000)
    assert throttle.can_use(Tentacle.CEREBRAS) is False


def test_usage_report_exposes_cost_cap_fields(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("SCBE_GROQ_DAILY_BUDGET_USD", "0.5")
    monkeypatch.setenv("SCBE_EST_COST_PER_1K_GROQ", "0.01")

    throttle = TentacleThrottle()
    throttle.record_use(Tentacle.GROQ, tokens=10_000)  # $0.10 estimated
    report = throttle.usage_report()["groq"]

    assert report["daily_cost_cap_usd"] == 0.5
    assert report["estimated_cost_per_1k"] == 0.01
    assert report["cost_used_usd_24h"] > 0
    assert report["cost_cap_reached"] is False
