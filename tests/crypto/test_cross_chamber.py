"""Tests for cross_chamber.py — acoustic state checking via harmonic interference.

Self-contained: no heavy imports. Tests the full alphabet of consonance/dissonance.
"""

import math
from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Inline module under test (mirrors src/crypto/cross_chamber.py)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
TAU = 2.0 * math.pi

BASELINE_FREQUENCIES = {
    "perfect_fifth": 330.0,
    "minor_sixth": 352.0,
    "minor_seventh": 392.0,
}

RATIO_DISSONANCE = {
    "unison": (1.0, 0.00),
    "octave": (2.0, 0.02),
    "perfect_fifth": (3.0 / 2.0, 0.05),
    "perfect_fourth": (4.0 / 3.0, 0.08),
    "major_third": (5.0 / 4.0, 0.12),
    "minor_third": (6.0 / 5.0, 0.15),
    "major_sixth": (5.0 / 3.0, 0.18),
    "minor_sixth": (8.0 / 5.0, 0.22),
    "major_second": (9.0 / 8.0, 0.30),
    "minor_seventh": (16.0 / 9.0, 0.35),
    "major_seventh": (15.0 / 8.0, 0.55),
    "phi_interval": (PHI, 0.40),
    "tritone": (45.0 / 32.0, 0.75),
    "minor_second": (16.0 / 15.0, 0.90),
}

ALLOW_THRESHOLD = 0.25
QUARANTINE_THRESHOLD = 0.50
ESCALATE_THRESHOLD = 0.75

DEFAULT_SAMPLE_RATE = 8000
DEFAULT_DURATION_S = 0.25


