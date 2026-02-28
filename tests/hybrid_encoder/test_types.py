"""Tests for hybrid_encoder.types."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.hybrid_encoder.types import (
    EncoderInput, EncoderResult, HybridRepresentation,
    NegativeSpaceEmbedding, MolecularBond, TONGUE_NAMES,
)


def test_tongue_names():
    assert TONGUE_NAMES == ["KO", "AV", "RU", "CA", "UM", "DR"]


def test_encoder_input_defaults():
    inp = EncoderInput()
    assert inp.state_21d is None
    assert inp.raw_signal is None
    assert inp.code_text is None
    assert inp.tongue_hint is None
    assert inp.context == {}


def test_encoder_input_with_signal():
    inp = EncoderInput(raw_signal=0.5, tongue_hint="KO")
    assert inp.raw_signal == 0.5
    assert inp.tongue_hint == "KO"


def test_hybrid_representation_frozen():
    h = HybridRepresentation(
        ternary_trits=(1, 0, -1),
        binary_bits=(1, 0, 1),
        ternary_int=7,
        binary_int=5,
        tongue_polarity="KO",
    )
    assert h.ternary_int == 7
    assert h.tongue_polarity == "KO"


def test_negative_space_embedding():
    ns = NegativeSpaceEmbedding(
        complement_trits=(-1, 0, 1, -1, 0, 1),
        excluded_tongues=["KO", "CA"],
        anti_energy=5.236,
    )
    assert len(ns.excluded_tongues) == 2


def test_molecular_bond():
    bond = MolecularBond(
        element_a="module",
        element_b="os",
        bond_type="ionic",
        valence=1,
        tongue_affinity="AV",
    )
    assert bond.bond_type == "ionic"
    assert bond.tongue_affinity == "AV"
