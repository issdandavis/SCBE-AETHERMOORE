from src.api.stripe_billing import meter_provider_usage


def test_two_percent_fee_rounds_up() -> None:
    line = meter_provider_usage(1, provider="openai", model="gpt-4.1")
    assert line["provider_cost_cents"] == 1
    assert line["fee_cents"] == 1
    assert line["billed_cents"] == 2
    assert line["fee_rate"] == 0.02


def test_two_percent_on_even_dollar() -> None:
    line = meter_provider_usage(100, provider="anthropic", model="claude")
    assert line["fee_cents"] == 2
    assert line["billed_cents"] == 102


def test_zero_provider_cost_is_free() -> None:
    line = meter_provider_usage(0, provider="ollama", model="local")
    assert line["fee_cents"] == 0
    assert line["billed_cents"] == 0


def test_fee_rate_cap() -> None:
    try:
        meter_provider_usage(100, provider="x", model="y", fee_rate=0.10)
    except ValueError as exc:
        assert "fee_rate" in str(exc)
    else:
        raise AssertionError("expected ValueError for fee_rate > 5%")
