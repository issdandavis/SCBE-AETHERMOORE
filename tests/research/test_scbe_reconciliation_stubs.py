from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototype" / "reconciliation"))

from scbe_reconciliation_stubs import (  # noqa: E402
    BreakType, DecisionLog, Fill, Ledger, PositionState, VenueReport,
    may_trade, position_state, reconcile, to_scaled,
)


def fill(tid="t1", cid="c1", qty="0.5", price="100.25", venue="coinbase"):
    return Fill(venue, "BTC-USD", tid, cid, to_scaled(qty), to_scaled(price), 1_000)


def test_scaled_integers_avoid_float_drift():
    assert to_scaled("0.1") + to_scaled("0.2") == to_scaled("0.3")
    with pytest.raises(ValueError):
        to_scaled("0.000000001")


def test_duplicate_fill_is_idempotent():
    led = Ledger()
    assert led.record_fill(fill()) is True
    assert led.record_fill(fill()) is False
    assert led.position("coinbase", "BTC-USD") == to_scaled("0.5")


def test_clean_reconcile_allows_trading():
    led = Ledger(); led.issue("c1"); led.record_fill(fill())
    rep = VenueReport("coinbase", "BTC-USD", to_scaled("0.5"), (fill(),))
    br = reconcile(led, rep)
    assert br == [] and may_trade(rep, br)


def test_no_data_is_not_flat_and_fails_closed():
    led = Ledger()
    rep = VenueReport("coinbase", "BTC-USD", None)
    assert position_state(rep) is PositionState.NO_DATA
    br = reconcile(led, rep)
    assert [b.kind for b in br] == [BreakType.NO_DATA]
    assert not may_trade(rep, br)
    flat = VenueReport("coinbase", "BTC-USD", 0)
    assert may_trade(flat, reconcile(led, flat))


def test_missing_fill_detected_partial_fill_silence():
    led = Ledger(); led.issue("c1")
    rep = VenueReport("coinbase", "BTC-USD", to_scaled("0.5"), (fill(),))
    kinds = {b.kind for b in reconcile(led, rep)}
    assert {BreakType.MISSING_FILL, BreakType.POSITION_MISMATCH} <= kinds


def test_phantom_fill_detected():
    led = Ledger(); led.issue("c1"); led.record_fill(fill()); led.record_fill(fill(tid="t2"))
    rep = VenueReport("coinbase", "BTC-USD", to_scaled("0.5"), (fill(),))
    assert BreakType.PHANTOM_FILL in {b.kind for b in reconcile(led, rep)}


def test_unknown_client_order_id_flagged():
    led = Ledger()
    rep = VenueReport("coinbase", "BTC-USD", to_scaled("0.5"), (fill(cid="stranger"),))
    assert BreakType.UNKNOWN_ORDER in {b.kind for b in reconcile(led, rep)}


def test_qty_and_price_mismatch():
    led = Ledger(); led.issue("c1"); led.record_fill(fill(qty="0.4", price="100"))
    rep = VenueReport("coinbase", "BTC-USD", to_scaled("0.5"), (fill(),))
    kinds = {b.kind for b in reconcile(led, rep)}
    assert {BreakType.QTY_MISMATCH, BreakType.PRICE_MISMATCH} <= kinds


def test_decision_log_hash_chain_detects_tamper():
    log = DecisionLog(); led = Ledger()
    reconcile(led, VenueReport("coinbase", "BTC-USD", None), log)
    reconcile(led, VenueReport("binance", "BTC-USD", 0), log)
    assert log.verify()
    log.entries[0]["payload"]["breaks"] = []
    assert not log.verify()
