"""
Tests for Gallery Chromatics — Dual-Seeded Color Field from Dead Tone Harmonics
================================================================================

Tests the full pipeline: frequency → harmonic → polar → CIELAB → material → iris

Covers:
    - Harmonic number computation (log-phi scaling)
    - Polar coordinate mapping (golden angle spiral)
    - 4-color quad scattering (90° spacing, material bands)
    - Dead tone color chords (per-tongue phase rotation)
    - Dual iris construction (left=structure, right=creativity)
    - Cross-eye coherence (cosine similarity)
    - Spectral coverage (hue wheel fraction)
    - Integration with gallery ambient data
    - Perpendicular echo formula (the idea that started this)
"""

import math
import sys

sys.path.insert(0, ".")

from src.crypto.gallery_chromatics import (
    PHI,
    TAU,
    TONGUE_PHASE_OFFSETS,
    MATERIAL_ORDER,
    LEFT_EYE_TONGUES,
    RIGHT_EYE_TONGUES,
    DEAD_TONE_RATIOS,
    LabColor,
    DeadToneColorChord,
    frequency_to_harmonic_number,
    harmonic_to_polar,
    scatter_color_quad,
    compute_gallery_color_field,
)

# ---------------------------------------------------------------------------
# Perpendicular Echo Formula (the seed idea)
# ---------------------------------------------------------------------------


def perp_echo_response(echo_tangent: float, k: float = 1.0, eps: float = 1e-9) -> float:
    """S_perp = -phi * k / (|E(tangent)| + eps)"""
    return -(PHI * k) / (abs(echo_tangent) + eps)


class TestPerpEchoFormula:
    """The idea that started the gallery color field."""

    def test_inverse_relation(self):
        """Weaker tangent → stronger perpendicular response."""
        assert abs(perp_echo_response(0.5)) > abs(perp_echo_response(2.0))

    def test_negative_sign(self):
        """Response is always negative (opposite direction)."""
        assert perp_echo_response(1.0) < 0

    def test_finite_at_zero(self):
        """No blow-up when tangent is zero."""
        assert math.isfinite(perp_echo_response(0.0))

    def test_phi_scaling(self):
        """Response at tangent=1 is -phi (the natural unit)."""
        r = perp_echo_response(1.0)
        assert abs(r - (-PHI)) < 0.01

    def test_monotonic_decrease(self):
        """As tangent grows, |response| shrinks monotonically."""
        prev = abs(perp_echo_response(0.01))
        for t in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            cur = abs(perp_echo_response(t))
            assert cur < prev, f"|response| should decrease: {t}"
            prev = cur


# ---------------------------------------------------------------------------
# Harmonic Number
# ---------------------------------------------------------------------------


class TestFrequencyToHarmonicNumber:

    def test_unison_is_zero(self):
        """Ratio 1.0 → harmonic 0 (no movement)."""
        assert frequency_to_harmonic_number(1.0) == 0.0

    def test_phi_is_one(self):
        """Ratio phi → harmonic 1 (by definition of log-phi)."""
        h = frequency_to_harmonic_number(PHI)
        assert abs(h - 1.0) < 1e-10

    def test_phi_squared_is_two(self):
        """Ratio phi² → harmonic 2."""
        h = frequency_to_harmonic_number(PHI**2)
        assert abs(h - 2.0) < 1e-10

    def test_dead_tones_are_irrational(self):
        """Dead tone harmonics should NOT be integers (they're gaps)."""
        for name, ratio in DEAD_TONE_RATIOS.items():
            h = frequency_to_harmonic_number(ratio)
            assert abs(h - round(h)) > 0.01, f"{name} harmonic too close to integer"

    def test_monotonic(self):
        """Higher ratio → higher harmonic number."""
        h_fifth = frequency_to_harmonic_number(1.5)
        h_sixth = frequency_to_harmonic_number(1.6)
        h_seventh = frequency_to_harmonic_number(16 / 9)
        assert h_fifth < h_sixth < h_seventh

    def test_zero_ratio(self):
        """Zero ratio → harmonic 0 (edge case)."""
        assert frequency_to_harmonic_number(0.0) == 0.0

    def test_negative_ratio(self):
        """Negative ratio → harmonic 0 (edge case)."""
        assert frequency_to_harmonic_number(-1.0) == 0.0


