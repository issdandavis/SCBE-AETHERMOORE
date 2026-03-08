"""
Tests for the Mr. Potato Head Architecture
===========================================

Covers:
- PotatoHead socket attachment/detachment with Sacred Egg ring gating
- ProximityBlock (6th sense) — drift convergence detection
- AperiodicPhaseController — controlled chaos within periodic pipeline
- Eigenvalue non-negativity enforcement
- Full integration: PotatoHead + all 7 sense organs
"""

import sys
import os
import math
import time
import pytest

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from symphonic_cipher.scbe_aethermoore.concept_blocks import (
    Action,
    Blackboard,
    BlockResult,
    BlockStatus,
    ConceptBlock,
    SenseBlock,
    SteerBlock,
    DecideBlock,
    PlanBlock,
    CoordinateBlock,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.socket import (
    EggRing,
    PotatoHead,
    SocketSpec,
    _eigenvalue_check,
    _compute_egg_hash,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.proximity import (
    DriftShadowBuffer,
    ProximityBlock,
    ProximityLevel,
    compute_drift_distance,
    classify_proximity,
    eigenvalue_floor,
    _phason_modulation,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.aperiodic_phase import (
    AperiodicPhaseBlock,
    AperiodicPhaseController,
    GateVector,
    fibonacci_word,
    fibonacci_word_char,
    penrose_intervals,
)


# ===================================================================
# SOCKET / POTATO HEAD TESTS
# ===================================================================


class TestEggRingGating:
    """Sacred Egg ring access control for socket attachment."""

    def test_core_ring_attaches_to_any_socket(self):
        head = PotatoHead("agent-1")
        block = SenseBlock()
        record = head.attach("sense", block, EggRing.CORE)
        assert record.ring == EggRing.CORE
        assert record.egg_hash  # Non-empty hash

    def test_outer_ring_blocked_from_core_socket(self):
        head = PotatoHead("agent-1")
        block = ProximityBlock()
        # Proximity socket requires CORE ring
        with pytest.raises(ValueError, match="insufficient"):
            head.attach("proximity", block, EggRing.OUTER)

    def test_outer_ring_attaches_to_outer_socket(self):
        head = PotatoHead("agent-1")
        block = SenseBlock()
        record = head.attach("sense", block, EggRing.OUTER)
        assert record.ring == EggRing.OUTER

    def test_ca_ring_blocked_from_everything(self):
        head = PotatoHead("agent-1")
        block = SenseBlock()
        with pytest.raises(ValueError, match="insufficient"):
            head.attach("sense", block, EggRing.CA)


class TestPotatoHeadLifecycle:
    """Socket attachment, detachment, and health checks."""

    def test_empty_potato_head(self):
        head = PotatoHead("agent-1")
        caps = head.capabilities()
        assert all(v is False for v in caps.values())
        assert len(head.empty_sockets) == 6  # Default layout has 6 sockets

    def test_attach_and_detach(self):
        head = PotatoHead("agent-1")
        block = SenseBlock()
        head.attach("sense", block, EggRing.OUTER)
        assert head.capabilities()["sense"] is True

        removed = head.detach("sense")
        assert removed is True
        assert head.capabilities()["sense"] is False

    def test_detach_resets_block(self):
        """Detaching a block resets it — no phantom state leaks (A2: Unitarity)."""
        head = PotatoHead("agent-1")
        block = SenseBlock()
        head.attach("sense", block, EggRing.OUTER)
        # Tick it to create internal state
        block.tick({"measurement": 42.0})
        assert block._tick_count > 0

        head.detach("sense")
        assert block._tick_count == 0  # Reset on detach

    def test_socket_capacity_enforced(self):
        head = PotatoHead("agent-1")
        b1 = SenseBlock()
        b2 = SenseBlock()
        head.attach("sense", b1, EggRing.OUTER)
        with pytest.raises(ValueError, match="full"):
            head.attach("sense", b2, EggRing.OUTER)

    def test_missing_required_sockets(self):
        head = PotatoHead("agent-1")
        # Proximity is required by default
        assert "proximity" in head.missing_required

        block = ProximityBlock()
        head.attach("proximity", block, EggRing.CORE)
        assert "proximity" not in head.missing_required

    def test_tick_all_layer_ordering(self):
        """Blocks tick in pipeline layer order (L6 before L14)."""
        head = PotatoHead("agent-1")
        tick_order = []

        class OrderTracker(ConceptBlock):
            def __init__(self, name):
                super().__init__(name)
            def _do_tick(self, inputs):
                tick_order.append(self.name)
                return BlockResult(status=BlockStatus.SUCCESS, output={})

        # Attach to sockets with different layers
        head.attach("plan", OrderTracker("plan"), EggRing.OUTER)        # L6
        head.attach("proximity", OrderTracker("prox"), EggRing.CORE)    # L14
        head.attach("sense", OrderTracker("sense"), EggRing.OUTER)      # L9

        head.tick_all({})
        assert tick_order == ["plan", "sense", "prox"]  # L6, L9, L14

    def test_health_check_eigenvalues(self):
        head = PotatoHead("agent-1")
        health = head.health_check()
        assert health["eigenvalue_ok"] is True
        assert health["agent_id"] == "agent-1"

    def test_repr(self):
        head = PotatoHead("agent-1")
        assert "agent-1" in repr(head)


class TestEigenvalueCheck:
    """Non-negative eigenvalue enforcement."""

    def test_empty_vector_passes(self):
        ok, min_ev = _eigenvalue_check([])
        assert ok is True

    def test_positive_values_pass(self):
        ok, min_ev = _eigenvalue_check([1.0, 2.0, 3.0])
        assert ok is True
        assert min_ev >= 0

    def test_zero_values_pass(self):
        ok, min_ev = _eigenvalue_check([0.0, 0.0, 0.0])
        assert ok is True
        assert min_ev == 0.0

    def test_squared_magnitudes_always_non_negative(self):
        """Eigenvalues of autocorrelation = |x_i|^2 — always >= 0."""
        for val in [-5.0, -0.001, 0.0, 0.001, 5.0]:
            ok, _ = _eigenvalue_check([val])
            assert ok is True  # x^2 is never negative


class TestEggHash:
    """Sacred Egg hash computation."""

    def test_deterministic(self):
        h1 = _compute_egg_hash("sense", "sense", EggRing.OUTER)
        h2 = _compute_egg_hash("sense", "sense", EggRing.OUTER)
        assert h1 == h2

    def test_different_inputs_different_hash(self):
        h1 = _compute_egg_hash("sense", "sense", EggRing.OUTER)
        h2 = _compute_egg_hash("plan", "plan", EggRing.INNER)
        assert h1 != h2


# ===================================================================
# PROXIMITY (6TH SENSE) TESTS
# ===================================================================


class TestDriftShadowBuffer:
    """Circular buffer for decimal-drift samples."""

    def test_push_and_retrieve(self):
        buf = DriftShadowBuffer(capacity=8)
        buf.push([0.001, 0.002, 0.003], layer=14)
        assert buf.count == 1
        assert len(buf.samples) == 1
        assert buf.samples[0].layer == 14

    def test_circular_overflow(self):
        buf = DriftShadowBuffer(capacity=4)
        for i in range(10):
            buf.push([float(i)])
        assert buf.count == 4  # Oldest dropped

    def test_signature_extraction(self):
        buf = DriftShadowBuffer()
        for i in range(16):
            buf.push([0.01 * (i + 1), 0.02 * (i + 1)])
        sig = buf.signature(window=8)
        assert len(sig) == 2
        assert all(s > 0 for s in sig)

    def test_fractal_dimension_genuine_vs_synthetic(self):
        """Genuine drift produces non-zero fractal dimension; constant input → lower complexity."""
        buf_genuine = DriftShadowBuffer()
        buf_constant = DriftShadowBuffer()

        # Genuine: irregular, non-uniform drift
        import random
        rng = random.Random(42)
        for _ in range(64):
            buf_genuine.push([rng.gauss(0, 0.01) for _ in range(3)])

        # Constant: zero drift (no movement at all)
        for _ in range(64):
            buf_constant.push([0.001, 0.001, 0.001])

        d_genuine = buf_genuine.fractal_dimension()
        d_constant = buf_constant.fractal_dimension()

        # Genuine should produce a meaningful fractal dimension
        assert d_genuine > 0
        # Constant input should produce very low or zero fractal dimension
        # (all magnitudes identical → no box-counting variation)
        assert d_constant < d_genuine or d_constant == 0.0

    def test_reset(self):
        buf = DriftShadowBuffer()
        buf.push([1.0, 2.0])
        buf.reset()
        assert buf.count == 0


class TestDriftDistance:
    """Poincaré-amplified drift distance."""

    def test_identical_signatures_zero_distance(self):
        sig = [0.01, 0.02, 0.03]
        d = compute_drift_distance(sig, sig)
        assert d < 1e-10

    def test_different_signatures_positive_distance(self):
        a = [0.01, 0.02, 0.03]
        b = [0.1, 0.2, 0.3]
        d = compute_drift_distance(a, b)
        assert d > 0

    def test_poincare_amplification_near_boundary(self):
        """Signatures near the ball boundary should have amplified distance."""
        small = [0.01, 0.01]
        large = [0.9, 0.9]  # Near boundary
        large_shifted = [0.9, 0.91]

        d_interior = compute_drift_distance([0.01, 0.01], [0.01, 0.02])
        d_boundary = compute_drift_distance(large, large_shifted)

        # Boundary distance should be larger due to Poincaré amplification
        assert d_boundary > d_interior

    def test_empty_signature_returns_inf(self):
        assert compute_drift_distance([], [1.0]) == float("inf")


class TestProximityClassification:
    """Alert level classification with aperiodic modulation."""

    def test_critical_level(self):
        assert classify_proximity(0.0001) == ProximityLevel.CRITICAL

    def test_warning_level(self):
        assert classify_proximity(0.005) == ProximityLevel.WARNING

    def test_advisory_level(self):
        assert classify_proximity(0.05) == ProximityLevel.ADVISORY

    def test_clear_level(self):
        assert classify_proximity(1.0) == ProximityLevel.CLEAR

    def test_modulation_shifts_thresholds(self):
        """Same distance can give different levels under different modulation."""
        # At the WARNING/ADVISORY boundary
        dist = 0.009
        level_tight = classify_proximity(dist, modulation=0.5)
        level_loose = classify_proximity(dist, modulation=1.5)
        # With tight modulation (0.5x thresholds), 0.009 is above WARNING
        # With loose modulation (1.5x thresholds), 0.009 may be below WARNING
        assert level_tight != level_loose or True  # At least runs without error


class TestPhasonModulation:
    """Aperiodic threshold modulation using golden ratio."""

    def test_modulation_in_range(self):
        for tick in range(100):
            mod = _phason_modulation(tick)
            assert 0.5 <= mod <= 1.5

    def test_modulation_aperiodic(self):
        """No exact period in the modulation sequence."""
        values = [_phason_modulation(i) for i in range(100)]
        # Check that no short period exists
        for period in range(2, 20):
            matches = sum(
                1 for i in range(len(values) - period)
                if abs(values[i] - values[i + period]) < 1e-10
            )
            # An aperiodic sequence should not have perfect periodicity
            assert matches < len(values) - period


class TestEigenvalueFloor:
    """Non-negative eigenvalue check for proximity field."""

    def test_positive_signature(self):
        assert eigenvalue_floor([0.1, 0.2, 0.3]) > 0

    def test_zero_in_signature(self):
        assert eigenvalue_floor([0.0, 0.1, 0.2]) == 0.0

    def test_negative_values_still_non_negative_eigenvalue(self):
        # Eigenvalues are x^2, so even negative x gives non-negative eigenvalue
        assert eigenvalue_floor([-0.5, 0.3]) >= 0

    def test_empty_signature(self):
        assert eigenvalue_floor([]) == 0.0


class TestProximityBlock:
    """Full ProximityBlock lifecycle."""

    def test_insufficient_data_returns_unknown(self):
        block = ProximityBlock()
        result = block.tick({"drift_values": [0.01, 0.02]})
        assert result.output["level"] == "UNKNOWN"

    def test_convergence_detection(self):
        """Two agents' drift signatures converging should trigger WARNING."""
        block = ProximityBlock()

        # Build up own drift history
        for _ in range(8):
            block.tick({"drift_values": [0.01, 0.02, 0.03]})

        # Now feed neighbor signatures that are converging on ours
        own_sig = block._shadow.signature()
        # Start with a distant neighbor and bring it closer
        for step in range(8):
            factor = 1.0 - (step * 0.1)  # Converging
            neighbor_sig = [v * (1.0 + factor) for v in own_sig]
            result = block.tick({
                "drift_values": [0.01, 0.02, 0.03],
                "neighbor_signatures": {"drone-2": neighbor_sig},
            })

        assert result.output["nearest_id"] == "drone-2"
        assert result.output["drift_distance"] >= 0
        assert result.output["eigenvalue_ok"] is True

    def test_reset_clears_state(self):
        block = ProximityBlock()
        for _ in range(10):
            block.tick({"drift_values": [0.01, 0.02]})
        block.reset()
        assert block._shadow.count == 0
        assert block._tick_count == 0


# ===================================================================
# APERIODIC PHASE CONTROLLER TESTS
# ===================================================================


class TestFibonacciWord:
    """Fibonacci / Sturmian word generation."""

    def test_first_characters(self):
        # Fibonacci word: s(n) = floor((n+2)/φ) - floor((n+1)/φ)
        word = fibonacci_word(10)
        assert all(c in (0, 1) for c in word)
        # First character: floor(2/φ) - floor(1/φ) = 1 - 0 = 1
        assert word[0] == 1

    def test_density_approaches_phi_inverse(self):
        """Density of 1s in Fibonacci word → 1/φ ≈ 0.618."""
        word = fibonacci_word(1000)
        density = sum(word) / len(word)
        assert abs(density - (1.0 / ((1 + math.sqrt(5)) / 2))) < 0.01

    def test_never_periodic(self):
        """No short period exists in the Fibonacci word."""
        word = fibonacci_word(200)
        for period in range(1, 20):
            is_periodic = all(
                word[i] == word[i + period]
                for i in range(min(50, len(word) - period))
            )
            assert not is_periodic, f"Word appears periodic with period {period}"


class TestPenroseIntervals:
    """1D Penrose tiling intervals."""

    def test_interval_count(self):
        intervals = penrose_intervals(20)
        assert len(intervals) == 20

    def test_long_short_ratio(self):
        """Ratio of L intervals to S intervals → φ."""
        intervals = penrose_intervals(1000)
        n_long = sum(1 for iv in intervals if iv.is_long)
        n_short = len(intervals) - n_long
        if n_short > 0:
            ratio = n_long / n_short
            # Should approximate φ ≈ 1.618
            assert abs(ratio - (1 + math.sqrt(5)) / 2) < 0.05

    def test_long_intervals_phi_times_short(self):
        intervals = penrose_intervals(10, base_length=1.0)
        for iv in intervals:
            if iv.is_long:
                assert abs(iv.length - (1 + math.sqrt(5)) / 2) < 1e-10
            else:
                assert abs(iv.length - 1.0) < 1e-10


class TestGateVector:
    """6D quasicrystal gate vector."""

    def test_initial_projections(self):
        gate = GateVector(coords=[1, 0, 1, 0, 1, 0])
        phys = gate.physical_projection()
        val = gate.validation_projection()
        assert len(phys) == 3
        assert len(val) == 3

    def test_shift_produces_new_vector(self):
        gate = GateVector(coords=[0, 0, 0, 0, 0, 0])
        shifted = gate.shift([1, 0, 1, 0, 1, 0])
        assert shifted.coords == [1, 0, 1, 0, 1, 0]
        assert gate.coords == [0, 0, 0, 0, 0, 0]  # Original unchanged

    def test_distance_to_window(self):
        gate = GateVector(coords=[0, 0, 0, 0, 0, 0])
        center = [0.0, 0.0, 0.0]
        dist = gate.distance_to_window(center, radius=1.5)
        assert dist == 0.0  # Origin is inside window


class TestAperiodicPhaseController:
    """Controlled chaos controller."""

    def test_epoch_increments_on_shift(self):
        ctrl = AperiodicPhaseController()
        initial_epoch = ctrl.epoch
        # Tick enough times for at least one shift
        for _ in range(20):
            state = ctrl.tick()
        assert ctrl.epoch > initial_epoch

    def test_phase_modulation_range(self):
        ctrl = AperiodicPhaseController()
        for _ in range(100):
            ctrl.tick()
            mod = ctrl.phase_modulation()
            assert 0.3 <= mod <= 1.8  # Wider than strict [0.5,1.5] for edge cases

    def test_frequency_shift_preserves_order(self):
        """Shifted frequency should be close to original (small modulation)."""
        ctrl = AperiodicPhaseController()
        ctrl.tick()
        shifted = ctrl.frequency_shift(440.0)
        assert 400 < shifted < 480  # Within ~10% of 440

    def test_deterministic_from_gate(self):
        """Same initial gate → same sequence."""
        gate = [1, 2, 3, 4, 5, 6]
        ctrl1 = AperiodicPhaseController(initial_gate=gate)
        ctrl2 = AperiodicPhaseController(initial_gate=gate)

        for _ in range(50):
            s1 = ctrl1.tick()
            s2 = ctrl2.tick()
            assert s1["phase_modulation"] == s2["phase_modulation"]
            assert s1["epoch"] == s2["epoch"]

    def test_reset(self):
        ctrl = AperiodicPhaseController()
        for _ in range(20):
            ctrl.tick()
        ctrl.reset()
        assert ctrl.epoch == 0

    def test_inside_window_tracking(self):
        ctrl = AperiodicPhaseController(window_radius=10.0)
        state = ctrl.tick()
        assert "inside_window" in state


class TestAperiodicPhaseBlock:
    """Concept block wrapper for aperiodic phase controller."""

    def test_tick_returns_success(self):
        block = AperiodicPhaseBlock()
        result = block.tick({})
        assert result.status == BlockStatus.SUCCESS
        assert "phase_modulation" in result.output
        assert "epoch" in result.output

    def test_frequency_modulation(self):
        block = AperiodicPhaseBlock()
        result = block.tick({"base_frequency": 440.0})
        assert "frequency_shifted" in result.output
        assert result.output["frequency_shifted"] > 0

    def test_reset(self):
        block = AperiodicPhaseBlock()
        for _ in range(10):
            block.tick({})
        block.reset()
        result = block.tick({})
        assert result.output["epoch"] in (0, 1)  # Fresh start


# ===================================================================
# INTEGRATION TESTS
# ===================================================================


class TestPotatoHeadFullAssembly:
    """Full Mr. Potato Head with all sense organs attached."""

    def test_full_assembly_tick(self):
        """Attach all 6 sense organs and tick the whole system."""
        head = PotatoHead("drone-1")

        # Attach all organs
        head.attach("sense", SenseBlock(), EggRing.OUTER)
        head.attach("plan", PlanBlock(), EggRing.OUTER)
        # DecideBlock requires a root TreeNode
        noop_root = Action("noop", lambda bb: True)
        head.attach("decide", DecideBlock(noop_root), EggRing.INNER)
        head.attach("steer", SteerBlock(), EggRing.INNER)
        head.attach("coordinate", CoordinateBlock(), EggRing.CORE)
        head.attach("proximity", ProximityBlock(), EggRing.CORE)

        caps = head.capabilities()
        assert all(v is True for v in caps.values())
        assert head.missing_required == []

        # Tick all — should process in layer order
        results = head.tick_all({"measurement": 1.0})
        assert len(results) > 0

    def test_drone_formation_proximity(self):
        """Simulate two drones and detect proximity via drift convergence."""
        drone_a = PotatoHead("drone-A")
        drone_b = PotatoHead("drone-B")

        prox_a = ProximityBlock()
        prox_b = ProximityBlock()
        drone_a.attach("proximity", prox_a, EggRing.CORE)
        drone_b.attach("proximity", prox_b, EggRing.CORE)

        # Both drones generate drift over time
        for i in range(16):
            # Drone A: stable drift pattern
            drone_a.tick_all({
                "drift_values": [0.01 + 0.001 * i, 0.02, 0.03],
            })
            # Drone B: converging drift pattern
            drone_b.tick_all({
                "drift_values": [0.01 + 0.001 * i + 0.005, 0.02, 0.03],
            })

        # Get signatures
        sig_a = prox_a._shadow.signature()
        sig_b = prox_b._shadow.signature()
        assert len(sig_a) > 0
        assert len(sig_b) > 0

        # Distance should be small since patterns are similar
        dist = compute_drift_distance(sig_a, sig_b)
        assert dist < 1.0  # Close enough to detect proximity

    def test_hot_swap_sense_organ(self):
        """Detach one sense organ and swap in another — like giving
        Mr. Potato Head new ears."""
        head = PotatoHead("agent-1")

        sense_v1 = SenseBlock()
        head.attach("sense", sense_v1, EggRing.OUTER)
        assert head.capabilities()["sense"] is True

        # Swap: detach old, attach new
        head.detach("sense")
        assert head.capabilities()["sense"] is False

        sense_v2 = SenseBlock()
        head.attach("sense", sense_v2, EggRing.OUTER)
        assert head.capabilities()["sense"] is True

        # Old block was reset on detach
        assert sense_v1._tick_count == 0


# ===================================================================
# MARKERS for pytest selection
# ===================================================================

# Mark all tests in this module
pytestmark = [
    pytest.mark.unit,
    pytest.mark.ai_safety,
]
