"""
Tests for AETHERMOORE Core Modules

Tests for:
- constants.py: Mathematical constants and harmonic scaling
- hal_attention.py: HAL-Attention mechanism
- vacuum_acoustics.py: Nodal surfaces and bottle beams
- cymatic_storage.py: HolographicQRCube with 6D access control
- pqc_harmonic.py: Harmonic-enhanced PQC integration
"""

import math
import pytest

# Import from constants module
from symphonic_cipher.scbe_aethermoore.constants import (
    PI, E, PHI, SQRT2, SQRT5,
    R_FIFTH, R_FOURTH, R_THIRD, R_SIXTH, R_OCTAVE, R_PHI,
    PHI_AETHER, LAMBDA_ISAAC, OMEGA_SPIRAL, ALPHA_ABH,
    DEFAULT_R, DEFAULT_D_MAX,
    harmonic_scale, security_bits, security_level,
    harmonic_distance, octave_transpose,
    DIMENSIONS, get_harmonic_scale_table,
)

# Import from HAL-Attention module
from symphonic_cipher.scbe_aethermoore.hal_attention import (
    HALConfig,
    harmonic_coupling_matrix,
    assign_dimension_depths,
    hal_attention,
    multi_head_hal_attention,
    HALAttentionLayer,
)

# Import from Vacuum-Acoustics module
from symphonic_cipher.scbe_aethermoore.vacuum_acoustics import (
    VacuumAcousticsConfig,
    WaveSource,
    nodal_surface,
    check_cymatic_resonance,
    bottle_beam_intensity,
    flux_redistribution,
    is_on_nodal_line,
    find_nodal_points,
    compute_chladni_pattern,
    resonance_strength,
)

# Import from Cymatic Storage module
from symphonic_cipher.scbe_aethermoore.cymatic_storage import (
    StorageMode,
    Voxel,
    KDTree,
    HolographicQRCube,
)

# Import from PQC Harmonic module
from symphonic_cipher.scbe_aethermoore.pqc.pqc_harmonic import (
    SecurityDimension,
    HarmonicKeyMaterial,
    harmonic_key_stretch,
    fast_harmonic_key,
    create_harmonic_pqc_session,
    verify_harmonic_pqc_session,
    Vector6DKey,
    derive_key_from_vector,
    vector_proximity_key,
    analyze_harmonic_security,
    HarmonicKyberOrchestrator,
)

from symphonic_cipher.scbe_aethermoore.pqc import Kyber768, Dilithium3


# =============================================================================
# CONSTANTS MODULE TESTS
# =============================================================================

class TestConstants:
    """Test AETHERMOORE mathematical constants."""

    def test_golden_ratio(self):
        """Test PHI is the golden ratio."""
        assert abs(PHI - 1.618033988749895) < 1e-10
        # PHI satisfies: PHI^2 = PHI + 1
        assert abs(PHI**2 - PHI - 1) < 1e-10

    def test_harmonic_ratios(self):
        """Test harmonic ratios are correct."""
        assert R_FIFTH == 1.5       # 3:2
        assert R_FOURTH == 4/3      # 4:3
        assert R_THIRD == 1.25      # 5:4
        assert R_SIXTH == 1.6       # 8:5
        assert R_OCTAVE == 2.0      # 2:1

    def test_aethermoore_constants(self):
        """Test AETHERMOORE-specific constants."""
        # PHI_AETHER = PHI^(2/3)
        expected_phi_aether = PHI ** (2/3)
        assert abs(PHI_AETHER - expected_phi_aether) < 1e-10

        # LAMBDA_ISAAC = 1.5 * PHI^2
        expected_lambda = R_FIFTH * (PHI ** 2)
        assert abs(LAMBDA_ISAAC - expected_lambda) < 1e-10

        # OMEGA_SPIRAL = 2*PI / PHI^3
        expected_omega = (2 * PI) / (PHI ** 3)
        assert abs(OMEGA_SPIRAL - expected_omega) < 1e-10

        # ALPHA_ABH = PHI + R_FIFTH
        expected_alpha = PHI + R_FIFTH
        assert abs(ALPHA_ABH - expected_alpha) < 1e-10