# ---------------------------------------------------------------------------
# Polar Mapping
# ---------------------------------------------------------------------------


class TestHarmonicToPolar:

    def test_zero_harmonic_at_origin(self):
        """Harmonic 0 → near origin (r ≈ 0)."""
        theta, r = harmonic_to_polar(0.0)
        assert r < 1.0  # very close to center

    def test_radius_saturates(self):
        """Large harmonics → radius approaches max."""
        _, r1 = harmonic_to_polar(1.0)
        _, r5 = harmonic_to_polar(5.0)
        _, r50 = harmonic_to_polar(50.0)
        assert r1 < r5 < r50
        assert r50 < 51.0  # never exceeds radius param

    def test_golden_angle_spiral(self):
        """Consecutive harmonics advance by golden angle."""
        t1, _ = harmonic_to_polar(1.0)
        t2, _ = harmonic_to_polar(2.0)
        expected_advance = PHI * math.pi
        assert abs((t2 - t1) - expected_advance) < 1e-10

    def test_custom_radius(self):
        """Custom radius parameter works."""
        _, r = harmonic_to_polar(10.0, radius=100.0)
        assert r > 50.0  # should be near 100 for large harmonic


# ---------------------------------------------------------------------------
# Color Quad Scattering
# ---------------------------------------------------------------------------


class TestScatterColorQuad:

    def test_returns_four_colors(self):
        """Always produces exactly 4 colors."""
        colors = scatter_color_quad(0.0, 40.0, 0.0)
        assert len(colors) == 4

    def test_four_materials(self):
        """Each color has a different material band."""
        colors = scatter_color_quad(0.0, 40.0, 0.0)
        materials = [c.material for c in colors]
        assert materials == MATERIAL_ORDER

    def test_90_degree_spacing(self):
        """Colors are approximately 90° apart on the hue wheel."""
        colors = scatter_color_quad(0.0, 40.0, 0.0)
        hues = [c.hue_angle for c in colors]
        for i in range(len(hues) - 1):
            diff = hues[i + 1] - hues[i]
            # Normalize to [-pi, pi] to handle wrap-around
            diff = (diff + math.pi) % TAU - math.pi
            # Allow for material hue shift to perturb slightly (metallic=0.08 stacks)
            assert abs(abs(diff) - math.pi / 2) < 0.3, f"Hue gap {i}→{i+1} not ~90°: {math.degrees(diff):.1f}°"

    def test_tongue_phase_rotates_all(self):
        """Different tongue phases produce different color sets."""
        c1 = scatter_color_quad(0.0, 40.0, 0.0)
        c2 = scatter_color_quad(0.0, 40.0, math.pi / 3)
        # Same chroma (material scaling), different hue
        for a, b in zip(c1, c2):
            assert abs(a.chroma - b.chroma) < 0.01  # same radius
            assert abs(a.hue_angle - b.hue_angle) > 0.1  # different angle

    def test_lightness_in_range(self):
        """All L* values stay in [0, 100]."""
        colors = scatter_color_quad(0.0, 80.0, 0.0, L_base=90.0)
        for c in colors:
            assert 0.0 <= c.L <= 100.0

    def test_neon_has_highest_chroma(self):
        """Neon material band has the highest chroma scale."""
        colors = scatter_color_quad(0.0, 40.0, 0.0)
        neon = next(c for c in colors if c.material == "neon")
        for c in colors:
            if c.material != "neon":
                assert neon.chroma >= c.chroma - 0.01

    def test_matte_is_darkest(self):
        """Matte has the lowest lightness."""
        colors = scatter_color_quad(0.0, 40.0, 0.0)
        matte = next(c for c in colors if c.material == "matte")
        for c in colors:
            if c.material != "matte":
                assert matte.L <= c.L + 0.01


# ---------------------------------------------------------------------------
# LabColor
# ---------------------------------------------------------------------------


