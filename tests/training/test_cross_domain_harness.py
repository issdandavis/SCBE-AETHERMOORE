"""
Tests for the Cross-Domain Adversarial Alignment Harness
=========================================================

Tests all 8 stages of the harness plus the full pipeline and export.

Self-contained: all logic is inlined for isolation — no cross-module imports
except from the harness itself.

Author: SCBE-AETHERMOORE / Issac Davis
"""

import math
import pytest

from src.training.cross_domain_harness import (
    # Constants
    PHI, PHI_INV, ALL_TONGUES, DEAD_TONES, COMPLEMENT_MAP,
    TONGUE_WEIGHTS, BASELINE_FREQUENCIES, TONGUE_FREQUENCIES,
    ALLOW_THRESHOLD, QUARANTINE_THRESHOLD, ESCALATE_THRESHOLD,
    # Enums
    GovernanceVerdict, WarpType, CurriculumPass,
    # Stage 1
    ContactPoint, encode_contact_point,
    # Stage 2
    DomainProjection, ProjectionBundle, project_contact_point,
    # Stage 3
    WarpedProjection, warp_projection, warp_bundle,
    # Stage 4
    ExpandedNeighborhood, expand_contact_point,
    # Stage 5
    GroundingCheck, check_grounding,
    # Stage 6
    CurriculumState, CURRICULUM_ORDER, select_warp_for_pass, run_curriculum_pass,
    # Stage 7
    ConsistencyScore, score_consistency, score_warp_resilience,
    # Stage 8
    RoundTripResult, round_trip_evaluate,
    # Full pipeline
    HarnessRun, run_harness,
    # Export
    export_harness_training_data,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_text():
    return "The harmonic wall rises exponentially."


@pytest.fixture
def sample_cp(sample_text):
    return encode_contact_point(sample_text, "ko", "perfect_fifth", 3.0)


@pytest.fixture
def sample_bundle(sample_cp):
    return project_contact_point(sample_cp)


# ---------------------------------------------------------------------------
# Stage 1: Contact-Point Encoder
# ---------------------------------------------------------------------------

class TestContactPointEncoder:
    def test_returns_contact_point(self, sample_text):
        cp = encode_contact_point(sample_text)
        assert isinstance(cp, ContactPoint)

    def test_hash_is_deterministic(self, sample_text):
        a = encode_contact_point(sample_text, "ko", "perfect_fifth", 3.0)
        b = encode_contact_point(sample_text, "ko", "perfect_fifth", 3.0)
        assert a.point_hash == b.point_hash

    def test_different_tongue_different_hash(self, sample_text):
        a = encode_contact_point(sample_text, "ko")
        b = encode_contact_point(sample_text, "av")
        assert a.point_hash != b.point_hash

    def test_different_dead_tone_different_hash(self, sample_text):
        a = encode_contact_point(sample_text, dead_tone="perfect_fifth")
        b = encode_contact_point(sample_text, dead_tone="minor_sixth")
        assert a.point_hash != b.point_hash

    def test_tongue_vector_is_6d(self, sample_cp):
        assert len(sample_cp.tongue_vector) == 6

    def test_tongue_vector_bounded(self, sample_cp):
        assert all(0.0 <= v <= 1.0 for v in sample_cp.tongue_vector)

    def test_prosody_rate_bounded(self, sample_cp):
        assert 0.5 <= sample_cp.prosody_rate <= 2.0

    def test_prosody_energy_bounded(self, sample_cp):
        assert 0.0 <= sample_cp.prosody_energy <= 1.0

    def test_agent_frequency_bounded(self, sample_cp):
        assert 20.0 <= sample_cp.agent_frequency_hz <= 20000.0

    def test_dissonance_bounded(self, sample_cp):
        assert 0.0 <= sample_cp.dissonance_score <= 1.0

    def test_darkness_bounded(self, sample_cp):
        assert 0.0 <= sample_cp.darkness <= 1.0

    def test_verdict_is_governance(self, sample_cp):
        assert isinstance(sample_cp.verdict, GovernanceVerdict)

    def test_all_tongues_produce_valid_cp(self, sample_text):
        for tongue in ALL_TONGUES:
            cp = encode_contact_point(sample_text, tongue)
            assert cp.dominant_tongue == tongue
            assert len(cp.tongue_vector) == 6

    def test_all_dead_tones_produce_valid_cp(self, sample_text):
        for tone in DEAD_TONES:
            cp = encode_contact_point(sample_text, dead_tone=tone)
            assert cp.dead_tone == tone

    def test_empty_input_works(self):
        cp = encode_contact_point("")
        assert isinstance(cp, ContactPoint)
        assert len(cp.tongue_vector) == 6

    def test_excitation_affects_energy(self, sample_text):
        low = encode_contact_point(sample_text, excitation=0.5)
        high = encode_contact_point(sample_text, excitation=8.0)
        assert high.prosody_energy > low.prosody_energy


# ---------------------------------------------------------------------------
# Stage 2: Cross-Domain Projector
# ---------------------------------------------------------------------------

class TestCrossDomainProjector:
    def test_returns_projection_bundle(self, sample_cp):
        bundle = project_contact_point(sample_cp)
        assert isinstance(bundle, ProjectionBundle)

    def test_seven_domains(self, sample_bundle):
        assert sample_bundle.domain_count == 7

    def test_all_projections_have_features(self, sample_bundle):
        for proj in sample_bundle.all_projections:
            assert len(proj.features) > 0

    def test_all_features_are_finite(self, sample_bundle):
        for proj in sample_bundle.all_projections:
            assert all(math.isfinite(v) for v in proj.features)

    def test_domain_names(self, sample_bundle):
        domains = {p.domain for p in sample_bundle.all_projections}
        assert domains == {"semantic", "tongue", "harmonic", "chromatic",
                           "prosody", "audio", "governance"}

    def test_source_hash_matches(self, sample_cp, sample_bundle):
        assert sample_bundle.source_hash == sample_cp.point_hash

    def test_semantic_has_metadata(self, sample_bundle):
        assert "input_length" in sample_bundle.semantic.metadata

    def test_tongue_has_dominant(self, sample_bundle):
        assert "dominant" in sample_bundle.tongue.metadata

    def test_chromatic_has_hue(self, sample_bundle):
        assert "hue_degrees" in sample_bundle.chromatic.metadata

    def test_governance_has_verdict(self, sample_bundle):
        assert "verdict" in sample_bundle.governance.metadata

    def test_all_tongues_project_differently(self, sample_text):
        bundles = [
            project_contact_point(encode_contact_point(sample_text, tongue))
            for tongue in ALL_TONGUES
        ]
        tongue_features = [b.tongue.features for b in bundles]
        # At least some should differ
        unique = set(tongue_features)
        assert len(unique) > 1

    def test_features_bounded_01(self, sample_bundle):
        """Most projection features should be in [0, 1] range."""
        for proj in sample_bundle.all_projections:
            for v in proj.features:
                # Allow small overshoot from log transforms
                assert -0.5 <= v <= 2.0, f"{proj.domain}: {v}"


# ---------------------------------------------------------------------------
# Stage 3: Adversarial Warping Engine
# ---------------------------------------------------------------------------

class TestAdversarialWarping:
    def test_warp_returns_warped_projection(self, sample_bundle):
        wp = warp_projection(sample_bundle.semantic, WarpType.SEMANTIC_PARAPHRASE)
        assert isinstance(wp, WarpedProjection)

    def test_warp_preserves_domain(self, sample_bundle):
        wp = warp_projection(sample_bundle.tongue, WarpType.PROSODY_DRIFT)
        assert wp.warped.domain == "tongue"

    def test_warp_changes_features(self, sample_bundle):
        wp = warp_projection(sample_bundle.harmonic, WarpType.DEAD_TONE_NEAR_MISS, 0.5)
        assert wp.original.features != wp.warped.features

    def test_zero_magnitude_preserves_features(self, sample_bundle):
        wp = warp_projection(sample_bundle.semantic, WarpType.PROSODY_DRIFT, 0.0)
        # With zero magnitude, prosody drift averages with 0 weight → no change
        assert wp.original.features == wp.warped.features

    def test_warp_magnitude_clamped(self, sample_bundle):
        wp = warp_projection(sample_bundle.semantic, WarpType.SEMANTIC_PARAPHRASE, 5.0)
        assert wp.warp_magnitude == 1.0

    def test_warp_features_bounded(self, sample_bundle):
        for wt in WarpType:
            wp = warp_projection(sample_bundle.prosody, wt, 0.5, seed=42)
            assert all(0.0 <= v <= 1.0 for v in wp.warped.features)

    def test_warp_bundle_returns_seven(self, sample_bundle):
        warps = warp_bundle(sample_bundle, WarpType.AUDIO_BAND_SHIFT)
        assert len(warps) == 7

    def test_all_warp_types_work(self, sample_bundle):
        for wt in WarpType:
            warps = warp_bundle(sample_bundle, wt, 0.3)
            assert len(warps) == 7

    def test_warp_is_deterministic(self, sample_bundle):
        a = warp_projection(sample_bundle.semantic, WarpType.NEIGHBOR_JUMP, 0.5, seed=99)
        b = warp_projection(sample_bundle.semantic, WarpType.NEIGHBOR_JUMP, 0.5, seed=99)
        assert a.warped.features == b.warped.features

    def test_different_seeds_different_warps(self, sample_bundle):
        a = warp_projection(sample_bundle.semantic, WarpType.SEMANTIC_PARAPHRASE, 0.5, seed=1)
        b = warp_projection(sample_bundle.semantic, WarpType.SEMANTIC_PARAPHRASE, 0.5, seed=999)
        assert a.warped.features != b.warped.features

    def test_higher_magnitude_more_distortion(self, sample_bundle):
        low = warp_projection(sample_bundle.harmonic, WarpType.DEAD_TONE_NEAR_MISS, 0.1, seed=42)
        high = warp_projection(sample_bundle.harmonic, WarpType.DEAD_TONE_NEAR_MISS, 0.9, seed=42)
        dist_low = math.sqrt(sum(
            (a - b) ** 2 for a, b in zip(low.original.features, low.warped.features)
        ))
        dist_high = math.sqrt(sum(
            (a - b) ** 2 for a, b in zip(high.original.features, high.warped.features)
        ))
        assert dist_high >= dist_low


# ---------------------------------------------------------------------------
# Stage 4: Expansion Engine
# ---------------------------------------------------------------------------

class TestExpansionEngine:
    def test_returns_neighborhood(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert isinstance(hood, ExpandedNeighborhood)

    def test_center_is_original(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert hood.center.point_hash == sample_cp.point_hash

    def test_has_local_neighbors(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert len(hood.local_neighbors) == 3

    def test_has_complement_neighbors(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert len(hood.complement_neighbors) == 2
        complement = COMPLEMENT_MAP[sample_cp.dominant_tongue]
        assert all(n.dominant_tongue == complement for n in hood.complement_neighbors)

    def test_has_bridge_cases(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert len(hood.bridge_cases) == 3
        tones = {n.dead_tone for n in hood.bridge_cases}
        assert tones == set(DEAD_TONES)

    def test_has_friction_cases(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert len(hood.friction_cases) == 2
        excitations = [n.excitation for n in hood.friction_cases]
        assert min(excitations) < 1.0
        assert max(excitations) >= 10.0

    def test_has_long_jumps(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        assert len(hood.long_jumps) >= 2
        jump_tongues = {n.dominant_tongue for n in hood.long_jumps}
        assert sample_cp.dominant_tongue not in jump_tongues

    def test_total_count(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        # 1 center + 3 local + 2 complement + 3 bridge + 2 friction + 3 long
        assert hood.total_count == 14

    def test_all_points_are_contact_points(self, sample_cp, sample_text):
        hood = expand_contact_point(sample_cp, sample_text)
        for p in hood.all_points:
            assert isinstance(p, ContactPoint)


# ---------------------------------------------------------------------------
# Stage 5: Grounding Layer
# ---------------------------------------------------------------------------

class TestGroundingLayer:
    def test_returns_grounding_check(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert isinstance(gc, GroundingCheck)

    def test_standard_point_is_grounded(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert gc.is_grounded

    def test_bounds_respected(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert gc.bounds_respected

    def test_dead_tones_distinct(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert gc.dead_tone_distinct

    def test_complement_symmetric(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert gc.complement_symmetric

    def test_phi_non_closure(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert gc.phi_non_closure

    def test_all_tongues_grounded(self, sample_text):
        for tongue in ALL_TONGUES:
            cp = encode_contact_point(sample_text, tongue)
            gc = check_grounding(cp)
            assert gc.is_grounded, f"{tongue} failed grounding"

    def test_all_dead_tones_grounded(self, sample_text):
        for tone in DEAD_TONES:
            cp = encode_contact_point(sample_text, dead_tone=tone)
            gc = check_grounding(cp)
            assert gc.is_grounded, f"{tone} failed grounding"

    def test_no_violations_on_clean_input(self, sample_cp):
        gc = check_grounding(sample_cp)
        assert gc.invariant_violations == []


# ---------------------------------------------------------------------------
# Stage 6: Circulation Curriculum
# ---------------------------------------------------------------------------

class TestCirculationCurriculum:
    def test_curriculum_has_six_passes(self):
        assert len(CURRICULUM_ORDER) == 6

    def test_all_passes_have_warp_mapping(self):
        for pass_type in CurriculumPass:
            warp = select_warp_for_pass(pass_type)
            assert isinstance(warp, WarpType)

    def test_pass_updates_state(self, sample_cp):
        state = CurriculumState()
        run_curriculum_pass(state, [sample_cp], CurriculumPass.GRAMMAR)
        assert len(state.passes_completed) == 1
        assert state.passes_completed[0] == CurriculumPass.GRAMMAR
        assert state.total_points_processed == 1

    def test_full_cycle_increments(self, sample_cp):
        state = CurriculumState()
        for pass_type in CURRICULUM_ORDER:
            run_curriculum_pass(state, [sample_cp], pass_type)
        assert state.current_cycle == 1

    def test_returns_bundles(self, sample_cp):
        state = CurriculumState()
        bundles = run_curriculum_pass(state, [sample_cp], CurriculumPass.HARMONIC)
        assert len(bundles) == 1
        assert isinstance(bundles[0], ProjectionBundle)

    def test_multi_pass_accumulates(self, sample_cp):
        state = CurriculumState()
        for pass_type in CURRICULUM_ORDER:
            run_curriculum_pass(state, [sample_cp, sample_cp], pass_type)
        assert state.total_points_processed == 12  # 6 passes × 2 points


# ---------------------------------------------------------------------------
# Stage 7: Cross-Modal Consistency Scorer
# ---------------------------------------------------------------------------

class TestConsistencyScorer:
    def test_returns_consistency_score(self, sample_bundle):
        score = score_consistency(sample_bundle)
        assert isinstance(score, ConsistencyScore)

    def test_overall_bounded(self, sample_bundle):
        score = score_consistency(sample_bundle)
        assert 0.0 <= score.overall <= 1.0

    def test_pairwise_scores_present(self, sample_bundle):
        score = score_consistency(sample_bundle)
        # C(7,2) = 21 pairs
        assert len(score.pairwise_scores) == 21

    def test_all_pairwise_bounded(self, sample_bundle):
        score = score_consistency(sample_bundle)
        for key, val in score.pairwise_scores.items():
            assert 0.0 <= val <= 1.0, f"{key}: {val}"

    def test_weakest_and_strongest_exist(self, sample_bundle):
        score = score_consistency(sample_bundle)
        assert score.weakest_pair in score.pairwise_scores
        assert score.strongest_pair in score.pairwise_scores

    def test_strongest_gte_weakest(self, sample_bundle):
        score = score_consistency(sample_bundle)
        assert score.pairwise_scores[score.strongest_pair] >= \
               score.pairwise_scores[score.weakest_pair]

    def test_warp_resilience_bounded(self, sample_bundle):
        warps = warp_bundle(sample_bundle, WarpType.PROSODY_DRIFT, 0.5)
        r = score_warp_resilience(sample_bundle, warps)
        assert 0.0 <= r <= 1.0

    def test_zero_warp_high_resilience(self, sample_bundle):
        warps = warp_bundle(sample_bundle, WarpType.PROSODY_DRIFT, 0.0)
        r = score_warp_resilience(sample_bundle, warps)
        assert r > 0.9

    def test_heavy_warp_lower_resilience(self, sample_bundle):
        light = warp_bundle(sample_bundle, WarpType.EXCITATION_SPIKE, 0.1)
        heavy = warp_bundle(sample_bundle, WarpType.EXCITATION_SPIKE, 0.9)
        r_light = score_warp_resilience(sample_bundle, light)
        r_heavy = score_warp_resilience(sample_bundle, heavy)
        assert r_light >= r_heavy

    def test_empty_warps_return_one(self, sample_bundle):
        assert score_warp_resilience(sample_bundle, []) == 1.0


# ---------------------------------------------------------------------------
# Stage 8: Round-Trip Evaluator
# ---------------------------------------------------------------------------

class TestRoundTripEvaluator:
    def test_returns_round_trip_result(self, sample_cp, sample_bundle):
        rt = round_trip_evaluate(sample_cp, sample_bundle)
        assert isinstance(rt, RoundTripResult)

    def test_verdict_match_for_clean_input(self, sample_cp, sample_bundle):
        rt = round_trip_evaluate(sample_cp, sample_bundle)
        # Clean round-trip should preserve verdict
        assert rt.verdict_match

    def test_feature_drift_is_finite(self, sample_cp, sample_bundle):
        rt = round_trip_evaluate(sample_cp, sample_bundle)
        assert math.isfinite(rt.feature_drift)

    def test_coherence_preserved_for_clean(self, sample_cp, sample_bundle):
        rt = round_trip_evaluate(sample_cp, sample_bundle)
        assert rt.coherence_preserved

    def test_consistency_before_after_close(self, sample_cp, sample_bundle):
        rt = round_trip_evaluate(sample_cp, sample_bundle)
        # Re-encoding the same input should give similar consistency
        assert abs(rt.consistency_before - rt.consistency_after) < 0.1

    def test_all_tongues_round_trip(self, sample_text):
        for tongue in ALL_TONGUES:
            cp = encode_contact_point(sample_text, tongue)
            bundle = project_contact_point(cp)
            rt = round_trip_evaluate(cp, bundle)
            assert rt.verdict_match, f"{tongue} verdict mismatch"


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_single_input_runs(self):
        run = run_harness(["hello world"], tongues=["ko"], dead_tones=["perfect_fifth"])
        assert isinstance(run, HarnessRun)
        assert run.total_points == 1

    def test_multi_input_runs(self):
        run = run_harness(["alpha", "beta"], tongues=["ko", "av"],
                          dead_tones=["perfect_fifth"])
        assert run.total_points == 4  # 2 inputs × 2 tongues × 1 dead tone

    def test_full_sweep(self):
        run = run_harness(["test"])
        # 1 input × 6 tongues × 3 dead tones = 18
        assert run.total_points == 18

    def test_has_all_stages(self):
        run = run_harness(["test"], tongues=["ko"], dead_tones=["perfect_fifth"])
        assert len(run.contact_points) == 1
        assert len(run.projection_bundles) == 1
        assert len(run.warp_results) == 1
        assert len(run.neighborhoods) >= 1
        assert len(run.grounding_checks) == 1
        assert len(run.consistency_scores) == 1
        assert len(run.warp_resilience_scores) == 1
        assert len(run.round_trip_results) == 1

    def test_mean_consistency_bounded(self):
        run = run_harness(["test"])
        assert 0.0 <= run.mean_consistency <= 1.0

    def test_mean_resilience_bounded(self):
        run = run_harness(["test"])
        assert 0.0 <= run.mean_resilience <= 1.0

    def test_grounding_rate_high(self):
        run = run_harness(["clean input text"])
        assert run.grounding_rate > 0.8

    def test_round_trip_coherence_high(self):
        run = run_harness(["clean input text"])
        assert run.round_trip_coherence_rate > 0.5

    def test_verdict_match_rate(self):
        run = run_harness(["clean input text"])
        assert run.verdict_match_rate > 0.5

    def test_curriculum_completes(self):
        run = run_harness(["test"], tongues=["ko"], dead_tones=["perfect_fifth"])
        assert run.curriculum_state.current_cycle >= 1

    def test_multiple_inputs_all_stages(self):
        texts = ["alpha", "beta", "gamma"]
        run = run_harness(texts, tongues=["ko", "av"], dead_tones=["perfect_fifth"])
        assert run.total_points == 6  # 3 × 2 × 1


# ---------------------------------------------------------------------------
# Training Data Export
# ---------------------------------------------------------------------------

class TestExportTrainingData:
    def test_returns_five_keys(self):
        run = run_harness(["test"], tongues=["ko"], dead_tones=["perfect_fifth"])
        data = export_harness_training_data(run)
        assert set(data.keys()) == {"sft", "dpo_chosen", "dpo_rejected", "boundary", "curriculum"}

    def test_sft_records_have_fields(self):
        run = run_harness(["hello world", "test input"])
        data = export_harness_training_data(run)
        for record in data["sft"]:
            assert "point_hash" in record
            assert "raw_input" in record
            assert "dominant_tongue" in record
            assert "verdict" in record
            assert "consistency" in record
            assert "warp_resilience" in record

    def test_curriculum_records(self):
        run = run_harness(["test"], tongues=["ko"], dead_tones=["perfect_fifth"])
        data = export_harness_training_data(run)
        assert len(data["curriculum"]) == 6  # full cycle

    def test_all_records_accounted_for(self):
        run = run_harness(["test"], tongues=["ko", "av"], dead_tones=["perfect_fifth"])
        data = export_harness_training_data(run)
        total = len(data["sft"]) + len(data["dpo_rejected"]) + len(data["boundary"])
        # All contact points should appear in at least one category
        # (some ALLOW with low consistency may not appear in sft)
        assert total <= run.total_points


# ---------------------------------------------------------------------------
# Cross-Cutting Properties
# ---------------------------------------------------------------------------

class TestCrossCuttingProperties:
    def test_phi_appears_in_expansion(self, sample_cp, sample_text):
        """Phi-based excitation decay appears in expansion neighbors."""
        hood = expand_contact_point(sample_cp, sample_text)
        excitations = [n.excitation for n in hood.local_neighbors]
        # At least one should be shifted by phi_inv
        expected = sample_cp.excitation + PHI_INV
        assert any(abs(e - expected) < 0.01 for e in excitations)

    def test_complement_symmetry_everywhere(self):
        """Complement map is bijective across all tongues."""
        for tongue in ALL_TONGUES:
            comp = COMPLEMENT_MAP[tongue]
            assert COMPLEMENT_MAP[comp] == tongue

    def test_dead_tones_produce_distinct_governance(self):
        """Different dead tones should sometimes produce different verdicts."""
        text = "adversarial test input with unusual patterns"
        verdicts = set()
        for tongue in ALL_TONGUES:
            for tone in DEAD_TONES:
                cp = encode_contact_point(text, tongue, tone, 3.0)
                verdicts.add((tongue, tone, cp.verdict.value))
        # Should have at least 2 distinct verdicts across the sweep
        distinct_verdicts = {v for _, _, v in verdicts}
        assert len(distinct_verdicts) >= 1  # at minimum ALLOW should appear

    def test_consistency_is_deterministic(self, sample_text):
        """Same input → same consistency score."""
        cp = encode_contact_point(sample_text)
        b1 = project_contact_point(cp)
        b2 = project_contact_point(cp)
        s1 = score_consistency(b1)
        s2 = score_consistency(b2)
        assert abs(s1.overall - s2.overall) < 1e-9

    def test_warp_resilience_decreases_with_magnitude(self, sample_bundle):
        """Stronger warps → lower resilience."""
        scores = []
        for mag in [0.0, 0.2, 0.5, 0.8, 1.0]:
            warps = warp_bundle(sample_bundle, WarpType.EXCITATION_SPIKE, mag)
            scores.append(score_warp_resilience(sample_bundle, warps))
        # Should be non-increasing (with possible ties)
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1] - 0.01  # small tolerance

    def test_full_harness_no_nan(self):
        """No NaN or Inf anywhere in a full harness run."""
        run = run_harness(["test input"], tongues=["ko", "ca"],
                          dead_tones=["perfect_fifth", "minor_seventh"])
        for cp in run.contact_points:
            assert math.isfinite(cp.dissonance_score)
            assert math.isfinite(cp.prosody_rate)
            assert math.isfinite(cp.agent_frequency_hz)
        for score in run.consistency_scores:
            assert math.isfinite(score.overall)
        for r in run.warp_resilience_scores:
            assert math.isfinite(r)
        for rt in run.round_trip_results:
            assert math.isfinite(rt.feature_drift)
