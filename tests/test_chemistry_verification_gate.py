"""Tests for the chemistry verification gate.

Verifies that the gate correctly:
  - PASSes valid molecules
  - DENYies invalid molecules
  - Checks RDKit parse, valence, and SCBE fusion
  - Fails batch if expected-valid molecules are denied
"""

from scripts.eval.chemistry_verification_gate import (
    promote,
    run_gate,
    rdkit_parse_check,
    valence_check,
    scbe_fusion_check,
)


class TestRdkitParseCheck:
    def test_water_passes(self):
        ok, msg = rdkit_parse_check("O")
        assert ok
        assert "atoms" in msg

    def test_nonsense_fails(self):
        ok, msg = rdkit_parse_check("NotASmiles")
        assert not ok

    def test_pentavalent_carbon_fails(self):
        ok, msg = rdkit_parse_check("C(C)(C)(C)(C)(C)")
        assert not ok


class TestValenceCheck:
    def test_ethanol_passes(self):
        ok, msg = valence_check("CCO")
        assert ok

    def test_pentavalent_carbon_fails(self):
        ok, msg = valence_check("C(C)(C)(C)(C)(C)")
        assert not ok
        assert "valence" in msg or "Parse failed" in msg


class TestScbeFusionCheck:
    def test_ethanol_finite(self):
        ok, msg, summary = scbe_fusion_check("CCO")
        assert ok
        assert "state_vector" in summary

    def test_empty_fails(self):
        ok, msg, summary = scbe_fusion_check("")
        assert not ok


class TestRunGate:
    def test_water_pass(self):
        result = run_gate("O")
        assert result["verdict"] == "PASS"
        assert result["checks"]["rdkit_parse"]
        assert result["checks"]["valence"]
        assert result["checks"]["scbe_fusion"]

    def test_nonsense_deny(self):
        result = run_gate("NotASmiles")
        assert result["verdict"] == "DENY"

    def test_aspirin_pass(self):
        result = run_gate("CC(=O)Oc1ccccc1C(=O)O")
        assert result["verdict"] == "PASS"

    def test_pentavalent_deny(self):
        result = run_gate("C(C)(C)(C)(C)(C)")
        assert result["verdict"] == "DENY"


class TestPromote:
    def test_promote_water(self):
        assert promote("O")

    def test_no_promote_nonsense(self):
        assert not promote("NotASmiles")

    def test_no_promote_pentavalent(self):
        assert not promote("C(C)(C)(C)(C)(C)")
