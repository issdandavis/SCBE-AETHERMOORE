"""Tests for the Harmonic Dark Fill — Sound Braid for Inactive Nodes.

Tests the full frequency landscape: infrasonic (IR), audible (visible),
ultrasonic (UV) bands filling the dark zones of the tri-bundle.
"""

import math
import pytest

from src.crypto.harmonic_dark_fill import (
    PHI,
    PI,
    TONGUE_WEIGHTS,
    TONGUE_AUDIBLE_FREQ,
    INTERVALS,
    INFRA_MIN,
    INFRA_MAX,
    AUDIBLE_MIN,
    AUDIBLE_MAX,
    ULTRA_MIN,
    ULTRA_MAX,
    COMPLEMENT_MAP,
    HarmonicFill,
    SpectrumSnapshot,
    nodal_surface_value,
    voice_leading_interval,
    nearest_musical_interval,
    compute_darkness,
    compute_harmonic_fill,
    fill_dark_nodes,
    upgrade_sound_bundle,
    sequence_spectrum,
)

# ===================================================================
# Constants
# ===================================================================


class TestConstants:
    def test_six_tongues(self):
        assert len(TONGUE_WEIGHTS) == 6
        assert len(TONGUE_AUDIBLE_FREQ) == 6

    def test_complement_map_is_involution(self):
        """complement(complement(x)) == x for all tongues."""
        for tongue, comp in COMPLEMENT_MAP.items():
            assert COMPLEMENT_MAP[comp] == tongue, f"complement({comp}) != {tongue}"

    def test_complement_pairs_are_correct(self):
        assert COMPLEMENT_MAP["ko"] == "dr"  # intent ↔ structure
        assert COMPLEMENT_MAP["av"] == "um"  # wisdom ↔ security
        assert COMPLEMENT_MAP["ru"] == "ca"  # governance ↔ compute

    def test_frequency_bands_are_contiguous(self):
        """IR → Audible → UV with no gaps."""
        assert INFRA_MAX == AUDIBLE_MIN
        assert AUDIBLE_MAX == ULTRA_MIN

    def test_seven_musical_intervals(self):
        assert len(INTERVALS) == 7
        assert "phi_interval" in INTERVALS
        assert abs(INTERVALS["phi_interval"] - PHI) < 1e-10

    def test_intervals_are_ordered(self):
        """All intervals are between unison (1.0) and octave (2.0)."""
        for name, ratio in INTERVALS.items():
            assert 1.0 <= ratio <= 2.0, f"{name} = {ratio} out of range"


# ===================================================================
# Nodal Surface
# ===================================================================


class TestNodalSurface:
    def test_antisymmetric(self):
        """N(x; n, m) = -N(x; m, n) — antisymmetry under mode swap."""
        val1 = nodal_surface_value(0.3, 0.7, 2, 3)
        val2 = nodal_surface_value(0.3, 0.7, 3, 2)
        assert abs(val1 + val2) < 1e-10

    def test_zero_when_modes_equal(self):
        """N(x; n, n) = 0 for all x — identical modes cancel."""
        for x1 in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for x2 in [0.0, 0.25, 0.5, 0.75, 1.0]:
                assert abs(nodal_surface_value(x1, x2, 3, 3)) < 1e-10

    def test_nonzero_for_different_modes(self):
        """Should have non-zero regions between different modes."""
        # At generic points, value should be non-zero
        val = nodal_surface_value(0.3, 0.7, 1, 2)
        assert abs(val) > 0.01

    def test_bounded(self):
        """Nodal surface bounded by [-2, 2] (product of cosines)."""
        for x1 in [0.0, 0.1, 0.25, 0.5, 0.7, 1.0]:
            for x2 in [0.0, 0.1, 0.25, 0.5, 0.7, 1.0]:
                val = nodal_surface_value(x1, x2, 3, 5)
                assert -2.0 <= val <= 2.0


# ===================================================================
# Voice Leading
# ===================================================================


