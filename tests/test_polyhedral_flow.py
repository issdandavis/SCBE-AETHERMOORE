"""
Tests for src/symphonic_cipher/scbe_aethermoore/axiom_grouped/polyhedral_flow.py
================================================================================

Covers:
- 16 PHDM polyhedra data integrity
- Fibonacci spin and LFSR bit generation
- Dual spin routing
- Polyhedral flow router
- Composite harmonic wall
- Polyhedral friction and training signal
"""

import sys
import math
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from symphonic_cipher.scbe_aethermoore.axiom_grouped.polyhedral_flow import (
    PHI,
    TONGUE_WEIGHTS,
    POLYHEDRA,
    FLOW_ADJACENCY,
    fibonacci_spin,
    fibonacci_phase,
    FibonacciLFSR,
    DualSpin,
    PolyhedralFlowRouter,
    PLATONIC_CONSTRAINT_ORDERS,
    composite_harmonic_wall,
    poincare_distance,
    evaluate_flow_confinement,
    polyhedral_natural_frequency,
    contact_friction,
    compute_friction_spectrum,
    friction_laplacian,
    geometric_training_signal,
    generate_hash_training_pair,
    generate_flow_training_pairs,
)

# ============================================================
# Polyhedra data integrity
# ============================================================


@pytest.mark.unit
class TestPolyhedraData:
    def test_exactly_16_polyhedra(self):
        assert len(POLYHEDRA) == 16

    def test_indices_sequential(self):
        for i, p in enumerate(POLYHEDRA):
            assert p.index == i

    def test_all_have_positive_faces(self):
        for p in POLYHEDRA:
            assert p.faces > 0

    def test_euler_characteristic_platonic(self):
        """Platonic solids have Euler characteristic 2 (V - E + F = 2)."""
        for p in POLYHEDRA:
            if p.family == "platonic":
                assert p.vertices - p.edges + p.faces == 2, f"{p.name}: V-E+F = {p.vertices - p.edges + p.faces} != 2"

    def test_toroidal_euler_zero(self):
        """Toroidal polyhedra have Euler characteristic 0."""
        for p in POLYHEDRA:
            if p.family == "toroidal":
                assert p.euler_chi == 0

    def test_dual_pairs_symmetric(self):
        """If A's dual is B, then B's dual should be A."""
        for p in POLYHEDRA:
            if p.dual_index is not None:
                dual = POLYHEDRA[p.dual_index]
                assert dual.dual_index is None or dual.dual_index == p.index

    def test_depths_in_valid_range(self):
        for p in POLYHEDRA:
            assert 0.0 <= p.depth <= 1.0

    def test_adjacency_covers_all_nodes(self):
        assert set(FLOW_ADJACENCY.keys()) == set(range(16))

    def test_adjacency_symmetric(self):
        """If i is adjacent to j, then j should be adjacent to i."""
        for i, neighbors in FLOW_ADJACENCY.items():
            for j in neighbors:
                assert i in FLOW_ADJACENCY[j], f"Asymmetric adjacency: {i} -> {j} but not {j} -> {i}"

    def test_no_self_loops(self):
        for i, neighbors in FLOW_ADJACENCY.items():
            assert i not in neighbors


# ============================================================
# Fibonacci spin
# ============================================================


@pytest.mark.unit
class TestFibonacciSpin:
    def test_returns_list_of_bits(self):
        bits = fibonacci_spin(0, 8)
        assert len(bits) == 8
        assert all(b in (0, 1) for b in bits)

    def test_deterministic(self):
        assert fibonacci_spin(5, 8) == fibonacci_spin(5, 8)

    def test_different_steps_differ(self):
        b0 = fibonacci_spin(0, 8)
        b1 = fibonacci_spin(1, 8)
        assert b0 != b1  # rotation should change pattern

    def test_custom_n_bits(self):
        bits = fibonacci_spin(0, 16)
        assert len(bits) == 16

    def test_step_wraps(self):
        """Step mod n_bits should produce same result."""
        assert fibonacci_spin(0, 8) == fibonacci_spin(8, 8)


