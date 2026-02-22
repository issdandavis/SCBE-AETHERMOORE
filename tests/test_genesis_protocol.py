"""Genesis Protocol Tests — AI Identity Cube + Batch Birth

Tests cover:
  - Identity Cube minting from hatched eggs
  - Batch offset generation (phi-spiral, non-duplicate)
  - GenesisField coherence computation
  - Batch creation and hatching
  - Cube verification (hash integrity)
  - Batch membership checks
  - No two cubes in a batch are identical

@layer Layer 12, Layer 13
@component Genesis Protocol Tests
"""

import base64
import math
import os

import pytest

from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    CrossTokenizer,
    TongueTokenizer,
    Lexicons,
    TONGUES,
)
from src.symphonic_cipher.scbe_aethermoore.sacred_egg_integrator import (
    SacredEggIntegrator,
)
from src.symphonic_cipher.scbe_aethermoore.genesis_protocol import (
    IdentityCube,
    GenesisField,
    GenesisProtocol,
    generate_batch_offsets,
    mint_identity_cube,
    PHI,
)


@pytest.fixture
def integrator():
    lex = Lexicons()
    tok = TongueTokenizer(lex)
    xt = CrossTokenizer(tok)
    return SacredEggIntegrator(xt)


@pytest.fixture
def protocol(integrator):
    return GenesisProtocol(integrator)


@pytest.fixture
def key_pair():
    pk = base64.b64encode(os.urandom(32)).decode()
    sk = pk
    return pk, sk


@pytest.fixture
def interior_context():
    return [0.0, 0.0, 0.0, -5.0, -5.0, -5.0]


class TestBatchOffsets:

    def test_correct_count(self):
        offsets = generate_batch_offsets(6, os.urandom(32))
        assert len(offsets) == 6

    def test_6d_vectors(self):
        offsets = generate_batch_offsets(3, os.urandom(32))
        for off in offsets:
            assert len(off) == 6

    def test_no_duplicates(self):
        offsets = generate_batch_offsets(100, os.urandom(32))
        assert len(set(offsets)) == 100

    def test_deterministic_from_seed(self):
        seed = b"fixed_seed_for_testing_12345678"
        off1 = generate_batch_offsets(10, seed)
        off2 = generate_batch_offsets(10, seed)
        assert off1 == off2

    def test_different_seeds_different_offsets(self):
        off1 = generate_batch_offsets(5, b"seed_a_" + b"\x00" * 25)
        off2 = generate_batch_offsets(5, b"seed_b_" + b"\x00" * 25)
        assert off1 != off2

    def test_values_bounded(self):
        offsets = generate_batch_offsets(50, os.urandom(32))
        for off in offsets:
            for v in off:
                assert -1.0 <= v <= 1.0


