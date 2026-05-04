"""Tests for the SCBE 9D State Engine — Chemistry Determinism Extension.

Coverage:
  - SMILES parsing (common organics, aromatics, halides, brackets)
  - Molecular property computation (MW, entropy, fractions)
  - Context vector mapping from molecular properties
  - Full chemical 9D state assembly
  - Determinism (same input → same output)
  - Benchmark report structure
"""

import math

import numpy as np
import pytest

from python.scbe.state9d_chemistry import (
    ATOMIC_WEIGHTS,
    BENCHMARK_LEADERBOARD,
    MolecularProperties,
    assemble_chemical_state_vector,
    compute_molecular_properties,
    get_benchmark_report,
    molecular_properties_to_context,
    parse_smiles_atoms,
)
from python.scbe.state9d_engine import INTENT_PHASE


# ---------------------------------------------------------------------------
# SMILES Parsing
# ---------------------------------------------------------------------------
class TestParseSmilesAtoms:
    def test_ethanol(self):
        assert parse_smiles_atoms("CCO") == ["C", "C", "O"]

    def test_benzene_aromatic(self):
        atoms = parse_smiles_atoms("c1ccccc1")
        assert atoms == ["c", "c", "c", "c", "c", "c"]

    def test_benzene_aliphatic(self):
        atoms = parse_smiles_atoms("C1=CC=CC=C1")
        assert atoms == ["C", "C", "C", "C", "C", "C"]

    def test_cyclohexane(self):
        atoms = parse_smiles_atoms("C1CCCCC1")
        assert atoms == ["C", "C", "C", "C", "C", "C"]

    def test_halides(self):
        assert parse_smiles_atoms("CCl") == ["C", "Cl"]
        assert parse_smiles_atoms("CBr") == ["C", "Br"]
        assert parse_smiles_atoms("CI") == ["C", "I"]
        assert parse_smiles_atoms("CF") == ["C", "F"]

    def test_chloroform(self):
        assert parse_smiles_atoms("ClC(Cl)Cl") == ["Cl", "C", "Cl", "Cl"]

    def test_pyridine(self):
        atoms = parse_smiles_atoms("c1ccncc1")
        assert atoms.count("c") == 5
        assert atoms.count("n") == 1

    def test_empty_and_whitespace(self):
        assert parse_smiles_atoms("") == []
        assert parse_smiles_atoms("   ") == []

    def test_brackets(self):
        # Charge in brackets should still extract the element
        atoms = parse_smiles_atoms("[Na+].[Cl-]")
        assert "Na" in atoms
        assert "Cl" in atoms

    def test_silicon(self):
        assert parse_smiles_atoms("C[Si](C)(C)C") == ["C", "Si", "C", "C", "C"]

    def test_sulfur(self):
        assert parse_smiles_atoms("CS") == ["C", "S"]

    def test_phosphorus(self):
        assert parse_smiles_atoms("CP") == ["C", "P"]


# ---------------------------------------------------------------------------
# Molecular Properties
# ---------------------------------------------------------------------------
class TestMolecularProperties:
    def test_ethanol(self):
        props = compute_molecular_properties("CCO")
        assert props.atom_count == 3
        assert props.atom_types == {"C": 2, "O": 1}
        assert props.element_diversity == 2
        assert props.heavy_atom_count == 3
        # MW ≈ 2*12 + 16 + 6*1 = 46
        # 2*C + O + 4*H ≈ 24.022 + 15.999 + 4.032 = 44.053
        assert props.estimated_mw == pytest.approx(44.05, abs=2.0)
        assert props.heteroatom_fraction == pytest.approx(1 / 3, abs=1e-6)
        assert props.aromatic_fraction == 0.0
        assert props.atom_entropy > 0.0

    def test_benzene(self):
        props = compute_molecular_properties("c1ccccc1")
        assert props.atom_count == 6
        assert props.atom_types == {"c": 6}
        assert props.element_diversity == 1
        assert props.atom_entropy == pytest.approx(0.0, abs=1e-11)
        assert props.aromatic_fraction == 1.0

    def test_water(self):
        props = compute_molecular_properties("O")
        assert props.atom_count == 1
        assert props.atom_types == {"O": 1}
        # O + 1*H ≈ 15.999 + 1.008 = 17.007
        assert props.estimated_mw == pytest.approx(17.0, abs=2.0)

    def test_tetrachloromethane(self):
        props = compute_molecular_properties("C(Cl)(Cl)(Cl)Cl")
        assert props.atom_count == 5
        assert props.atom_types == {"C": 1, "Cl": 4}
        assert props.heteroatom_fraction == pytest.approx(4 / 5, abs=1e-6)

    def test_determinism(self):
        p1 = compute_molecular_properties("CC(=O)Oc1ccccc1C(=O)O")
        p2 = compute_molecular_properties("CC(=O)Oc1ccccc1C(=O)O")
        assert p1 == p2

    def test_empty_smiles(self):
        props = compute_molecular_properties("")
        assert props.atom_count == 0
        assert props.atom_entropy == 0.0
        assert props.estimated_mw == 0.0