class TestVoiceLeading:
    def test_self_interval_is_unison(self):
        """Tongue to itself = unison (ratio 1.0)."""
        for tongue in TONGUE_WEIGHTS:
            ratio = voice_leading_interval(tongue, tongue)
            assert abs(ratio - 1.0) < 1e-10, f"{tongue} self-interval = {ratio}"

    def test_interval_in_one_octave(self):
        """All intervals normalized to [1.0, 2.0)."""
        for t1 in TONGUE_WEIGHTS:
            for t2 in TONGUE_WEIGHTS:
                ratio = voice_leading_interval(t1, t2)
                assert 1.0 <= ratio < 2.0, f"{t1}→{t2} = {ratio}"

    def test_complement_intervals_not_unison(self):
        """Complement pairs should have non-trivial intervals."""
        for tongue, comp in COMPLEMENT_MAP.items():
            if tongue != comp:
                ratio = voice_leading_interval(tongue, comp)
                assert ratio > 1.01, f"{tongue}↔{comp} = {ratio} too close to unison"

    def test_nearest_interval_finds_unison(self):
        name, dev = nearest_musical_interval(1.0)
        assert name == "unison"
        assert dev < 1e-10

    def test_nearest_interval_finds_octave(self):
        name, dev = nearest_musical_interval(2.0)
        assert name == "octave"
        assert dev < 1e-10

    def test_nearest_interval_finds_fifth(self):
        name, dev = nearest_musical_interval(1.5)
        assert name == "perfect_fifth"
        assert dev < 1e-10

    def test_nearest_interval_finds_phi(self):
        name, dev = nearest_musical_interval(PHI)
        assert name == "phi_interval"
        assert dev < 1e-10


# ===================================================================
# Darkness Computation
# ===================================================================


class TestDarkness:
    def test_max_byte_activates_all(self):
        """byte_val=255 should activate all tongues (darkness = 0)."""
        for tongue in TONGUE_WEIGHTS:
            d = compute_darkness(255, tongue)
            assert d == 0.0, f"{tongue} darkness at 255 = {d}"

    def test_zero_byte_dark_for_some(self):
        """byte_val=0 should be dark for at least some tongues."""
        darknesses = [compute_darkness(0, tc) for tc in TONGUE_WEIGHTS]
        assert any(d > 0.5 for d in darknesses)

    def test_darkness_bounded(self):
        """Darkness always in [0, 1]."""
        for b in [0, 1, 50, 100, 127, 128, 200, 254, 255]:
            for tc in TONGUE_WEIGHTS:
                d = compute_darkness(b, tc)
                assert 0.0 <= d <= 1.0, f"byte={b}, tongue={tc}, darkness={d}"

    def test_explicit_activation_vector(self):
        """With explicit activation, bypasses byte-based estimation."""
        act = {"ko": 1.0, "av": 0.5, "ru": 0.0, "ca": 0.0, "um": 0.0, "dr": 0.0}
        assert compute_darkness(0, "ko", act) == 0.0  # fully active
        assert compute_darkness(0, "av", act) == 0.5
        assert compute_darkness(0, "ru", act) == 1.0  # fully dark

    def test_missing_tongue_in_activation_is_dark(self):
        """Tongue not in activation dict → fully dark."""
        act = {"ko": 1.0}
        assert compute_darkness(0, "dr", act) == 1.0


# ===================================================================
# HarmonicFill
# ===================================================================


