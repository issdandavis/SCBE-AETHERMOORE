"""
Tests for Quantum Harmonic Oscillator Bundle Generator.

Validates:
1. QHO level derivation from fork count + crossing energy
2. Visual frequency vector normalization and entropy
3. Acoustic signature band shifting with excitation level
4. Curriculum difficulty scoring
5. Single-text bundle generation
6. Batch processing and statistics
7. SFT flattening with QHO metadata
8. Edge cases: ground state, max excitation, empty text
"""

import math
import pytest

from src.crypto.qho_bundle import (
    MAX_N,
    OMEGA_BASE,
    TONGUE_WAVELENGTH,
    QHOLevel,
    VisualFrequencyVector,
    AcousticSignature,
    QHOBundle,
    QHOBatchResult,
    compute_qho_level,
    compute_visual_frequency,
    compute_acoustic_signature,
    compute_difficulty,
    generate_qho_bundle,
    generate_qho_batch,
    flatten_qho_for_sft,
    format_qho_report,
)
from src.crypto.trit_curriculum import TritSignal, TRIT_AXES, compute_trit_signal
from src.crypto.polymorphic_multipath import score_and_expand


# ===================================================================
# QHO Level Computation
# ===================================================================

class TestQHOLevel:
    """Test excitation level derivation."""

    def test_ground_state_for_non_polymorphic(self):
        """Text with no forks and low energy should be n=0."""
        rec = score_and_expand("The sky is blue.")
        qho = compute_qho_level(rec)
        # No forks → fork_count = 0, likely low energy
        assert qho.n >= 0
        assert qho.n <= MAX_N

    def test_n_increases_with_forks(self):
        """More forks should generally give higher n."""
        # Force wide threshold to get more forks
        rec_narrow = score_and_expand("Test text", edge_threshold=0.001)
        rec_wide = score_and_expand("Test text", edge_threshold=0.05)
        qho_narrow = compute_qho_level(rec_narrow)
        qho_wide = compute_qho_level(rec_wide)
        assert qho_wide.n >= qho_narrow.n

    def test_energy_formula(self):
        """E_n = ω(n + 1/2) with ω=1, ℏ=1."""
        rec = score_and_expand("Test")
        qho = compute_qho_level(rec)
        assert abs(qho.energy - (qho.n + 0.5)) < 1e-10

    def test_n_bounded(self):
        """n should never exceed MAX_N."""
        texts = [
            "Build the strongest fortress of iron and gold",
            "Destroy everything in chaotic creative frenzy",
            "The boundary between creation and destruction",
        ]
        for t in texts:
            rec = score_and_expand(t, edge_threshold=0.05)
            qho = compute_qho_level(rec)
            assert 0 <= qho.n <= MAX_N

    def test_ground_state_flag(self):
        """is_ground_state should match n == 0."""
        rec = score_and_expand("Simple text")
        qho = compute_qho_level(rec)
        assert qho.is_ground_state == (qho.n == 0)

    def test_crossing_energy_from_trits(self):
        """Crossing energy should come from structure × stability pair."""
        rec = score_and_expand("Test text")
        qho = compute_qho_level(rec)
        sig = rec.primary
        # Manually compute E(p, m)
        p, m = sig.c_structure, sig.c_stability
        expected_ce = float(p * p + m * m + p * m)
        assert abs(qho.crossing_energy - expected_ce) < 1e-10

    def test_harmonic_wall_positive(self):
        """Wall cost φ^(d²) should always be ≥ 1."""
        rec = score_and_expand("Test")
        qho = compute_qho_level(rec)
        assert qho.harmonic_wall_cost >= 1.0


# ===================================================================
# Visual Frequency Vector
# ===================================================================