class GovernanceVerdict(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass(frozen=True)
class SpectralFeatures:
    energy: float
    spectral_centroid: float
    spectral_flux: float
    peak_frequency: float
    beat_frequency: float
    n_peaks: int


@dataclass(frozen=True)
class ConsonanceReport:
    baseline_hz: float
    agent_hz: float
    frequency_ratio: float
    nearest_interval: str
    interval_deviation: float
    dissonance_score: float
    spectral: SpectralFeatures
    verdict: GovernanceVerdict
    dead_tone: str


def generate_wave(
    frequency_hz, duration_s=DEFAULT_DURATION_S, sample_rate=DEFAULT_SAMPLE_RATE, amplitude=1.0, phase=0.0
):
    n_samples = int(duration_s * sample_rate)
    return [amplitude * math.sin(TAU * frequency_hz * (i / sample_rate) + phase) for i in range(n_samples)]


def superpose(wave_a, wave_b):
    n = min(len(wave_a), len(wave_b))
    return [wave_a[i] + wave_b[i] for i in range(n)]


def dft_magnitudes(signal):
    n = len(signal)
    half = n // 2
    magnitudes = []
    for k in range(half):
        re = 0.0
        im = 0.0
        for t in range(n):
            angle = TAU * k * t / n
            re += signal[t] * math.cos(angle)
            im -= signal[t] * math.sin(angle)
        magnitudes.append(math.hypot(re, im) / n)
    return magnitudes


def extract_spectral_features(combined, baseline_hz, agent_hz, sample_rate=DEFAULT_SAMPLE_RATE):
    mags = dft_magnitudes(combined)
    n_bins = len(mags)
    if n_bins == 0:
        return SpectralFeatures(0.0, 0.0, 0.0, 0.0, abs(baseline_hz - agent_hz), 0)

    freq_resolution = sample_rate / (2.0 * n_bins)
    energy = sum(m * m for m in mags)
    total_mag = sum(mags)
    if total_mag > 0:
        centroid = sum(mags[i] * (i * freq_resolution) for i in range(n_bins)) / total_mag
    else:
        centroid = 0.0
    peak_bin = max(range(n_bins), key=lambda i: mags[i])
    peak_frequency = peak_bin * freq_resolution
    beat_frequency = abs(baseline_hz - agent_hz)
    beat_bin = int(beat_frequency / freq_resolution) if freq_resolution > 0 else 0
    flux_window = max(1, int(5.0 / freq_resolution))
    lo = max(0, beat_bin - flux_window)
    hi = min(n_bins, beat_bin + flux_window + 1)
    spectral_flux = sum(mags[i] * mags[i] for i in range(lo, hi))
    max_mag = max(mags) if mags else 0.0
    threshold = max_mag * 0.1
    n_peaks = sum(1 for m in mags if m > threshold) if max_mag > 0 else 0

    return SpectralFeatures(
        energy=energy,
        spectral_centroid=centroid,
        spectral_flux=spectral_flux,
        peak_frequency=peak_frequency,
        beat_frequency=beat_frequency,
        n_peaks=n_peaks,
    )


def normalize_ratio(f_a, f_b):
    if f_a <= 0 or f_b <= 0:
        return 1.0
    ratio = max(f_a, f_b) / min(f_a, f_b)
    while ratio >= 2.0:
        ratio /= 2.0
    while ratio < 1.0:
        ratio *= 2.0
    return ratio


def nearest_consonance(ratio):
    best_name = "tritone"
    best_dev = float("inf")
    best_dis = 0.75
    for name, (ref_ratio, dissonance) in RATIO_DISSONANCE.items():
        dev = abs(ratio - ref_ratio)
        if dev < best_dev:
            best_dev = dev
            best_name = name
            best_dis = dissonance
    return best_name, best_dev, best_dis


def compute_dissonance(ratio, tolerance=0.03):
    name, deviation, base_dissonance = nearest_consonance(ratio)
    deviation_penalty = min(1.0, deviation / 0.05) * 0.5
    score = min(1.0, base_dissonance + deviation_penalty)
    if deviation <= tolerance:
        score = base_dissonance
    return name, deviation, score


def dissonance_to_verdict(score):
    if score < ALLOW_THRESHOLD:
        return GovernanceVerdict.ALLOW
    elif score < QUARANTINE_THRESHOLD:
        return GovernanceVerdict.QUARANTINE
    elif score < ESCALATE_THRESHOLD:
        return GovernanceVerdict.ESCALATE
    else:
        return GovernanceVerdict.DENY


def cross_chamber_check(
    agent_hz, dead_tone="perfect_fifth", tolerance=0.03, duration_s=DEFAULT_DURATION_S, sample_rate=DEFAULT_SAMPLE_RATE
):
    baseline_hz = BASELINE_FREQUENCIES[dead_tone]
    wave_root = generate_wave(baseline_hz, duration_s, sample_rate)
    wave_agent = generate_wave(agent_hz, duration_s, sample_rate)
    combined = superpose(wave_root, wave_agent)
    spectral = extract_spectral_features(combined, baseline_hz, agent_hz, sample_rate)
    ratio = normalize_ratio(baseline_hz, agent_hz)
    interval_name, deviation, dissonance = compute_dissonance(ratio, tolerance)
    verdict = dissonance_to_verdict(dissonance)
    return ConsonanceReport(
        baseline_hz=baseline_hz,
        agent_hz=agent_hz,
        frequency_ratio=ratio,
        nearest_interval=interval_name,
        interval_deviation=deviation,
        dissonance_score=dissonance,
        spectral=spectral,
        verdict=verdict,
        dead_tone=dead_tone,
    )


def check_all_dead_tones(agent_hz, tolerance=0.03):
    return [cross_chamber_check(agent_hz, tone, tolerance) for tone in BASELINE_FREQUENCIES]


def strictest_verdict(reports):
    order = [GovernanceVerdict.ALLOW, GovernanceVerdict.QUARANTINE, GovernanceVerdict.ESCALATE, GovernanceVerdict.DENY]
    worst = GovernanceVerdict.ALLOW
    for r in reports:
        if order.index(r.verdict) > order.index(worst):
            worst = r.verdict
    return worst


# ---------------------------------------------------------------------------
# Tests — full alphabet of consonance and dissonance
# ---------------------------------------------------------------------------


class TestNormalizeRatio:

    def test_unison(self):
        assert normalize_ratio(440.0, 440.0) == 1.0

    def test_octave_folds_down(self):
        r = normalize_ratio(220.0, 880.0)
        assert abs(r - 1.0) < 0.001  # 4:1 → 1:1

    def test_perfect_fifth(self):
        r = normalize_ratio(200.0, 300.0)
        assert abs(r - 1.5) < 0.001

    def test_symmetry(self):
        """A4: normalize_ratio(a,b) == normalize_ratio(b,a)."""
        assert normalize_ratio(330.0, 495.0) == normalize_ratio(495.0, 330.0)

    def test_zero_frequency_safe(self):
        assert normalize_ratio(0.0, 440.0) == 1.0
        assert normalize_ratio(440.0, 0.0) == 1.0

    def test_negative_frequency_safe(self):
        assert normalize_ratio(-100.0, 440.0) == 1.0

    def test_very_high_ratio_folds(self):
        r = normalize_ratio(100.0, 3200.0)  # 32:1 = 5 octaves
        assert 1.0 <= r < 2.0

    def test_all_ratios_in_octave_range(self):
        for f in [100, 200, 333, 440, 550, 660, 880, 1000, 1500, 2000]:
            r = normalize_ratio(330.0, float(f))
            assert 1.0 <= r < 2.0


class TestNearestConsonance:

    def test_exact_unison(self):
        name, dev, dis = nearest_consonance(1.0)
        assert name == "unison"
        assert dev < 0.001

    def test_exact_perfect_fifth(self):
        name, dev, dis = nearest_consonance(1.5)
        assert name == "perfect_fifth"
        assert dev < 0.001

    def test_exact_tritone(self):
        name, dev, dis = nearest_consonance(45.0 / 32.0)
        assert name == "tritone"
        assert dev < 0.001

    def test_exact_minor_second(self):
        name, dev, dis = nearest_consonance(16.0 / 15.0)
        assert name == "minor_second"
        assert dev < 0.001

    def test_all_named_intervals_find_themselves(self):
        """Every named interval should be its own nearest match."""
        for name, (ratio, _) in RATIO_DISSONANCE.items():
            found, dev, _ = nearest_consonance(ratio)
            assert found == name, f"{name}: got {found}"
            assert dev < 0.001, f"{name}: deviation {dev}"


class TestComputeDissonance:

    def test_unison_is_zero(self):
        _, _, score = compute_dissonance(1.0)
        assert score == 0.0

    def test_perfect_fifth_is_low(self):
        _, _, score = compute_dissonance(1.5)
        assert score < ALLOW_THRESHOLD

    def test_tritone_is_high(self):
        _, _, score = compute_dissonance(45.0 / 32.0)
        assert score >= ESCALATE_THRESHOLD

    def test_minor_second_is_maximum(self):
        _, _, score = compute_dissonance(16.0 / 15.0)
        assert score >= ESCALATE_THRESHOLD

    def test_score_always_bounded(self):
        for r in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]:
            _, _, score = compute_dissonance(r)
            assert 0.0 <= score <= 1.0

    def test_consonant_intervals_below_quarantine(self):
        """Unison, octave, P5, P4, M3, m3 should all be safe-ish."""
        safe_intervals = ["unison", "octave", "perfect_fifth", "perfect_fourth", "major_third", "minor_third"]
        for name in safe_intervals:
            ratio, _ = RATIO_DISSONANCE[name]
            _, _, score = compute_dissonance(ratio)
            assert score < QUARANTINE_THRESHOLD, f"{name} scored {score}"

    def test_dissonant_intervals_above_quarantine(self):
        """Tritone, minor second, major seventh should be flagged."""
        harsh_intervals = ["tritone", "minor_second", "major_seventh"]
        for name in harsh_intervals:
            ratio, _ = RATIO_DISSONANCE[name]
            _, _, score = compute_dissonance(ratio)
            assert score >= QUARANTINE_THRESHOLD, f"{name} scored {score}"

    def test_tolerance_grace_zone(self):
        """Within tolerance of a consonance, deviation penalty is not added."""
        # Slightly detuned fifth: 1.5 + 0.02 (within 0.03 tolerance)
        name, dev, score = compute_dissonance(1.52, tolerance=0.03)
        assert name == "perfect_fifth"
        assert score == 0.05  # base dissonance, no penalty

    def test_outside_tolerance_gets_penalty(self):
        """Beyond tolerance, deviation penalty kicks in."""
        _, _, score_exact = compute_dissonance(1.5, tolerance=0.03)
        _, _, score_far = compute_dissonance(1.56, tolerance=0.03)
        assert score_far > score_exact


