"""Tests for the SCBE Chemistry Adapter.

Verifies:
  - Check molecules for promotion
  - Batch checking
  - Gate check returns booleans
  - SFT scoring produces valid scores
  - Chemistry elements map correctly (not all Fe)
"""

import pytest

from python.scbe.chemistry_adapter import (
    ChemistryAdapter,
    ChemistryCheckResult,
    training_gate_check,
)


class TestChemistryAdapter:
    def test_water_passes(self):
        adapter = ChemistryAdapter()
        result = adapter.check("O")
        assert result.can_promote
        assert result.rdkit_ok
        assert result.valence_ok
        assert result.fusion_ok
        assert result.governance_verdict == "ALLOW"

    def test_nonsense_fails(self):
        adapter = ChemistryAdapter()
        result = adapter.check("NotASmiles")
        assert not result.can_promote
        assert not result.rdkit_ok

    def test_pentavalent_carbon_fails(self):
        adapter = ChemistryAdapter()
        result = adapter.check("C(C)(C)(C)(C)(C)")
        assert not result.can_promote

    def test_aspirin_passes(self):
        adapter = ChemistryAdapter()
        result = adapter.check("CC(=O)Oc1ccccc1C(=O)O")
        assert result.can_promote
        assert result.rdkit_ok
        assert result.valence_ok
        assert result.fusion_ok

    def test_batch_check(self):
        adapter = ChemistryAdapter()
        results = adapter.batch_check(["O", "CCO", "NotASmiles"])
        assert len(results) == 3
        assert results[0].can_promote
        assert results[1].can_promote
        assert not results[2].can_promote

    def test_gate_check(self):
        adapter = ChemistryAdapter()
        assert adapter.gate_check("O")
        assert not adapter.gate_check("NotASmiles")

    def test_sft_score(self):
        adapter = ChemistryAdapter()
        score = adapter.score_for_sft("CCO")
        assert score["can_promote"]
        assert score["rdkit_ok"]
        assert 0.0 <= score["score"] <= 1.0
        assert "tau_hat" in score
        assert "votes" in score

    def test_elements_are_real_not_fe(self):
        adapter = ChemistryAdapter()
        result = adapter.check("CCO")
        summary = result.summary
        elements = summary.get("elements", [])
        # In chemistry mode, C and O should map to themselves, not Fe
        assert "C" in elements or "O" in elements
        assert elements.count("Fe") < len(elements)  # Not ALL Fe

    def test_pressure_threshold(self):
        adapter = ChemistryAdapter(max_valence_pressure=0.0)
        result = adapter.check("CCO")
        # Even valid molecules have some pressure, so 0.0 threshold should deny
        assert not result.can_promote
        assert "Valence pressure" in " ".join(result.reasons)

    def test_to_dict(self):
        adapter = ChemistryAdapter()
        result = adapter.check("O")
        d = result.to_dict()
        assert "smiles" in d
        assert "can_promote" in d
        assert "rdkit_ok" in d


class TestTrainingGate:
    def test_training_gate_water(self):
        assert training_gate_check("O")

    def test_training_gate_nonsense(self):
        assert not training_gate_check("NotASmiles")

    def test_training_gate_aspirin(self):
        assert training_gate_check("CC(=O)Oc1ccccc1C(=O)O")