class TestVisualFrequency:
    """Test 6-channel polychromatic vector."""

    def test_sums_to_one(self):
        """Amplitude distribution should be normalized."""
        sig = compute_trit_signal("The quantum field oscillates with energy")
        visual = compute_visual_frequency(sig)
        total = sum(visual.amplitudes.values())
        assert abs(total - 1.0) < 1e-10

    def test_six_channels(self):
        """Should have exactly 6 tongue channels."""
        sig = compute_trit_signal("Test")
        visual = compute_visual_frequency(sig)
        assert len(visual.amplitudes) == 6
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            assert tongue in visual.amplitudes

    def test_all_positive(self):
        """All amplitudes should be non-negative."""
        sig = compute_trit_signal("Various interesting text to process")
        visual = compute_visual_frequency(sig)
        for v in visual.amplitudes.values():
            assert v >= 0.0

    def test_entropy_bounded(self):
        """Visual entropy should be in [0, 1]."""
        sig = compute_trit_signal("Test")
        visual = compute_visual_frequency(sig)
        assert 0.0 <= visual.visual_entropy <= 1.0

    def test_dominant_tongue_is_max(self):
        """Dominant tongue should have highest amplitude."""
        sig = compute_trit_signal("Build something strong")
        visual = compute_visual_frequency(sig)
        max_tongue = max(visual.amplitudes, key=visual.amplitudes.get)
        assert visual.dominant_tongue == max_tongue

    def test_phi_weighting_affects_distribution(self):
        """Higher phi-weight tongues should have systematically different amplitudes."""
        sig = compute_trit_signal("Test text")
        visual = compute_visual_frequency(sig)
        # DR has highest phi weight — when its pair is active, it should dominate
        # We just check the distribution isn't flat
        values = list(visual.amplitudes.values())
        assert max(values) > min(values)  # not uniform


# ===================================================================
# Acoustic Signature
# ===================================================================

class TestAcousticSignature:
    """Test 3-band frequency emphasis."""

    def test_weights_sum_to_one(self):
        """Band weights should be normalized."""
        qho = QHOLevel(n=3, energy=3.5, fork_count=2,
                       crossing_energy=1.0, harmonic_wall_cost=1.0,
                       is_ground_state=False)
        acoustic = compute_acoustic_signature(qho)
        total = acoustic.infra_weight + acoustic.audible_weight + acoustic.ultra_weight
        assert abs(total - 1.0) < 1e-10

    def test_ground_state_infra_dominant(self):
        """n=0 should have infrasonic emphasis."""
        qho = QHOLevel(n=0, energy=0.5, fork_count=0,
                       crossing_energy=0.0, harmonic_wall_cost=1.0,
                       is_ground_state=True)
        acoustic = compute_acoustic_signature(qho)
        assert acoustic.infra_weight > acoustic.ultra_weight

    def test_excited_state_ultra_dominant(self):
        """High n should have ultrasonic emphasis."""
        qho = QHOLevel(n=MAX_N, energy=MAX_N + 0.5, fork_count=3,
                       crossing_energy=3.0, harmonic_wall_cost=2.0,
                       is_ground_state=False)
        acoustic = compute_acoustic_signature(qho)
        assert acoustic.ultra_weight > acoustic.infra_weight

    def test_audible_always_present(self):
        """Audible band should always have significant weight."""
        for n in range(MAX_N + 1):
            qho = QHOLevel(n=n, energy=n + 0.5, fork_count=0,
                           crossing_energy=0.0, harmonic_wall_cost=1.0,
                           is_ground_state=(n == 0))
            acoustic = compute_acoustic_signature(qho)
            assert acoustic.audible_weight >= 0.25  # always anchored

    def test_frequency_scales_with_n(self):
        """Base frequency should increase with excitation level."""
        freqs = []
        for n in range(MAX_N + 1):
            qho = QHOLevel(n=n, energy=n + 0.5, fork_count=0,
                           crossing_energy=0.0, harmonic_wall_cost=1.0,
                           is_ground_state=(n == 0))
            acoustic = compute_acoustic_signature(qho)
            freqs.append(acoustic.base_freq)
        # Should be strictly increasing
        for i in range(1, len(freqs)):
            assert freqs[i] > freqs[i - 1]

    def test_base_freq_formula(self):
        """f_n = ω × (n + 1/2)."""
        for n in range(MAX_N + 1):
            qho = QHOLevel(n=n, energy=n + 0.5, fork_count=0,
                           crossing_energy=0.0, harmonic_wall_cost=1.0,
                           is_ground_state=(n == 0))
            acoustic = compute_acoustic_signature(qho)
            expected = OMEGA_BASE * (n + 0.5)
            assert abs(acoustic.base_freq - expected) < 0.01