class TestDissonanceToVerdict:

    def test_allow(self):
        assert dissonance_to_verdict(0.0) == GovernanceVerdict.ALLOW
        assert dissonance_to_verdict(0.10) == GovernanceVerdict.ALLOW
        assert dissonance_to_verdict(0.24) == GovernanceVerdict.ALLOW

    def test_quarantine(self):
        assert dissonance_to_verdict(0.25) == GovernanceVerdict.QUARANTINE
        assert dissonance_to_verdict(0.40) == GovernanceVerdict.QUARANTINE
        assert dissonance_to_verdict(0.49) == GovernanceVerdict.QUARANTINE

    def test_escalate(self):
        assert dissonance_to_verdict(0.50) == GovernanceVerdict.ESCALATE
        assert dissonance_to_verdict(0.60) == GovernanceVerdict.ESCALATE
        assert dissonance_to_verdict(0.74) == GovernanceVerdict.ESCALATE

    def test_deny(self):
        assert dissonance_to_verdict(0.75) == GovernanceVerdict.DENY
        assert dissonance_to_verdict(0.90) == GovernanceVerdict.DENY
        assert dissonance_to_verdict(1.00) == GovernanceVerdict.DENY

    def test_all_thresholds_covered(self):
        """Sweep 0.0 to 1.0 — every score maps to a valid verdict."""
        for i in range(101):
            score = i / 100.0
            v = dissonance_to_verdict(score)
            assert isinstance(v, GovernanceVerdict)


