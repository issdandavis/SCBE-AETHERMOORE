from __future__ import annotations

from scripts.system.monetization_connector_push import _build_offers


def test_monetization_connector_push_includes_live_cash_offers() -> None:
    offers = _build_offers(include_gumroad=False)
    by_id = {offer["id"]: offer for offer in offers}

    assert by_id["supporter_monthly"]["price_usd"] == 20.0
    assert by_id["supporter_monthly"]["stripe_url"] == "https://buy.stripe.com/00w8wQd4CbqfgJidOKdby0i"
    assert by_id["supporter_monthly"]["cadence"] == "monthly"

    assert by_id["governance_snapshot"]["price_usd"] == 500.0
    assert by_id["governance_snapshot"]["stripe_url"] == "https://buy.stripe.com/eVqeVeaWu79ZgJi11Ydby0j"
    assert by_id["governance_snapshot"]["cadence"] == "one_time"
    assert by_id["governance_snapshot"]["intake_url"] == "https://aethermoore.com/governance-snapshot.html#intake"
    assert "governance_snapshot_intake.py" in by_id["governance_snapshot"]["fulfillment_command"]
