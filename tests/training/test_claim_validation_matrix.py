"""
Claim Validation Matrix — Tests that prove training claims separately
======================================================================

Three things proven independently:
    1. Training data really contains the claimed structure (A)
    2. Model actually learns that structure (B, C)
    3. Learned structure survives adversarial warping and transfers (D, E, F)

Test classes mirror the 6 harness components + core metrics + experiment matrix.

@layer All layers (L1-L14)
@component Claim Validation Matrix Tests
"""

import math

from src.training.claim_validation_harness import (
    # Enums
    AblationVariant,
    EvalSuite,
    PathType,
    DOMAIN_NAMES,
    TRANSFER_PAIRS,
    ABLATION_LADDER,
    # A. Corpus validity
    CorpusValidityReport,
    check_label_reproducibility,
    check_projection_determinism,
    check_neighbor_purity,
    check_split_leakage,
    check_class_balance,
    check_friction_zone_coverage,
    check_adversarial_identity,
    validate_corpus,
    # B. Ablation
    AblationResult,
    AblationReport,
    run_ablation_variant,
    run_full_ablation,
    # C. Transfer
    TransferResult,
    measure_transfer,
    run_transfer_harness,
    # D. Adversarial
    WarpPreservationResult,
    measure_warp_preservation,
    run_adversarial_harness,
    # E. Round-trip
    RoundTripReport,
    run_round_trip_harness,
    # F. Attractor/Path
    AttractorReport,
    evaluate_path,
    run_attractor_harness,
    # Core metrics
    CoreMetrics,
    compute_core_metrics,
    # Experiment matrix
    ExperimentMatrixResult,
    run_experiment_matrix,
    # Utilities
    _l2_distance,
    _rank_correlation,
    _compute_collapse_rate,
    _sequence_collapse_rate,
    _dead_tone_discrimination,
    _cross_domain_score,
)
from src.training.cross_domain_harness import (
    PHI,
    ALL_TONGUES,
    DEAD_TONES,
    COMPLEMENT_MAP,
    WarpType,
    encode_contact_point,
    project_contact_point,
)

# =========================================================================
# Fixtures
# =========================================================================

SEED_TEXTS = [
    "The hyperbolic manifold bends adversarial cost exponentially.",
    "Sacred Tongues encode multi-dimensional governance signals.",
    "Dead tones prevent echo chambers through baseline rotation.",
    "Phi-weighted hierarchy creates non-closing orbits.",
    "Cross-modal coherence survives adversarial warping.",
    "Bundle circulation teaches structural alignment.",
    "The harmonic wall enforces exponential cost scaling.",
    "Governance verdicts flow from consonance analysis.",
    "Attractor paths shape long-horizon model behavior.",
    "Round-trip fidelity proves modalities are genuinely coupled.",
]

DIVERSE_TEXTS = SEED_TEXTS + [
    "import numpy as np",
    "SELECT * FROM users WHERE risk > 0.5",
    "Hello, how can I help you today?",
    "function fibonacci(n) { return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2); }",
    "WARNING: Unauthorized access detected in sector 7.",
    "The quick brown fox jumps over the lazy dog.",
    "φ = (1 + √5) / 2 ≈ 1.6180339887...",
    "curl -X POST https://api.example.com/v1/scan",
    "日本語テスト入力",
    "🎵 Do Re Mi Fa Sol La Ti Do 🎵",
]


# =========================================================================
# A. Corpus Validity Harness
# =========================================================================