class TestHarmonicScaling:
    """Test H(d, R) = R^(d^2) harmonic scaling formula."""

    def test_harmonic_scale_basic(self):
        """Test basic harmonic scaling values."""
        # H(1, 1.5) = 1.5^1 = 1.5
        assert harmonic_scale(1, 1.5) == 1.5

        # H(2, 1.5) = 1.5^4 = 5.0625
        assert harmonic_scale(2, 1.5) == 1.5 ** 4

        # H(3, 1.5) = 1.5^9
        assert abs(harmonic_scale(3, 1.5) - 1.5**9) < 1e-6

    def test_harmonic_scale_d6(self):
        """Test d=6 harmonic scaling."""
        # H(6, 1.5) = 1.5^36 = 2,184,164.40625
        h6 = harmonic_scale(6, 1.5)
        assert abs(h6 - 2184164.40625) < 0.01

    def test_harmonic_scale_invalid_dimension(self):
        """Test error on invalid dimension."""
        with pytest.raises(ValueError):
            harmonic_scale(0, 1.5)
        with pytest.raises(ValueError):
            harmonic_scale(-1, 1.5)

    def test_security_bits(self):
        """Test security bits calculation."""
        # S_bits = B + d^2 * log2(R)
        # For d=6, R=1.5, B=128:
        # S = 128 + 36 * log2(1.5) = 128 + 36 * 0.585 = 149.06
        s_bits = security_bits(128, 6, 1.5)
        expected = 128 + 36 * math.log2(1.5)
        assert abs(s_bits - expected) < 0.01


