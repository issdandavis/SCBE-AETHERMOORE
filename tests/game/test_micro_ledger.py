"""
Tests for Spiral Forge RPG micro blockchain ledger — Python reference.

Covers: credit minting, Merkle integrity, chain verification,
ownership transfer, denomination rates.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from symphonic_cipher.scbe_aethermoore.game.micro_ledger import (
    DENOMINATION_WEIGHTS,
    SERVICE_BASE_COSTS,
    exchange_rate,
    mint_credit,
    merkle_root,
    ContextLedger,
    CreditDNA,
)
from symphonic_cipher.scbe_aethermoore.game.types import PHI


class TestDenominationSystem:
    def test_golden_ratio_weights(self):
        assert DENOMINATION_WEIGHTS["KO"] == pytest.approx(1.0)
        assert DENOMINATION_WEIGHTS["AV"] == pytest.approx(PHI, rel=1e-3)
        assert DENOMINATION_WEIGHTS["DR"] == pytest.approx(PHI**5, rel=1e-2)

    def test_exchange_rate_symmetry(self):
        ab = exchange_rate("KO", "DR")
        ba = exchange_rate("DR", "KO")
        assert ab * ba == pytest.approx(1.0, abs=1e-8)

    def test_self_exchange_is_one(self):
        assert exchange_rate("CA", "CA") == pytest.approx(1.0)


class TestServiceCosts:
    def test_all_services_have_cost(self):
        services = [
            "healing", "formation_buff", "scouting", "transform_assist",
            "evolution_catalyst", "drift_cleanse", "codex_query", "escort",
            "training", "governance_vote",
        ]
        for svc in services:
            assert SERVICE_BASE_COSTS[svc] > 0

    def test_evolution_catalyst_most_expensive(self):
        assert SERVICE_BASE_COSTS["evolution_catalyst"] == max(SERVICE_BASE_COSTS.values())


class TestCreditMinting:
    def test_mint_valid_credit(self):
        credit = mint_credit("agent-1", "crysling", "CA", "healing", (0.1, 0.1, 0.1, 0.6, 0.1, 0.1))
        assert credit.credit_id.startswith("cr_")
        assert credit.denomination == "CA"
        assert credit.service_type == "healing"
        assert credit.dna.agent_id == "agent-1"

    def test_face_value_formula(self):
        credit = mint_credit("a", "s", "KO", "scouting", (0, 0, 0, 0, 0, 0), 0, 0)
        # KO weight=1, energy=1/(1+0+0)=1, legibility=1 → 1.0
        assert credit.face_value == pytest.approx(1.0, abs=0.01)

    def test_higher_denomination_higher_value(self):
        ko = mint_credit("a", "s", "KO", "healing", (0, 0, 0, 0, 0, 0))
        dr = mint_credit("a", "s", "DR", "healing", (0, 0, 0, 0, 0, 0))
        assert dr.face_value > ko.face_value

    def test_energy_cost_formula(self):
        dna = CreditDNA("a", "s", (0,) * 6, hamiltonian_d=2.0, hamiltonian_pd=1.0)
        # H(2,1) = 1/(1+2+2) = 0.2
        assert dna.energy_cost == pytest.approx(0.2)

    def test_legibility_affects_value(self):
        full = mint_credit("a", "s", "KO", "healing", (0,) * 6, legibility=1.0)
        half = mint_credit("a", "s", "KO", "healing", (0,) * 6, legibility=0.5)
        assert full.face_value > half.face_value


class TestMerkleTree:
    def test_single_hash(self):
        assert merkle_root(["abc"]) == "abc"

    def test_empty_list(self):
        result = merkle_root([])
        assert len(result) == 64  # SHA-256 hex

    def test_deterministic(self):
        hashes = ["aaa", "bbb", "ccc"]
        assert merkle_root(hashes) == merkle_root(hashes)


class TestContextLedger:
    def test_genesis_block(self):
        ledger = ContextLedger()
        assert ledger.chain_length == 1
        assert ledger.pending_count == 0

    def test_add_and_mine(self):
        ledger = ContextLedger()
        credit = mint_credit("a", "s", "KO", "healing", (0,) * 6)
        ledger.add_credit(credit)
        assert ledger.pending_count == 1
        block = ledger.mine_block("v")
        assert block is not None
        assert block.credit_count == 1
        assert ledger.chain_length == 2
        assert ledger.pending_count == 0

    def test_mine_empty_returns_none(self):
        ledger = ContextLedger()
        assert ledger.mine_block("v") is None

    def test_balance_tracking(self):
        ledger = ContextLedger()
        ledger.add_credit(mint_credit("alice", "s", "KO", "healing", (0,) * 6))
        ledger.add_credit(mint_credit("bob", "s", "CA", "scouting", (0,) * 6))
        ledger.mine_block("v")
        assert ledger.balance("alice") > 0
        assert ledger.balance("bob") > 0
        assert ledger.balance("nobody") == 0

    def test_transfer_ownership(self):
        ledger = ContextLedger()
        credit = mint_credit("alice", "s", "KO", "healing", (0,) * 6)
        ledger.add_credit(credit)
        ledger.mine_block("v")

        alice_before = ledger.balance("alice")
        assert ledger.transfer(credit.credit_id, "alice", "bob")
        assert ledger.balance("alice") < alice_before
        assert ledger.balance("bob") > 0

    def test_reject_wrong_owner_transfer(self):
        ledger = ContextLedger()
        credit = mint_credit("alice", "s", "KO", "healing", (0,) * 6)
        ledger.add_credit(credit)
        ledger.mine_block("v")
        assert not ledger.transfer(credit.credit_id, "bob", "charlie")

    def test_chain_integrity(self):
        ledger = ContextLedger()
        for i in range(5):
            ledger.add_credit(mint_credit(f"agent-{i}", "s", "KO", "healing", (0,) * 6))
            ledger.mine_block(f"v-{i}")
        valid, err_at, reason = ledger.verify_chain()
        assert valid
        assert err_at is None

    def test_total_supply(self):
        ledger = ContextLedger()
        ledger.add_credit(mint_credit("a", "s", "KO", "healing", (0,) * 6))
        ledger.add_credit(mint_credit("b", "s", "KO", "scouting", (0,) * 6))
        ledger.mine_block("v")
        assert ledger.total_supply() > 0

    def test_credits_by_agent(self):
        ledger = ContextLedger()
        ledger.add_credit(mint_credit("alice", "s", "KO", "healing", (0,) * 6))
        ledger.add_credit(mint_credit("alice", "s", "CA", "scouting", (0,) * 6))
        ledger.add_credit(mint_credit("bob", "s", "DR", "training", (0,) * 6))
        ledger.mine_block("v")
        assert len(ledger.credits_by_agent("alice")) == 2
        assert len(ledger.credits_by_agent("bob")) == 1
        assert len(ledger.credits_by_agent("nobody")) == 0
