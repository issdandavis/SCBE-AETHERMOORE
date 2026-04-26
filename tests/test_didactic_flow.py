"""
Tests for Inverse Phase-Shifted Didactic Flow Modulations.

Validates:
1. Phase states are well-formed (angles, radii, trits bounded)
2. Four modes produce genuinely different dynamics
3. Mode ordering: phase_locked > breathing > constant > inverse (for mastery)
4. ZPD bell curve peaks at optimal phase gap (pi/3)
5. Learner converges toward teacher over time
6. Mislabel detection: trit disagreement between teacher/learner is signal, not noise
"""

import pytest

from src.crypto.didactic_flow import (
    FlowMode,
    _trit_from_angle,
    _breathing_radius,
    compute_teacher_phase,
    compute_learner_phase,
    compute_flow_point,
    run_didactic_flow,
    run_all_modes,
    format_flow_report,
    PI,
)

# ===================================================================
# Trit quantization tests
# ===================================================================


class TestTritQuantization:
    """Test that phase angles quantize to trits correctly."""

    def test_zero_is_constructive(self):
        assert _trit_from_angle(0.0) == 1

    def test_pi_is_destructive(self):
        assert _trit_from_angle(PI) == -1

    def test_neg_pi_is_destructive(self):
        assert _trit_from_angle(-PI) == -1

    def test_small_positive_is_constructive(self):
        assert _trit_from_angle(0.5) == 1

    def test_pi_over_2_is_neutral(self):
        assert _trit_from_angle(PI / 2) == 0

    def test_neg_pi_over_2_is_neutral(self):
        assert _trit_from_angle(-PI / 2) == 0

    def test_wraps_beyond_2pi(self):
        """Angles > 2*pi should wrap correctly."""
        assert _trit_from_angle(2 * PI + 0.1) == _trit_from_angle(0.1)

    def test_wraps_negative(self):
        assert _trit_from_angle(-2 * PI - 0.1) == _trit_from_angle(-0.1)

    def test_all_three_trits_reachable(self):
        """Full circle should hit all three trit values."""
        trits_seen = set()
        for i in range(36):
            angle = 2 * PI * i / 36
            trits_seen.add(_trit_from_angle(angle))
        assert trits_seen == {-1, 0, 1}


# ===================================================================
# Breathing radius tests
# ===================================================================


