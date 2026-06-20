"""Regression locks for the geometry view (python/scbe/geometry_view.py).

The rotor classifier is a pure function and always runs; the RDKit-backed paths
skip cleanly where RDKit is not installed.
"""

from __future__ import annotations

import pytest

from python.scbe.geometry_view import GeometryEngineError, rotor_type


def test_rotor_type_pure_classification():
    assert rotor_type([0.0, 1.0, 1.0]) == "linear"
    assert rotor_type([1.0, 1.0, 1.0]) == "spherical_top"
    assert rotor_type([1.0, 1.0, 2.0]) == "symmetric_top"
    assert rotor_type([1.0, 2.0, 3.0]) == "asymmetric_top"


def test_rotor_type_is_order_independent():
    assert rotor_type([2.0, 0.0, 2.0]) == "linear"


def test_geometry_descriptors_co2_is_linear():
    pytest.importorskip("rdkit")
    from python.scbe.geometry_view import geometry_descriptors

    desc = geometry_descriptors("O=C=O")
    assert desc["rotor_type"] == "linear"
    assert desc["formula"] == "CO2"


def test_geometry_descriptors_methane_is_spherical():
    pytest.importorskip("rdkit")
    from python.scbe.geometry_view import geometry_descriptors

    desc = geometry_descriptors("C")
    assert desc["rotor_type"] == "spherical_top"


def test_geometry_packet_is_lossy_recoverable_and_hash_verifies():
    pytest.importorskip("rdkit")
    from python.scbe.geometry_view import geometry_view_packet

    packet = geometry_view_packet("CCO")
    assert packet.domain == "geometry"
    assert packet.classification == "LOSSY_RECOVERABLE"
    assert packet.verify_hash()
    assert packet.target.metadata["rotor_type"] in {
        "linear",
        "spherical_top",
        "symmetric_top",
        "asymmetric_top",
    }


def test_invalid_smiles_raises():
    pytest.importorskip("rdkit")
    from python.scbe.geometry_view import geometry_descriptors

    with pytest.raises(GeometryEngineError):
        geometry_descriptors("not_a_smiles@@@")