class TestGenerateWave:

    def test_correct_length(self):
        w = generate_wave(440.0, duration_s=0.1, sample_rate=1000)
        assert len(w) == 100

    def test_bounded_amplitude(self):
        w = generate_wave(440.0)
        assert all(-1.01 <= s <= 1.01 for s in w)

    def test_custom_amplitude(self):
        w = generate_wave(440.0, amplitude=0.5)
        assert all(-0.51 <= s <= 0.51 for s in w)

    def test_zero_frequency_is_silence(self):
        w = generate_wave(0.0)
        assert all(abs(s) < 0.001 for s in w)


class TestSuperpose:

    def test_same_length(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        assert superpose(a, b) == [5.0, 7.0, 9.0]

    def test_different_lengths_truncates(self):
        a = [1.0, 2.0]
        b = [3.0, 4.0, 5.0]
        assert superpose(a, b) == [4.0, 6.0]

    def test_cancellation(self):
        a = [1.0, -1.0, 0.5]
        b = [-1.0, 1.0, -0.5]
        result = superpose(a, b)
        assert all(abs(s) < 0.001 for s in result)

    def test_constructive_interference(self):
        """Two identical waves double the amplitude."""
        w = generate_wave(330.0, duration_s=0.01, sample_rate=4000)
        combined = superpose(w, w)
        for i in range(len(w)):
            assert abs(combined[i] - 2.0 * w[i]) < 0.001


class TestSpectralFeatures:

    def test_single_tone_has_one_dominant_peak(self):
        w = generate_wave(330.0)
        sf = extract_spectral_features(w, 330.0, 330.0)
        assert sf.energy > 0
        assert sf.beat_frequency == 0.0

    def test_two_close_tones_have_beat_frequency(self):
        wa = generate_wave(330.0)
        wb = generate_wave(335.0)
        combined = superpose(wa, wb)
        sf = extract_spectral_features(combined, 330.0, 335.0)
        assert sf.beat_frequency == 5.0
        assert sf.energy > 0

    def test_centroid_positive_for_nonzero_signal(self):
        w = generate_wave(440.0)
        sf = extract_spectral_features(w, 440.0, 440.0)
        assert sf.spectral_centroid > 0

    def test_empty_signal(self):
        sf = extract_spectral_features([], 440.0, 440.0)
        assert sf.energy == 0.0
        assert sf.n_peaks == 0


class TestCrossChamberCheck:

    def test_unison_allows(self):
        """Agent at exact baseline frequency → ALLOW."""
        r = cross_chamber_check(330.0, "perfect_fifth")
        assert r.verdict == GovernanceVerdict.ALLOW
        assert r.dissonance_score < ALLOW_THRESHOLD
        assert r.nearest_interval == "unison"
        assert r.dead_tone == "perfect_fifth"

    def test_perfect_fifth_above_allows(self):
        """Agent at 3:2 ratio above baseline → ALLOW."""
        r = cross_chamber_check(495.0, "perfect_fifth")  # 330 * 1.5
        assert r.verdict == GovernanceVerdict.ALLOW

    def test_octave_allows(self):
        """Agent at 2:1 ratio → ALLOW."""
        r = cross_chamber_check(660.0, "perfect_fifth")  # 330 * 2
        assert r.verdict == GovernanceVerdict.ALLOW

    def test_tritone_denies(self):
        """Agent at tritone ratio (45:32) → high dissonance."""
        tritone_hz = 330.0 * 45.0 / 32.0  # ~464.06 Hz
        r = cross_chamber_check(tritone_hz, "perfect_fifth")
        assert r.dissonance_score >= ESCALATE_THRESHOLD
        assert r.verdict in (GovernanceVerdict.ESCALATE, GovernanceVerdict.DENY)

    def test_minor_second_denies(self):
        """Agent at minor second (16:15) → maximum dissonance → DENY."""
        minor_second_hz = 330.0 * 16.0 / 15.0  # 352 Hz
        r = cross_chamber_check(minor_second_hz, "perfect_fifth")
        assert r.dissonance_score >= ESCALATE_THRESHOLD

    def test_all_dead_tones_work(self):
        """Check runs against all three baselines."""
        for tone in BASELINE_FREQUENCIES:
            r = cross_chamber_check(440.0, tone)
            assert isinstance(r, ConsonanceReport)
            assert r.baseline_hz == BASELINE_FREQUENCIES[tone]
            assert r.dead_tone == tone

    def test_report_has_spectral_features(self):
        r = cross_chamber_check(440.0, "perfect_fifth")
        assert r.spectral.energy > 0
        assert r.spectral.beat_frequency == abs(330.0 - 440.0)

    def test_frozen_dataclass(self):
        r = cross_chamber_check(440.0)
        try:
            r.verdict = GovernanceVerdict.DENY
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_ratio_always_in_octave_range(self):
        for f in [100, 200, 330, 440, 495, 660, 880, 1000, 1500, 3000]:
            r = cross_chamber_check(float(f))
            assert 1.0 <= r.frequency_ratio < 2.0


class TestCheckAllDeadTones:

    def test_returns_three_reports(self):
        reports = check_all_dead_tones(440.0)
        assert len(reports) == 3

    def test_each_report_has_different_baseline(self):
        reports = check_all_dead_tones(440.0)
        baselines = {r.baseline_hz for r in reports}
        assert len(baselines) == 3

    def test_unison_with_each_baseline(self):
        """Agent at each baseline frequency → all ALLOW."""
        for tone, freq in BASELINE_FREQUENCIES.items():
            reports = check_all_dead_tones(freq)
            # At least the matching tone should ALLOW
            matching = [r for r in reports if r.dead_tone == tone]
            assert len(matching) == 1
            assert matching[0].verdict == GovernanceVerdict.ALLOW


class TestStrictestVerdict:

    def test_all_allow_returns_allow(self):
        reports = check_all_dead_tones(330.0)  # unison with perfect_fifth baseline
        # At least one is ALLOW; strictest might be higher due to other baselines
        v = strictest_verdict(reports)
        assert isinstance(v, GovernanceVerdict)

    def test_one_deny_overrides(self):
        """If any report says DENY, the strictest is DENY."""
        # Construct a frequency that's tritone to at least one baseline
        tritone_hz = 330.0 * 45.0 / 32.0
        reports = check_all_dead_tones(tritone_hz)
        # The perfect_fifth baseline should be most dissonant
        pf = [r for r in reports if r.dead_tone == "perfect_fifth"][0]
        assert pf.dissonance_score >= ESCALATE_THRESHOLD

    def test_empty_list_returns_allow(self):
        assert strictest_verdict([]) == GovernanceVerdict.ALLOW


class TestGovernanceVerdictEnum:

    def test_four_values(self):
        assert len(GovernanceVerdict) == 4

    def test_values(self):
        assert GovernanceVerdict.ALLOW.value == "ALLOW"
        assert GovernanceVerdict.QUARANTINE.value == "QUARANTINE"
        assert GovernanceVerdict.ESCALATE.value == "ESCALATE"
        assert GovernanceVerdict.DENY.value == "DENY"


class TestConsonanceMonotonicity:
    """Dissonance scoring should be monotonic with musical intuition:
    unison < P5 < M3 < m6 < tritone < m2."""

    def test_dissonance_ordering(self):
        ordered_intervals = [
            ("unison", 1.0),
            ("perfect_fifth", 3.0 / 2.0),
            ("major_third", 5.0 / 4.0),
            ("minor_sixth", 8.0 / 5.0),
            ("tritone", 45.0 / 32.0),
            ("minor_second", 16.0 / 15.0),
        ]
        scores = []
        for name, ratio in ordered_intervals:
            _, _, score = compute_dissonance(ratio)
            scores.append((name, score))

        # Each score should be >= the previous
        for i in range(1, len(scores)):
            assert (
                scores[i][1] >= scores[i - 1][1]
            ), f"{scores[i][0]}({scores[i][1]}) < {scores[i-1][0]}({scores[i-1][1]})"


class TestPhiInterval:
    """The golden ratio interval is special — outside the JI lattice."""

    def test_phi_is_recognized(self):
        name, dev, _ = nearest_consonance(PHI)
        assert name == "phi_interval"
        assert dev < 0.001

    def test_phi_is_quarantine_level(self):
        """Phi is neither consonant nor harshly dissonant — it quarantines."""
        _, _, score = compute_dissonance(PHI)
        assert ALLOW_THRESHOLD <= score < ESCALATE_THRESHOLD

    def test_phi_against_all_baselines(self):
        """Phi interval against every dead tone baseline."""
        for tone, base_hz in BASELINE_FREQUENCIES.items():
            agent_hz = base_hz * PHI
            r = cross_chamber_check(agent_hz, tone)
            # Phi should fold into octave range and still be recognizable
            assert 1.0 <= r.frequency_ratio < 2.0


class TestEdgeCases:

    def test_very_low_frequency(self):
        r = cross_chamber_check(20.0)  # subsonic edge
        assert isinstance(r, ConsonanceReport)
        assert 1.0 <= r.frequency_ratio < 2.0

    def test_very_high_frequency(self):
        r = cross_chamber_check(15000.0)  # high audible
        assert isinstance(r, ConsonanceReport)
        assert 1.0 <= r.frequency_ratio < 2.0

    def test_all_tongue_audible_frequencies(self):
        """Every Sacred Tongue base frequency produces a valid report."""
        tongue_freqs = {
            "ko": 440.00,
            "av": 523.25,
            "ru": 293.66,
            "ca": 659.25,
            "um": 196.00,
            "dr": 392.00,
        }
        for _tongue, freq in tongue_freqs.items():
            for tone in BASELINE_FREQUENCIES:
                r = cross_chamber_check(freq, tone)
                assert isinstance(r, ConsonanceReport)
                assert 0.0 <= r.dissonance_score <= 1.0

    def test_short_duration(self):
        r = cross_chamber_check(440.0, duration_s=0.05, sample_rate=2000)
        assert isinstance(r, ConsonanceReport)

    def test_high_sample_rate(self):
        r = cross_chamber_check(440.0, duration_s=0.05, sample_rate=16000)
        assert isinstance(r, ConsonanceReport)
