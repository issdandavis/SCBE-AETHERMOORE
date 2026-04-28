import numpy as np

from python.scbe.brain import (
    PHDMLattice,
    PoincareBall,
    ThoughtStatus,
    TrustRing,
    create_brain,
)
from python.scbe.phdm_embedding import PHDMEmbedder


def test_lattice_exposes_canonical_dimension_depth():
    assert PHDMLattice().get_dimension_depth() == 14


def test_trust_ring_uses_poincare_block_when_given_21d_vector():
    point = np.zeros(21)
    point[:6] = 0.05
    point[12:15] = 0.9

    assert PoincareBall().get_trust_ring(point) == TrustRing.CORE


def test_aetherbrain_legacy_path_accepts_21d_embedding_without_dict_path_crash():
    brain = create_brain()
    brain._circuit = None
    brain.lobes.trace_path = lambda _u, _context: {
        "nodes": [0],
        "tongue": "KO",
        "energy_cost": 1.0,
        "is_hamiltonian": True,
        "violations": [],
        "symplectic_momentum": 0.0,
    }

    result = brain.think(np.full(6, 0.05), {"session_id": "routing-test"})

    assert result.status in {ThoughtStatus.SUCCESS, ThoughtStatus.ESCALATED}
    assert result.ring != TrustRing.WALL
    assert result.result["path"]


def test_phdm_embedding_defaults_are_deterministic():
    embedder = PHDMEmbedder()

    first = embedder.encode("safe routing packet")
    second = embedder.encode("safe routing packet")

    np.testing.assert_allclose(first, second)
    assert len(first) == 21