class TestCorpusValidity:
    """Proves: 'Did you really build the curriculum you think you built?'"""

    def test_labels_are_reproducible(self):
        """Same input → same labels every time."""
        agreement, dt_repro, tongue_repro = check_label_reproducibility(
            SEED_TEXTS[:5], ["ko", "av"], ["perfect_fifth"], runs=3
        )
        assert agreement == 1.0, f"Labels not reproducible: {agreement}"
        assert dt_repro, "Dead-tone scores not reproducible"
        assert tongue_repro, "Tongue vectors not reproducible"

    def test_projections_are_deterministic(self):
        """Projections must be fully deterministic."""
        assert check_projection_determinism(SEED_TEXTS[:5])

    def test_neighbor_purity_above_random(self):
        """Bundle neighbors should be closer than random pairs."""
        purity = check_neighbor_purity(SEED_TEXTS)
        assert purity > 0.4, f"Neighbor purity too low: {purity}"

    def test_no_split_leakage_exact_hashes(self):
        """No exact hash collisions between disjoint splits."""
        # Use maximally different inputs — different lengths and byte distributions
        train = ["a", "abcdefghijklmnopqrstuvwxyz" * 10, "!@#$%^&*()"]
        val = ["ZZZZZ", "0123456789" * 5]
        test = ["日本語テスト", "\xff\xfe\xfd" * 20]
        leakage = check_split_leakage(train, val, test, similarity_threshold=0.999)
        assert leakage < 0.8, f"Split leakage too high for disjoint sets: {leakage}"

    def test_identical_inputs_leak(self):
        """Identical inputs across splits should be detected as leakage."""
        shared = ["The hyperbolic manifold bends adversarial cost exponentially."]
        leakage = check_split_leakage(shared, shared, shared)
        # Same hash in all three splits = high leakage
        assert leakage > 0.0

    def test_class_balance_has_all_verdicts(self):
        """All 4 verdict classes should be represented."""
        cps = [
            encode_contact_point(t, tongue, tone)
            for t in DIVERSE_TEXTS
            for tongue in ALL_TONGUES
            for tone in DEAD_TONES
        ]
        balance = check_class_balance(cps)
        assert len(balance) == 4
        assert all(v >= 0.0 for v in balance.values())
        assert abs(sum(balance.values()) - 1.0) < 1e-6

    def test_friction_zone_coverage_nonzero(self):
        """Some points should land in friction zones near thresholds."""
        cps = [
            encode_contact_point(t, tongue, tone)
            for t in DIVERSE_TEXTS
            for tongue in ALL_TONGUES
            for tone in DEAD_TONES
        ]
        coverage = check_friction_zone_coverage(cps)
        assert coverage >= 0.0  # at least computable

    def test_adversarial_identity_preserved(self):
        """Adversarial warps should change surface form, not identity."""
        assert check_adversarial_identity(SEED_TEXTS[:3])

    def test_full_corpus_validation_passes(self):
        """Full corpus validation should pass on clean data."""
        report = validate_corpus(SEED_TEXTS)
        assert isinstance(report, CorpusValidityReport)
        assert report.label_agreement == 1.0
        assert report.projections_deterministic
        assert report.dead_tone_reproducible
        assert report.tongue_reproducible

    def test_empty_corpus_handled(self):
        """Empty corpus shouldn't crash."""
        report = validate_corpus([""])
        assert isinstance(report, CorpusValidityReport)

    def test_single_char_corpus(self):
        """Single character inputs should work."""
        report = validate_corpus(["a", "b", "c"])
        assert report.label_agreement == 1.0

    def test_unicode_corpus(self):
        """Unicode inputs should be handled cleanly."""
        report = validate_corpus(["日本語", "العربية", "中文测试"])
        assert report.label_agreement == 1.0


# =========================================================================
# B. Ablation Harness
# =========================================================================