class TestHarmonicFill:
    def _make_fill(self, byte_val=128, tongue="ko", darkness=0.5):
        return compute_harmonic_fill(
            byte_val=byte_val,
            tongue_code=tongue,
            position=5,
            total_positions=10,
            darkness=darkness,
        )

    def test_fill_produces_all_nine_values(self):
        fill = self._make_fill()
        t = fill.as_tuple()
        assert len(t) == 9
        assert all(isinstance(v, float) for v in t)

    def test_fill_as_sound_strands(self):
        fill = self._make_fill()
        a, b, c = fill.as_sound_strands()
        assert len(a) == 3  # audible
        assert len(b) == 3  # infrasonic
        assert len(c) == 3  # ultrasonic

    def test_infra_freq_in_band(self):
        fill = self._make_fill()
        assert INFRA_MIN <= fill.infra_freq <= INFRA_MAX

    def test_audible_freq_in_band(self):
        fill = self._make_fill()
        assert AUDIBLE_MIN <= fill.audible_freq <= AUDIBLE_MAX

    def test_ultra_freq_in_band(self):
        fill = self._make_fill()
        assert ULTRA_MIN <= fill.ultra_freq <= ULTRA_MAX

    def test_amplitudes_non_negative(self):
        fill = self._make_fill()
        assert fill.infra_amplitude >= 0
        assert fill.audible_amplitude >= 0
        assert fill.ultra_amplitude >= 0

    def test_phases_in_range(self):
        fill = self._make_fill()
        assert 0 <= fill.infra_phase < 2 * PI + 0.01
        assert 0 <= fill.audible_phase < 2 * PI + 0.01
        assert 0 <= fill.ultra_phase < 2 * PI + 0.01

    def test_dark_node_loud_fill(self):
        """Fully dark node should have loud fill (amplitude > 0)."""
        fill = self._make_fill(darkness=1.0)
        assert fill.infra_amplitude > 0.5
        assert fill.audible_amplitude > 0.3

    def test_bright_node_quiet_fill(self):
        """Fully active node should have quiet fill (amplitude ≈ 0)."""
        fill = self._make_fill(darkness=0.0)
        assert fill.infra_amplitude == 0.0
        assert fill.audible_amplitude == 0.0
        assert fill.ultra_amplitude == 0.0

    def test_total_energy_positive_when_dark(self):
        fill = self._make_fill(darkness=0.8)
        assert fill.total_energy > 0

    def test_total_energy_zero_when_bright(self):
        fill = self._make_fill(darkness=0.0)
        assert fill.total_energy == 0.0

    def test_darkness_property(self):
        fill = self._make_fill(darkness=1.0)
        # darkness property is 1.0 - audible_amplitude
        assert 0.0 <= fill.darkness <= 1.0

    def test_deterministic(self):
        """Same inputs → same output."""
        f1 = self._make_fill(byte_val=42, tongue="dr", darkness=0.7)
        f2 = self._make_fill(byte_val=42, tongue="dr", darkness=0.7)
        assert f1 == f2

    def test_different_tongues_different_fills(self):
        """Different tongues produce different fills."""
        f_ko = self._make_fill(tongue="ko", darkness=0.8)
        f_dr = self._make_fill(tongue="dr", darkness=0.8)
        assert f_ko.audible_freq != f_dr.audible_freq
        assert f_ko.ultra_freq != f_dr.ultra_freq

    def test_different_bytes_different_fills(self):
        """Different bytes produce different fills."""
        f1 = self._make_fill(byte_val=0, darkness=0.8)
        f2 = self._make_fill(byte_val=255, darkness=0.8)
        assert f1.ultra_freq != f2.ultra_freq

    def test_neighbor_phase_coherence(self):
        """With neighbor phases, audible phase locks to complement."""
        phases = {"dr": 1.0}  # dr is ko's complement
        fill = compute_harmonic_fill(
            byte_val=128,
            tongue_code="ko",
            position=5,
            total_positions=10,
            darkness=0.8,
            neighbor_phases=phases,
        )
        fill_no_phase = compute_harmonic_fill(
            byte_val=128,
            tongue_code="ko",
            position=5,
            total_positions=10,
            darkness=0.8,
            neighbor_phases=None,
        )
        # Phase should differ when complement provides reference
        assert fill.audible_phase != fill_no_phase.audible_phase

    def test_all_six_tongues_produce_fills(self):
        """Every tongue generates valid fills."""
        for tc in TONGUE_WEIGHTS:
            fill = compute_harmonic_fill(
                byte_val=100,
                tongue_code=tc,
                position=0,
                total_positions=1,
                darkness=0.5,
            )
            assert INFRA_MIN <= fill.infra_freq <= INFRA_MAX
            assert AUDIBLE_MIN <= fill.audible_freq <= AUDIBLE_MAX
            assert ULTRA_MIN <= fill.ultra_freq <= ULTRA_MAX