@pytest.mark.unit
class TestFibonacciPhase:
    def test_returns_float(self):
        phase = fibonacci_phase(0)
        assert isinstance(phase, float)

    def test_within_2pi(self):
        for step in range(100):
            phase = fibonacci_phase(step)
            assert 0 <= phase < 2 * math.pi

    def test_golden_angle_spacing(self):
        golden_angle = 2 * math.pi / (PHI * PHI)
        p0 = fibonacci_phase(0)
        p1 = fibonacci_phase(1)
        assert abs((p1 - p0) % (2 * math.pi) - golden_angle) < 1e-10


# ============================================================
# Fibonacci LFSR
# ============================================================


@pytest.mark.unit
class TestFibonacciLFSR:
    def test_default_8bit(self):
        lfsr = FibonacciLFSR(n_bits=8, state=1)
        assert lfsr.n_bits == 8
        assert lfsr.state == 1

    def test_generates_bits(self):
        lfsr = FibonacciLFSR(n_bits=8, state=1)
        bits = lfsr.generate(16)
        assert len(bits) == 16
        assert all(b in (0, 1) for b in bits)

    def test_deterministic(self):
        lfsr1 = FibonacciLFSR(n_bits=8, state=42)
        lfsr2 = FibonacciLFSR(n_bits=8, state=42)
        assert lfsr1.generate(20) == lfsr2.generate(20)

    def test_never_reaches_zero(self):
        lfsr = FibonacciLFSR(n_bits=8, state=1)
        for _ in range(300):
            lfsr.step()
            assert lfsr.state != 0

    def test_current_bits_length(self):
        lfsr = FibonacciLFSR(n_bits=8, state=1)
        bits = lfsr.current_bits()
        assert len(bits) == 8

    def test_16bit_constructor(self):
        lfsr = FibonacciLFSR(n_bits=16, state=1)
        assert lfsr.taps == (15, 13, 8, 5)

    def test_32bit_constructor(self):
        lfsr = FibonacciLFSR(n_bits=32, state=1)
        assert lfsr.taps == (31, 21, 13, 8)


# ============================================================
# Dual spin
# ============================================================


@pytest.mark.unit
class TestDualSpin:
    def test_spin_returns_bits(self):
        ds = DualSpin()
        bits = ds.spin()
        assert len(bits) == 8
        assert all(b in (0, 1) for b in bits)

    def test_route_index_in_range(self):
        ds = DualSpin()
        for _ in range(50):
            idx = ds.route_index()
            assert 0 <= idx < 16

    def test_ternary_state_values(self):
        ds = DualSpin()
        ternary = ds.ternary_state()
        assert all(t in (-1, 0, 1) for t in ternary)

    def test_deterministic_with_seed(self):
        ds1 = DualSpin(seed=42)
        ds2 = DualSpin(seed=42)
        for _ in range(10):
            assert ds1.spin() == ds2.spin()

    def test_different_seeds_differ(self):
        ds1 = DualSpin(seed=1)
        ds2 = DualSpin(seed=99)
        # Not guaranteed per spin, but over 10 spins they should differ
        results1 = [ds1.route_index() for _ in range(10)]
        results2 = [ds2.route_index() for _ in range(10)]
        assert results1 != results2


# ============================================================
# Polyhedral flow router
# ============================================================


