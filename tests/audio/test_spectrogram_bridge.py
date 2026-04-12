"""
Tests for Spectrogram Bridge — Raw Audio → Gallery Color Field Projection
==========================================================================

Covers:
    - Synthetic signal generation (sinusoid sums)
    - STFT computation (magnitudes, shape, frequency bins)
    - Tongue band energy distribution for known frequencies
    - Spectral centroid and HF ratio
    - Frequency-to-hue mapping (log scale, inverse of gallery sonifier)
    - Energy-to-chroma mapping (sqrt scaling)
    - Centroid-to-lightness mapping
    - Gallery projection from frames
    - Dead tone detection in synthesized spectra
    - Cross-modal alignment (audio ↔ text color field)
    - Tongue material mapping completeness
    - Edge cases: silence, single tone, broadband
"""

import math
import sys

sys.path.insert(0, ".")

import numpy as np

from src.audio.spectrogram_bridge import (
    # Constants
    TONGUE_FREQ_BANDS,
    TONGUE_ORDER,
    GALLERY_FREQ_MIN,
    GALLERY_FREQ_MAX,
    DEFAULT_FFT_SIZE,
    DEFAULT_HOP_SIZE,
    DEAD_TONE_RATIOS,
    _TONGUE_MATERIAL,
    # Core functions
    compute_stft,
    bin_to_hz,
    tongue_band_energy,
    spectral_centroid,
    hf_ratio,
    freq_to_hue,
    energy_to_chroma,
    centroid_to_lightness,
    project_frame_to_gallery,
    project_analysis_to_gallery,
    generate_test_signal,
    detect_dead_tones_in_spectrum,
    audio_text_alignment,
    # Data structures
    SpectrogramFrame,
    SpectrogramAnalysis,
    GalleryProjection,
)


# ===========================================================================
# Synthetic Signal Generator
# ===========================================================================

class TestGenerateTestSignal:
    """Verify synthetic signal generation."""

    def test_default_440hz(self):
        sr, sig = generate_test_signal()
        assert sr == 44100
        assert len(sig) == 44100  # 1 second

    def test_custom_duration(self):
        sr, sig = generate_test_signal(duration_sec=0.5, sample_rate=22050)
        assert sr == 22050
        assert len(sig) == 11025

    def test_normalized_to_unit(self):
        sr, sig = generate_test_signal(frequencies=[200.0, 5000.0])
        assert np.max(np.abs(sig)) <= 1.0 + 1e-9

    def test_multiple_frequencies(self):
        sr, sig = generate_test_signal(frequencies=[100.0, 1000.0, 5000.0])
        # Signal should not be all zeros
        assert np.max(np.abs(sig)) > 0.5

    def test_custom_amplitudes(self):
        sr, sig = generate_test_signal(
            frequencies=[440.0, 880.0],
            amplitudes=[1.0, 0.5],
        )
        assert len(sig) == 44100

    def test_zero_duration_edge(self):
        """Zero duration produces empty signal; normalization raises on empty array."""
        import pytest
        with pytest.raises(ValueError):
            generate_test_signal(duration_sec=0.0)


# ===========================================================================
# STFT Computation
# ===========================================================================

class TestComputeSTFT:
    """STFT produces correct shapes and non-negative magnitudes."""

    def test_shape_default(self):
        _, sig = generate_test_signal(duration_sec=1.0)
        mags, bins = compute_stft(sig)
        assert mags.ndim == 2
        assert mags.shape[1] == DEFAULT_FFT_SIZE // 2 + 1  # rfft bins
        assert mags.shape[0] > 0

    def test_magnitudes_non_negative(self):
        _, sig = generate_test_signal()
        mags, _ = compute_stft(sig)
        assert np.all(mags >= 0)

    def test_bin_count_matches_fft_size(self):
        fft_size = 1024
        _, sig = generate_test_signal()
        mags, bins = compute_stft(sig, fft_size=fft_size)
        assert mags.shape[1] == fft_size // 2 + 1
        assert len(bins) == fft_size // 2 + 1

    def test_more_frames_with_smaller_hop(self):
        _, sig = generate_test_signal(duration_sec=1.0)
        mags_big, _ = compute_stft(sig, hop_size=1024)
        mags_small, _ = compute_stft(sig, hop_size=256)
        assert mags_small.shape[0] > mags_big.shape[0]

    def test_hamming_window(self):
        _, sig = generate_test_signal()
        mags, _ = compute_stft(sig, window="hamming")
        assert mags.shape[0] > 0

    def test_rectangular_window(self):
        _, sig = generate_test_signal()
        mags, _ = compute_stft(sig, window="rectangular")
        assert mags.shape[0] > 0