class TestLabColor:

    def test_chroma_computation(self):
        """C* = sqrt(a² + b²)."""
        c = LabColor(L=50, a=30, b=40, material="neon")
        assert abs(c.chroma - 50.0) < 0.01

    def test_hue_angle(self):
        """Hue angle is atan2(b, a)."""
        c = LabColor(L=50, a=0, b=50, material="matte")
        assert abs(c.hue_angle - math.pi / 2) < 0.01

    def test_to_dict_keys(self):
        """Serialization has all expected keys."""
        c = LabColor(L=50, a=30, b=40, material="neon")
        d = c.to_dict()
        assert set(d.keys()) == {"L", "a", "b", "chroma", "hue_deg", "material"}

    def test_hue_deg_positive(self):
        """Hue degrees are in [0, 360)."""
        for a, b in [(-30, 40), (30, -40), (-30, -40), (30, 40)]:
            c = LabColor(L=50, a=a, b=b, material="matte")
            assert 0 <= c.to_dict()["hue_deg"] < 360


# ---------------------------------------------------------------------------
# Dead Tone Color Chord
# ---------------------------------------------------------------------------


class TestDeadToneColorChord:

    def _make_chord(self, tongue="ko"):
        h = frequency_to_harmonic_number(1.5)
        theta, r = harmonic_to_polar(h)
        colors = scatter_color_quad(theta, r, TONGUE_PHASE_OFFSETS[tongue])
        return DeadToneColorChord(
            dead_tone="perfect_fifth",
            tongue=tongue,
            harmonic_number=h,
            colors=colors,
        )

    def test_mean_chroma_positive(self):
        chord = self._make_chord()
        assert chord.mean_chroma > 0

    def test_hue_spread_reasonable(self):
        """4 colors at 90° should spread ~270° of the wheel."""
        chord = self._make_chord()
        assert chord.hue_spread_deg > 180  # at least half the wheel

    def test_different_tongues_different_chords(self):
        """KO and DR tongues produce different color orientations."""
        chord_ko = self._make_chord("ko")
        chord_dr = self._make_chord("dr")
        # Same chroma (same harmonic), different hues
        assert abs(chord_ko.mean_chroma - chord_dr.mean_chroma) < 1.0
        # At least one color pair should differ in hue
        hue_diffs = [abs(a.hue_angle - b.hue_angle) for a, b in zip(chord_ko.colors, chord_dr.colors)]
        assert max(hue_diffs) > 0.1

    def test_serialization(self):
        chord = self._make_chord()
        d = chord.to_dict()
        assert d["dead_tone"] == "perfect_fifth"
        assert len(d["colors"]) == 4


# ---------------------------------------------------------------------------
# Full Gallery Color Field (Integration)
# ---------------------------------------------------------------------------