class TestGenesisField:

    def test_single_vector_coherence_is_one(self):
        field = GenesisField(
            intent_vectors=[[1.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
            tongue_weights={"KO": 1.0},
        )
        field.compute_coherence()
        assert field.coherence_score == 1.0

    def test_identical_vectors_high_coherence(self):
        v = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        field = GenesisField(
            intent_vectors=[v, v, v],
            tongue_weights={"KO": 1.0, "AV": 1.618, "RU": 2.618},
        )
        field.compute_coherence()
        assert field.coherence_score > 0.99

    def test_opposite_vectors_low_coherence(self):
        field = GenesisField(
            intent_vectors=[
                [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            tongue_weights={"KO": 1.0},
        )
        field.compute_coherence()
        assert field.coherence_score < -0.99

    def test_compute_centroid(self):
        field = GenesisField(
            intent_vectors=[
                [2.0, 4.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            tongue_weights={},
        )
        field.compute_centroid()
        assert field.centroid[0] == pytest.approx(1.0)
        assert field.centroid[1] == pytest.approx(2.0)


class TestMintIdentityCube:

    def test_mint_produces_cube(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        egg = integrator.create_egg(
            b"init data", "KO", "cube", {"path": "interior"},
            interior_context, pk, sk,
        )
        result = integrator.hatch_egg(
            egg, interior_context, "KO", sk, pk, ritual_mode="solitary",
        )
        assert result.success

        offset = (0.01, -0.02, 0.03, -0.01, 0.02, -0.03)
        cube = mint_identity_cube(
            egg, result, "batch_001", 0, offset, interior_context,
        )
        assert len(cube.cube_id) == 16
        assert cube.tongue_affinity == "KO"
        assert cube.batch_id == "batch_001"
        assert cube.batch_index == 0
        assert cube.egg_id == egg.egg_id
        assert len(cube.cube_vector) == 6

    def test_different_offsets_different_cubes(self, integrator, key_pair, interior_context):
        pk, sk = key_pair
        egg = integrator.create_egg(
            b"data", "AV", "g", {"path": "interior"},
            interior_context, pk, sk,
        )
        result = integrator.hatch_egg(
            egg, interior_context, "AV", sk, pk, ritual_mode="solitary",
        )

        cube1 = mint_identity_cube(
            egg, result, "batch", 0, (0.1, 0.1, 0.1, 0.1, 0.1, 0.1), interior_context,
        )
        cube2 = mint_identity_cube(
            egg, result, "batch", 1, (-0.1, -0.1, -0.1, -0.1, -0.1, -0.1), interior_context,
        )
        assert cube1.cube_id != cube2.cube_id
        assert cube1.cube_vector != cube2.cube_vector


class TestGenesisProtocol:

    def test_create_batch(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        payloads = [b"ai_0", b"ai_1", b"ai_2"]
        batch_id, eggs = protocol.create_batch(
            payloads, "RU", interior_context, pk, sk,
        )
        assert len(batch_id) == 12
        assert len(eggs) == 3
        for egg in eggs:
            assert egg.primary_tongue == "RU"
            assert egg.glyph == "hatchling"

    def test_hatch_batch(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        payloads = [b"ai_0", b"ai_1", b"ai_2", b"ai_3"]
        batch_id, eggs = protocol.create_batch(
            payloads, "KO", interior_context, pk, sk,
            hatch_condition={"path": "interior"},
        )

        cubes = protocol.hatch_batch(
            batch_id, eggs, interior_context, "KO", sk, pk,
            batch_seed=b"test_seed_" + b"\x00" * 22,
        )
        assert len(cubes) == 4
        for cube in cubes:
            assert cube is not None
            assert cube.batch_id == batch_id
            assert cube.tongue_affinity == "KO"

    def test_all_cubes_unique(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        payloads = [f"ai_{i}".encode() for i in range(6)]
        batch_id, eggs = protocol.create_batch(
            payloads, "DR", interior_context, pk, sk,
            hatch_condition={"path": "interior"},
        )
        cubes = protocol.hatch_batch(
            batch_id, eggs, interior_context, "DR", sk, pk,
        )
        cube_ids = [c.cube_id for c in cubes if c is not None]
        assert len(set(cube_ids)) == 6  # all unique

    def test_failed_hatch_returns_none(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        batch_id, eggs = protocol.create_batch(
            [b"data"], "KO", interior_context, pk, sk,
            hatch_condition={"path": "interior"},
        )
        # Hatch with wrong tongue
        cubes = protocol.hatch_batch(
            batch_id, eggs, interior_context, "DR", sk, pk,
        )
        assert cubes[0] is None

    def test_verify_cube(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        batch_id, eggs = protocol.create_batch(
            [b"verify_me"], "UM", interior_context, pk, sk,
            hatch_condition={"path": "interior"},
        )
        cubes = protocol.hatch_batch(
            batch_id, eggs, interior_context, "UM", sk, pk,
        )
        cube = cubes[0]
        assert cube is not None
        assert protocol.verify_cube(cube) is True

    def test_tampered_cube_fails_verification(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        batch_id, eggs = protocol.create_batch(
            [b"tamper"], "CA", interior_context, pk, sk,
            hatch_condition={"path": "interior"},
        )
        cubes = protocol.hatch_batch(
            batch_id, eggs, interior_context, "CA", sk, pk,
        )
        cube = cubes[0]
        # Tamper with batch_index
        import dataclasses
        tampered = dataclasses.replace(cube, batch_index=999)
        assert protocol.verify_cube(tampered) is False

    def test_cubes_in_same_batch(self, protocol, key_pair, interior_context):
        pk, sk = key_pair
        batch_id, eggs = protocol.create_batch(
            [b"a", b"b"], "KO", interior_context, pk, sk,
            hatch_condition={"path": "interior"},
        )
        cubes = protocol.hatch_batch(
            batch_id, eggs, interior_context, "KO", sk, pk,
        )
        assert protocol.cubes_in_same_batch(cubes)

    def test_six_tongue_batch(self, protocol, key_pair, interior_context):
        """Create 6 AIs, one per tongue."""
        pk, sk = key_pair
        all_cubes = []
        for tongue in TONGUES:
            batch_id, eggs = protocol.create_batch(
                [f"init_{tongue}".encode()], tongue, interior_context, pk, sk,
                hatch_condition={"path": "interior"},
            )
            cubes = protocol.hatch_batch(
                batch_id, eggs, interior_context, tongue, sk, pk,
            )
            assert cubes[0] is not None
            assert cubes[0].tongue_affinity == tongue
            all_cubes.append(cubes[0])

        # All 6 have different tongue affinities
        affinities = {c.tongue_affinity for c in all_cubes}
        assert affinities == set(TONGUES)

        # All 6 have unique cube IDs
        ids = {c.cube_id for c in all_cubes}
        assert len(ids) == 6