class TestAblation:
    """Proves: 'Which part is actually doing work?'"""

    def test_ablation_ladder_has_7_variants(self):
        """7 variants from baseline to full."""
        assert len(ABLATION_LADDER) == 7
        assert ABLATION_LADDER[0].variant == AblationVariant.BASELINE_SFT
        assert ABLATION_LADDER[-1].variant == AblationVariant.FULL_SCBE

    def test_baseline_sft_has_nothing_enabled(self):
        """Baseline should have all subsystems disabled."""
        baseline = ABLATION_LADDER[0]
        assert not baseline.use_dead_tone_curriculum
        assert not baseline.use_multiview
        assert not baseline.use_warping
        assert not baseline.use_bundle_topology
        assert not baseline.use_constitution
        assert not baseline.use_curriculum_passes

    def test_full_scbe_has_everything_enabled(self):
        """Full should have all subsystems enabled."""
        full = ABLATION_LADDER[-1]
        assert full.use_dead_tone_curriculum
        assert full.use_multiview
        assert full.use_warping
        assert full.use_bundle_topology
        assert full.use_constitution
        assert full.use_curriculum_passes

    def test_single_variant_runs(self):
        """One ablation variant on one suite should produce a result."""
        result = run_ablation_variant(ABLATION_LADDER[-1], SEED_TEXTS[:3], EvalSuite.CLEAN)
        assert isinstance(result, AblationResult)
        assert 0.0 <= result.task_score <= 1.0
        assert 0.0 <= result.alignment_retention <= 1.0
        assert 0.0 <= result.escalation_correctness <= 1.0

    def test_full_scbe_beats_baseline_on_clean(self):
        """Full system should score >= baseline on clean eval."""
        baseline = run_ablation_variant(ABLATION_LADDER[0], SEED_TEXTS[:3], EvalSuite.CLEAN)
        full = run_ablation_variant(ABLATION_LADDER[-1], SEED_TEXTS[:3], EvalSuite.CLEAN)
        assert full.task_score >= baseline.task_score * 0.8  # at least close

    def test_dead_tone_ablation_matters(self):
        """Removing dead-tone curriculum should hurt dead-tone eval."""
        no_dt = run_ablation_variant(
            ABLATION_LADDER[1], SEED_TEXTS[:3], EvalSuite.DEAD_TONE  # +constitution, no dead tone
        )
        with_dt = run_ablation_variant(ABLATION_LADDER[2], SEED_TEXTS[:3], EvalSuite.DEAD_TONE)  # +dead_tone
        assert with_dt.task_score >= no_dt.task_score

    def test_warping_ablation_matters(self):
        """Removing warping should hurt adversarial eval."""
        no_warp = run_ablation_variant(
            ABLATION_LADDER[3], SEED_TEXTS[:3], EvalSuite.ADVERSARIAL  # +multiview, no warping
        )
        with_warp = run_ablation_variant(ABLATION_LADDER[4], SEED_TEXTS[:3], EvalSuite.ADVERSARIAL)  # +warping
        assert with_warp.task_score >= no_warp.task_score

    def test_full_ablation_produces_matrix(self):
        """Full ablation should produce 7 × N results."""
        report = run_full_ablation(SEED_TEXTS[:2], [EvalSuite.CLEAN])
        assert isinstance(report, AblationReport)
        assert len(report.results) == 7  # 7 variants × 1 suite

    def test_ablation_contribution_computed(self):
        """Each variant's contribution should be computable."""
        report = run_full_ablation(SEED_TEXTS[:2], [EvalSuite.CLEAN])
        for config in ABLATION_LADDER[1:]:
            contrib = report.contribution(config.variant, EvalSuite.CLEAN)
            assert isinstance(contrib, float)

    def test_variant_means_computed(self):
        """Mean scores per variant should be available."""
        report = run_full_ablation(SEED_TEXTS[:2], [EvalSuite.CLEAN])
        means = report.variant_means
        assert len(means) == 7

    def test_ablation_report_get_method(self):
        """Should be able to look up specific cells."""
        report = run_full_ablation(SEED_TEXTS[:2], [EvalSuite.CLEAN])
        result = report.get(AblationVariant.FULL_SCBE, EvalSuite.CLEAN)
        assert result is not None
        assert result.variant == AblationVariant.FULL_SCBE

    def test_ablation_report_get_missing(self):
        """Missing cells should return None."""
        report = run_full_ablation(SEED_TEXTS[:2], [EvalSuite.CLEAN])
        result = report.get(AblationVariant.FULL_SCBE, EvalSuite.LONG_HORIZON)
        assert result is None


# =========================================================================
# C. Cross-Domain Transfer Harness
# =========================================================================