# ---------------------------------------------------------------------------
# Context Vector from Molecular Properties
# ---------------------------------------------------------------------------
class TestMolecularPropertiesToContext:
    def test_shape_and_dtype(self):
        props = compute_molecular_properties("CCO")
        c = molecular_properties_to_context(props, t=1.0)
        assert c.shape == (6,)
        assert c.dtype == object

    def test_v1_time_oscillation(self):
        props = compute_molecular_properties("CCO")
        c = molecular_properties_to_context(props, t=math.pi / 2)
        assert float(c[0]) == pytest.approx(1.0, abs=1e-12)

    def test_v2_intent_phase(self):
        props = compute_molecular_properties("CCO")
        c = molecular_properties_to_context(props, t=0.0)
        assert isinstance(c[1], (complex, np.complexfloating))
        assert abs(c[1] - INTENT_PHASE) < 1e-12

    def test_v3_entropy_normalized(self):
        # Single element type → entropy = 0 → v3 = 0
        props = compute_molecular_properties("c1ccccc1")
        c = molecular_properties_to_context(props, t=0.0)
        assert float(c[2]) == pytest.approx(0.0, abs=1e-12)

        # Multiple element types → v3 > 0
        props = compute_molecular_properties("CCO")
        c = molecular_properties_to_context(props, t=0.0)
        assert float(c[2]) > 0.0
        assert float(c[2]) <= 1.0

    def test_v4_linear_time(self):
        props = compute_molecular_properties("CCO")
        c = molecular_properties_to_context(props, t=42.0)
        assert float(c[3]) == pytest.approx(42.0, abs=1e-12)

    def test_v5_mw_hetero(self):
        # Higher MW × hetero fraction → higher v5
        props_small = compute_molecular_properties("CC")
        props_large = compute_molecular_properties("C(Cl)(Cl)(Cl)Cl")
        c_small = molecular_properties_to_context(props_small, t=0.0)
        c_large = molecular_properties_to_context(props_large, t=0.0)
        assert float(c_large[4]) > float(c_small[4])
        assert 0.0 <= float(c_large[4]) <= 1.0

    def test_v6_aromatic_penalty(self):
        # Aromatic fraction = 1.0 → v6 = 0 (if signature_validity = 1)
        props_aromatic = compute_molecular_properties("c1ccccc1")
        c_aromatic = molecular_properties_to_context(props_aromatic, t=0.0, signature_validity=1.0)
        assert float(c_aromatic[5]) == pytest.approx(0.0, abs=1e-12)

        # Aliphatic → v6 = signature_validity
        props_aliphatic = compute_molecular_properties("CCO")
        c_aliphatic = molecular_properties_to_context(props_aliphatic, t=0.0, signature_validity=0.8)
        assert float(c_aliphatic[5]) == pytest.approx(0.8, abs=1e-12)