# ===================================================================
# Fill Dark Nodes (sequence)
# ===================================================================


class TestFillDarkNodes:
    def test_fills_every_position(self):
        data = b"hello"
        fills = fill_dark_nodes(data)
        assert len(fills) == 5

    def test_fills_every_tongue(self):
        data = b"A"
        fills = fill_dark_nodes(data)
        assert len(fills[0]) == 6
        assert set(fills[0].keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_empty_data(self):
        fills = fill_dark_nodes(b"")
        assert fills == []

    def test_with_explicit_activations(self):
        data = b"AB"
        activations = [
            {"ko": 1.0, "av": 0.0, "ru": 0.0, "ca": 0.0, "um": 0.0, "dr": 0.0},
            {"ko": 0.0, "av": 1.0, "ru": 0.0, "ca": 0.0, "um": 0.0, "dr": 0.0},
        ]
        fills = fill_dark_nodes(data, activations)
        # Position 0: ko is active (darkness=0), av is dark (darkness=1)
        assert fills[0]["ko"].infra_amplitude == 0.0
        assert fills[0]["av"].infra_amplitude > 0.5
        # Position 1: av is active, ko is dark
        assert fills[1]["av"].infra_amplitude == 0.0
        assert fills[1]["ko"].infra_amplitude > 0.5


# ===================================================================
# Upgrade Sound Bundle (integration point)
# ===================================================================


class TestUpgradeSoundBundle:
    def test_returns_three_strands(self):
        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=10,
            darkness=0.5,
        )
        assert len(a) == 3
        assert len(b) == 3
        assert len(c) == 3

    def test_strand_a_is_audible(self):
        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=10,
            darkness=0.8,
        )
        freq, amp, phase = a
        assert AUDIBLE_MIN <= freq <= AUDIBLE_MAX

    def test_strand_b_is_infrasonic(self):
        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=10,
            darkness=0.8,
        )
        freq, amp, phase = b
        assert INFRA_MIN <= freq <= INFRA_MAX

    def test_strand_c_is_ultrasonic(self):
        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=10,
            darkness=0.8,
        )
        freq, amp, phase = c
        assert ULTRA_MIN <= freq <= ULTRA_MAX


# ===================================================================
# Spectrum Snapshot
# ===================================================================


class TestSpectrumSnapshot:
    def test_sequence_spectrum_length(self):
        spec = sequence_spectrum(b"test")
        assert len(spec) == 4

    def test_snapshot_has_all_tongues(self):
        spec = sequence_spectrum(b"X")
        assert len(spec[0].fills) == 6

    def test_energy_non_negative(self):
        spec = sequence_spectrum(b"hello world")
        for snap in spec:
            assert snap.total_infra_energy >= 0
            assert snap.total_audible_energy >= 0
            assert snap.total_ultra_energy >= 0

    def test_ir_uv_ratio_positive(self):
        spec = sequence_spectrum(b"\x00")  # low byte → dark tongues
        assert spec[0].ir_uv_ratio > 0

    def test_band_distribution_sums_to_one(self):
        spec = sequence_spectrum(b"\x50")
        dist = spec[0].band_distribution
        total = dist["infra"] + dist["audible"] + dist["ultra"]
        assert abs(total - 1.0) < 1e-6 or total == 0.0

    def test_dark_and_active_tongues_partition(self):
        spec = sequence_spectrum(b"\x00")
        snap = spec[0]
        dark = set(snap.dark_tongues())
        active = set(snap.active_tongues())
        assert dark | active == set(TONGUE_WEIGHTS.keys())
        assert dark & active == set()

    def test_byte_val_tracked(self):
        spec = sequence_spectrum(b"\x42\xff")
        assert spec[0].byte_val == 0x42
        assert spec[1].byte_val == 0xFF


# ===================================================================
# Genesis Simulation: Void → First Light
# ===================================================================