# ===========================================================================
# Bin to Hz Conversion
# ===========================================================================

class TestBinToHz:
    """FFT bin index → frequency conversion."""

    def test_dc_bin_is_zero(self):
        bins = np.array([0])
        hz = bin_to_hz(bins, 44100, 2048)
        assert hz[0] == 0.0

    def test_nyquist_bin(self):
        fft_size = 2048
        bins = np.array([fft_size // 2])
        hz = bin_to_hz(bins, 44100, fft_size)
        assert abs(hz[0] - 22050.0) < 1.0

    def test_known_frequency(self):
        # Bin 10 at sr=44100, fft=2048 → 10 * 44100/2048 ≈ 215.3 Hz
        bins = np.array([10])
        hz = bin_to_hz(bins, 44100, 2048)
        assert abs(hz[0] - 215.33) < 0.1


# ===========================================================================
# Tongue Band Energy
# ===========================================================================

class TestTongueBandEnergy:
    """Frequency bands correctly attribute energy to tongues."""

    def _make_spectrum(self, target_freq: float, sr: int = 44100, fft_size: int = 2048):
        """Create a magnitude spectrum peaked at target_freq."""
        n_bins = fft_size // 2 + 1
        freq_hz = np.arange(n_bins) * sr / fft_size
        mags = np.zeros(n_bins)
        # Place energy in a narrow band around target
        mask = (freq_hz >= target_freq * 0.9) & (freq_hz <= target_freq * 1.1)
        mags[mask] = 1.0
        return mags, freq_hz

    def test_low_freq_goes_to_dr(self):
        mags, freqs = self._make_spectrum(80.0)  # 80 Hz → DR band (20-150)
        energies = tongue_band_energy(mags, freqs)
        assert energies["dr"] > 0.5, f"DR should dominate at 80Hz, got {energies}"

    def test_mid_freq_goes_to_ru(self):
        mags, freqs = self._make_spectrum(700.0)  # 700 Hz → RU band (400-1000)
        energies = tongue_band_energy(mags, freqs)
        assert energies["ru"] > 0.5, f"RU should dominate at 700Hz, got {energies}"

    def test_voice_freq_goes_to_ko(self):
        mags, freqs = self._make_spectrum(1500.0)  # 1500 Hz → KO band (1000-2500)
        energies = tongue_band_energy(mags, freqs)
        assert energies["ko"] > 0.5, f"KO should dominate at 1500Hz, got {energies}"

    def test_high_freq_goes_to_av(self):
        mags, freqs = self._make_spectrum(4000.0)  # 4000 Hz → AV band (2500-6000)
        energies = tongue_band_energy(mags, freqs)
        assert energies["av"] > 0.5, f"AV should dominate at 4000Hz, got {energies}"

    def test_ultra_high_goes_to_ca(self):
        mags, freqs = self._make_spectrum(10000.0)  # 10 kHz → CA band (6000-20000)
        energies = tongue_band_energy(mags, freqs)
        assert energies["ca"] > 0.5, f"CA should dominate at 10kHz, got {energies}"

    def test_wind_hum_goes_to_um(self):
        mags, freqs = self._make_spectrum(250.0)  # 250 Hz → UM band (150-400)
        energies = tongue_band_energy(mags, freqs)
        assert energies["um"] > 0.5, f"UM should dominate at 250Hz, got {energies}"

    def test_all_tongues_present(self):
        mags, freqs = self._make_spectrum(700.0)
        energies = tongue_band_energy(mags, freqs)
        assert set(energies.keys()) == set(TONGUE_FREQ_BANDS.keys())

    def test_energies_sum_to_roughly_one(self):
        """Tongue energies should approximately sum to 1 (normalized)."""
        mags, freqs = self._make_spectrum(700.0)
        energies = tongue_band_energy(mags, freqs)
        total = sum(energies.values())
        # May not be exactly 1 if some energy falls outside all bands
        assert 0.5 <= total <= 1.1, f"Tongue energy total: {total}"

    def test_silence_yields_tiny_values(self):
        n_bins = 1025
        freq_hz = np.arange(n_bins) * 44100.0 / 2048
        mags = np.zeros(n_bins)
        energies = tongue_band_energy(mags, freq_hz)
        for v in energies.values():
            assert v < 0.01


# ===========================================================================
# Spectral Centroid and HF Ratio
# ===========================================================================

class TestSpectralCentroid:
    """Weighted mean frequency computation."""

    def test_single_peak(self):
        freqs = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        mags = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
        c = spectral_centroid(mags, freqs)
        assert abs(c - 300.0) < 1.0

    def test_two_equal_peaks(self):
        freqs = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        mags = np.array([1.0, 0.0, 0.0, 0.0, 1.0])
        c = spectral_centroid(mags, freqs)
        assert abs(c - 300.0) < 1.0  # mean of 100 and 500

    def test_higher_peak_pulls_centroid(self):
        freqs = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        mags = np.array([0.1, 0.0, 0.0, 0.0, 0.9])
        c = spectral_centroid(mags, freqs)
        assert c > 400.0  # pulled toward 500


class TestHFRatio:
    """High-frequency energy fraction."""

    def test_all_low_freq(self):
        freqs = np.array([100.0, 500.0, 1000.0, 2000.0])
        mags = np.array([1.0, 1.0, 1.0, 1.0])
        r = hf_ratio(mags, freqs, cutoff=2500.0)
        assert r < 0.01

    def test_all_high_freq(self):
        freqs = np.array([3000.0, 5000.0, 8000.0, 12000.0])
        mags = np.array([1.0, 1.0, 1.0, 1.0])
        r = hf_ratio(mags, freqs, cutoff=2500.0)
        assert r > 0.99

    def test_mixed(self):
        freqs = np.array([500.0, 1000.0, 3000.0, 5000.0])
        mags = np.array([1.0, 1.0, 1.0, 1.0])
        r = hf_ratio(mags, freqs, cutoff=2500.0)
        assert 0.3 < r < 0.7


# ===========================================================================
# Gallery Projection Functions
# ===========================================================================

class TestFreqToHue:
    """Frequency → hue angle (log scale)."""

    def test_min_freq_maps_to_zero(self):
        assert abs(freq_to_hue(GALLERY_FREQ_MIN) - 0.0) < 0.01

    def test_max_freq_maps_to_360(self):
        assert abs(freq_to_hue(GALLERY_FREQ_MAX) - 360.0) < 0.01

    def test_clamps_below_min(self):
        h = freq_to_hue(10.0)  # way below 100 Hz
        assert abs(h - 0.0) < 0.01

    def test_clamps_above_max(self):
        h = freq_to_hue(50000.0)  # way above 4000 Hz
        assert abs(h - 360.0) < 0.01

    def test_monotonically_increasing(self):
        freqs = [100, 200, 500, 1000, 2000, 4000]
        hues = [freq_to_hue(f) for f in freqs]
        for i in range(len(hues) - 1):
            assert hues[i] < hues[i + 1]

    def test_log_scale_equidistant_ratios(self):
        """Equal frequency ratios should produce equal hue distances."""
        h1 = freq_to_hue(200)
        h2 = freq_to_hue(400)
        h3 = freq_to_hue(800)
        gap_a = h2 - h1
        gap_b = h3 - h2
        assert abs(gap_a - gap_b) < 1.0  # should be roughly equal


class TestEnergyToChroma:
    """Energy → CIELAB chroma (sqrt scaling)."""

    def test_zero_energy(self):
        assert energy_to_chroma(0.0) == 0.0

    def test_max_energy(self):
        assert abs(energy_to_chroma(1.0, max_energy=1.0) - 130.0) < 0.01

    def test_sqrt_scaling(self):
        """Quarter energy → half chroma (sqrt relationship)."""
        c = energy_to_chroma(0.25, max_energy=1.0)
        assert abs(c - 65.0) < 0.5

    def test_clamped_above_max(self):
        c = energy_to_chroma(10.0, max_energy=1.0)
        assert c <= 130.0


class TestCentroidToLightness:
    """Spectral centroid → CIELAB lightness."""

    def test_low_centroid_low_lightness(self):
        L = centroid_to_lightness(GALLERY_FREQ_MIN)
        assert 18.0 <= L <= 22.0

    def test_high_centroid_high_lightness(self):
        L = centroid_to_lightness(GALLERY_FREQ_MAX)
        assert 78.0 <= L <= 82.0

    def test_mid_range(self):
        L = centroid_to_lightness(500.0)
        assert 20.0 < L < 80.0


# ===========================================================================
# Gallery Projection from Frames
# ===========================================================================

class TestProjectFrameToGallery:
    """Frame → GalleryProjection mapping."""

    def _make_frame(self, centroid=1000.0, energy=0.5, tongue="ko"):
        return SpectrogramFrame(
            time_sec=0.0,
            frequencies=np.array([]),
            magnitudes=np.array([]),
            tongue_energies={t: 0.0 for t in TONGUE_ORDER},
            dominant_tongue=tongue,
            total_energy=energy,
            spectral_centroid=centroid,
            hf_ratio=0.3,
        )

    def test_valid_projection(self):
        frame = self._make_frame()
        proj = project_frame_to_gallery(frame)
        assert 0.0 <= proj.hue_degrees <= 360.0
        assert 0.0 <= proj.chroma <= 130.0
        assert 0.0 <= proj.lightness <= 100.0

    def test_tongue_material_mapping(self):
        for tongue, expected_mat in _TONGUE_MATERIAL.items():
            frame = self._make_frame(tongue=tongue)
            proj = project_frame_to_gallery(frame)
            assert proj.material == expected_mat, f"{tongue} → {proj.material}, expected {expected_mat}"
            assert proj.tongue == tongue

    def test_higher_centroid_higher_hue(self):
        low = project_frame_to_gallery(self._make_frame(centroid=200.0))
        high = project_frame_to_gallery(self._make_frame(centroid=3000.0))
        assert high.hue_degrees > low.hue_degrees

    def test_higher_energy_higher_chroma(self):
        low = project_frame_to_gallery(self._make_frame(energy=0.1))
        high = project_frame_to_gallery(self._make_frame(energy=2.0))
        assert high.chroma > low.chroma

    def test_time_preserved(self):
        frame = self._make_frame()
        frame.time_sec = 1.234
        proj = project_frame_to_gallery(frame)
        assert proj.time_sec == 1.234


# ===========================================================================
# Tongue Material Mapping
# ===========================================================================

class TestTongueMaterialMapping:
    """All 6 tongues have a material assignment."""

    def test_all_tongues_mapped(self):
        for tongue in TONGUE_ORDER:
            assert tongue in _TONGUE_MATERIAL

    def test_materials_are_valid(self):
        valid = {"matte", "fluorescent", "neon", "metallic"}
        for mat in _TONGUE_MATERIAL.values():
            assert mat in valid


# ===========================================================================
# Dead Tone Detection
# ===========================================================================

class TestDeadToneDetection:
    """Dead tone frequency ratio detection in spectra."""

    def _make_two_peaks(self, f1, f2, sr=44100, fft_size=4096):
        """Create magnitude spectrum with two broad peaks for find_peaks detection."""
        n_bins = fft_size // 2 + 1
        freq_hz = np.arange(n_bins) * sr / fft_size
        mags = np.zeros(n_bins)
        # Build Gaussian-like peaks (width ~8 bins) so find_peaks can detect them
        for f in [f1, f2]:
            center = int(round(f * fft_size / sr))
            for offset in range(-8, 9):
                idx = center + offset
                if 0 <= idx < n_bins:
                    mags[idx] += math.exp(-0.5 * (offset / 2.5) ** 2)
        return mags, freq_hz

    def test_perfect_fifth_detected(self):
        """Two tones at 3:2 ratio should detect perfect fifth."""
        mags, freqs = self._make_two_peaks(440.0, 660.0)  # 660/440 = 1.5
        det = detect_dead_tones_in_spectrum(mags, freqs)
        assert det["perfect_fifth"] > 0.3, f"Perfect fifth not detected: {det}"

    def test_minor_sixth_detected(self):
        """Two tones at 8:5 ratio should detect minor sixth."""
        mags, freqs = self._make_two_peaks(500.0, 800.0)  # 800/500 = 1.6
        det = detect_dead_tones_in_spectrum(mags, freqs)
        assert det["minor_sixth"] > 0.3, f"Minor sixth not detected: {det}"

    def test_silence_no_detection(self):
        n_bins = 1025
        freq_hz = np.arange(n_bins) * 44100.0 / 2048
        mags = np.zeros(n_bins)
        det = detect_dead_tones_in_spectrum(mags, freq_hz)
        for v in det.values():
            assert v == 0.0

    def test_all_dead_tones_returned(self):
        mags, freqs = self._make_two_peaks(440.0, 660.0)
        det = detect_dead_tones_in_spectrum(mags, freqs)
        assert set(det.keys()) == set(DEAD_TONE_RATIOS.keys())


# ===========================================================================
# Cross-Modal Alignment
# ===========================================================================

class TestAudioTextAlignment:
    """Audio ↔ text color field cosine similarity."""

    def _make_analysis(self, tongue_profile):
        return SpectrogramAnalysis(
            filename="test.wav",
            sample_rate=44100,
            duration_sec=1.0,
            n_frames=10,
            fft_size=2048,
            hop_size=512,
            frames=[],
            tongue_profile=tongue_profile,
            dominant_tongue=max(tongue_profile, key=tongue_profile.get),
        )

    def _make_text_color_dict(self, dominant_tongue="ko"):
        return {
            "left_iris": {
                "dominant_tongue": dominant_tongue,
                "chords": {
                    "perfect_fifth": {"mean_chroma": 50.0},
                    "minor_sixth": {"mean_chroma": 30.0},
                    "minor_seventh": {"mean_chroma": 20.0},
                },
            }
        }

    def test_alignment_bounded(self):
        profile = {t: 1.0 / 6 for t in TONGUE_ORDER}
        analysis = self._make_analysis(profile)
        text = self._make_text_color_dict()
        score = audio_text_alignment(analysis, text)
        assert 0.0 <= score <= 1.0

    def test_same_tongue_higher_alignment(self):
        """Audio dominated by KO should align better with KO-dominant text."""
        ko_profile = {"ko": 0.7, "av": 0.1, "ru": 0.05, "ca": 0.05, "um": 0.05, "dr": 0.05}
        dr_profile = {"ko": 0.05, "av": 0.05, "ru": 0.05, "ca": 0.05, "um": 0.05, "dr": 0.75}
        ko_analysis = self._make_analysis(ko_profile)
        dr_analysis = self._make_analysis(dr_profile)
        text = self._make_text_color_dict(dominant_tongue="ko")
        score_ko = audio_text_alignment(ko_analysis, text)
        score_dr = audio_text_alignment(dr_analysis, text)
        assert score_ko > score_dr, f"KO={score_ko} should beat DR={score_dr}"

    def test_empty_text_dict(self):
        """Graceful handling of missing text color fields."""
        profile = {t: 1.0 / 6 for t in TONGUE_ORDER}
        analysis = self._make_analysis(profile)
        score = audio_text_alignment(analysis, {})
        assert 0.0 <= score <= 1.0


# ===========================================================================
# SpectrogramAnalysis Properties
# ===========================================================================

class TestSpectrogramAnalysisProperties:
    """Analysis dataclass properties and serialization."""

    def test_frame_rate(self):
        a = SpectrogramAnalysis(
            filename="test.wav", sample_rate=44100, duration_sec=1.0,
            n_frames=86, fft_size=2048, hop_size=512, frames=[],
        )
        expected = 44100 / 512
        assert abs(a.frame_rate - expected) < 0.1

    def test_to_dict_keys(self):
        a = SpectrogramAnalysis(
            filename="test.wav", sample_rate=44100, duration_sec=1.0,
            n_frames=86, fft_size=2048, hop_size=512, frames=[],
            tongue_profile={"ko": 0.2, "av": 0.2, "ru": 0.15, "ca": 0.15, "um": 0.15, "dr": 0.15},
            dominant_tongue="ko",
            mean_centroid=1200.0,
            mean_hf_ratio=0.25,
        )
        d = a.to_dict()
        assert "filename" in d
        assert "tongue_profile" in d
        assert "dominant_tongue" in d
        assert d["dominant_tongue"] == "ko"
        assert d["sample_rate"] == 44100


# ===========================================================================
# Integration: Synthetic Signal → Full Pipeline
# ===========================================================================

class TestFullPipelineSynthetic:
    """End-to-end: generate signal → STFT → tongue analysis → gallery projection."""

    def test_440hz_pipeline(self):
        """440 Hz tone should land in RU band (400-1000 Hz)."""
        sr, sig = generate_test_signal(frequencies=[440.0], duration_sec=0.5)
        mags, bins = compute_stft(sig, fft_size=2048, hop_size=512)
        freq_hz = bin_to_hz(bins, sr, 2048)

        # Check a middle frame
        mid = mags.shape[0] // 2
        energies = tongue_band_energy(mags[mid], freq_hz)
        assert energies["ru"] > 0.3, f"440Hz should be RU-dominant: {energies}"

    def test_100hz_pipeline(self):
        """100 Hz tone should land in DR band (20-150 Hz)."""
        sr, sig = generate_test_signal(frequencies=[100.0], duration_sec=0.5)
        mags, bins = compute_stft(sig, fft_size=4096, hop_size=512)
        freq_hz = bin_to_hz(bins, sr, 4096)

        mid = mags.shape[0] // 2
        energies = tongue_band_energy(mags[mid], freq_hz)
        assert energies["dr"] > 0.3, f"100Hz should be DR-dominant: {energies}"

    def test_8000hz_pipeline(self):
        """8 kHz tone should land in CA band (6000-20000 Hz)."""
        sr, sig = generate_test_signal(frequencies=[8000.0], duration_sec=0.5)
        mags, bins = compute_stft(sig, fft_size=2048, hop_size=512)
        freq_hz = bin_to_hz(bins, sr, 2048)

        mid = mags.shape[0] // 2
        energies = tongue_band_energy(mags[mid], freq_hz)
        assert energies["ca"] > 0.3, f"8kHz should be CA-dominant: {energies}"

    def test_gallery_projection_from_synthetic(self):
        """Full signal → frame → gallery projection path."""
        sr, sig = generate_test_signal(frequencies=[1500.0], duration_sec=0.5)
        mags, bins = compute_stft(sig, fft_size=2048, hop_size=512)
        freq_hz = bin_to_hz(bins, sr, 2048)

        mid = mags.shape[0] // 2
        energies = tongue_band_energy(mags[mid], freq_hz)
        dominant = max(energies, key=energies.get)
        cent = spectral_centroid(mags[mid], freq_hz)
        total_e = float(np.sum(mags[mid] ** 2))

        frame = SpectrogramFrame(
            time_sec=0.25,
            frequencies=freq_hz,
            magnitudes=mags[mid],
            tongue_energies=energies,
            dominant_tongue=dominant,
            total_energy=total_e,
            spectral_centroid=cent,
            hf_ratio=hf_ratio(mags[mid], freq_hz),
        )
        proj = project_frame_to_gallery(frame)
        assert 0.0 <= proj.hue_degrees <= 360.0
        assert 0.0 <= proj.chroma <= 130.0
        assert 20.0 <= proj.lightness <= 80.0
        assert proj.material in {"matte", "fluorescent", "neon", "metallic"}

    def test_multi_tone_broadband(self):
        """Signal with tones spanning multiple bands produces mixed tongue profile."""
        freqs = [80.0, 300.0, 700.0, 1500.0, 4000.0, 10000.0]
        sr, sig = generate_test_signal(frequencies=freqs, duration_sec=0.5)
        mags, bins = compute_stft(sig, fft_size=4096, hop_size=512)
        freq_hz = bin_to_hz(bins, sr, 4096)

        mid = mags.shape[0] // 2
        energies = tongue_band_energy(mags[mid], freq_hz)
        # At least 3 tongues should have meaningful energy
        active = sum(1 for v in energies.values() if v > 0.05)
        assert active >= 3, f"Only {active} tongues active in broadband signal: {energies}"


# ===========================================================================
# Constants Consistency
# ===========================================================================

class TestConstants:
    """Verify constants are consistent and complete."""

    def test_tongue_order_matches_bands(self):
        assert set(TONGUE_ORDER) == set(TONGUE_FREQ_BANDS.keys())

    def test_bands_contiguous(self):
        """Frequency bands should be contiguous (no gaps)."""
        sorted_bands = sorted(TONGUE_FREQ_BANDS.values(), key=lambda x: x[0])
        for i in range(len(sorted_bands) - 1):
            assert sorted_bands[i][1] == sorted_bands[i + 1][0], \
                f"Gap between {sorted_bands[i]} and {sorted_bands[i+1]}"

    def test_bands_cover_audible_range(self):
        sorted_bands = sorted(TONGUE_FREQ_BANDS.values(), key=lambda x: x[0])
        assert sorted_bands[0][0] == 20.0  # starts at 20 Hz
        assert sorted_bands[-1][1] == 20000.0  # ends at 20 kHz

    def test_dead_tone_ratios_correct(self):
        assert abs(DEAD_TONE_RATIOS["perfect_fifth"] - 1.5) < 0.001
        assert abs(DEAD_TONE_RATIOS["minor_sixth"] - 1.6) < 0.001
        assert abs(DEAD_TONE_RATIOS["minor_seventh"] - 16.0/9.0) < 0.001

    def test_tongue_material_all_six(self):
        assert set(_TONGUE_MATERIAL.keys()) == set(TONGUE_ORDER)