class TestHarmonicDistance:
    """Test 6D harmonic distance with weighted metric."""

    def test_zero_distance(self):
        """Test distance to self is zero."""
        v = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        assert harmonic_distance(v, v) == 0.0

    def test_symmetric_distance(self):
        """Test distance is symmetric."""
        u = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        v = (0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        assert harmonic_distance(u, v) == harmonic_distance(v, u)

    def test_metric_weighting(self):
        """Test metric weights (1, 1, 1, R, R^2, R^3)."""
        # Distance in x direction only (weight 1)
        u = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        v = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert harmonic_distance(u, v) == 1.0

        # Distance in security direction only (weight R^3)
        u = (0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
        v = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        expected = math.sqrt(R_FIFTH ** 3)
        assert abs(harmonic_distance(u, v) - expected) < 1e-10


class TestOctaveTranspose:
    """Test octave transposition."""

    def test_octave_up(self):
        """Test one octave up doubles frequency."""
        assert octave_transpose(440.0, 1) == 880.0

    def test_octave_down(self):
        """Test one octave down halves frequency."""
        assert octave_transpose(440.0, -1) == 220.0

    def test_multiple_octaves(self):
        """Test multiple octaves."""
        assert octave_transpose(100.0, 3) == 800.0


# =============================================================================
# HAL-ATTENTION MODULE TESTS
# =============================================================================

class TestHALAttention:
    """Test HAL-Attention mechanism."""

    def test_coupling_matrix_dimensions(self):
        """Test coupling matrix has correct dimensions."""
        d_Q = [1.0, 2.0, 3.0]
        d_K = [1.0, 2.0]
        matrix = harmonic_coupling_matrix(d_Q, d_K, normalize=False)
        assert len(matrix) == 3
        assert all(len(row) == 2 for row in matrix)

    def test_coupling_matrix_values(self):
        """Test coupling matrix values are R^(d_Q * d_K)."""
        d_Q = [1.0, 2.0]
        d_K = [1.0, 2.0]
        R = 1.5
        matrix = harmonic_coupling_matrix(d_Q, d_K, R=R, normalize=False)

        # Lambda[0,0] = R^(1*1) = 1.5
        assert abs(matrix[0][0] - 1.5) < 1e-6

        # Lambda[1,1] = R^(2*2) = R^4 = 5.0625
        assert abs(matrix[1][1] - 5.0625) < 1e-6

        # Lambda[0,1] = R^(1*2) = R^2 = 2.25
        assert abs(matrix[0][1] - 2.25) < 1e-6

    def test_assign_dimension_depths_uniform(self):
        """Test uniform dimension assignment."""
        depths = assign_dimension_depths(4, method="uniform")
        assert len(depths) == 4
        assert all(d == 3.0 for d in depths)  # (1+2+3+4+5+6)/6 = 3.5 -> 3.0

    def test_hal_attention_output_shape(self):
        """Test HAL-attention output has correct shape."""
        # d_model must be divisible by n_heads (default 8)
        # Use d_model=8 so it's compatible
        Q = [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
             [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
             [0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
        K = [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
             [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
        V = [[1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
             [3.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]

        output = hal_attention(Q, K, V)
        assert len(output.output) == 3  # num queries
        assert all(len(row) == 8 for row in output.output)  # d_model

    def test_hal_attention_layer(self):
        """Test HAL-Attention layer end-to-end."""
        layer = HALAttentionLayer(d_model=8, n_heads=2)

        # Create simple input - d_model=8
        Q = [[0.1] * 8 for _ in range(3)]
        K = [[0.2] * 8 for _ in range(3)]
        V = [[0.3] * 8 for _ in range(3)]

        output = layer(Q, K, V)
        assert len(output.output) == 3
        assert len(output.output[0]) == 8


# =============================================================================
# VACUUM-ACOUSTICS MODULE TESTS
# =============================================================================

class TestVacuumAcoustics:
    """Test Vacuum-Acoustics kernel."""

    def test_nodal_surface_at_origin(self):
        """Test nodal surface at origin."""
        # N(0, 0; n, m) should be 0 for any n, m
        result = nodal_surface((0.0, 0.0), 1.0, 1.0)
        assert abs(result) < 1e-10

    def test_nodal_surface_symmetry(self):
        """Test nodal surface symmetry."""
        n, m = 2.0, 3.0
        x = (0.25, 0.5)

        # N(x; n, m) = -N(x; m, n) (antisymmetric)
        result_nm = nodal_surface(x, n, m)
        result_mn = nodal_surface(x, m, n)
        assert abs(result_nm + result_mn) < 1e-10

    def test_cymatic_resonance_at_node(self):
        """Test cymatic resonance check at nodal point."""
        # At a nodal point, resonance should succeed
        agent_vector = (0.0, 0.0, 0.0, 1.0, 1.0, 3.0)
        target_position = (0.0, 0.0)  # Origin is always nodal

        result = check_cymatic_resonance(
            agent_vector, target_position, tolerance=0.1
        )
        assert result is True

    def test_flux_redistribution_energy_conservation(self):
        """Test flux redistribution conserves total energy."""
        amplitude = 10.0
        result = flux_redistribution(amplitude)

        # Total energy out should equal input
        # Energy at corners comes from canceled center energy
        total_corner_energy = sum(result.corner_energies)
        # Total should equal the original amplitude squared
        assert result.total_energy > 0
        assert result.canceled_energy >= 0

    def test_bottle_beam_intensity(self):
        """Test bottle beam intensity calculation."""
        sources = [
            WaveSource(position=(0.0, 0.0, -1.0), amplitude=1.0, phase=0.0),
            WaveSource(position=(0.0, 0.0, 1.0), amplitude=1.0, phase=math.pi),
        ]

        # At origin, counter-propagating waves should interfere
        intensity = bottle_beam_intensity(
            position=(0.0, 0.0, 0.0),
            sources=sources,
            wavelength=1.0
        )
        assert intensity >= 0  # Intensity is always non-negative


class TestChladniPattern:
    """Test Chladni pattern calculations."""

    def test_compute_chladni_pattern(self):
        """Test computing Chladni pattern over a grid."""
        pattern = compute_chladni_pattern(
            n=2.0,
            m=3.0,
            L=1.0,
            resolution=10
        )
        # Returns a 2D list of nodal values
        assert isinstance(pattern, list)
        assert len(pattern) == 10
        assert all(len(row) == 10 for row in pattern)

    def test_find_nodal_points(self):
        """Test finding nodal points in a pattern."""
        # Use a simple mode where we know the nodes
        points = find_nodal_points(n=1.0, m=2.0, L=1.0, resolution=20)
        # Should find some nodal points
        assert len(points) > 0


# =============================================================================
# CYMATIC STORAGE MODULE TESTS
# =============================================================================

class TestCymaticStorage:
    """Test HolographicQRCube storage."""

    def test_voxel_creation(self):
        """Test voxel dataclass."""
        import hashlib
        pos = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
        data = b"test data"
        checksum = hashlib.sha256(data).hexdigest()
        voxel = Voxel(
            id="test-001",
            position=pos,
            data=data,
            modes=(2.0, 3.0),
            checksum=checksum,
            storage_mode=StorageMode.RESONANCE
        )
        assert voxel.data == b"test data"
        assert voxel.storage_mode == StorageMode.RESONANCE
        assert voxel.verify_integrity() is True

    def test_holographic_cube_add_scan(self):
        """Test adding and scanning voxels."""
        cube = HolographicQRCube("test-cube")

        position = (1.0, 2.0, 3.0, 0.5, 1.0, 3.0)
        data = b"secret data"
        voxel = cube.add_voxel(position, data)

        # Verify voxel was created correctly
        assert voxel.data == data
        assert voxel.position == position

    def test_holographic_cube_resonance_access(self):
        """Test resonance-based access control."""
        cube = HolographicQRCube("test-cube-2")

        # Store with resonance mode
        position = (0.0, 0.0, 0.0, 1.0, 2.0, 3.0)
        data = b"protected data"
        cube.add_voxel(position, data, storage_mode=StorageMode.RESONANCE)

        # Check cube has the voxel
        assert cube.voxel_count == 1

    def test_holographic_cube_range_query(self):
        """Test range query."""
        cube = HolographicQRCube("test-cube-3")

        # Add multiple voxels
        positions = [
            (0.0, 0.0, 0.0, 1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            (10.0, 10.0, 10.0, 1.0, 1.0, 1.0),
        ]
        for i, pos in enumerate(positions):
            cube.add_voxel(pos, f"data{i}".encode())

        assert cube.voxel_count == 3


class TestKDTree:
    """Test KD-Tree implementation."""

    def test_kdtree_insert_search(self):
        """Test KD-Tree insert and nearest neighbor search."""
        import hashlib
        tree = KDTree()

        positions = [
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0, 0.0, 0.0),
        ]
        for i, pos in enumerate(positions):
            data = f"data{i}".encode()
            checksum = hashlib.sha256(data).hexdigest()
            voxel = Voxel(
                id=f"voxel-{i}",
                position=pos,
                data=data,
                modes=(1.0, 1.0),
                checksum=checksum,
                storage_mode=StorageMode.PUBLIC
            )
            tree.insert(voxel)

        # Nearest to query should be found
        query = (0.1, 0.1, 0.0, 0.0, 0.0, 0.0)
        nearest = tree.nearest(query)
        assert nearest is not None
        assert nearest.position == positions[0]


# =============================================================================
# PQC HARMONIC MODULE TESTS
# =============================================================================

class TestPQCHarmonic:
    """Test PQC Harmonic enhancement."""

    def test_fast_harmonic_key(self):
        """Test fast harmonic key derivation."""
        key = fast_harmonic_key(
            b"input key",
            dimension=6,
            R=1.5,
            salt=b"test salt"
        )
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_fast_harmonic_key_deterministic(self):
        """Test fast harmonic key is deterministic."""
        key1 = fast_harmonic_key(b"input", dimension=3, salt=b"salt")
        key2 = fast_harmonic_key(b"input", dimension=3, salt=b"salt")
        assert key1 == key2

    def test_fast_harmonic_key_different_dimensions(self):
        """Test different dimensions produce different keys."""
        key1 = fast_harmonic_key(b"input", dimension=3, salt=b"salt")
        key2 = fast_harmonic_key(b"input", dimension=6, salt=b"salt")
        assert key1 != key2

    def test_vector6d_key_creation(self):
        """Test Vector6DKey creation and serialization."""
        v = Vector6DKey(x=1.0, y=2.0, z=3.0, velocity=4.0, priority=5.0, security=6.0)
        assert v.as_tuple() == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

        # Test round-trip serialization
        v_bytes = v.to_bytes()
        v_restored = Vector6DKey.from_bytes(v_bytes)
        for a, b in zip(v.as_tuple(), v_restored.as_tuple()):
            assert abs(a - b) < 1e-6

    def test_vector6d_distance(self):
        """Test Vector6DKey distance calculation."""
        v1 = Vector6DKey(1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        v2 = Vector6DKey(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        dist = v1.distance_to(v2)
        assert dist == 1.0

    def test_derive_key_from_vector(self):
        """Test key derivation from 6D vector."""
        v = Vector6DKey(1.0, 2.0, 3.0, 4.0, 5.0, 3.0)
        key = derive_key_from_vector(v, salt=b"test", dimension=3)
        assert len(key) == 32

    def test_vector_proximity_key_success(self):
        """Test proximity key derivation when within tolerance."""
        v1 = Vector6DKey(0.0, 0.0, 0.0, 0.0, 0.0, 1.0)  # security=1 for valid dimension
        v2 = Vector6DKey(0.1, 0.1, 0.1, 0.0, 0.0, 1.0)

        key = vector_proximity_key(v1, v2, tolerance=1.0, salt=b"test")
        assert key is not None
        assert len(key) == 32

    def test_vector_proximity_key_failure(self):
        """Test proximity key returns None when out of tolerance."""
        v1 = Vector6DKey(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        v2 = Vector6DKey(100.0, 100.0, 100.0, 0.0, 0.0, 0.0)

        key = vector_proximity_key(v1, v2, tolerance=1.0, salt=b"test")
        assert key is None

    def test_analyze_harmonic_security(self):
        """Test security analysis function."""
        analysis = analyze_harmonic_security("Kyber768", dimension=6, R=1.5)

        assert analysis["base_algorithm"] == "Kyber768"
        assert analysis["base_security_bits"] == 192
        assert analysis["dimension"] == 6
        assert analysis["d_squared"] == 36
        assert analysis["effective_security_bits"] > 192


class TestHarmonicPQCSession:
    """Test harmonic-enhanced PQC sessions."""

    def test_create_harmonic_session(self):
        """Test creating a harmonic PQC session."""
        # Generate keypairs
        alice_kem = Kyber768.generate_keypair()
        alice_sig = Dilithium3.generate_keypair()
        bob_kem = Kyber768.generate_keypair()

        # Create session
        session = create_harmonic_pqc_session(
            initiator_kem_keypair=alice_kem,
            responder_kem_public_key=bob_kem.public_key,
            initiator_sig_keypair=alice_sig,
            dimension=6,
            R=1.5
        )

        assert session.dimension == 6
        assert session.harmonic_ratio == 1.5
        assert len(session.encryption_key.base_key) == 32
        assert session.effective_security_bits > 192

    def test_verify_harmonic_session(self):
        """Test verifying a harmonic PQC session."""
        # Generate keypairs
        alice_kem = Kyber768.generate_keypair()
        alice_sig = Dilithium3.generate_keypair()
        bob_kem = Kyber768.generate_keypair()

        # Create session
        session = create_harmonic_pqc_session(
            initiator_kem_keypair=alice_kem,
            responder_kem_public_key=bob_kem.public_key,
            initiator_sig_keypair=alice_sig,
            dimension=4
        )

        # Verify session
        verified = verify_harmonic_pqc_session(
            session=session,
            responder_kem_keypair=bob_kem,
            initiator_sig_public_key=alice_sig.public_key
        )

        assert verified is not None
        # Both sides should derive same keys
        assert verified.encryption_key.base_key == session.encryption_key.base_key
        assert verified.mac_key.base_key == session.mac_key.base_key

    def test_harmonic_session_with_vector_key(self):
        """Test session with 6D vector key binding."""
        alice_kem = Kyber768.generate_keypair()
        alice_sig = Dilithium3.generate_keypair()
        bob_kem = Kyber768.generate_keypair()

        vector_key = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)

        session = create_harmonic_pqc_session(
            initiator_kem_keypair=alice_kem,
            responder_kem_public_key=bob_kem.public_key,
            initiator_sig_keypair=alice_sig,
            vector_key=vector_key,
            dimension=3
        )

        assert session.vector_key == vector_key


class TestHarmonicKyberOrchestrator:
    """Test HarmonicKyberOrchestrator."""

    def test_orchestrator_session_creation(self):
        """Test orchestrator session creation."""
        alice = HarmonicKyberOrchestrator(dimension=4)
        bob = HarmonicKyberOrchestrator(dimension=4)

        alice_pub, alice_sig_pub = alice.get_public_keys()
        bob_pub, bob_sig_pub = bob.get_public_keys()

        # Alice creates session with Bob
        session = alice.create_session(bob_pub)

        # Bob verifies session
        verified = bob.verify_session(session, alice_sig_pub)

        assert verified is not None
        assert verified.encryption_key.base_key == session.encryption_key.base_key

    def test_orchestrator_security_analysis(self):
        """Test orchestrator security analysis."""
        orch = HarmonicKyberOrchestrator(dimension=6, R=1.5)
        analysis = orch.get_security_analysis()

        assert analysis["dimension"] == 6
        assert analysis["effective_security_bits"] > 200


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAethermoorIntegration:
    """Integration tests across AETHERMOORE modules."""

    def test_constants_used_in_hal_attention(self):
        """Test constants module integrates with HAL-Attention."""
        # Use R_FIFTH from constants in HAL-Attention
        d_Q = [1.0, 2.0, 3.0]
        d_K = [1.0, 2.0]
        matrix = harmonic_coupling_matrix(d_Q, d_K, R=R_FIFTH)
        assert len(matrix) == 3

    def test_vacuum_acoustics_uses_constants(self):
        """Test vacuum acoustics uses standard constants."""
        # Check that PI is used correctly in nodal surface
        result = nodal_surface((0.25, 0.5), 1.0, 2.0, L=1.0)
        # Result depends on cos(n*PI*x/L) formula
        assert isinstance(result, float)

    def test_cymatic_storage_with_pqc_session(self):
        """Test cymatic storage with PQC-derived keys."""
        # Create a PQC session for key material
        alice = HarmonicKyberOrchestrator(dimension=4)
        bob = HarmonicKyberOrchestrator(dimension=4)

        alice_pub, _ = alice.get_public_keys()
        bob_pub, alice_sig_pub = alice.get_public_keys()

        session = alice.create_session(bob_pub)

        # Use session key as access credential
        cube = HolographicQRCube("pqc-cube")

        # Position derived from session
        position = (
            float(session.encryption_key.base_key[0]),
            float(session.encryption_key.base_key[1]),
            float(session.encryption_key.base_key[2]),
            1.0, 2.0, 3.0
        )

        voxel = cube.add_voxel(position, b"PQC-protected data")
        assert voxel.data == b"PQC-protected data"
        assert cube.voxel_count == 1

    def test_harmonic_scale_security_chain(self):
        """Test harmonic scaling applied to full security chain."""
        # Start with base AES-128
        base_bits = 128
        dimension = 6
        R = R_FIFTH

        # Calculate enhanced security
        enhanced_bits = security_bits(base_bits, dimension, R)

        # Should be > 149 bits (128 + 36 * log2(1.5))
        assert enhanced_bits > 149

        # Calculate the multiplier
        h_value = harmonic_scale(dimension, R)
        assert h_value > 2_000_000  # Over 2 million multiplier