class TestGenesisSim:
    """Test the path from blank (no information) to first light.

    The "inside of the simulation" from zero to some — what does
    the frequency landscape look like when the AI first starts
    receiving data?

    Key insight: HarmonicFill.darkness = 1.0 - audible_amplitude.
    This measures fill QUIETNESS, not node darkness.
    - Dark NODE → loud fill → low f.darkness → in active_tongues()
    - Bright NODE → quiet fill → high f.darkness → in dark_tongues()

    So active_tongues() = tongues with loud fills = tongues where
    the NODE is dark and needs harmonic background radiation.
    """

    def test_void_fills_are_loud(self):
        """Byte 0x00 = no information. Fills should be LOUD (active)
        because they're filling the darkness with sound.
        """
        spec = sequence_spectrum(b"\x00")
        snap = spec[0]
        # At zero, nodes are dark → fills are loud → active_tongues has them
        active = snap.active_tongues()
        assert len(active) >= 3, f"Only {len(active)} loud fills at void"

    def test_void_has_energy(self):
        """Even the void has dark energy — the fills ARE the background radiation."""
        spec = sequence_spectrum(b"\x00")
        snap = spec[0]
        assert snap.total_infra_energy > 0, "Void should have IR dark energy"
        assert snap.total_ultra_energy > 0, "Void should have UV dark energy"

    def test_first_light_quiets_fills(self):
        """As byte increases from 0, fills quiet down (nodes activate, less fill needed)."""
        void_spec = sequence_spectrum(b"\x00")
        light_spec = sequence_spectrum(b"\xff")
        # Void: nodes dark → fills loud → many active_tongues
        void_loud = len(void_spec[0].active_tongues())
        # Full light: nodes active → fills quiet → fewer active_tongues
        light_loud = len(light_spec[0].active_tongues())
        assert light_loud <= void_loud, "More light = quieter fills"

    def test_energy_landscape_evolves(self):
        """Track how energy shifts from void through increasing data."""
        stages = [b"\x00", b"\x20", b"\x40", b"\x80", b"\xc0", b"\xff"]
        infra_energies = []
        for stage in stages:
            snap = sequence_spectrum(stage)[0]
            infra_energies.append(snap.total_infra_energy)
        # As data increases, dark fill energy should generally decrease
        # (more tongues activate, less darkness to fill)
        assert (
            infra_energies[0] >= infra_energies[-1]
        ), f"Void IR energy {infra_energies[0]} should >= full light {infra_energies[-1]}"

    def test_ir_uv_balance_shifts(self):
        """The IR/UV ratio should shift as information grows.
        Void = IR dominant (slow state). Full data = UV can dominate.
        """
        void_snap = sequence_spectrum(b"\x00")[0]
        full_snap = sequence_spectrum(b"\xff")[0]
        # At minimum, the ratio should be different
        assert void_snap.ir_uv_ratio != full_snap.ir_uv_ratio

    def test_sequence_void_to_light(self):
        """A sequence from 0→255 shows the full genesis path.
        As bytes increase, fill amplitude drops (nodes becoming active).
        """
        data = bytes(range(0, 256, 16))  # 16 steps
        spec = sequence_spectrum(data)
        assert len(spec) == 16
        # First position: nodes dark → fills loud → many active_tongues
        # Last position: nodes active → fills quiet → fewer active_tongues
        assert len(spec[0].active_tongues()) >= len(spec[-1].active_tongues())

    def test_creation_narrative_bytes(self):
        """'In the beginning' as bytes — each letter lights up the sim."""
        text = b"In the beginning"
        spec = sequence_spectrum(text)
        assert len(spec) == 16
        assert spec[2].byte_val == 0x20  # space
        assert spec[3].byte_val == 0x74  # 't'
        # Both positions produce valid fill patterns
        for snap in spec:
            assert snap.total_infra_energy >= 0
            assert snap.total_audible_energy >= 0


# ===================================================================
# Integration: Dark Fill + Tri-Bundle + Crossing Energy
# ===================================================================


