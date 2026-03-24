"""
Tests for Energy Token system — Python reference.

Covers: token packages, purchases, consumption, refunds, compute hours.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from symphonic_cipher.scbe_aethermoore.game.energy_token import (
    TOKEN_PACKAGES,
    ACTIVITY_COSTS,
    EnergyWallet,
)


class TestTokenPackages:
    def test_has_four_packages(self):
        assert len(TOKEN_PACKAGES) == 4

    def test_increasing_tokens(self):
        for i in range(1, len(TOKEN_PACKAGES)):
            assert TOKEN_PACKAGES[i].tokens > TOKEN_PACKAGES[i - 1].tokens

    def test_increasing_prices(self):
        for i in range(1, len(TOKEN_PACKAGES)):
            assert TOKEN_PACKAGES[i].price_usd > TOKEN_PACKAGES[i - 1].price_usd

    def test_better_rates_for_larger(self):
        rates = [
            p.price_usd / (p.tokens + p.bonus_tokens) for p in TOKEN_PACKAGES
        ]
        for i in range(1, len(rates)):
            assert rates[i] < rates[i - 1]

    def test_unique_ids(self):
        ids = [p.package_id for p in TOKEN_PACKAGES]
        assert len(set(ids)) == len(ids)


class TestActivityCosts:
    def test_all_positive(self):
        for key, cost in ACTIVITY_COSTS.items():
            assert cost.base_cost > 0
            assert cost.activity_type == key

    def test_world_simulation_most_expensive(self):
        max_cost = max(c.base_cost for c in ACTIVITY_COSTS.values())
        assert ACTIVITY_COSTS["world_simulation"].base_cost == max_cost

    def test_codex_cheapest(self):
        min_cost = min(c.base_cost for c in ACTIVITY_COSTS.values())
        assert ACTIVITY_COSTS["codex_deep_query"].base_cost == min_cost


class TestWalletPurchases:
    def test_starts_at_zero(self):
        w = EnergyWallet("player-1")
        assert w.balance == 0
        assert w.total_purchased == 0
        assert w.total_consumed == 0

    def test_record_purchase(self):
        w = EnergyWallet("player-1")
        rec = w.record_purchase("starter", "pi_stripe_123")
        assert rec is not None
        assert rec.tokens_minted == 100
        assert rec.price_usd == 4.99
        assert rec.status == "completed"
        assert w.balance == 100

    def test_bonus_tokens(self):
        w = EnergyWallet("player-1")
        rec = w.record_purchase("adventurer", "pi_456")
        assert rec is not None
        assert rec.tokens_minted == 550
        assert w.balance == 550

    def test_invalid_package(self):
        w = EnergyWallet("player-1")
        assert w.record_purchase("fake", "pi") is None
        assert w.balance == 0

    def test_accumulate(self):
        w = EnergyWallet("player-1")
        w.record_purchase("starter", "pi_1")
        w.record_purchase("adventurer", "pi_2")
        assert w.balance == 650
        assert len(w.get_purchases()) == 2


class TestWalletConsumption:
    def _funded(self) -> EnergyWallet:
        w = EnergyWallet("player-1")
        w.record_purchase("adventurer", "pi_1")
        return w

    def test_can_afford(self):
        w = self._funded()
        assert w.can_afford("dungeon_run") is True
        assert w.can_afford("nonexistent") is False

    def test_consume(self):
        w = self._funded()
        rec = w.consume("dungeon_run", "comp-1", "s1")
        assert rec is not None
        assert rec.tokens_spent == 20
        assert w.balance == 530

    def test_insufficient_balance(self):
        w = EnergyWallet("player-1")
        w.record_purchase("starter", "pi_1")  # 100
        w.consume("world_simulation", None, "s1")  # costs 100
        assert w.balance == 0
        assert w.consume("codex_deep_query", None, "s2") is None

    def test_training_tracking(self):
        w = self._funded()
        w.consume("dungeon_run", "c1", "s1", True, "hf-ds-1")
        w.consume("tower_floor", "c1", "s1", False)
        assert len(w.get_training_consumptions()) == 1


class TestWalletRefund:
    def test_refund_unspent(self):
        w = EnergyWallet("player-1")
        p = w.record_purchase("starter", "pi_1")
        ok, amount = w.process_refund(p.purchase_id)
        assert ok is True
        assert amount == 100
        assert w.balance == 0

    def test_partial_refund(self):
        w = EnergyWallet("player-1")
        p = w.record_purchase("starter", "pi_1")
        w.consume("dungeon_run", None, "s1")
        ok, amount = w.process_refund(p.purchase_id)
        assert ok is True
        assert amount == 80

    def test_reject_unknown(self):
        w = EnergyWallet("player-1")
        ok, _ = w.process_refund("fake")
        assert ok is False

    def test_reject_double(self):
        w = EnergyWallet("player-1")
        p = w.record_purchase("starter", "pi_1")
        w.process_refund(p.purchase_id)
        ok, _ = w.process_refund(p.purchase_id)
        assert ok is False


class TestComputeHours:
    def test_purchased_hours(self):
        w = EnergyWallet("player-1")
        w.record_purchase("starter", "pi_1")
        assert w.compute_hours_purchased() == pytest.approx(100 * 60 / 3600)

    def test_summary(self):
        w = EnergyWallet("player-1")
        w.record_purchase("starter", "pi_1")
        w.consume("dungeon_run", "c1", "s1", True)
        s = w.summary()
        assert s["balance"] == 80
        assert s["total_purchased"] == 100
        assert s["total_consumed"] == 20
        assert s["training_data_generated"] == 1
