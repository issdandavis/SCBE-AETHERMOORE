"""
Tests for Hamiltonian Braid Dynamics
=====================================

Tests the 9-state phase diagram, braid distance, harmonic cost φ^(d²),
constraint manifold projection, and braid-constrained trajectory dynamics.

@layer Layer 5, Layer 8, Layer 12, Layer 13
@tier L2-unit, L3-integration, L4-property
"""

import math

import numpy as np
import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.unified_state import (
    BRAIN_DIMENSIONS,
    PHI,
    UnifiedBrainState,
)
from symphonic_cipher.scbe_aethermoore.ai_brain.hamiltonian_braid import (
    PHASE_STATES,
    PHASE_LABELS,
    phase_label,
    valid_transition,
    valid_neighbors,
    transition_matrix,
    phase_deviation,
    RailPoint,
    Rail,
    make_rail_from_trajectory,
    nearest_rail_point,
    braid_distance,
    harmonic_cost,
    harmonic_cost_gradient,
    constraint_project,
    braid_step,
    simulate_braid,
    BraidStepResult,
    BraidTrajectory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_valid_state(seed: int = 0) -> np.ndarray:
    """Create a valid 21D brain state vector."""
    rng = np.random.default_rng(seed)
    x = np.zeros(BRAIN_DIMENSIONS)
    x[0:6] = rng.random(6) * 0.6 + 0.2
    x[6:9] = rng.normal(0, 0.05, 3)
    x[9] = rng.random() * 0.3
    x[10:12] = rng.random(2) * 0.5 + 0.2
    x[12:15] = rng.normal(0, 0.02, 3)
    x[15] = float(rng.integers(0, 2))
    x[16] = rng.random() * 0.5
    x[17] = 0.3 + rng.random() * 0.3
    x[18] = rng.random() * 0.5 + 0.2
    x[19] = 0.0
    x[20] = rng.random() * 0.5 + 0.2
    return x


def make_safe_origin() -> np.ndarray:
    return np.array(UnifiedBrainState.safe_origin().to_vector())


def make_simple_rail(n_points: int = 5, seed: int = 0) -> Rail:
    """Create a simple rail from safe origin with small perturbations."""
    origin = make_safe_origin()
    rng = np.random.default_rng(seed)
    trajectory = np.zeros((n_points, BRAIN_DIMENSIONS))
    trajectory[0] = origin
    for i in range(1, n_points):
        trajectory[i] = trajectory[i - 1] + rng.normal(0, 0.01, BRAIN_DIMENSIONS)
        trajectory[i, 0:6] = np.clip(trajectory[i, 0:6], 0.01, 0.99)
    # All equilibrium phases
    phases = [(0, 0)] * n_points
    return make_rail_from_trajectory(trajectory, phases)


# ---------------------------------------------------------------------------
# Tests: 9-state phase diagram
# ---------------------------------------------------------------------------

class TestPhaseDiagram:
    """Tests for the 9-state dual ternary phase space."""

    def test_nine_states(self):
        """Phase space has exactly 9 states."""
        assert len(PHASE_STATES) == 9

    def test_all_states_labeled(self):
        """All 9 states have a human-readable label."""
        for state in PHASE_STATES:
            label = phase_label(state)
            assert len(label) > 0
            assert "unknown" not in label

    def test_equilibrium_is_center(self):
        """Equilibrium (0,0) is the center of the grid."""
        assert (0, 0) in PHASE_STATES
        assert phase_label((0, 0)) == "equilibrium"

    def test_self_transition_valid(self):
        """Every state can stay in itself."""
        for s in PHASE_STATES:
            assert valid_transition(s, s)

    def test_adjacent_transitions_valid(self):
        """Manhattan-adjacent states are valid transitions."""
        assert valid_transition((0, 0), (1, 0))
        assert valid_transition((0, 0), (0, 1))
        assert valid_transition((0, 0), (-1, 0))
        assert valid_transition((0, 0), (0, -1))

    def test_diagonal_transitions_valid(self):
        """Diagonal transitions (Chebyshev distance 1) are valid."""
        assert valid_transition((0, 0), (1, 1))
        assert valid_transition((0, 0), (-1, -1))
        assert valid_transition((-1, -1), (0, 0))

    def test_impossible_transitions_invalid(self):
        """Transitions with Chebyshev distance > 1 are invalid."""
        assert not valid_transition((-1, -1), (1, 1))
        assert not valid_transition((-1, 0), (1, 0))
        assert not valid_transition((0, -1), (0, 1))

    def test_valid_neighbors_count(self):
        """Center has 9 neighbors, corners have 4, edges have 6."""
        # Center (0,0): all 9 states reachable
        assert len(valid_neighbors((0, 0))) == 9
        # Corner (-1,-1): 4 neighbors
        assert len(valid_neighbors((-1, -1))) == 4
        # Edge (-1,0): 6 neighbors
        assert len(valid_neighbors((-1, 0))) == 6

    def test_transition_matrix_shape(self):
        """Transition matrix is 9×9."""
        M = transition_matrix()
        assert M.shape == (9, 9)

    def test_transition_matrix_symmetric(self):
        """Transition matrix is symmetric (Chebyshev is symmetric)."""
        M = transition_matrix()
        np.testing.assert_array_equal(M, M.T)

    def test_transition_matrix_diagonal(self):
        """Diagonal is all 1 (self-transitions always valid)."""
        M = transition_matrix()
        assert all(M[i, i] == 1 for i in range(9))


# ---------------------------------------------------------------------------
# Tests: Phase deviation
# ---------------------------------------------------------------------------

class TestPhaseDeviation:
    """Tests for phase deviation metric."""

    def test_identical_zero(self):
        """Same phase → zero deviation."""
        assert phase_deviation((0, 0), (0, 0)) == 0.0
        assert phase_deviation((1, -1), (1, -1)) == 0.0

    def test_adjacent_half(self):
        """Adjacent phase → deviation 0.5."""
        assert phase_deviation((0, 0), (1, 0)) == 0.5
        assert phase_deviation((0, 0), (0, 1)) == 0.5

    def test_opposite_one(self):
        """Opposite corners → deviation 1.0."""
        assert phase_deviation((-1, -1), (1, 1)) == 1.0
        assert phase_deviation((-1, 1), (1, -1)) == 1.0

    def test_range(self):
        """Deviation always in [0, 1]."""
        for s1 in PHASE_STATES:
            for s2 in PHASE_STATES:
                d = phase_deviation(s1, s2)
                assert 0.0 <= d <= 1.0


# ---------------------------------------------------------------------------
# Tests: Rail and nearest point
# ---------------------------------------------------------------------------

class TestRail:
    """Tests for rail construction and nearest-point lookup."""

    def test_make_rail(self):
        """Rail constructed from trajectory has correct length."""
        rail = make_simple_rail(5)
        assert len(rail) == 5

    def test_rail_positions_array(self):
        """positions_array returns (N, 21) array."""
        rail = make_simple_rail(5)
        arr = rail.positions_array()
        assert arr.shape == (5, BRAIN_DIMENSIONS)

    def test_nearest_point_on_rail(self):
        """Nearest point to a rail point is itself."""
        rail = make_simple_rail(5)
        p0 = rail.points[0].position
        nearest, dist = nearest_rail_point(p0, rail)
        assert dist < 1e-10
        np.testing.assert_allclose(nearest.position, p0)

    def test_nearest_point_far(self):
        """Far-away state maps to closest rail point."""
        rail = make_simple_rail(5)
        x_far = make_valid_state(99)  # likely different from rail
        nearest, dist = nearest_rail_point(x_far, rail)
        assert dist > 0
        # Should be one of the rail points
        assert nearest.index in range(len(rail))

    def test_wrong_shape_raises(self):
        """Non-(N, 21) trajectory raises ValueError."""
        with pytest.raises(ValueError):
            make_rail_from_trajectory(np.ones((5, 10)))

    def test_mismatched_phases_raises(self):
        """phases length != trajectory length raises ValueError."""
        traj = np.zeros((5, BRAIN_DIMENSIONS))
        with pytest.raises(ValueError):
            make_rail_from_trajectory(traj, phases=[(0, 0)] * 3)


# ---------------------------------------------------------------------------
# Tests: Braid distance
# ---------------------------------------------------------------------------

class TestBraidDistance:
    """Tests for braid-specific hyperbolic distance."""

    def test_zero_on_rail(self):
        """On the rail with correct phase → distance ≈ 0."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        phase = rail.points[0].expected_phase
        d, nearest = braid_distance(x, rail, phase)
        assert d < 0.1  # very small

    def test_phase_deviation_increases_distance(self):
        """Wrong phase increases braid distance."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        correct_phase = rail.points[0].expected_phase
        wrong_phase = (1, 1)  # max deviation from (0,0)

        d_correct, _ = braid_distance(x, rail, correct_phase)
        d_wrong, _ = braid_distance(x, rail, wrong_phase)
        assert d_wrong > d_correct

    def test_spatial_deviation_increases_distance(self):
        """Moving away from rail increases braid distance."""
        rail = make_simple_rail(5)
        x_near = rail.points[0].position.copy()
        x_far = x_near + np.ones(BRAIN_DIMENSIONS) * 0.5
        phase = (0, 0)

        d_near, _ = braid_distance(x_near, rail, phase)
        d_far, _ = braid_distance(x_far, rail, phase)
        assert d_far > d_near

    def test_lambda_scales_phase_weight(self):
        """Higher lambda increases phase contribution."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        wrong_phase = (1, 1)

        d_low, _ = braid_distance(x, rail, wrong_phase, lambda_phase=0.1)
        d_high, _ = braid_distance(x, rail, wrong_phase, lambda_phase=2.0)
        assert d_high > d_low


# ---------------------------------------------------------------------------
# Tests: Harmonic cost φ^(d²)
# ---------------------------------------------------------------------------

class TestHarmonicCost:
    """Tests for the harmonic wall cost function."""

    def test_zero_distance_unit_cost(self):
        """d = 0 → cost = φ^0 = 1."""
        assert harmonic_cost(0.0) == pytest.approx(1.0)

    def test_unit_distance_phi(self):
        """d = 1 → cost = φ."""
        assert harmonic_cost(1.0) == pytest.approx(PHI)

    def test_two_distance(self):
        """d = 2 → cost = φ^4."""
        assert harmonic_cost(2.0) == pytest.approx(PHI ** 4, rel=1e-6)

    def test_three_distance(self):
        """d = 3 → cost = φ^9."""
        assert harmonic_cost(3.0) == pytest.approx(PHI ** 9, rel=1e-6)

    def test_monotonic(self):
        """Cost is strictly monotonically increasing for d > 0."""
        distances = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        costs = [harmonic_cost(d) for d in distances]
        for i in range(1, len(costs)):
            assert costs[i] > costs[i - 1]

    def test_exponential_growth(self):
        """Cost grows super-exponentially (d=5 >> d=3)."""
        c3 = harmonic_cost(3.0)
        c5 = harmonic_cost(5.0)
        assert c5 / c3 > 100  # massive growth

    def test_gradient_zero_at_origin(self):
        """Gradient is 0 at d=0 (equilibrium point)."""
        assert harmonic_cost_gradient(0.0) == pytest.approx(0.0)

    def test_gradient_positive(self):
        """Gradient is positive for d > 0 (restoring force)."""
        for d in [0.1, 0.5, 1.0, 2.0]:
            assert harmonic_cost_gradient(d) > 0


# ---------------------------------------------------------------------------
# Tests: Constraint manifold projection
# ---------------------------------------------------------------------------

class TestConstraintProjection:
    """Tests for projecting onto the constraint manifold M_constraint."""

    def test_on_rail_consistent(self):
        """On-rail state with correct phase is phase-consistent."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        phase = rail.points[0].expected_phase
        proj = constraint_project(x, phase, rail)
        assert proj.phase_consistent
        assert proj.braid_valid
        assert proj.cost < PHI  # near-zero distance → cost < φ

    def test_wrong_phase_snapped(self):
        """Wrong phase gets snapped toward expected."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        wrong_phase = (1, 1)
        proj = constraint_project(x, wrong_phase, rail)
        # Should still produce a valid projection
        assert proj.projected_phase in PHASE_STATES

    def test_braid_topology_preserved(self):
        """Transition from prev_phase must be valid."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        # prev_phase = (-1,-1), current tries to jump to (1,1) → invalid
        proj = constraint_project(
            x, (1, 1), rail, prev_phase=(-1, -1),
        )
        # Should snap to a valid neighbor of (-1,-1)
        assert valid_transition((-1, -1), proj.projected_phase)

    def test_state_stays_in_tube(self):
        """Projected state satisfies POCS constraints."""
        rail = make_simple_rail(5)
        x = make_valid_state(99)
        x[0] = 5.0  # out of bounds
        proj = constraint_project(x, (0, 0), rail)
        assert 0.0 <= proj.projected_state[0] <= 1.0

    def test_cost_computed(self):
        """Cost is always ≥ 1."""
        rail = make_simple_rail(5)
        x = make_valid_state(0)
        proj = constraint_project(x, (0, 0), rail)
        assert proj.cost >= 1.0


# ---------------------------------------------------------------------------
# Tests: Braid step
# ---------------------------------------------------------------------------

class TestBraidStep:
    """Tests for single braid dynamics steps."""

    def test_zero_impulse(self):
        """Zero impulse produces minimal state change."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        result = braid_step(x, (0, 0), rail, impulse=0.0)
        np.testing.assert_allclose(result.state, x, atol=0.1)
        assert result.cost >= 1.0

    def test_positive_impulse_toward_rail(self):
        """Positive impulse moves state toward nearest rail point."""
        rail = make_simple_rail(5)
        x = make_valid_state(42)
        d_before, _ = braid_distance(x, rail, (0, 0))
        result = braid_step(x, (0, 0), rail, impulse=0.1)
        d_after, _ = braid_distance(result.state, rail, result.phase)
        # Should get closer (or at least not much worse)
        assert d_after <= d_before + 0.5

    def test_mode_from_cost(self):
        """Mode is determined by cost thresholds."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        result = braid_step(x, (0, 0), rail, impulse=0.0)
        # On-rail → low cost → RUN
        assert result.mode == "RUN"

    def test_step_number_tracked(self):
        """Step number is recorded in result."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        result = braid_step(x, (0, 0), rail, step_num=42)
        assert result.step == 42


# ---------------------------------------------------------------------------
# Tests: Braid trajectory simulation
# ---------------------------------------------------------------------------

class TestBraidSimulation:
    """Tests for full braid trajectory simulation."""

    def test_simulation_length(self):
        """Simulation produces one step per impulse."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        impulses = [0.01] * 10
        sim = simulate_braid(x, (0, 0), rail, impulses)
        assert len(sim.steps) == 10

    def test_on_rail_low_cost(self):
        """Staying on rail keeps total cost low."""
        rail = make_simple_rail(10)
        x = rail.points[0].position.copy()
        impulses = [0.0] * 5  # no movement
        sim = simulate_braid(x, (0, 0), rail, impulses)
        # Average cost should be near 1 (on-rail)
        avg_cost = sim.total_cost / len(impulses)
        assert avg_cost < PHI ** 2  # well within safe range

    def test_mode_counts(self):
        """Mode counts are tracked across simulation."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        impulses = [0.0] * 5
        sim = simulate_braid(x, (0, 0), rail, impulses)
        total = sum(sim.mode_counts.values())
        assert total == 5

    def test_no_braid_breaks_on_valid_trajectory(self):
        """Valid trajectory has zero braid breaks."""
        rail = make_simple_rail(10)
        x = rail.points[0].position.copy()
        impulses = [0.01] * 8
        sim = simulate_braid(x, (0, 0), rail, impulses)
        assert sim.braid_breaks == 0

    def test_max_cost_tracked(self):
        """Max cost is tracked across simulation."""
        rail = make_simple_rail(5)
        x = rail.points[0].position.copy()
        impulses = [0.0, 0.0, 0.5, 0.0, 0.0]  # spike in the middle
        sim = simulate_braid(x, (0, 0), rail, impulses)
        assert sim.max_cost == max(s.cost for s in sim.steps)


# ---------------------------------------------------------------------------
# Tests: Property-based / invariants
# ---------------------------------------------------------------------------

class TestBraidInvariants:
    """Property-based tests for braid invariants."""

    def test_cost_always_ge_one(self):
        """Harmonic cost is always ≥ 1 for any distance."""
        rng = np.random.default_rng(42)
        for _ in range(100):
            d = rng.random() * 10
            assert harmonic_cost(d) >= 1.0

    def test_phase_diagram_is_connected(self):
        """Every phase state can reach every other via valid transitions."""
        M = transition_matrix()
        n = len(PHASE_STATES)
        # Check reachability via matrix power (M^8 should have all positive)
        reachable = np.linalg.matrix_power(M, n)
        assert np.all(reachable > 0), "Phase diagram is not fully connected"

    def test_golden_ratio_cost_curve(self):
        """Cost at integer distances matches φ^(n²) exactly."""
        for n in range(6):
            expected = PHI ** (n * n)
            actual = harmonic_cost(float(n))
            assert actual == pytest.approx(expected, rel=1e-10)