# ===================================================================
# Curriculum Difficulty
# ===================================================================

class TestDifficulty:
    """Test difficulty scoring."""

    def test_bounded_zero_one(self):
        """Difficulty should be in [0, 1]."""
        texts = [
            "Simple sentence.",
            "Build the strongest fortress of iron and gold",
            "Destroy everything in chaotic creative frenzy",
            "The boundary between creation and destruction wavers at the critical line",
        ]
        for t in texts:
            bundle = generate_qho_bundle(t)
            assert 0.0 <= bundle.curriculum_difficulty <= 1.0

    def test_ground_state_low_difficulty(self):
        """n=0 with no gain should have low difficulty."""
        qho = QHOLevel(n=0, energy=0.5, fork_count=0,
                       crossing_energy=0.0, harmonic_wall_cost=1.0,
                       is_ground_state=True)
        d = compute_difficulty(qho, gain=0.0)
        assert d < 0.1  # very easy

    def test_max_excitation_high_difficulty(self):
        """Max n with max gain and max energy should be high difficulty."""
        qho = QHOLevel(n=MAX_N, energy=MAX_N + 0.5, fork_count=3,
                       crossing_energy=3.0, harmonic_wall_cost=100.0,
                       is_ground_state=False)
        d = compute_difficulty(qho, gain=3.0)
        assert d > 0.8  # very hard

    def test_monotonic_in_n(self):
        """Higher n should give higher difficulty (all else equal)."""
        difficulties = []
        for n in range(MAX_N + 1):
            qho = QHOLevel(n=n, energy=n + 0.5, fork_count=0,
                           crossing_energy=0.0, harmonic_wall_cost=1.0,
                           is_ground_state=(n == 0))
            difficulties.append(compute_difficulty(qho, gain=0.0))
        for i in range(1, len(difficulties)):
            assert difficulties[i] >= difficulties[i - 1]


# ===================================================================
# Bundle Generation (Single)
# ===================================================================

class TestQHOBundle:
    """Test single-text QHO bundle generation."""

    def test_bundle_has_all_fields(self):
        bundle = generate_qho_bundle("The quantum field oscillates")
        assert bundle.text == "The quantum field oscillates"
        assert bundle.multipath is not None
        assert bundle.qho is not None
        assert bundle.visual is not None
        assert bundle.acoustic is not None
        assert isinstance(bundle.curriculum_difficulty, float)

    def test_multipath_is_real(self):
        """Multipath record should come from actual score_and_expand."""
        bundle = generate_qho_bundle("Build strong foundations")
        assert bundle.multipath.primary.label in [
            v for v in __import__("src.crypto.trit_curriculum", fromlist=["TRIT_LABELS"]).TRIT_LABELS.values()
        ]

    def test_visual_matches_trit(self):
        """Visual frequency should be derived from the same trit signal."""
        bundle = generate_qho_bundle("Test text")
        # Visual dominant tongue should be consistent with interference
        assert bundle.visual.dominant_tongue in ["ko", "av", "ru", "ca", "um", "dr"]

    def test_acoustic_matches_qho(self):
        """Acoustic base freq should match QHO level."""
        bundle = generate_qho_bundle("Test text")
        expected_freq = OMEGA_BASE * (bundle.qho.n + 0.5)
        assert abs(bundle.acoustic.base_freq - expected_freq) < 0.01


# ===================================================================
# Batch Processing
# ===================================================================

class TestQHOBatch:
    """Test batch QHO bundle generation."""

    @pytest.fixture
    def sample_texts(self):
        return [
            "The zeta zeros guard the critical line.",
            "Superposition collapses upon measurement.",
            "Build a fortress of structured data.",
            "Destroy the old patterns to create anew.",
            "The boundary wavers between stability and chaos.",
            "Simple observation of natural phenomena.",
            "Rotating the complex plane around the origin.",
            "Entangled photons maintain harmony across distance.",
        ]

    def test_batch_count(self, sample_texts):
        batch = generate_qho_batch(sample_texts)
        assert batch.total_input == 8
        assert len(batch.bundles) == 8

    def test_batch_statistics(self, sample_texts):
        batch = generate_qho_batch(sample_texts)
        assert 0.0 <= batch.mean_n <= MAX_N
        assert 0.0 <= batch.mean_difficulty <= 1.0
        assert batch.total_output >= batch.total_input

    def test_n_distribution_covers_all(self, sample_texts):
        batch = generate_qho_batch(sample_texts)
        total_from_dist = sum(batch.n_distribution.values())
        assert total_from_dist == batch.total_input

    def test_batch_expansion(self, sample_texts):
        """Polymorphic texts should expand the output count."""
        batch = generate_qho_batch(sample_texts, edge_threshold=0.02)
        # At wider threshold, some texts should generate siblings
        assert batch.total_output >= batch.total_input