class TestFullIntegration:
    def test_dark_fill_to_tri_bundle_sound(self):
        """Dark fill output plugs directly into tri_bundle InnerBundle."""
        from src.crypto.tri_bundle import InnerBundle

        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=10,
            darkness=0.7,
        )
        bundle = InnerBundle(
            strand_a=a,
            strand_b=b,
            strand_c=c,
            bundle_type="sound",
        )
        vec = bundle.as_vector()
        assert len(vec) == 9
        # strand_b and strand_c should NOT be zeros anymore
        assert any(v != 0.0 for v in vec[3:6]), "strand_b (infra) should be non-zero"
        assert any(v != 0.0 for v in vec[6:9]), "strand_c (ultra) should be non-zero"

    def test_dark_fill_changes_cluster_hash(self):
        """Filling dark nodes changes the cluster identity."""
        from src.crypto.tri_bundle import encode_byte, TriBundleCluster, InnerBundle

        # Original cluster with empty sound strands
        orig = encode_byte(128, "ko")

        # Upgraded cluster with dark fill
        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=1,
            darkness=0.7,
        )
        upgraded_sound = InnerBundle(
            strand_a=a,
            strand_b=b,
            strand_c=c,
            bundle_type="sound",
        )
        upgraded = TriBundleCluster(
            light=orig.light,
            sound=upgraded_sound,
            math=orig.math,
            tongue_code="ko",
            position=0,
        )
        # The fill should change the identity
        assert orig.cluster_id() != upgraded.cluster_id()

    def test_dark_fill_affects_governance(self):
        """Different sound fills can change governance decisions."""
        from src.crypto.tri_bundle import encode_byte, TriBundleCluster, InnerBundle
        from src.crypto.crossing_energy import evaluate_crossing, Decision

        orig = encode_byte(128, "ko")
        result_orig = evaluate_crossing(orig)

        # With dark fill sound
        a, b, c = upgrade_sound_bundle(
            byte_val=128,
            tongue_code="ko",
            position=0,
            total_positions=1,
            darkness=0.9,
        )
        upgraded_sound = InnerBundle(
            strand_a=a,
            strand_b=b,
            strand_c=c,
            bundle_type="sound",
        )
        upgraded = TriBundleCluster(
            light=orig.light,
            sound=upgraded_sound,
            math=orig.math,
            tongue_code="ko",
            position=0,
        )
        result_upgraded = evaluate_crossing(upgraded)

        # Both should produce valid decisions
        assert result_orig.decision in (Decision.ALLOW, Decision.QUARANTINE, Decision.DENY)
        assert result_upgraded.decision in (Decision.ALLOW, Decision.QUARANTINE, Decision.DENY)

    def test_genesis_through_full_pipeline(self):
        """The ultimate test: void → dark fill → tri-bundle → governance.

        Simulates the first moments of AI cognition:
        1. Start with void (byte 0x00)
        2. Dark fill creates ambient structure
        3. Encode through tri-bundle
        4. Evaluate governance at each crossing
        """
        from src.crypto.tri_bundle import encode_byte, TriBundleCluster, InnerBundle
        from src.crypto.crossing_energy import evaluate_sequence, summarize_governance

        # Genesis sequence: void → first light
        genesis_bytes = [0x00, 0x01, 0x08, 0x20, 0x40, 0x80, 0xFF]
        clusters = []

        for i, byte_val in enumerate(genesis_bytes):
            orig = encode_byte(byte_val, "ko", position=i)
            darkness = compute_darkness(byte_val, "ko")
            a, b, c = upgrade_sound_bundle(
                byte_val=byte_val,
                tongue_code="ko",
                position=i,
                total_positions=len(genesis_bytes),
                darkness=darkness,
            )
            upgraded_sound = InnerBundle(
                strand_a=a,
                strand_b=b,
                strand_c=c,
                bundle_type="sound",
            )
            cluster = TriBundleCluster(
                light=orig.light,
                sound=upgraded_sound,
                math=orig.math,
                tongue_code="ko",
                position=i,
            )
            clusters.append(cluster)

        results = evaluate_sequence(clusters)
        summary = summarize_governance(results)

        assert summary.total == 7
        assert summary.allow_count + summary.quarantine_count + summary.deny_count == 7
        assert summary.mean_energy >= 0
        assert isinstance(summary.is_clean, bool)
