"""Tests for SCBE 9D Chemistry via Atomic Tokenization + Fusion.

Verifies that molecules map deterministically through:
  SMILES → tokens → AtomicTokenState → fusion → 9D xi
"""

import numpy as np
import pytest

from python.scbe.state9d_chemistry_fusion import (
    assemble_fusion_state_vector,
    fuse_molecule,
    molecule_governance_summary,
    tokenize_molecule,
    _tokens_from_molecule,
    fusion_to_context,
)
from python.scbe.atomic_tokenization import TONGUES


class TestTokenFromMolecule:
    def test_ethanol(self):
        tokens = _tokens_from_molecule("CCO")
        assert "C" in tokens
        assert "O" in tokens

    def test_benzene_aromatic(self):
        tokens = _tokens_from_molecule("c1ccccc1")
        assert "carbon_aromatic" in tokens

    def test_halides(self):
        tokens = _tokens_from_molecule("CCl")
        assert "C" in tokens
        assert "Cl" in tokens

    def test_bonds_and_rings(self):
        tokens = _tokens_from_molecule("C1=CC=CC=C1")
        assert "double_bond" in tokens
        assert "ring_1" in tokens


class TestTokenizeMolecule:
    def test_ethanol_states(self):
        states = tokenize_molecule("CCO")
        assert len(states) > 0
        for s in states:
            assert s.element is not None
            assert s.tau is not None

    def test_benzene_states(self):
        states = tokenize_molecule("c1ccccc1")
        assert len(states) > 0

    def test_determinism(self):
        s1 = tokenize_molecule("CCO")
        s2 = tokenize_molecule("CCO")
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.token == b.token
            assert a.element.symbol == b.element.symbol


class TestFuseMolecule:
    def test_ethanol_fusion(self):
        states = tokenize_molecule("CCO")
        fusion = fuse_molecule(states)
        assert "tau_hat" in fusion
        assert "votes" in fusion
        assert "coherence_penalty" in fusion
        assert "valence_pressure" in fusion
        for t in TONGUES:
            assert t in fusion["tau_hat"]
            assert fusion["tau_hat"][t] in (-1, 0, 1)

    def test_empty_fusion(self):
        fusion = fuse_molecule([])
        assert fusion["signed_edge_tension"] == 0.0
        assert fusion["coherence_penalty"] == 0.0


class TestFusionToContext:
    def test_shape(self):
        states = tokenize_molecule("CCO")
        fusion = fuse_molecule(states)
        c = fusion_to_context(fusion, t=1.0, smiles="CCO")
        assert c.shape == (6,)
        assert c.dtype == object

    def test_v6_clipped(self):
        states = tokenize_molecule("CCO")
        fusion = fuse_molecule(states)
        c = fusion_to_context(fusion, t=0.0, smiles="CCO", signature_validity=2.0)
        assert 0.0 <= float(c[5]) <= 1.0


class TestAssembleFusionStateVector:
    def test_shape(self):
        xi = assemble_fusion_state_vector("CCO", t=1.0)
        assert xi.shape == (9,)
        assert xi.dtype == object

    def test_benzene(self):
        xi = assemble_fusion_state_vector("c1ccccc1", t=0.0)
        assert float(xi[6]) >= 0.0  # tau
        assert float(xi[7]) >= 0.0  # eta

    def test_quantum_normalized(self):
        xi = assemble_fusion_state_vector("CCO", t=2.0, q0=0.6 + 0.8j)
        q = complex(xi[8])
        assert abs(abs(q) - 1.0) < 1e-12

    def test_determinism(self):
        xi1 = assemble_fusion_state_vector("CC(=O)Oc1ccccc1C(=O)O", t=3.14)
        xi2 = assemble_fusion_state_vector("CC(=O)Oc1ccccc1C(=O)O", t=3.14)
        for i in range(9):
            if isinstance(xi1[i], (complex, np.complexfloating)):
                assert abs(xi1[i] - xi2[i]) < 1e-12
            else:
                assert float(xi1[i]) == pytest.approx(float(xi2[i]), abs=1e-12)

    def test_different_molecules(self):
        xi1 = assemble_fusion_state_vector("CCO", t=0.0)
        xi2 = assemble_fusion_state_vector("c1ccccc1", t=0.0)
        assert not np.array_equal(
            np.array([float(x) for x in xi1[:6]]),
            np.array([float(x) for x in xi2[:6]]),
        )


class TestMoleculeGovernanceSummary:
    def test_structure(self):
        summary = molecule_governance_summary("CCO", t=0.0)
        assert summary["smiles"] == "CCO"
        assert "tokens" in summary
        assert "elements" in summary
        assert "tau_hat" in summary
        assert "votes" in summary
        assert "state_vector" in summary

    def test_aspirin(self):
        summary = molecule_governance_summary("CC(=O)Oc1ccccc1C(=O)O", t=1.0)
        assert len(summary["tokens"]) > 0
        assert len(summary["elements"]) > 0
        sv = summary["state_vector"]
        assert "tau" in sv
        assert "eta" in sv
        assert "q" in sv
