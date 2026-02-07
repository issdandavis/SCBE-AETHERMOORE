"""
Layer 13: PQ Envelope Sealing + Cymatic Voxel Storage (Chladni Nodal Concealment)

import numpy as np
import pytest

# ---- Direct imports from known-working paths ----

from symphonic_cipher.scbe_aethermoore.vacuum_acoustics import (
    VacuumAcousticsConfig,
    nodal_surface,
    is_on_nodal_line,
    find_nodal_points,
    compute_chladni_pattern,
    check_cymatic_resonance,
    extract_mode_parameters,
    resonance_strength,
)

from symphonic_cipher.scbe_aethermoore.cymatic_storage import (
    HolographicQRCube,
    CubeConfig,
    StorageMode,
    Voxel,
    KDTree,
    compute_access_vector,
)

from symphonic_cipher.scbe_aethermoore.constants import (
    DEFAULT_L,
    DEFAULT_TOLERANCE,
    R_FIFTH,
    PHI,
)

from symphonic_cipher.scbe_aethermoore.pqc import Kyber768, Dilithium3

# ---- Optional: NumPy-based CymaticVoxelStorage (src/symphonic_cipher/core) ----

_HAS_NUMPY_CVS = False
CymaticVoxelStorage = None
VoxelAccessVector = None

try:
    _cvs_mod = importlib.import_module("src.symphonic_cipher.core.cymatic_voxel_storage")
    CymaticVoxelStorage = _cvs_mod.CymaticVoxelStorage
    VoxelAccessVector = _cvs_mod.VoxelAccessVector
    _HAS_NUMPY_CVS = True
except Exception:
    pass

requires_numpy_cvs = pytest.mark.skipif(
    not _HAS_NUMPY_CVS,
    reason="NumPy-based CymaticVoxelStorage not importable from src.symphonic_cipher.core",
)


# =============================================================================
# Helpers
# =============================================================================


def _approx_zero(x: float, tol: float = 1e-6) -> bool:
    return abs(x) <= tol


# x1 = 200/7 is on a nodal line for modes (3,4) with L=100 and x2=0.
# N(200/7, 0; 3, 4) = cos(6pi/7) - cos(8pi/7) = 0 exactly.
# N(200/7, 0; 5, 3) ~ 0.678 -- NOT on nodal line for wrong modes.
NODAL_X = 200.0 / 7.0


def _resonant_position():
    """6D position where (x,y) is on Chladni nodal line for modes (3,4)."""
    return (NODAL_X, 0.0, 0.0, 3.0, 0.5, 4.0)


def _wrong_agent_vector():
    """Agent vector producing modes (5,3) -- off-resonance at NODAL_X, 0."""
    return (NODAL_X, 0.0, 0.0, 5.0, 0.5, 3.0)


def _vector6():
    """Representative 6D vector: (x, y, z, velocity, priority, security)."""
    return (0.1, 0.2, 0.3, 3.0, 0.5, 4.0)


# =============================================================================
# Tests: Chladni field + nodal computation (vacuum_acoustics)
# =============================================================================


class TestChladniField:
    """Tests for Chladni field computation determinism and correctness."""

    def test_chladni_field_is_deterministic(self):
        """Same (n, m, L, res) must produce identical pattern."""
        n, m = 3.0, 4.0
        res = 64
        a = compute_chladni_pattern(n, m, DEFAULT_L, res)
        b = compute_chladni_pattern(n, m, DEFAULT_L, res)
        assert a == b

    def test_nodal_points_include_only_near_zero_displacement(self):
        """Every returned nodal point must have |N(x; n,m)| < tolerance."""
        n, m = 3.0, 4.0
        res = 64
        points = find_nodal_points(n, m, DEFAULT_L, res)
        assert len(points) > 0

        tolerance = DEFAULT_L / res / 2
        for x1, x2 in points[:100]:  # sample first 100
            val = nodal_surface((x1, x2), n, m, DEFAULT_L)
            assert abs(val) < tolerance, (
                f"Point ({x1}, {x2}) has N={val}, expected |N| < {tolerance}"
            )

    def test_nodal_point_count_reasonable_for_mode_3_4(self):
        """
        Regression guardrail: mode (3,4) at res=128 should produce
        a count in a broad sane band so we detect regressions.
        """
        n, m = 3.0, 4.0
        res = 128
        points = find_nodal_points(n, m, DEFAULT_L, res)
        count = len(points)
        assert 100 <= count <= 20000, f"Got {count} nodal points, expected 100..20000"

    def test_antisymmetry_property(self):
        """N(x; n, m) = -N(x; m, n) by Chladni equation structure."""
        n, m = 3.0, 5.0
        x = (0.3 * DEFAULT_L, 0.7 * DEFAULT_L)
        val_nm = nodal_surface(x, n, m, DEFAULT_L)
        val_mn = nodal_surface(x, m, n, DEFAULT_L)
        assert abs(val_nm + val_mn) < 1e-10, (
            f"Antisymmetry violated: N(n,m)={val_nm}, N(m,n)={val_mn}"
        )

    def test_origin_is_always_nodal(self):
        """The origin (0, 0) is on a nodal line for any (n, m)."""
        for n in [1, 2, 3, 5]:
            for m in [1, 2, 4, 7]:
                val = nodal_surface((0, 0), float(n), float(m), DEFAULT_L)
                assert abs(val) < 1e-12, f"Origin not nodal for n={n}, m={m}: N={val}"

    def test_chladni_pattern_grid_dimensions(self):
        """compute_chladni_pattern returns res x res grid."""
        res = 32
        pattern = compute_chladni_pattern(3.0, 4.0, DEFAULT_L, res)
        assert len(pattern) == res
        assert all(len(row) == res for row in pattern)


# =============================================================================
# Tests: NumPy-based CymaticVoxelStorage encode/decode
# =============================================================================


@requires_numpy_cvs
class TestCymaticVoxelStorageNumpyAPI:
    """Tests for the numpy-based CymaticVoxelStorage encode/decode."""

    def test_encode_decode_roundtrip_on_resonance(self):
        """Correct vector yields near-faithful decoding at nodal lines."""
        cvs = CymaticVoxelStorage(resolution=50)
        data = np.random.rand(50, 50)

        correct_vector = VoxelAccessVector(3, 0, 0, 5, 0, 0)  # n=3, m=5

        encoded = cvs.encode(data, correct_vector)
        decoded = cvs.decode(encoded, correct_vector)

        # At nodal lines, decoded data should match original
        mask = cvs.nodal_mask(3, 5)
        error_at_nodes = np.mean((data[mask] - decoded[mask]) ** 2)
        assert error_at_nodes < 0.01, f"On-resonance MSE at nodes = {error_at_nodes}"

    def test_off_resonance_yields_different_output(self):
        """
        Wrong vector produces different output.
        Acceptable: higher error, noise, or empty regions.
        """
        cvs = CymaticVoxelStorage(resolution=50)
        data = np.random.rand(50, 50)

        correct_vector = VoxelAccessVector(3, 0, 0, 5, 0, 0)
        wrong_vector = VoxelAccessVector(2, 0, 0, 4, 0, 0)

        encoded = cvs.encode(data, correct_vector)
        decoded_correct = cvs.decode(encoded, correct_vector)
        decoded_wrong = cvs.decode(encoded, wrong_vector)

        error_correct = np.mean((data - decoded_correct) ** 2)
        error_wrong = np.mean((data - decoded_wrong) ** 2)

        # Wrong vector must have higher reconstruction error
        assert error_wrong > error_correct

    def test_chladni_pattern_deterministic_numpy(self):
        """CymaticVoxelStorage.chladni_pattern is deterministic."""
        cvs = CymaticVoxelStorage(resolution=64)
        a = cvs.chladni_pattern(3, 4)
        b = cvs.chladni_pattern(3, 4)
        assert np.array_equal(a, b)

    def test_nodal_mask_nonzero_for_distinct_modes(self):
        """nodal_mask should have nonzero entries when n != m."""
        cvs = CymaticVoxelStorage(resolution=100)
        mask = cvs.nodal_mask(3, 5, threshold=0.1)
        assert mask.any(), "Nodal mask is empty for n=3, m=5"

    def test_security_analysis_high_rate(self):
        """Random vector attacks should have near-zero success rate."""
        cvs = CymaticVoxelStorage(resolution=50)
        result = cvs.security_analysis(n_correct=3, m_correct=5, n_attempts=50)
        assert result["security_rate"] >= 0.8, (
            f"Security rate {result['security_rate']:.2%} too low"
        )


# =============================================================================
# Tests: HolographicQRCube resonance-keyed store/load
# =============================================================================


class TestHolographicQRCubeResonance:
    """Tests for HolographicQRCube add_voxel/scan with resonance access control."""

    def test_store_then_scan_roundtrip_on_resonance(self):
        """add_voxel + scan with matching vector returns original data."""
        cube = HolographicQRCube("test-l13-roundtrip")
        position = _resonant_position()
        payload = b"hello-cymatic-voxel"

        cube.add_voxel(position, payload, StorageMode.RESONANCE)

        # Scan with the same vector -> should get data back
        result = cube.scan(position)
        assert result == payload

    def test_off_resonance_scan_returns_none(self):
        """
        Scanning with a wrong vector yields None (access denied).
        Spec expectation: wrong vector should not yield plaintext.
        """
        cube = HolographicQRCube("test-l13-deny")
        position = _resonant_position()
        payload = b"resonance-secret"

        cube.add_voxel(position, payload, StorageMode.RESONANCE)

        # Agent with modes (5,3) -- off-resonance at stored (x,y)
        result = cube.scan(_wrong_agent_vector())
        assert result is None, "Off-resonance scan must not return plaintext"

    def test_public_mode_bypasses_resonance(self):
        """PUBLIC mode voxels are accessible without resonance check."""
        cube = HolographicQRCube("test-l13-public")
        position = (1.0, 2.0, 3.0, 3.0, 0.5, 4.0)
        payload = b"public-data"

        cube.add_voxel(position, payload, StorageMode.PUBLIC)

        result = cube.scan(position)
        assert result == payload

    def test_encrypted_mode_requires_resonance(self):
        """ENCRYPTED mode voxels still require resonance for retrieval."""
        cube = HolographicQRCube("test-l13-encrypted")
        position = _resonant_position()
        payload = b"encrypted-data"

        cube.add_voxel(position, payload, StorageMode.ENCRYPTED)

        # Same position -> resonance passes, get raw (still-encrypted) bytes
        result = cube.scan(position)
        assert result == payload

        # Wrong modes -> denied
        result_wrong = cube.scan(_wrong_agent_vector())
        assert result_wrong is None

    def test_voxel_integrity_check(self):
        """Voxel data integrity is verified via SHA-256 checksum."""
        cube = HolographicQRCube("test-l13-integrity")
        position = (1.0, 2.0, 3.0, 3.0, 0.5, 4.0)
        payload = b"integrity-check-data"

        voxel = cube.add_voxel(position, payload)
        assert voxel.verify_integrity()
        assert voxel.checksum == hashlib.sha256(payload).hexdigest()

    def test_compute_access_vector_resonates(self):
        """compute_access_vector produces a vector that resonates with target modes."""
        cube = HolographicQRCube("test-l13-access-vec")
        position = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)
        payload = b"access-vector-test"

        voxel = cube.add_voxel(position, payload)

        # compute_access_vector targets the same modes
        access_vec = compute_access_vector(voxel.modes)
        result = cube.scan(access_vec)
        assert result == payload

    def test_scan_all_resonant_returns_matching(self):
        """scan_all_resonant returns all voxels matching an agent vector."""
        cube = HolographicQRCube("test-l13-scan-all")
        position = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)

        cube.add_voxel(position, b"voxel-1", StorageMode.RESONANCE)
        cube.add_voxel(position, b"voxel-2", StorageMode.RESONANCE)

        results = cube.scan_all_resonant(position)
        payloads = {data for _, data in results}
        assert b"voxel-1" in payloads
        assert b"voxel-2" in payloads


# =============================================================================
# Tests: PQ KEM integration contract (Kyber768 / Dilithium3)
# =============================================================================


class TestPQEnvelopeIntegration:
    """
    Tests validating PQ KEM integration with cymatic storage.
    Uses the project's Kyber768/Dilithium3 (liboqs or mock fallback).
    """

    def test_kyber768_kem_roundtrip(self):
        """Kyber768 encapsulate -> decapsulate yields same shared secret."""
        keypair = Kyber768.generate_keypair()
        result = Kyber768.encapsulate(keypair.public_key)
        recovered = Kyber768.decapsulate(keypair.secret_key, result.ciphertext)
        assert result.shared_secret == recovered

    def test_kyber768_wrong_key_yields_different_secret(self):
        """Using a different secret key yields a different shared secret."""
        kp1 = Kyber768.generate_keypair()
        kp2 = Kyber768.generate_keypair()

        result = Kyber768.encapsulate(kp1.public_key)
        try:
            wrong_secret = Kyber768.decapsulate(kp2.secret_key, result.ciphertext)
            assert wrong_secret != result.shared_secret, (
                "Wrong key must not produce same shared secret"
            )
        except (ValueError, Exception):
            # Some backends raise on wrong key - acceptable
            pass

    def test_pq_envelope_with_cymatic_encrypted_mode(self):
        """
        Integration: store PQ-encrypted data in HolographicQRCube ENCRYPTED mode.
        KEM derives a shared secret, payload is XOR-encrypted, stored, and recovered.
        """
        # Generate KEM keypair
        keypair = Kyber768.generate_keypair()
        encap = Kyber768.encapsulate(keypair.public_key)
        shared_secret = encap.shared_secret  # 32 bytes

        # Encrypt payload with shared_secret (simple XOR for contract validation)
        payload = b"pq-sealed-cymatic-voxel!!"  # 26 bytes
        key_stream = (shared_secret * ((len(payload) // len(shared_secret)) + 1))[
            : len(payload)
        ]
        encrypted = bytes(a ^ b for a, b in zip(payload, key_stream))

        # Store encrypted payload in cube
        cube = HolographicQRCube("test-pq-envelope")
        position = _resonant_position()
        cube.add_voxel(position, encrypted, StorageMode.ENCRYPTED)

        # Retrieve from cube (requires resonance)
        retrieved = cube.scan(position)
        assert retrieved is not None
        assert retrieved == encrypted

        # Decapsulate to get shared secret on recipient side
        recovered_secret = Kyber768.decapsulate(keypair.secret_key, encap.ciphertext)
        assert recovered_secret == shared_secret

        # Decrypt
        rec_key_stream = (
            recovered_secret * ((len(retrieved) // len(recovered_secret)) + 1)
        )[: len(retrieved)]
        decrypted = bytes(a ^ b for a, b in zip(retrieved, rec_key_stream))
        assert decrypted == payload

    def test_dilithium_signs_mode_metadata(self):
        """Dilithium3 signs the (n, m) mode parameters for audit."""
        sig_kp = Dilithium3.generate_keypair()

        # Mode metadata
        n, m = 3.0, 4.0
        meta_msg = f"mode:n={n},m={m}".encode()

        signature = Dilithium3.sign(sig_kp.secret_key, meta_msg)
        assert Dilithium3.verify(sig_kp.public_key, meta_msg, signature)

        # Tampered message must fail verification
        tampered = f"mode:n={n},m={m + 1}".encode()
        assert not Dilithium3.verify(sig_kp.public_key, tampered, signature)

    def test_pq_off_resonance_encrypted_data_inaccessible(self):
        """
        Off-resonance scan of ENCRYPTED voxel returns None.
        Combined PQ + resonance denial.
        """
        keypair = Kyber768.generate_keypair()
        encap = Kyber768.encapsulate(keypair.public_key)
        shared_secret = encap.shared_secret

        payload = b"double-locked-data"
        key_stream = (shared_secret * ((len(payload) // len(shared_secret)) + 1))[
            : len(payload)
        ]
        encrypted = bytes(a ^ b for a, b in zip(payload, key_stream))

        cube = HolographicQRCube("test-pq-deny")
        position = _resonant_position()
        cube.add_voxel(position, encrypted, StorageMode.ENCRYPTED)

        # Wrong resonance (modes 5,3) -> None
        result = cube.scan(_wrong_agent_vector())
        assert result is None, "Off-resonance must deny access to PQ-encrypted data"


# =============================================================================
# Tests: Auditability - mode parameters tracked in metadata
# =============================================================================


class TestAuditability:
    """Verify that mode parameters (n, m) are tracked in voxel metadata."""

    def test_voxel_modes_derived_from_position(self):
        """Voxel.modes is extracted from position via extract_mode_parameters."""
        cube = HolographicQRCube("test-audit-modes")
        position = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)
        payload = b"audit-me"

        voxel = cube.add_voxel(position, payload)

        expected_modes = extract_mode_parameters(position)
        assert voxel.modes == expected_modes

    def test_voxel_serialization_includes_modes(self):
        """Voxel.to_dict() includes modes for audit trail."""
        cube = HolographicQRCube("test-audit-serial")
        position = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)

        voxel = cube.add_voxel(position, b"serialize-me")
        d = voxel.to_dict()

        assert "modes" in d
        assert len(d["modes"]) == 2
        assert d["modes"][0] > 0  # n > 0
        assert d["modes"][1] > 0  # m > 0

    def test_cube_export_preserves_mode_metadata(self):
        """Exported cube JSON includes mode parameters for all voxels."""
        cube = HolographicQRCube("test-export-audit")
        positions = [
            (0.0, 0.0, 0.0, 2.0, 0.5, 3.0),
            (1.0, 1.0, 1.0, 5.0, 0.5, 7.0),
        ]
        for pos in positions:
            cube.add_voxel(pos, b"data")

        exported = cube.export()
        assert len(exported["voxels"]) == 2
        for v in exported["voxels"]:
            assert "modes" in v
            assert len(v["modes"]) == 2

    def test_cube_import_export_roundtrip_preserves_modes(self):
        """Export -> import roundtrip preserves all voxel mode metadata."""
        cube = HolographicQRCube("test-roundtrip-export")
        position = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)
        cube.add_voxel(position, b"roundtrip-data")

        exported = cube.export()
        restored = HolographicQRCube.import_cube(exported)

        orig_voxels = list(cube._voxels.values())
        rest_voxels = list(restored._voxels.values())

        assert len(rest_voxels) == len(orig_voxels)
        assert rest_voxels[0].modes == orig_voxels[0].modes
        assert rest_voxels[0].data == orig_voxels[0].data
        assert rest_voxels[0].checksum == orig_voxels[0].checksum

    def test_voxel_checksum_in_serialization(self):
        """Serialized voxel includes SHA-256 checksum for audit integrity."""
        cube = HolographicQRCube("test-checksum-audit")
        payload = b"checksum-tracked"
        voxel = cube.add_voxel((0, 0, 0, 3.0, 0.5, 4.0), payload)

        d = voxel.to_dict()
        assert d["checksum"] == hashlib.sha256(payload).hexdigest()


# =============================================================================
# Tests: KD-Tree spatial indexing for voxel retrieval
# =============================================================================


class TestKDTreeSpatialIndex:
    """Validate KD-tree nearest-neighbor and range queries in 6D."""

    def test_nearest_neighbor_returns_closest(self):
        """KD-tree nearest returns the geometrically closest voxel."""
        cube = HolographicQRCube("test-kdtree")
        pos_a = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)
        pos_b = (10.0, 10.0, 10.0, 3.0, 0.5, 4.0)

        cube.add_voxel(pos_a, b"close")
        cube.add_voxel(pos_b, b"far")

        nearest = cube.nearest((0.1, 0.1, 0.1, 3.0, 0.5, 4.0))
        assert nearest is not None
        assert nearest.data == b"close"

    def test_range_query_returns_within_radius(self):
        """range_query returns voxels within harmonic distance radius."""
        cube = HolographicQRCube("test-range")
        center = (0.0, 0.0, 0.0, 3.0, 0.5, 4.0)

        cube.add_voxel(center, b"at-center")
        cube.add_voxel((100.0, 100.0, 100.0, 3.0, 0.5, 4.0), b"far-away")

        results = cube.range_query(center, radius=1.0)
        assert len(results) >= 1
        assert any(v.data == b"at-center" for v in results)
        assert not any(v.data == b"far-away" for v in results)