# ---------------------------------------------------------------------------
# Full Chemical 9D Assembly
# ---------------------------------------------------------------------------
class TestAssembleChemicalStateVector:
    def test_shape_and_dtype(self):
        xi = assemble_chemical_state_vector("CCO", t=1.0)
        assert xi.shape == (9,)
        assert xi.dtype == object

    def test_layout(self):
        xi = assemble_chemical_state_vector(
            "CC(=O)Oc1ccccc1C(=O)O",  # aspirin-ish
            t=2.0,
            q0=1 + 0j,
            H=1.0,
            signature_validity=0.95,
        )
        assert isinstance(xi[0], float)
        assert isinstance(xi[1], (complex, np.complexfloating))
        assert isinstance(xi[2], float)
        assert isinstance(xi[3], float)
        assert isinstance(xi[4], float)
        assert isinstance(xi[5], float)
        assert isinstance(xi[6], float)  # tau
        assert isinstance(xi[7], float)  # eta
        assert isinstance(xi[8], (complex, np.complexfloating))  # q

    def test_molecular_entropy_path(self):
        xi = assemble_chemical_state_vector("c1ccccc1", t=0.0, use_molecular_entropy=True)
        # Benzene has only one atom type → atom entropy = 0
        assert float(xi[7]) == pytest.approx(0.0, abs=1e-11)

    def test_quantum_normalization(self):
        xi = assemble_chemical_state_vector("CCO", t=5.0, q0=0.8 + 0.6j)
        q = complex(xi[8])
        assert abs(abs(q) - 1.0) < 1e-12  # unitary evolution preserves |q|

    def test_determinism(self):
        xi1 = assemble_chemical_state_vector("CCO", t=3.14)
        xi2 = assemble_chemical_state_vector("CCO", t=3.14)
        for i in range(9):
            if isinstance(xi1[i], (complex, np.complexfloating)):
                assert abs(xi1[i] - xi2[i]) < 1e-12
            else:
                assert float(xi1[i]) == pytest.approx(float(xi2[i]), abs=1e-12)

    def test_different_molecules_different_states(self):
        xi_ethanol = assemble_chemical_state_vector("CCO", t=0.0)
        xi_benzene = assemble_chemical_state_vector("c1ccccc1", t=0.0)
        # At least one component should differ
        diffs = 0
        for i in range(9):
            if isinstance(xi_ethanol[i], (complex, np.complexfloating)):
                if abs(xi_ethanol[i] - xi_benzene[i]) > 1e-12:
                    diffs += 1
            elif float(xi_ethanol[i]) != pytest.approx(float(xi_benzene[i]), abs=1e-12):
                diffs += 1
        assert diffs >= 1

    def test_time_monotonicity(self):
        xi_t1 = assemble_chemical_state_vector("CCO", t=1.0)
        xi_t2 = assemble_chemical_state_vector("CCO", t=2.0)
        assert float(xi_t2[6]) > float(xi_t1[6])  # tau increases


# ---------------------------------------------------------------------------
# Benchmark Report
# ---------------------------------------------------------------------------
class TestBenchmarkReport:
    def test_report_structure(self):
        report = get_benchmark_report()
        assert "benchmarks" in report
        assert "leaderboard" in report
        assert "notes" in report
        assert len(report["benchmarks"]) >= 4

    def test_leaderboard_entries(self):
        assert len(BENCHMARK_LEADERBOARD) > 0
        for entry in BENCHMARK_LEADERBOARD:
            assert isinstance(entry.benchmark, str)
            assert isinstance(entry.metric, str)
            assert isinstance(entry.best_score, (int, float))
            assert isinstance(entry.best_model, str)
            assert isinstance(entry.year, int)

    def test_guacamol_top_scores(self):
        report = get_benchmark_report()
        gua = next(b for b in report["benchmarks"] if b["name"] == "GuacaMol")
        lstm = gua["top_models"]["LSTM"]
        assert lstm["FCD"] > 80
        assert lstm["KL"] > 90

    def test_moses_top_scores(self):
        report = get_benchmark_report()
        moses = next(b for b in report["benchmarks"] if b["name"] == "MOSES")
        jtvae = moses["top_models"]["JT-VAE"]
        assert jtvae["Validity"] == 100.0
        assert jtvae["Novelty"] > 99
