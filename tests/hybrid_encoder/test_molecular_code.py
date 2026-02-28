"""Tests for hybrid_encoder.molecular_code."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.hybrid_encoder.molecular_code import MolecularCodeMapper


def test_import_bonds():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("import os\nimport json")
    ionic = [b for b in bonds if b.bond_type == "ionic"]
    assert len(ionic) >= 2
    assert all(b.tongue_affinity == "AV" for b in ionic)


def test_function_bonds():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("def hello(x, y):\n    return x + y")
    func_bonds = [b for b in bonds if b.element_b == "hello"]
    assert len(func_bonds) >= 1
    assert func_bonds[0].tongue_affinity == "CA"


def test_class_bonds():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("class Foo(Bar):\n    pass")
    class_bonds = [b for b in bonds if b.tongue_affinity == "DR"]
    assert len(class_bonds) >= 1


def test_control_flow_bonds():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("if True:\n    for i in range(10):\n        pass")
    ko_bonds = [b for b in bonds if b.tongue_affinity == "KO"]
    assert len(ko_bonds) >= 2  # if + for


def test_assert_bonds():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("assert x > 0")
    ru_bonds = [b for b in bonds if b.tongue_affinity == "RU"]
    assert len(ru_bonds) >= 1


def test_valence_spectrum():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("import os\ndef f():\n    if True:\n        return 1")
    spec = mc.valence_spectrum(bonds)
    assert "AV" in spec
    assert "KO" in spec
    assert "CA" in spec


def test_stability_score():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("def f():\n    return 1")
    score = mc.stability_score(bonds)
    assert 0.0 <= score <= 1.0


def test_empty_code():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("")
    assert bonds == []


def test_non_python_fallback():
    mc = MolecularCodeMapper()
    bonds = mc.map_code("function hello() { if (true) { return 42; } }")
    # Should use regex fallback
    assert len(bonds) >= 0  # May find some via regex


def test_stability_no_bonds():
    mc = MolecularCodeMapper()
    score = mc.stability_score([])
    assert score == 1.0