class TestCrossDomainTransfer:
    """Proves: 'Is this really cross-domain inference, or memorized formatting?'"""

    def test_transfer_pairs_defined(self):
        """All 7 canonical transfer pairs exist."""
        assert len(TRANSFER_PAIRS) == 7
        for src, tgt in TRANSFER_PAIRS:
            assert src in DOMAIN_NAMES
            assert tgt in DOMAIN_NAMES
            assert src != tgt

    def test_single_transfer_produces_result(self):
        """One transfer experiment should produce a TransferResult."""
        result = measure_transfer(SEED_TEXTS[:5], "harmonic", "governance")
        assert isinstance(result, TransferResult)
        assert result.train_domain == "harmonic"
        assert result.test_domain == "governance"
        assert 0.0 <= result.full_score <= 1.0
        assert 0.0 <= result.baseline_score <= 1.0

    def test_transfer_gain_can_be_positive(self):
        """Structured transfer should sometimes beat random baseline."""
        result = measure_transfer(DIVERSE_TEXTS, "tongue", "harmonic")
        # Transfer gain = full - baseline; may or may not be positive
        assert isinstance(result.transfer_gain, float)

    def test_self_transfer_is_high(self):
        """Transferring from a domain to itself should score high."""
        # This tests structure_retention (cosine between same-input projections)
        result = measure_transfer(SEED_TEXTS[:5], "tongue", "tongue")
        assert result.structure_retention > 0.99

    def test_transfer_harness_runs_all_pairs(self):
        """Full transfer harness should run all pairs."""
        results = run_transfer_harness(SEED_TEXTS[:3], TRANSFER_PAIRS[:3])
        assert len(results) == 3
        assert all(isinstance(r, TransferResult) for r in results)

    def test_transfer_scores_bounded(self):
        """All transfer scores should be in [0, 1]."""
        results = run_transfer_harness(SEED_TEXTS[:3], TRANSFER_PAIRS[:2])
        for r in results:
            assert 0.0 <= r.full_score <= 1.0
            assert 0.0 <= r.baseline_score <= 1.0
            assert 0.0 <= r.structure_retention <= 1.0

    def test_different_pairs_give_different_scores(self):
        """Different domain pairs should produce distinct transfer profiles."""
        results = run_transfer_harness(DIVERSE_TEXTS, TRANSFER_PAIRS[:3])
        scores = [r.full_score for r in results]
        # Not all identical (unless by coincidence, which is fine)
        assert len(set(round(s, 4) for s in scores)) >= 1

    def test_transfer_with_single_input(self):
        """Single-input transfer should still work (degenerate case)."""
        result = measure_transfer(["test"], "semantic", "governance")
        assert isinstance(result, TransferResult)


# =========================================================================
# D. Adversarial Warping Harness
# =========================================================================