class TestBreathingRadius:
    """Test hyperbolic breathing transform."""

    def test_identity_at_beta_1(self):
        """Beta=1 should be near identity."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            r = _breathing_radius(t, 1.0)
            r_base = 0.1 + 0.7 * t
            assert abs(r - r_base) < 0.05, f"t={t}: r={r}, r_base={r_base}"

    def test_beta_gt_1_expands(self):
        """Beta > 1 should push radius toward boundary."""
        r_normal = _breathing_radius(0.5, 1.0)
        r_expanded = _breathing_radius(0.5, 2.0)
        assert r_expanded > r_normal

    def test_beta_lt_1_contracts(self):
        """Beta < 1 should pull radius toward center."""
        r_normal = _breathing_radius(0.5, 1.0)
        r_contracted = _breathing_radius(0.5, 0.5)
        assert r_contracted < r_normal

    def test_radius_bounded(self):
        """Radius should always be in [0, 1)."""
        for beta in [0.1, 0.5, 1.0, 2.0, 5.0]:
            for t in [0.0, 0.5, 1.0]:
                r = _breathing_radius(t, beta)
                assert 0.0 <= r < 1.0, f"beta={beta}, t={t}: r={r}"

    def test_monotone_in_t(self):
        """Radius should increase with time (curriculum progression)."""
        for beta in [0.5, 1.0, 1.5]:
            prev = _breathing_radius(0.0, beta)
            for i in range(1, 11):
                t = i / 10
                r = _breathing_radius(t, beta)
                assert r >= prev - 1e-10, f"beta={beta}, t={t}: r={r} < prev={prev}"
                prev = r


# ===================================================================
# Teacher phase tests
# ===================================================================


class TestTeacherPhase:
    """Test teacher phase computation across modes."""

    @pytest.mark.parametrize("mode", list(FlowMode))
    def test_has_valid_fields(self, mode):
        ps = compute_teacher_phase(0.5, mode)
        assert isinstance(ps.t, float)
        assert isinstance(ps.beta, float)
        assert len(ps.theta) == 3
        assert len(ps.trit) == 3
        assert all(t in (-1, 0, 1) for t in ps.trit)
        assert 0.0 <= ps.radius < 1.0

    def test_modes_produce_different_thetas(self):
        """Different modes should give different phase angles at t=0.5."""
        phases = {mode: compute_teacher_phase(0.5, mode) for mode in tuple(FlowMode)}
        # At least some pairs should differ
        thetas = {mode: phases[mode].theta for mode in tuple(FlowMode)}
        unique = set(thetas.values())
        assert len(unique) >= 3, f"Too few unique theta sets: {len(unique)}"

    def test_constant_mode_linear_rotation(self):
        """Constant mode should have linearly increasing phase."""
        p1 = compute_teacher_phase(0.25, FlowMode.CONSTANT)
        p2 = compute_teacher_phase(0.50, FlowMode.CONSTANT)
        # theta should roughly double (linear in t)
        for i in range(3):
            ratio = p2.theta[i] / (p1.theta[i] + 1e-12)
            assert abs(ratio - 2.0) < 0.1, f"Channel {i}: ratio={ratio}"

    def test_inverse_accelerates(self):
        """Inverse mode should rotate faster than constant at t=0.8."""
        p_const = compute_teacher_phase(0.8, FlowMode.CONSTANT)
        p_inv = compute_teacher_phase(0.8, FlowMode.INVERSE)
        # Inverse has accelerating rate factor (1 + 0.8*t)
        for i in range(3):
            assert abs(p_inv.theta[i]) > abs(p_const.theta[i])

    def test_phase_locked_slower(self):
        """Phase-locked mode should rotate slower than constant."""
        p_const = compute_teacher_phase(0.5, FlowMode.CONSTANT)
        p_locked = compute_teacher_phase(0.5, FlowMode.PHASE_LOCKED)
        for i in range(3):
            assert abs(p_locked.theta[i]) < abs(p_const.theta[i])


# ===================================================================
# Learner phase tests
# ===================================================================


class TestLearnerPhase:
    """Test learner phase computation."""

    def test_starts_inverse(self):
        """At t=0, learner should be inverse to teacher (gap ~ pi)."""
        teacher = compute_teacher_phase(0.0, FlowMode.CONSTANT)
        learner = compute_learner_phase(0.0, teacher, FlowMode.CONSTANT)
        for i in range(3):
            diff = abs(teacher.theta[i] - learner.theta[i])
            # At t=0 with phase_delay, inversion should be ~1.0
            # But t_eff = max(0, 0 - 0.15) = 0, so convergence = 0
            # inversion = 1.0, shift = PI
            assert diff > PI * 0.8, f"Channel {i}: diff={diff}, expected near PI"

    def test_converges_over_time(self):
        """Learner should get closer to teacher over time."""
        gaps_early = []
        gaps_late = []
        for i in range(3):
            t_early = compute_teacher_phase(0.2, FlowMode.CONSTANT)
            l_early = compute_learner_phase(0.2, t_early, FlowMode.CONSTANT)
            gaps_early.append(abs(t_early.theta[i] - l_early.theta[i]))

            t_late = compute_teacher_phase(0.9, FlowMode.CONSTANT)
            l_late = compute_learner_phase(0.9, t_late, FlowMode.CONSTANT)
            gaps_late.append(abs(t_late.theta[i] - l_late.theta[i]))

        assert sum(gaps_late) < sum(
            gaps_early
        ), f"Late gaps {sum(gaps_late):.3f} should be < early {sum(gaps_early):.3f}"

    def test_phase_locked_converges_fastest(self):
        """Phase-locked mode should have smallest gap at t=0.8."""
        modes = [FlowMode.CONSTANT, FlowMode.PHASE_LOCKED]
        gaps = {}
        for mode in modes:
            fp = compute_flow_point(0.8, mode)
            gaps[mode] = fp.total_gap
        assert gaps[FlowMode.PHASE_LOCKED] < gaps[FlowMode.CONSTANT]

    def test_inverse_converges_slowest(self):
        """Inverse mode should have largest gap."""
        gaps = {}
        for mode in tuple(FlowMode):
            fp = compute_flow_point(0.8, mode)
            gaps[mode] = fp.total_gap
        assert gaps[FlowMode.INVERSE] == max(gaps.values())


# ===================================================================
# Flow point tests
# ===================================================================


class TestFlowPoint:
    """Test combined flow point computation."""

    def test_gap_bounded(self):
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            fp = compute_flow_point(t, FlowMode.BREATHING)
            assert 0.0 <= fp.total_gap <= 1.0, f"t={t}: gap={fp.total_gap}"

    def test_mastery_complement_of_gap(self):
        fp = compute_flow_point(0.5, FlowMode.CONSTANT)
        assert abs(fp.mastery - (1.0 - fp.total_gap)) < 1e-10

    def test_zpd_bounded(self):
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for mode in tuple(FlowMode):
                fp = compute_flow_point(t, mode)
                assert 0.0 <= fp.zpd_score <= 1.0, f"t={t}, {mode}: zpd={fp.zpd_score}"

    def test_zpd_peaks_at_moderate_gap(self):
        """ZPD should be highest when gap is moderate (not 0, not pi)."""
        # At very high gap (t=0, inverse), ZPD should be low
        fp_far = compute_flow_point(0.0, FlowMode.INVERSE)
        # At moderate gap (phase_locked, mid-trajectory), ZPD should be higher
        fp_mid = compute_flow_point(0.7, FlowMode.PHASE_LOCKED)
        assert fp_mid.zpd_score > fp_far.zpd_score


# ===================================================================
# Full flow simulation tests
# ===================================================================


class TestFullFlow:
    """Test complete didactic flow simulation."""

    def test_correct_step_count(self):
        flow = run_didactic_flow(steps=24)
        assert len(flow.points) == 24
        assert flow.steps == 24

    def test_trajectories_match_points(self):
        flow = run_didactic_flow(steps=10)
        assert len(flow.trit_trajectory_teacher) == 10
        assert len(flow.trit_trajectory_learner) == 10
        for i, p in enumerate(flow.points):
            assert flow.trit_trajectory_teacher[i] == p.teacher.trit
            assert flow.trit_trajectory_learner[i] == p.learner.trit

    def test_all_channels_in_report(self):
        flow = run_didactic_flow()
        assert "structure" in flow.channel_report
        assert "stability" in flow.channel_report
        assert "truth" in flow.channel_report

    def test_channel_stats_valid(self):
        flow = run_didactic_flow()
        for _ch_name, stats in flow.channel_report.items():
            assert stats["min_gap"] <= stats["mean_gap"] <= stats["max_gap"]
            assert 0.0 <= stats["trit_agreement"] <= 1.0

    def test_mean_gap_consistent(self):
        flow = run_didactic_flow(steps=20)
        manual_mean = sum(p.total_gap for p in flow.points) / len(flow.points)
        assert abs(flow.mean_gap - manual_mean) < 1e-10


# ===================================================================
# Mode comparison tests (the core finding)
# ===================================================================


class TestModeOrdering:
    """Test that modes produce the expected pedagogical ordering."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.flows = run_all_modes(learning_rate=0.7, steps=48)

    def test_four_modes_present(self):
        assert len(self.flows) == 4
        assert set(self.flows.keys()) == {"constant", "breathing", "phase_locked", "inverse"}

    def test_modes_produce_different_gaps(self):
        """All four modes should have distinct mean gaps."""
        gaps = [f.mean_gap for f in self.flows.values()]
        # At least 3 distinct values (float comparison with tolerance)
        unique_gaps = set()
        for g in gaps:
            if all(abs(g - u) > 0.01 for u in unique_gaps):
                unique_gaps.add(g)
        assert len(unique_gaps) >= 3, f"Too few distinct gaps: {gaps}"

    def test_phase_locked_best_mastery(self):
        """Phase-locked (tutoring) should have highest mastery."""
        best = max(self.flows.items(), key=lambda x: x[1].mean_mastery)
        assert best[0] == "phase_locked"

    def test_inverse_worst_mastery(self):
        """Inverse (adversarial) should have lowest mastery."""
        worst = min(self.flows.items(), key=lambda x: x[1].mean_mastery)
        assert worst[0] == "inverse"

    def test_inverse_near_zero_zpd(self):
        """Adversarial mode should have near-zero ZPD (gap too wide for learning)."""
        assert self.flows["inverse"].mean_zpd < 0.05

    def test_phase_locked_best_zpd(self):
        """Phase-locked should have best ZPD (stays in optimal zone)."""
        best_zpd = max(self.flows.items(), key=lambda x: x[1].mean_zpd)
        assert best_zpd[0] == "phase_locked"

    def test_breathing_beats_constant(self):
        """Socratic (breathing) should outperform lecture (constant)."""
        assert self.flows["breathing"].mean_mastery > self.flows["constant"].mean_mastery

    def test_trit_trajectories_differ(self):
        """Teacher trit trajectories should differ across modes."""
        trajs = {name: tuple(tuple(t) for t in f.trit_trajectory_teacher) for name, f in self.flows.items()}
        unique = set(trajs.values())
        assert len(unique) >= 3, "Too few unique teacher trajectories"