class TestGalleryColorField:
    """Integration tests using mock gallery ambient data."""

    @staticmethod
    def _mock_gallery_notes():
        """Create minimal mock gallery notes."""
        from dataclasses import dataclass

        @dataclass
        class MockNote:
            observed_ratio: float

        return {
            "perfect_fifth": MockNote(observed_ratio=1.48),
            "minor_sixth": MockNote(observed_ratio=1.59),
            "minor_seventh": MockNote(observed_ratio=1.72),
        }

    @staticmethod
    def _mock_coefficients():
        return {
            "ko": 0.45,
            "dr": 0.55,  # structure pair
            "av": 0.50,
            "um": 0.50,  # stability pair
            "ru": 0.60,
            "ca": 0.40,  # creativity pair
        }

    def test_produces_24_colors(self):
        """2 eyes × 3 tones × 4 colors = 24 total."""
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert field.left_iris.color_count == 12
        assert field.right_iris.color_count == 12

    def test_left_eye_uses_structure_tongues(self):
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert field.left_iris.seed_tongues == LEFT_EYE_TONGUES
        assert field.left_iris.dominant_tongue in LEFT_EYE_TONGUES

    def test_right_eye_uses_creativity_tongues(self):
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert field.right_iris.seed_tongues == RIGHT_EYE_TONGUES
        assert field.right_iris.dominant_tongue in RIGHT_EYE_TONGUES

    def test_cross_eye_coherence_bounded(self):
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert 0.0 <= field.cross_eye_coherence <= 1.0

    def test_spectral_coverage_bounded(self):
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert 0.0 <= field.spectral_coverage <= 1.0

    def test_spectral_coverage_reasonable(self):
        """24 colors spread by golden angle should cover >50% of hue wheel."""
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert field.spectral_coverage > 0.5

    def test_dominant_material_valid(self):
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        assert field.dominant_material in MATERIAL_ORDER

    def test_different_ratios_different_colors(self):
        """Changing dead tone ratios should change the color field."""
        notes1 = self._mock_gallery_notes()
        notes2 = self._mock_gallery_notes()
        notes2["perfect_fifth"].observed_ratio = 1.30  # shift fifth

        field1 = compute_gallery_color_field(notes1, self._mock_coefficients())
        field2 = compute_gallery_color_field(notes2, self._mock_coefficients())

        # The fifth chord should differ
        h1 = field1.left_iris.chords["perfect_fifth"].harmonic_number
        h2 = field2.left_iris.chords["perfect_fifth"].harmonic_number
        assert abs(h1 - h2) > 0.1

    def test_different_coefficients_different_dominance(self):
        """Swapping tongue strengths should change dominant tongue."""
        coeffs1 = self._mock_coefficients()
        coeffs2 = dict(coeffs1)
        coeffs2["ko"] = 0.9
        coeffs2["dr"] = 0.1

        field1 = compute_gallery_color_field(self._mock_gallery_notes(), coeffs1)
        field2 = compute_gallery_color_field(self._mock_gallery_notes(), coeffs2)

        assert field1.left_iris.dominant_tongue == "dr"  # dr=0.55 > ko=0.45
        assert field2.left_iris.dominant_tongue == "ko"  # ko=0.9 > dr=0.1

    def test_serialization_complete(self):
        """Full to_dict produces valid nested structure."""
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        d = field.to_dict()
        assert "left_iris" in d
        assert "right_iris" in d
        assert len(d["left_iris"]["chords"]) == 3
        assert len(d["right_iris"]["chords"]) == 3
        # Check a color exists deep in the structure
        fifth_colors = d["left_iris"]["chords"]["perfect_fifth"]["colors"]
        assert len(fifth_colors) == 4
        assert "L" in fifth_colors[0]
        assert "material" in fifth_colors[0]

    def test_all_colors_finite(self):
        """No NaN or Inf in any color coordinate."""
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        for iris in (field.left_iris, field.right_iris):
            for chord in iris.chords.values():
                for color in chord.colors:
                    assert math.isfinite(color.L)
                    assert math.isfinite(color.a)
                    assert math.isfinite(color.b)

    def test_all_lightness_in_range(self):
        """L* stays in [0, 100] for all 24 colors."""
        field = compute_gallery_color_field(self._mock_gallery_notes(), self._mock_coefficients())
        for iris in (field.left_iris, field.right_iris):
            for chord in iris.chords.values():
                for color in chord.colors:
                    assert 0.0 <= color.L <= 100.0


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:

    def test_zero_coefficients(self):
        """All zero coefficients shouldn't crash."""
        from tests.crypto.test_gallery_chromatics import TestGalleryColorField

        notes = TestGalleryColorField._mock_gallery_notes()
        coeffs = {t: 0.0 for t in ["ko", "dr", "av", "um", "ru", "ca"]}
        field = compute_gallery_color_field(notes, coeffs)
        assert field.left_iris.color_count == 12

    def test_extreme_ratios(self):
        """Ratios at boundary of octave [1.0, 2.0) work."""
        from dataclasses import dataclass

        @dataclass
        class MockNote:
            observed_ratio: float

        notes = {
            "perfect_fifth": MockNote(observed_ratio=1.001),
            "minor_sixth": MockNote(observed_ratio=1.999),
            "minor_seventh": MockNote(observed_ratio=1.5),
        }
        coeffs = {t: 0.5 for t in ["ko", "dr", "av", "um", "ru", "ca"]}
        field = compute_gallery_color_field(notes, coeffs)
        assert field.left_iris.color_count == 12

    def test_identical_ratios(self):
        """All dead tones at same ratio — coherence should be high."""
        from dataclasses import dataclass

        @dataclass
        class MockNote:
            observed_ratio: float

        notes = {
            "perfect_fifth": MockNote(observed_ratio=1.5),
            "minor_sixth": MockNote(observed_ratio=1.5),
            "minor_seventh": MockNote(observed_ratio=1.5),
        }
        coeffs = {t: 0.5 for t in ["ko", "dr", "av", "um", "ru", "ca"]}
        field = compute_gallery_color_field(notes, coeffs)
        # Same ratios → same harmonics → very high coherence
        assert field.cross_eye_coherence > 0.99