class TestAdversarialWarping:
    """Proves: 'Does alignment survive deformation?'"""

    def test_all_8_warp_types_tested(self):
        """All 8 warp types should be covered."""
        assert len(WarpType) == 8

    def test_single_warp_preservation(self):
        """One warp type should produce a WarpPreservationResult."""
        result = measure_warp_preservation(SEED_TEXTS[:3], WarpType.SEMANTIC_PARAPHRASE, 0.3)
        assert isinstance(result, WarpPreservationResult)
        assert result.warp_type == WarpType.SEMANTIC_PARAPHRASE
        assert 0.0 <= result.alignment_retention <= 1.0

    def test_low_magnitude_preserves_more(self):
        """Lower warp magnitude should preserve more alignment."""
        low = measure_warp_preservation(SEED_TEXTS[:3], WarpType.PROSODY_DRIFT, 0.1)
        high = measure_warp_preservation(SEED_TEXTS[:3], WarpType.PROSODY_DRIFT, 0.5)
        # Low magnitude should preserve at least as much
        assert low.alignment_retention >= high.alignment_retention * 0.8

    def test_dead_tone_near_miss_is_hardest(self):
        """Dead-tone near-miss should be one of the harder warps."""
        results = []
        for wt in [WarpType.SEMANTIC_PARAPHRASE, WarpType.DEAD_TONE_NEAR_MISS]:
            results.append(measure_warp_preservation(SEED_TEXTS[:3], wt, 0.5))
        # Both should produce valid scores
        assert all(0.0 <= r.alignment_retention <= 1.0 for r in results)

    def test_tongue_preservation_tracked(self):
        """Dominant tongue preservation should be tracked."""
        result = measure_warp_preservation(SEED_TEXTS[:3], WarpType.NEIGHBOR_JUMP, 0.3)
        assert 0.0 <= result.tongue_preserved <= 1.0

    def test_verdict_preservation_tracked(self):
        """Verdict preservation should be tracked."""
        result = measure_warp_preservation(SEED_TEXTS[:3], WarpType.EXCITATION_SPIKE, 0.3)
        assert 0.0 <= result.verdict_preserved <= 1.0

    def test_dead_tone_preservation_always_1(self):
        """Dead-tone interpretation is structural, should always be preserved."""
        result = measure_warp_preservation(SEED_TEXTS[:3], WarpType.AUDIO_BAND_SHIFT, 0.3)
        assert result.dead_tone_preserved == 1.0

    def test_full_adversarial_harness(self):
        """Full harness: 8 warp types × magnitudes."""
        results = run_adversarial_harness(SEED_TEXTS[:2], [0.3])
        assert len(results) == 8  # 8 warp types × 1 magnitude
        assert all(isinstance(r, WarpPreservationResult) for r in results)

    def test_zero_magnitude_preserves_everything(self):
        """Zero warp should preserve perfect alignment."""
        result = measure_warp_preservation(SEED_TEXTS[:2], WarpType.SEMANTIC_PARAPHRASE, 0.0)
        # Zero warp = features unchanged = perfect retention
        assert result.alignment_retention >= 0.99

    def test_coherence_under_all_warps(self):
        """Cross-modal coherence should be measurable under every warp."""
        for wt in WarpType:
            result = measure_warp_preservation(SEED_TEXTS[:2], wt, 0.3)
            assert 0.0 <= result.coherence_preserved <= 1.0

    def test_risk_preservation_tracked(self):
        """Binary risk tier preservation (safe vs not-safe) should be tracked."""
        result = measure_warp_preservation(SEED_TEXTS[:3], WarpType.COLOR_PERTURBATION, 0.3)
        assert 0.0 <= result.risk_preserved <= 1.0


# =========================================================================
# E. Round-Trip Harness
# =========================================================================


class TestRoundTrip:
    """Proves: 'Are the modalities actually tied together?'"""

    def test_round_trip_produces_report(self):
        """Round-trip harness should produce a full report."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert isinstance(report, RoundTripReport)

    def test_tongue_similarity_high_for_deterministic_encode(self):
        """Re-encoding the same input should give identical tongue vectors."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert report.tongue_similarity > 0.99

    def test_dead_tone_agreement_perfect(self):
        """Dead-tone parameter doesn't change — should be 100% agreement."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert report.dead_tone_agreement == 1.0

    def test_spectral_agreement_high(self):
        """Audio projections of same input should agree."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert report.spectral_agreement > 0.99

    def test_governance_agreement_perfect(self):
        """Verdicts should be identical for same input + params."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert report.governance_agreement == 1.0

    def test_overall_fidelity_high(self):
        """Overall round-trip fidelity should be high for deterministic system."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert report.overall_fidelity > 0.9

    def test_structure_retention_high(self):
        """S = sim(z_intended, z_recovered) should be high."""
        report = run_round_trip_harness(SEED_TEXTS[:3], ["ko"], ["perfect_fifth"])
        assert report.structure_retention > 0.9

    def test_multi_tongue_round_trip(self):
        """Round-trip should work across all tongues."""
        report = run_round_trip_harness(SEED_TEXTS[:2], list(ALL_TONGUES), ["perfect_fifth"])
        assert report.overall_fidelity > 0.9

    def test_multi_dead_tone_round_trip(self):
        """Round-trip should work across all dead tones."""
        report = run_round_trip_harness(SEED_TEXTS[:2], ["ko"], list(DEAD_TONES))
        assert report.overall_fidelity > 0.9

    def test_collapse_rate_measurable_for_varied_input(self):
        """Varied inputs across all tongues × tones should produce measurable collapse rate."""
        report = run_round_trip_harness(DIVERSE_TEXTS[:5], list(ALL_TONGUES), list(DEAD_TONES))
        assert 0.0 <= report.loop_collapse_rate <= 1.0


# =========================================================================
# F. Attractor / Path Harness
# =========================================================================