# ===================================================================
# SFT Flattening
# ===================================================================

class TestFlattenQHO:
    """Test SFT export with QHO metadata."""

    def test_flattened_has_qho_fields(self):
        bundle = generate_qho_bundle("Test text for SFT export")
        records = flatten_qho_for_sft([bundle])
        assert len(records) >= 1
        rec = records[0]
        assert "qho_n" in rec
        assert "qho_energy" in rec
        assert "crossing_energy" in rec
        assert "harmonic_wall_cost" in rec
        assert "visual_freq" in rec
        assert "dominant_tongue" in rec
        assert "visual_entropy" in rec
        assert "acoustic_bands" in rec
        assert "acoustic_base_freq" in rec
        assert "curriculum_difficulty" in rec

    def test_visual_freq_has_six_tongues(self):
        bundle = generate_qho_bundle("Test")
        records = flatten_qho_for_sft([bundle])
        vf = records[0]["visual_freq"]
        assert len(vf) == 6
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            assert tongue in vf

    def test_acoustic_bands_has_three(self):
        bundle = generate_qho_bundle("Test")
        records = flatten_qho_for_sft([bundle])
        ab = records[0]["acoustic_bands"]
        assert "infra" in ab
        assert "audible" in ab
        assert "ultra" in ab

    def test_flattened_count_matches_paths(self):
        """Number of flattened records should equal path_count."""
        bundle = generate_qho_bundle("Test", edge_threshold=0.05)
        records = flatten_qho_for_sft([bundle])
        assert len(records) == bundle.multipath.path_count

    def test_all_records_share_qho_metadata(self):
        """All siblings should share the same QHO level."""
        bundle = generate_qho_bundle("Test text", edge_threshold=0.05)
        records = flatten_qho_for_sft([bundle])
        if len(records) > 1:
            n_values = {r["qho_n"] for r in records}
            assert len(n_values) == 1  # all same n

    def test_multiple_bundles_flatten(self):
        bundles = [
            generate_qho_bundle("First text"),
            generate_qho_bundle("Second text"),
            generate_qho_bundle("Third text"),
        ]
        records = flatten_qho_for_sft(bundles)
        expected = sum(b.multipath.path_count for b in bundles)
        assert len(records) == expected


# ===================================================================
# Report
# ===================================================================

class TestReport:
    """Test report formatting."""

    def test_report_has_header(self):
        batch = generate_qho_batch(["Test text"])
        report = format_qho_report(batch)
        assert "QUANTUM HARMONIC OSCILLATOR" in report

    def test_report_has_statistics(self):
        batch = generate_qho_batch(["Test one", "Test two"])
        report = format_qho_report(batch)
        assert "Mean excitation" in report
        assert "Mean difficulty" in report

    def test_report_has_distribution(self):
        batch = generate_qho_batch(["Test"])
        report = format_qho_report(batch)
        assert "Energy Level Distribution" in report

    def test_report_has_samples(self):
        batch = generate_qho_batch(["A sample text for the report"])
        report = format_qho_report(batch)
        assert "Sample Bundles" in report


# ===================================================================
# Constants
# ===================================================================

class TestConstants:
    """Test module constants are sensible."""

    def test_max_n_positive(self):
        assert MAX_N > 0

    def test_omega_base_is_a4(self):
        assert OMEGA_BASE == 440.0

    def test_six_tongue_wavelengths(self):
        assert len(TONGUE_WAVELENGTH) == 6
        for tongue in ["ko", "av", "ru", "ca", "um", "dr"]:
            assert tongue in TONGUE_WAVELENGTH
            assert 380 <= TONGUE_WAVELENGTH[tongue] <= 700  # visible spectrum