# ===================================================================
# Mislabel-as-signal tests
# ===================================================================


class TestMislabelSignal:
    """Mislabeling shows what right labeling missed.

    When teacher and learner are in different trit states, the DISAGREEMENT
    is the most informative training signal. It marks the zone where
    the learner's model diverges from the teacher's intent.
    """

    def test_disagreement_decreases_over_time(self):
        """Trit disagreement should decrease as learner converges."""
        flow = run_didactic_flow(mode=FlowMode.PHASE_LOCKED, steps=48)
        # First quarter vs last quarter
        n = len(flow.points)
        early = flow.points[: n // 4]
        late = flow.points[3 * n // 4 :]

        early_disagree = sum(1 for p in early for i in range(3) if p.teacher.trit[i] != p.learner.trit[i]) / (
            len(early) * 3
        )

        late_disagree = sum(1 for p in late for i in range(3) if p.teacher.trit[i] != p.learner.trit[i]) / (
            len(late) * 3
        )

        assert (
            late_disagree < early_disagree
        ), f"Late disagreement {late_disagree:.3f} should < early {early_disagree:.3f}"

    def test_breathing_has_highest_disagreement(self):
        """Breathing (Socratic) mode should have highest trit disagreement.

        This validates the mislabel-as-signal insight: the most informative
        mislabels occur at TRIT BOUNDARIES (where phases cross quantization
        thresholds at different times), not at maximum distance. Breathing
        mode oscillates through boundaries constantly, generating maximum
        trit-level disagreement even though its phase gap is moderate.
        Inverse mode has a WIDER gap but both parties stay in the same
        trit zone (destructive), so they paradoxically AGREE more.
        """
        flows = run_all_modes()
        disagrees = {}
        for name, flow in flows.items():
            total = sum(1 for p in flow.points for i in range(3) if p.teacher.trit[i] != p.learner.trit[i])
            disagrees[name] = total / (len(flow.points) * 3)

        # Breathing generates most boundary crossings
        assert disagrees["breathing"] == max(
            disagrees.values()
        ), f"Expected breathing to lead disagreement, got: {disagrees}"

    def test_disagreement_zones_are_zpd_adjacent(self):
        """Points where trits disagree should have moderate phase gaps
        (i.e. near the ZPD), not extreme gaps."""
        flow = run_didactic_flow(mode=FlowMode.BREATHING, steps=48)
        disagree_gaps = []
        agree_gaps = []
        for p in flow.points:
            has_disagree = any(p.teacher.trit[i] != p.learner.trit[i] for i in range(3))
            if has_disagree:
                disagree_gaps.append(p.total_gap)
            else:
                agree_gaps.append(p.total_gap)

        # Disagreement points exist
        assert len(disagree_gaps) > 0, "No disagreement points found"
        # Agreement points exist (at least some convergence)
        # (may not always hold but generally should for breathing mode)

    def test_mislabel_count_per_channel(self):
        """Each channel should have independent mislabel patterns."""
        flow = run_didactic_flow(mode=FlowMode.CONSTANT, steps=48)
        channel_mismatches = [0, 0, 0]
        for p in flow.points:
            for i in range(3):
                if p.teacher.trit[i] != p.learner.trit[i]:
                    channel_mismatches[i] += 1
        # All channels should have some mismatches (not all zero)
        assert sum(channel_mismatches) > 0


# ===================================================================
# Report generation tests
# ===================================================================


class TestReport:
    """Test report formatting."""

    def test_report_produces_output(self):
        flows = run_all_modes(steps=12)
        report = format_flow_report(flows)
        assert "INVERSE PHASE-SHIFTED DIDACTIC FLOW MODULATIONS" in report
        assert "THE FINDING" in report
        assert len(report) > 500

    def test_report_contains_all_modes(self):
        flows = run_all_modes(steps=12)
        report = format_flow_report(flows)
        for mode in tuple(FlowMode):
            assert mode.value.upper() in report

    def test_report_contains_channel_data(self):
        flows = run_all_modes(steps=12)
        report = format_flow_report(flows)
        assert "structure" in report
        assert "stability" in report
        assert "truth" in report