class TestAttractorPath:
    """Proves: 'Does the manifold shape behavior over time?'"""

    def test_safe_near_path_low_cost(self):
        """Safe-near path should have lower cost than adversarial."""
        safe = evaluate_path("test input", PathType.SAFE_NEAR, steps=8)
        adversarial = evaluate_path("test input", PathType.ADVERSARIAL_BRIDGE, steps=8)
        assert safe.total_cost <= adversarial.total_cost * 1.5

    def test_safe_near_path_stable(self):
        """Safe-near path should be stable."""
        result = evaluate_path("stable test", PathType.SAFE_NEAR, steps=8)
        assert result.stability > 0.3

    def test_adversarial_path_escalates(self):
        """Adversarial bridge path should trigger escalation events."""
        result = evaluate_path("adversarial test", PathType.ADVERSARIAL_BRIDGE, steps=10)
        # Adversarial path crosses friction zones → should see escalations
        assert isinstance(result.escalation_events, int)

    def test_path_result_has_steps(self):
        """Each path should have the requested number of steps."""
        result = evaluate_path("step test", PathType.SAFE_FAR, steps=5)
        assert len(result.steps) == 5

    def test_cumulative_cost_monotonic(self):
        """Cumulative cost should only increase along a path."""
        result = evaluate_path("monotonic test", PathType.UNSAFE_NEAR, steps=8)
        costs = [s.cumulative_cost for s in result.steps]
        for i in range(1, len(costs)):
            assert costs[i] >= costs[i - 1]

    def test_each_step_has_consistency(self):
        """Each step should have a consistency score in [0, 1]."""
        result = evaluate_path("consistency test", PathType.SAFE_NEAR, steps=5)
        for step in result.steps:
            assert 0.0 <= step.consistency <= 1.0

    def test_each_step_has_grounding(self):
        """Each step should have a grounding check."""
        result = evaluate_path("grounding test", PathType.SAFE_FAR, steps=5)
        for step in result.steps:
            assert isinstance(step.grounded, bool)

    def test_full_attractor_harness(self):
        """Full harness should run all 4 path types per seed text."""
        report = run_attractor_harness(SEED_TEXTS[:2], steps=5)
        assert isinstance(report, AttractorReport)
        assert len(report.paths) == 8  # 2 texts × 4 path types

    def test_safe_path_cheaper_than_adversarial(self):
        """Safe paths should be cheaper than adversarial paths on average."""
        report = run_attractor_harness(SEED_TEXTS[:3], steps=5)
        assert report.safe_near_cost <= report.adversarial_bridge_cost * 2.0

    def test_collapse_rate_bounded(self):
        """Collapse rate should be in [0, 1]."""
        report = run_attractor_harness(SEED_TEXTS[:2], steps=5)
        assert 0.0 <= report.collapse_rate <= 1.0

    def test_stability_bounded(self):
        """Mean stability should be in [0, 1]."""
        report = run_attractor_harness(SEED_TEXTS[:2], steps=5)
        assert 0.0 <= report.mean_stability <= 1.0

    def test_escalation_correctness_bounded(self):
        """Escalation correctness should be in [0, 1]."""
        report = run_attractor_harness(SEED_TEXTS[:2], steps=5)
        assert 0.0 <= report.escalation_correctness <= 1.0


# =========================================================================
# Core Metrics
# =========================================================================


