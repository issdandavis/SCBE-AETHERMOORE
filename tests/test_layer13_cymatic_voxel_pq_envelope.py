"""
Layer 13 contract tests for cymatic voxel storage + PQ envelope behavior.
"""

from __future__ import annotations

import hashlib

import pytest

from symphonic_cipher.scbe_aethermoore.cymatic_storage import (
    HolographicQRCube,
    StorageMode,
    compute_access_vector,
)
from symphonic_cipher.scbe_aethermoore.pqc import Dilithium3, Kyber768
from symphonic_cipher.scbe_aethermoore.vacuum_acoustics import (
    check_cymatic_resonance,
    extract_mode_parameters,
    find_nodal_points,
    nodal_surface,
)


def resonant_position() -> tuple[float, float, float, float, float, float]:
    # n = velocity = 3, m = security = 4.
    return (200.0 / 7.0, 0.0, 0.0, 3.0, 0.5, 4.0)


def non_resonant_vector() -> tuple[float, float, float, float, float, float]:
    # wrong modes for the same x/y target.
    return (200.0 / 7.0, 0.0, 0.0, 5.0, 0.5, 3.0)


class TestVacuumAcousticsNodalContracts:
    def test_origin_is_nodal(self):
        assert abs(nodal_surface((0.0, 0.0), 3.0, 4.0)) < 1e-12

    def test_find_nodal_points_nonempty(self):
        pts = find_nodal_points(3.0, 4.0, resolution=64)
        assert len(pts) > 0

    def test_mode_extraction_and_resonance(self):
        vec = resonant_position()
        n, m = extract_mode_parameters(vec)
        assert abs(n - 3.0) < 1e-9
        assert abs(m - 4.0) < 1e-9
        assert check_cymatic_resonance(vec, (200.0 / 7.0, 0.0))


class TestCymaticVoxelStorage:
    def test_store_scan_roundtrip(self):
        cube = HolographicQRCube("l13-roundtrip")
        pos = resonant_position()
        payload = b"hello-cymatic"
        cube.add_voxel(pos, payload, StorageMode.RESONANCE)
        out = cube.scan(pos)
        assert out == payload

    def test_off_resonance_denied(self):
        cube = HolographicQRCube("l13-deny")
        pos = resonant_position()
        cube.add_voxel(pos, b"secret", StorageMode.RESONANCE)
        out = cube.scan(non_resonant_vector())
        assert out is None

    def test_public_mode_bypass(self):
        cube = HolographicQRCube("l13-public")
        pos = resonant_position()
        cube.add_voxel(pos, b"public", StorageMode.PUBLIC)
        assert cube.scan(non_resonant_vector()) == b"public"

    def test_checksum_and_mode_metadata(self):
        cube = HolographicQRCube("l13-audit")
        pos = resonant_position()
        payload = b"audit"
        voxel = cube.add_voxel(pos, payload, StorageMode.ENCRYPTED)
        assert voxel.verify_integrity()
        assert voxel.checksum == hashlib.sha256(payload).hexdigest()
        assert voxel.modes == extract_mode_parameters(pos)

    def test_compute_access_vector_matches_modes(self):
        cube = HolographicQRCube("l13-access")
        pos = resonant_position()
        voxel = cube.add_voxel(pos, b"v1", StorageMode.RESONANCE)
        access_vec = compute_access_vector(voxel.modes)
        assert cube.scan(access_vec) == b"v1"


class TestPQEnvelope:
    def test_kyber_roundtrip(self):
        kp = Kyber768.generate_keypair()
        enc = Kyber768.encapsulate(kp.public_key)
        shared2 = Kyber768.decapsulate(kp.secret_key, enc.ciphertext)
        assert shared2 == enc.shared_secret

    def test_pq_xor_envelope_with_cymatic_storage(self):
        kp = Kyber768.generate_keypair()
        enc = Kyber768.encapsulate(kp.public_key)
        shared = enc.shared_secret
        payload = b"pq-sealed"
        key_stream = (shared * ((len(payload) // len(shared)) + 1))[: len(payload)]
        encrypted = bytes(a ^ b for a, b in zip(payload, key_stream))

        cube = HolographicQRCube("l13-pq")
        pos = resonant_position()
        cube.add_voxel(pos, encrypted, StorageMode.ENCRYPTED)
        retrieved = cube.scan(pos)
        assert retrieved == encrypted

        recovered = Kyber768.decapsulate(kp.secret_key, enc.ciphertext)
        key_stream2 = (recovered * ((len(payload) // len(recovered)) + 1))[: len(payload)]
        decrypted = bytes(a ^ b for a, b in zip(retrieved, key_stream2))
        assert decrypted == payload

    def test_dilithium_signature_for_mode_metadata(self):
        kp = Dilithium3.generate_keypair()
        message = b"mode:n=3,m=4"
        sig = Dilithium3.sign(kp.secret_key, message)
        assert Dilithium3.verify(kp.public_key, message, sig)
        assert not Dilithium3.verify(kp.public_key, b"mode:n=3,m=5", sig)