@pytest.mark.unit
class TestPolyhedralFlowRouter:
    def test_route_returns_path(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO")
        assert isinstance(path, list)
        assert len(path) > 0

    def test_route_starts_at_correct_polyhedron(self):
        router = PolyhedralFlowRouter()
        for tongue, expected_idx in router.TONGUE_START.items():
            path = router.route(tongue)
            assert path[0]["poly_index"] == expected_idx

    def test_route_length_bounded_by_max_hops(self):
        router = PolyhedralFlowRouter(max_hops=3)
        path = router.route("KO")
        assert len(path) <= 3

    def test_route_deterministic_with_seed(self):
        router1 = PolyhedralFlowRouter()
        router2 = PolyhedralFlowRouter()
        path1 = router1.route("CA", seed=42)
        path2 = router2.route("CA", seed=42)
        for h1, h2 in zip(path1, path2):
            assert h1["polyhedron"] == h2["polyhedron"]

    def test_route_has_required_keys(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO")
        required = {
            "hop",
            "polyhedron",
            "poly_index",
            "zone",
            "family",
            "depth",
            "phi_weight",
            "ternary_state",
            "fibonacci_phase",
            "faces",
            "euler_chi",
        }
        for hop in path:
            assert required.issubset(set(hop.keys()))

    def test_friction_penalty_adds_friction_data(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO", friction_penalty=True)
        # Hop 0 has no friction (no previous), but hop 1+ should
        if len(path) > 1:
            assert "friction" in path[1]
            assert "cumulative_friction" in path[1]

    def test_flow_address_format(self):
        router = PolyhedralFlowRouter()
        address = router.generate_flow_address("KO")
        assert address.startswith("KO:")
        assert "->" in address

    def test_all_tongues_route(self):
        router = PolyhedralFlowRouter()
        for tongue in TONGUE_WEIGHTS:
            path = router.route(tongue)
            assert len(path) > 0


# ============================================================
# Composite harmonic wall
# ============================================================


@pytest.mark.unit
class TestCompositeHarmonicWall:
    def test_legitimate_user_gets_allow(self):
        dists = {k: 0.01 for k in PLATONIC_CONSTRAINT_ORDERS}
        result = composite_harmonic_wall(dists, phase_deviation=0.0)
        assert result["tier"] == "ALLOW"
        assert result["h_composite"] > 0.75

    def test_adversary_gets_deny(self):
        dists = {k: 10.0 for k in PLATONIC_CONSTRAINT_ORDERS}
        result = composite_harmonic_wall(dists, phase_deviation=5.0)
        assert result["tier"] == "DENY"

    def test_mitm_immune_flag(self):
        dists = {"tetrahedron": 0.1}
        result = composite_harmonic_wall(dists)
        assert result["mitm_immune"] is True

    def test_h_composite_in_0_1(self):
        for d in [0.0, 0.5, 1.0, 5.0, 100.0]:
            dists = {"tetrahedron": d, "cube": d}
            result = composite_harmonic_wall(dists)
            assert 0 < result["h_composite"] <= 1.0

    def test_more_constraints_lower_trust(self):
        """Adding more polyhedral distances (even small) should lower H."""
        d1 = {"tetrahedron": 0.5}
        d5 = {k: 0.5 for k in PLATONIC_CONSTRAINT_ORDERS}
        r1 = composite_harmonic_wall(d1)
        r5 = composite_harmonic_wall(d5)
        assert r5["h_composite"] <= r1["h_composite"]

    def test_phase_deviation_lowers_trust(self):
        dists = {"tetrahedron": 0.1}
        r0 = composite_harmonic_wall(dists, phase_deviation=0.0)
        r1 = composite_harmonic_wall(dists, phase_deviation=1.0)
        assert r1["h_composite"] < r0["h_composite"]


# ============================================================
# Poincaré distance (scalar form)
# ============================================================


@pytest.mark.unit
class TestPoincaréDistanceScalar:
    def test_same_point_zero(self):
        d = poincare_distance(0.1, 0.1, 0.0)
        assert d == 0.0

    def test_boundary_gives_inf(self):
        d = poincare_distance(1.0, 0.0, 1.0)
        assert d == float("inf")

    def test_positive_distance(self):
        d = poincare_distance(0.1, 0.2, 0.05)
        assert d > 0


# ============================================================
# Flow confinement evaluation
# ============================================================


@pytest.mark.integration
class TestFlowConfinement:
    def test_evaluate_returns_dict(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO")
        result = evaluate_flow_confinement(path, "KO")
        assert "h_composite" in result
        assert "tier" in result
        assert "path_length" in result

    def test_legitimate_path_is_allowed(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO")
        result = evaluate_flow_confinement(path, "KO")
        assert result["tier"] == "ALLOW"


# ============================================================
# Polyhedral friction
# ============================================================


@pytest.mark.unit
class TestPolyhedralFriction:
    def test_natural_frequency_positive(self):
        for p in POLYHEDRA:
            freq = polyhedral_natural_frequency(p)
            assert freq > 0, f"{p.name} has non-positive frequency"

    def test_different_polyhedra_different_frequencies(self):
        freqs = [polyhedral_natural_frequency(p) for p in POLYHEDRA]
        # Not all should be the same
        assert len(set(round(f, 8) for f in freqs)) > 1

    def test_contact_friction_returns_dict(self):
        result = contact_friction(POLYHEDRA[0], POLYHEDRA[1])
        assert "beat_frequency" in result
        assert "torsional_moment" in result
        assert "friction_magnitude" in result

    def test_friction_magnitude_positive(self):
        for i in range(len(POLYHEDRA) - 1):
            f = contact_friction(POLYHEDRA[i], POLYHEDRA[i + 1])
            assert f["friction_magnitude"] >= 0

    def test_friction_symmetric(self):
        f_ab = contact_friction(POLYHEDRA[0], POLYHEDRA[1])
        f_ba = contact_friction(POLYHEDRA[1], POLYHEDRA[0])
        assert abs(f_ab["friction_magnitude"] - f_ba["friction_magnitude"]) < 1e-10


@pytest.mark.integration
class TestFrictionSpectrum:
    def test_spectrum_not_empty(self):
        spectrum = compute_friction_spectrum()
        assert len(spectrum) > 0

    def test_spectrum_sorted_descending(self):
        spectrum = compute_friction_spectrum()
        for i in range(len(spectrum) - 1):
            assert spectrum[i]["friction_magnitude"] >= spectrum[i + 1]["friction_magnitude"]


@pytest.mark.integration
class TestFrictionLaplacian:
    def test_laplacian_returns_dict(self):
        lap = friction_laplacian()
        assert "n_nodes" in lap
        assert "trace" in lap
        assert "laplacian_matrix" in lap

    def test_laplacian_16_nodes(self):
        lap = friction_laplacian()
        assert lap["n_nodes"] == 16

    def test_laplacian_trace_positive(self):
        lap = friction_laplacian()
        assert lap["trace"] > 0


# ============================================================
# Geometric training signal
# ============================================================


@pytest.mark.unit
class TestGeometricTrainingSignal:
    def test_returns_dict(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO")
        signal = geometric_training_signal(path, "KO")
        assert "friction_sequence" in signal
        assert "training_energy" in signal
        assert "tongue" in signal

    def test_training_energy_nonnegative(self):
        router = PolyhedralFlowRouter()
        for tongue in TONGUE_WEIGHTS:
            path = router.route(tongue)
            signal = geometric_training_signal(path, tongue)
            assert signal["training_energy"] >= 0

    def test_tongue_weight_scales_signal(self):
        router = PolyhedralFlowRouter()
        path = router.route("KO", seed=1)
        sig_ko = geometric_training_signal(path, "KO")
        sig_dr = geometric_training_signal(path, "DR")
        # DR has higher tongue weight, so training energy should be higher
        if sig_ko["total_friction"] > 0:
            assert sig_dr["training_energy"] > sig_ko["training_energy"]


# ============================================================
# Training pair generation
# ============================================================


@pytest.mark.integration
class TestTrainingPairGeneration:
    def test_hash_training_pair(self):
        pair = generate_hash_training_pair("KO", seed=0)
        assert "instruction" in pair
        assert "output" in pair
        assert "h_composite" in pair
        assert "tier" in pair

    def test_adversarial_pair(self):
        pair = generate_hash_training_pair("CA", seed=1, adversarial=True)
        assert pair["adversarial"] is True

    def test_flow_training_pairs(self):
        pairs = generate_flow_training_pairs(n_pairs=12)
        assert len(pairs) == 12
        for pair in pairs:
            assert "instruction" in pair
            assert "flow_address" in pair