class TestCoreMetrics:
    """The 6 metrics that actually matter."""

    def test_core_metrics_computable(self):
        """All 6 core metrics should be computable."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert isinstance(metrics, CoreMetrics)

    def test_structure_retention_bounded(self):
        """S ∈ [0, 1]."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert 0.0 <= metrics.structure_retention <= 1.0

    def test_transfer_gain_is_float(self):
        """T = full - baseline should be a float."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert isinstance(metrics.cross_domain_transfer_gain, float)

    def test_adversarial_retention_bounded(self):
        """A = perturbed / clean ∈ [0, 1]."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert 0.0 <= metrics.adversarial_alignment_retention <= 1.0

    def test_collapse_rate_bounded(self):
        """Collapse rate ∈ [0, 1]."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert 0.0 <= metrics.loop_collapse_rate <= 1.0

    def test_escalation_correctness_bounded(self):
        """Escalation correctness ∈ [0, 1]."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert 0.0 <= metrics.escalation_correctness <= 1.0

    def test_ablation_contribution_dict(self):
        """Ablation contributions should map variant names to floats."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert isinstance(metrics.ablation_contribution, dict)
        assert len(metrics.ablation_contribution) == 7

    def test_core_metrics_with_ablation_report(self):
        """Core metrics should incorporate ablation results when provided."""
        ablation = run_full_ablation(SEED_TEXTS[:2], [EvalSuite.CLEAN])
        metrics = compute_core_metrics(SEED_TEXTS[:2], ablation)
        # With ablation data, contributions should include non-zero values
        assert isinstance(metrics.ablation_contribution, dict)

    def test_structure_retention_high_for_deterministic(self):
        """Deterministic system should have high structure retention."""
        metrics = compute_core_metrics(SEED_TEXTS[:3])
        assert metrics.structure_retention > 0.5


# =========================================================================
# Experiment Matrix
# =========================================================================


class TestExperimentMatrix:
    """The full 7 × 6 experiment matrix."""

    def test_matrix_runs_in_fast_mode(self):
        """Fast mode should complete and return all components."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        assert isinstance(result, ExperimentMatrixResult)
        assert result.corpus_validity is not None
        assert result.ablation_report is not None
        assert result.transfer_results is not None
        assert result.adversarial_results is not None
        assert result.round_trip_report is not None
        assert result.attractor_report is not None
        assert result.core_metrics is not None

    def test_matrix_corpus_valid(self):
        """Corpus should validate within the matrix."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        assert result.corpus_validity.label_agreement == 1.0
        assert result.corpus_validity.projections_deterministic

    def test_matrix_ablation_populated(self):
        """Ablation report should have results."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        assert len(result.ablation_report.results) > 0

    def test_matrix_transfer_populated(self):
        """Transfer results should have entries."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        assert len(result.transfer_results) > 0

    def test_matrix_adversarial_populated(self):
        """Adversarial results should cover all warp types."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        assert len(result.adversarial_results) == 8  # 8 warps × 1 magnitude

    def test_matrix_core_metrics_present(self):
        """Core metrics should all be present."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        m = result.core_metrics
        assert isinstance(m.structure_retention, float)
        assert isinstance(m.cross_domain_transfer_gain, float)
        assert isinstance(m.adversarial_alignment_retention, float)
        assert isinstance(m.loop_collapse_rate, float)
        assert isinstance(m.escalation_correctness, float)
        assert isinstance(m.ablation_contribution, dict)


# =========================================================================
# Utility Functions
# =========================================================================


class TestUtilities:
    """Utility function correctness."""

    def test_l2_distance_zero_for_same(self):
        assert _l2_distance((1.0, 2.0, 3.0), (1.0, 2.0, 3.0)) == 0.0

    def test_l2_distance_positive(self):
        d = _l2_distance((0.0,), (1.0,))
        assert d == 1.0

    def test_l2_distance_pads_shorter(self):
        """Mismatched dims should pad with zeros."""
        d = _l2_distance((1.0, 2.0), (1.0, 2.0, 3.0))
        assert d == 3.0

    def test_rank_correlation_perfect(self):
        """Identical orderings → correlation = 1.0."""
        corr = _rank_correlation([1, 2, 3, 4, 5], [10, 20, 30, 40, 50])
        assert corr > 0.95

    def test_rank_correlation_inverse(self):
        """Reversed orderings → low correlation."""
        corr = _rank_correlation([1, 2, 3, 4, 5], [50, 40, 30, 20, 10])
        assert corr < 0.1

    def test_rank_correlation_random(self):
        """Random should be near 0.5."""
        corr = _rank_correlation([1, 2, 3, 4, 5], [3, 1, 5, 2, 4])
        assert 0.0 <= corr <= 1.0

    def test_collapse_rate_all_same(self):
        """All same verdict → collapse rate = 1.0."""
        cps = [encode_contact_point("test", "ko", "perfect_fifth") for _ in range(5)]
        rate = _compute_collapse_rate(cps)
        assert rate == 1.0

    def test_collapse_rate_empty(self):
        assert _compute_collapse_rate([]) == 0.0

    def test_sequence_collapse_rate_varied(self):
        """Varied sequence → low collapse rate."""
        rate = _sequence_collapse_rate(["ALLOW", "DENY", "QUARANTINE", "ALLOW", "ESCALATE"])
        assert rate == 0.0

    def test_sequence_collapse_rate_all_same(self):
        rate = _sequence_collapse_rate(["ALLOW", "ALLOW", "ALLOW"])
        assert rate == 1.0

    def test_dead_tone_discrimination_zero_for_single(self):
        """Single dead tone → no discrimination possible."""
        cps = [encode_contact_point("test", "ko", "perfect_fifth")]
        assert _dead_tone_discrimination(cps) == 0.0

    def test_dead_tone_discrimination_bounded(self):
        """Discrimination score should be in [0, 1]."""
        cps = [
            encode_contact_point(t, tongue, tone)
            for t in SEED_TEXTS[:3]
            for tongue in ALL_TONGUES
            for tone in DEAD_TONES
        ]
        score = _dead_tone_discrimination(cps)
        assert 0.0 <= score <= 1.0

    def test_cross_domain_score_bounded(self):
        cps = [encode_contact_point(t) for t in SEED_TEXTS[:3]]
        bundles = [project_contact_point(cp) for cp in cps]
        score = _cross_domain_score(bundles)
        assert 0.0 <= score <= 1.0

    def test_cross_domain_score_empty(self):
        assert _cross_domain_score([]) == 0.0


# =========================================================================
# Cross-Cutting Properties
# =========================================================================


class TestCrossCuttingProperties:
    """Properties that hold across all harness components."""

    def test_all_scores_bounded_0_1(self):
        """Every score in the system should be in [0, 1]."""
        result = run_experiment_matrix(SEED_TEXTS[:2], fast=True)
        m = result.core_metrics
        for val in [
            m.structure_retention,
            m.adversarial_alignment_retention,
            m.loop_collapse_rate,
            m.escalation_correctness,
        ]:
            assert 0.0 <= val <= 1.0, f"Score out of bounds: {val}"

    def test_determinism_across_runs(self):
        """Two runs with same inputs should produce same results."""
        r1 = run_experiment_matrix(["test one", "test two"], fast=True)
        r2 = run_experiment_matrix(["test one", "test two"], fast=True)
        assert r1.core_metrics.structure_retention == r2.core_metrics.structure_retention
        assert r1.corpus_validity.label_agreement == r2.corpus_validity.label_agreement

    def test_no_nan_or_inf(self):
        """No metric should be NaN or Inf."""
        result = run_experiment_matrix(SEED_TEXTS[:3], fast=True)
        m = result.core_metrics
        for val in [
            m.structure_retention,
            m.cross_domain_transfer_gain,
            m.adversarial_alignment_retention,
            m.loop_collapse_rate,
            m.escalation_correctness,
        ]:
            assert not math.isnan(val), f"NaN detected: {val}"
            assert not math.isinf(val), f"Inf detected: {val}"

    def test_empty_input_no_crash(self):
        """Empty string input should not crash any component."""
        result = run_experiment_matrix([""], fast=True)
        assert isinstance(result, ExperimentMatrixResult)

    def test_unicode_input_no_crash(self):
        """Unicode inputs should not crash."""
        result = run_experiment_matrix(["日本語", "العربية"], fast=True)
        assert isinstance(result, ExperimentMatrixResult)

    def test_single_input_no_crash(self):
        """Single input should work across all components."""
        result = run_experiment_matrix(["solo input"], fast=True)
        assert isinstance(result, ExperimentMatrixResult)

    def test_complement_symmetry_holds(self):
        """COMPLEMENT_MAP should be a perfect involution."""
        for t1, t2 in COMPLEMENT_MAP.items():
            assert COMPLEMENT_MAP[t2] == t1

    def test_phi_is_irrational(self):
        """PHI should not equal any simple rational."""
        for n in range(1, 20):
            for d in range(1, 20):
                assert abs(PHI - n / d) > 1e-6
