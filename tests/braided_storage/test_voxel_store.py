"""Tests for BraidedVoxelStore — VoxelComb."""

import pytest

from src.braided_storage.braid_weaver import BraidWeaver
from src.braided_storage.types import BraidedPayload, SemanticBits
from src.braided_storage.voxel_store import VoxelComb
from src.symphonic_cipher.core.cymatic_voxel_storage import VoxelAccessVector


def _make_braided(**overrides) -> BraidedPayload:
    bits = SemanticBits(
        dominant_tongue=overrides.pop("tongue", "KO"),
        tongue_trits=overrides.pop("trits", [1, 0, -1, 0, 1, -1]),
        fingerprint_ids=["fp1"],
        sha256_hash="a" * 64,
        threat_score=0.0,
        governance_decision="ALLOW",
    )
    defaults = dict(
        strand_intent=0.8,
        strand_memory=0.9,
        strand_governance=0.1,
        braided_time=0.072,
        d_braid=0.5,
        harmonic_cost=1.3,
        phase_state=(1, -1),
        phase_label="advance-contract",
        semantic_bits=bits,
        raw_bytes=b"test data for voxel store",
        source="test://voxel",
        mime_type="text/plain",
        quarantined=False,
    )
    defaults.update(overrides)
    return BraidedPayload(**defaults)


@pytest.fixture
def comb():
    return VoxelComb(resolution=16, octree_grid_size=32, octree_max_depth=4)


class TestDepositRetrieve:
    def test_deposit_retrieve(self, comb):
        braided = _make_braided()
        cube_id = comb.deposit(braided)
        assert cube_id.startswith("vx_")

        result = comb.retrieve(cube_id)
        assert result is not None
        decoded_grid, retrieved_braided = result
        assert retrieved_braided.source == "test://voxel"

    def test_retrieve_nonexistent(self, comb):
        assert comb.retrieve("vx_nonexistent") is None


class TestCluster:
    def test_cluster_by_tongue(self, comb):
        for tongue in ["KO", "KO", "AV", "DR"]:
            braided = _make_braided(tongue=tongue)
            comb.deposit(braided)

        clusters = comb.cluster(tongue="KO")
        assert isinstance(clusters, dict)
        # Should have at least some non-zero cluster
        assert sum(clusters.values()) > 0

    def test_cluster_polarity(self, comb):
        braided = _make_braided()
        comb.deposit(braided)
        clusters = comb.cluster()
        assert isinstance(clusters, dict)


class TestAccessVector:
    def test_access_vector_from_braid(self, comb):
        braided = _make_braided(trits=[1, 0, -1, 1, -1, 0])
        vec = comb._access_vector_from_braid(braided)
        assert isinstance(vec, VoxelAccessVector)
        # trit 1 -> 3, trit 0 -> 2, trit -1 -> 1
        assert vec.velocity_x == 3.0
        assert vec.velocity_y == 2.0
        assert vec.velocity_z == 1.0
        assert vec.security_x == 3.0
        assert vec.security_y == 1.0
        assert vec.security_z == 2.0


class TestOctree:
    def test_octree_insertion(self, comb):
        braided = _make_braided()
        comb.deposit(braided)
        assert comb.octree_point_count >= 1

    def test_occupancy(self, comb):
        occ = comb.occupancy()
        assert isinstance(occ, float)
        assert 0.0 <= occ <= 1.0


class TestSpectralNeighbors:
    def test_spectral_neighbors(self, comb):
        for i in range(5):
            braided = _make_braided(tongue="KO")
            comb.deposit(braided)

        neighbors = comb.find_neighbors("abc123", max_distance=2.0)
        assert isinstance(neighbors, list)
