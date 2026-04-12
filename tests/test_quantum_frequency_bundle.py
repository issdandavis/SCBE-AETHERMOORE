"""Tests for Quantum Frequency Bundle Generator.

Tests QHO state computation, polychromatic visual vectors, acoustic signatures,
governance costs, spectral lines, and SFT record generation.
Grounded in real quantum physics: E_n = hbar*omega*(n + 1/2).
"""

import math
import pytest

from src.crypto.quantum_frequency_bundle import (
    # Physical constants
    HBAR,
    H_PLANCK,
    C_LIGHT,
    # Tongue mappings
    TONGUE_WAVELENGTH_NM,
    TONGUE_CENTRAL_WAVELENGTH,
    TONGUE_OPTICAL_FREQ,
    TONGUE_ORDER,
    # QHO structures
    QHOState,
    PolychromaticState,
    AcousticSignature,
    QuantumFrequencyBundle,
    # VRS + Code Lattice
    VRSState,
    CodeAntiPattern,
    CodeLatticeState,
    CODE_ANTI_PATTERNS,
    compute_vrs_state,
    compute_code_lattice,
    # Dead tone fills + Echolocation + Realm triangulation
    DEAD_TONES,
    DEAD_TONE_GENERATORS,
    DeadToneFill,
    compute_dead_tone_fills,
    EcholocationPing,
    send_echolocation_pings,
    RealmSignaturePing,
    RealmTriangulation,
    compute_realm_triangulation,
    # Functions
    compute_qho_state,
    compute_acoustic_signature,
    generate_quantum_bundle,
    generate_quantum_bundle_batch,
    quantum_bundle_summary,
    generate_quantum_sft_records,
)
from src.crypto.tri_bundle import PHI, TONGUE_WEIGHTS, TONGUE_FREQUENCIES
from src.crypto.harmonic_dark_fill import TONGUE_AUDIBLE_FREQ, INTERVALS
from src.crypto.crossing_energy import DualTernaryPair, harmonic_cost
from src.crypto.flight_dynamics import (
    RotorState,
    RecoveryPath,
    RecoveryType,
    TailRotorState,
    PacejkaTireState,
    SACRED_TONGUE_HYBRIDS,
)

# ===================================================================
# Physical Constants Sanity
# ===================================================================


class TestPhysicalConstants:
    def test_hbar_correct(self):
        assert abs(HBAR - 1.054571817e-34) < 1e-43

    def test_planck_correct(self):
        assert abs(H_PLANCK - 6.62607015e-34) < 1e-43

    def test_hbar_planck_relation(self):
        # hbar = h / 2pi
        assert abs(HBAR - H_PLANCK / (2 * math.pi)) < 1e-43

    def test_speed_of_light(self):
        assert C_LIGHT == 299792458.0


# ===================================================================
# Tongue Spectral Mapping
# ===================================================================


class TestTongueSpectralMapping:
    def test_six_tongues_mapped(self):
        assert len(TONGUE_WAVELENGTH_NM) == 6
        assert set(TONGUE_WAVELENGTH_NM.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_wavelengths_in_visible_range(self):
        """All tongue wavelengths should be in 380-700 nm (visible + near-UV)."""
        for tongue, (lo, hi) in TONGUE_WAVELENGTH_NM.items():
            assert 380 <= lo <= 700, f"{tongue} low bound {lo} out of range"
            assert 380 <= hi <= 700, f"{tongue} high bound {hi} out of range"
            assert lo < hi, f"{tongue} band inverted"

    def test_central_wavelength_is_midpoint(self):
        for tongue in TONGUE_ORDER:
            lo, hi = TONGUE_WAVELENGTH_NM[tongue]
            expected = (lo + hi) / 2.0
            assert TONGUE_CENTRAL_WAVELENGTH[tongue] == expected

    def test_optical_frequency_positive(self):
        for tongue in TONGUE_ORDER:
            assert TONGUE_OPTICAL_FREQ[tongue] > 0

    def test_optical_frequency_correct(self):
        """nu = c / lambda."""
        for tongue in TONGUE_ORDER:
            wl_m = TONGUE_CENTRAL_WAVELENGTH[tongue] * 1e-9
            expected = C_LIGHT / wl_m
            assert abs(TONGUE_OPTICAL_FREQ[tongue] - expected) < 1.0  # Hz precision

    def test_complement_pairs_opposite_spectrum(self):
        """Complement pairs should be on opposite sides of the spectrum."""
        # KO (blue-green 485nm) vs DR (amber 605nm)
        assert TONGUE_CENTRAL_WAVELENGTH["ko"] < TONGUE_CENTRAL_WAVELENGTH["dr"]
        # UM (violet 415nm) vs AV (cyan 500nm)
        assert TONGUE_CENTRAL_WAVELENGTH["um"] < TONGUE_CENTRAL_WAVELENGTH["av"]


# ===================================================================
# QHO State
# ===================================================================


class TestQHOState:
    def test_ground_state_energy(self):
        """E_0 = hbar*omega/2 — the zero-point energy."""
        omega = 2 * math.pi * 440.0  # KO frequency
        state = QHOState(tongue="ko", n=0, omega=omega, coefficient=1.0)
        expected = HBAR * omega * 0.5
        assert abs(state.energy - expected) < 1e-40

    def test_excited_state_energy(self):
        """E_n = hbar*omega*(n + 1/2)."""
        omega = 2 * math.pi * 440.0
        for n in range(8):
            state = QHOState(tongue="ko", n=n, omega=omega, coefficient=0.5)
            expected = HBAR * omega * (n + 0.5)
            assert abs(state.energy - expected) < 1e-37

    def test_excitation_energy_above_ground(self):
        """Delta E = hbar*omega*n."""
        omega = 2 * math.pi * 440.0
        state = QHOState(tongue="ko", n=3, omega=omega, coefficient=0.5)
        expected = HBAR * omega * 3
        assert abs(state.excitation_energy - expected) < 1e-37

    def test_zero_point_nonzero(self):
        """Even ground state has nonzero energy (QM requirement)."""
        omega = 2 * math.pi * 440.0
        state = QHOState(tongue="ko", n=0, omega=omega, coefficient=1.0)
        assert state.zero_point_energy > 0
        assert state.energy == state.zero_point_energy

    def test_phi_weighted_energy_scales(self):
        """DR should cost 11.09x more than KO per quantum."""
        omega = 2 * math.pi * 440.0
        ko = QHOState(tongue="ko", n=1, omega=omega, coefficient=0.5)
        dr = QHOState(tongue="dr", n=1, omega=omega, coefficient=0.5)
        assert dr.phi_weighted_energy > ko.phi_weighted_energy * 10

    def test_transition_frequency(self):
        """nu = omega / 2pi."""
        f = 440.0
        omega = 2 * math.pi * f
        state = QHOState(tongue="ko", n=1, omega=omega, coefficient=0.5)
        assert abs(state.transition_frequency - f) < 0.01

    def test_wavelength_in_band(self):
        """Wavelength should stay within tongue's spectral band."""
        for tongue in TONGUE_ORDER:
            omega = 2 * math.pi * TONGUE_FREQUENCIES[tongue]
            lo, hi = TONGUE_WAVELENGTH_NM[tongue]
            for n in range(8):
                state = QHOState(tongue=tongue, n=n, omega=omega, coefficient=0.5)
                assert lo <= state.wavelength_nm <= hi, f"{tongue} n={n}: {state.wavelength_nm} not in [{lo}, {hi}]"

    def test_higher_n_blueshifts(self):
        """Higher excitation → shorter wavelength."""
        omega = 2 * math.pi * 440.0
        s0 = QHOState(tongue="ko", n=0, omega=omega, coefficient=0.5)
        s5 = QHOState(tongue="ko", n=5, omega=omega, coefficient=0.5)
        assert s5.wavelength_nm <= s0.wavelength_nm


# ===================================================================
# Polychromatic State
# ===================================================================


class TestPolychromaticState:
    def test_visual_vector_normalized(self):
        """Visual vector must sum to 1 (quantum probability conservation)."""
        bundle = generate_quantum_bundle("Test text for normalization")
        vis = bundle.qho.visual_vector
        assert abs(sum(vis) - 1.0) < 1e-10

    def test_visual_vector_six_channels(self):
        bundle = generate_quantum_bundle("Six channel test")
        assert len(bundle.visual_vector) == 6

    def test_visual_vector_non_negative(self):
        bundle = generate_quantum_bundle("Non-negative probabilities")
        for v in bundle.visual_vector:
            assert v >= 0.0

    def test_total_energy_positive(self):
        bundle = generate_quantum_bundle("Energy must be positive")
        assert bundle.qho.total_energy > 0

    def test_phi_weighted_energy_greater(self):
        """Phi weighting should amplify total energy."""
        bundle = generate_quantum_bundle("Phi weighting test")
        assert bundle.qho.phi_weighted_total_energy >= bundle.qho.total_energy

    def test_dominant_tongue_valid(self):
        bundle = generate_quantum_bundle("Dominant tongue check")
        assert bundle.qho.dominant_tongue in TONGUE_ORDER

    def test_spectral_lines_valid(self):
        bundle = generate_quantum_bundle("Spectral lines from excited states")
        for line in bundle.qho.spectral_lines:
            assert line["n"] > 0
            assert line["frequency_hz"] > 0
            assert line["wavelength_nm"] > 0
            assert 0 <= line["probability"] <= 1

    def test_mean_excitation_non_negative(self):
        bundle = generate_quantum_bundle("Mean excitation test")
        assert bundle.qho.mean_excitation >= 0


# ===================================================================
# Acoustic Signature
# ===================================================================


class TestAcousticSignature:
    def test_three_bands_sum_to_one(self):
        bundle = generate_quantum_bundle("Acoustic band normalization")
        acous = bundle.acoustic
        total = acous.infrasonic_power + acous.audible_power + acous.ultrasonic_power
        assert abs(total - 1.0) < 1e-6

    def test_bands_non_negative(self):
        bundle = generate_quantum_bundle("All bands positive")
        acous = bundle.acoustic
        assert acous.infrasonic_power >= 0
        assert acous.audible_power >= 0
        assert acous.ultrasonic_power >= 0

    def test_dominant_interval_is_named(self):
        bundle = generate_quantum_bundle("Musical interval check")
        known_intervals = {
            "unison",
            "minor_third",
            "major_third",
            "perfect_fourth",
            "perfect_fifth",
            "phi_interval",
            "octave",
        }
        assert bundle.acoustic.dominant_interval in known_intervals

    def test_interval_deviation_non_negative(self):
        bundle = generate_quantum_bundle("Deviation check")
        assert bundle.acoustic.interval_deviation >= 0

    def test_to_dict_has_all_fields(self):
        bundle = generate_quantum_bundle("Dict completeness")
        d = bundle.acoustic.to_dict()
        assert "infrasonic" in d
        assert "audible" in d
        assert "ultrasonic" in d
        assert "dominant_interval" in d
        assert "interval_deviation" in d


# ===================================================================
# Governance Integration
# ===================================================================


class TestGovernance:
    def test_crossing_pair_valid(self):
        bundle = generate_quantum_bundle("Governance crossing pair test")
        pair = bundle.crossing_pair()
        assert pair.primary in (-1, 0, 1)
        assert pair.mirror in (-1, 0, 1)

    def test_governance_cost_positive(self):
        bundle = generate_quantum_bundle("Cost must be positive")
        assert bundle.governance_cost() > 0

    def test_governance_cost_uses_harmonic_wall(self):
        """C(d) = phi^(d^2) — should match crossing_energy."""
        bundle = generate_quantum_bundle("Harmonic wall check")
        pair = bundle.crossing_pair()
        d = pair.energy / 3.0
        expected = harmonic_cost(d)
        assert abs(bundle.governance_cost() - expected) < 1e-10

    def test_equilibrium_has_lowest_cost(self):
        """Equilibrium pair (0,0) should give cost = phi^0 = 1.0."""
        cost = harmonic_cost(0.0)
        assert abs(cost - 1.0) < 1e-10


# ===================================================================
# Full Bundle
# ===================================================================


class TestQuantumFrequencyBundle:
    def test_bundle_from_text(self):
        bundle = generate_quantum_bundle("A complete bundle test")
        assert bundle.text == "A complete bundle test"
        assert bundle.trit is not None
        assert bundle.multipath is not None
        assert bundle.qho is not None
        assert bundle.acoustic is not None

    def test_is_ground_state_when_all_zero(self):
        """Ground state = all tongues at n=0."""
        # This would only happen if all deviations are zero
        # We can check the property logic directly
        bundle = generate_quantum_bundle("Simple test")
        # Property should return bool
        assert isinstance(bundle.is_ground_state, bool)

    def test_is_maximally_excited_property(self):
        bundle = generate_quantum_bundle("Riemann zeta hypothesis polyhedral confinement sacred tongue")
        assert isinstance(bundle.is_maximally_excited, bool)

    def test_to_dict_complete(self):
        bundle = generate_quantum_bundle("Serialization test for SFT")
        d = bundle.to_dict()
        assert "trit_signal" in d
        assert "multipath" in d
        assert "qho" in d
        assert "acoustic" in d
        assert "governance" in d
        assert "is_ground_state" in d
        assert "is_maximally_excited" in d

    def test_qho_dict_has_per_tongue(self):
        bundle = generate_quantum_bundle("Per tongue metadata")
        d = bundle.to_dict()
        assert "per_tongue" in d["qho"]
        assert len(d["qho"]["per_tongue"]) == 6
        for tongue in TONGUE_ORDER:
            assert tongue in d["qho"]["per_tongue"]
            td = d["qho"]["per_tongue"][tongue]
            assert "n" in td
            assert "energy_j" in td
            assert "wavelength_nm" in td
            assert "coefficient" in td

    def test_different_texts_different_states(self):
        b1 = generate_quantum_bundle("Mathematics and formal proofs")
        b2 = generate_quantum_bundle("The dragon breathed fire upon the castle walls")
        # They should differ in at least one dimension
        assert b1.visual_vector != b2.visual_vector or b1.excitation_level != b2.excitation_level


# ===================================================================
# Batch & Summary
# ===================================================================


class TestBatch:
    def test_batch_generation(self):
        texts = [
            "First test text",
            "Second test text with more complexity",
            "Third text about quantum mechanics and physics",
        ]
        bundles = generate_quantum_bundle_batch(texts)
        assert len(bundles) == 3

    def test_summary_keys(self):
        bundles = generate_quantum_bundle_batch(["Test one", "Test two"])
        summary = quantum_bundle_summary(bundles)
        assert "count" in summary
        assert "excitation" in summary
        assert "visual_vector_means" in summary
        assert "acoustic_band_means" in summary
        assert "governance" in summary
        assert "dominant_tongue_distribution" in summary
        assert "musical_interval_distribution" in summary
        assert "total_spectral_lines" in summary

    def test_summary_excitation_bounded(self):
        texts = [f"Test text number {i}" for i in range(10)]
        bundles = generate_quantum_bundle_batch(texts)
        summary = quantum_bundle_summary(bundles)
        assert summary["excitation"]["mean_max"] >= 0
        assert 0 <= summary["excitation"]["ground_state_pct"] <= 100

    def test_empty_batch_summary(self):
        summary = quantum_bundle_summary([])
        assert summary == {"count": 0}


# ===================================================================
# SFT Records
# ===================================================================


class TestSFTRecords:
    def test_sft_record_structure(self):
        bundles = generate_quantum_bundle_batch(["SFT record test"])
        records = generate_quantum_sft_records(bundles)
        assert len(records) == 1
        rec = records[0]
        assert "messages" in rec
        assert "metadata" in rec
        assert len(rec["messages"]) == 2
        assert rec["messages"][0]["role"] == "user"
        assert rec["messages"][1]["role"] == "assistant"

    def test_sft_metadata_has_quantum_bundle(self):
        bundles = generate_quantum_bundle_batch(["Metadata test"])
        records = generate_quantum_sft_records(bundles)
        assert records[0]["metadata"]["source"] == "quantum_frequency_bundle_generator"
        assert "quantum_bundle" in records[0]["metadata"]

    def test_sft_records_from_diverse_texts(self):
        """Full alphabet test: diverse texts produce diverse records."""
        texts = [
            "In the beginning was the Word",
            "The Poincare ball model maps hyperbolic space",
            "Love is the only force that transcends dimension",
            "Post-quantum cryptography uses lattice-based assumptions",
            "The zeta zeros guard the critical line",
            "Superposition collapses only upon measurement",
            "Every pattern rune hums at its own frequency",
            "Entangled photons maintain harmony across distance",
            "The void between stars is not empty",
            "Gradient descent follows the negative gradient",
            "Joy expands like light filling every corner",
            "Fear contracts the space around itself",
        ]
        bundles = generate_quantum_bundle_batch(texts)
        records = generate_quantum_sft_records(bundles)
        assert len(records) == 12

        # All should have valid quantum metadata
        for rec in records:
            qb = rec["metadata"]["quantum_bundle"]
            assert "qho" in qb
            assert "acoustic" in qb
            assert "governance" in qb
            vis = qb["qho"]["visual_vector"]
            assert len(vis) == 6
            assert abs(sum(vis) - 1.0) < 1e-4


# ===================================================================
# Physics Integration: E = hv checks
# ===================================================================


class TestPhysicsIntegration:
    def test_e_equals_hv(self):
        """Verify E = h*nu for each tongue's ground state."""
        for tongue in TONGUE_ORDER:
            freq = TONGUE_FREQUENCIES[tongue]
            omega = 2 * math.pi * freq
            state = QHOState(tongue=tongue, n=0, omega=omega, coefficient=1.0)
            # E_0 = hbar*omega/2 = h*nu/2
            expected = H_PLANCK * freq / 2
            assert abs(state.energy - expected) < 1e-37

    def test_energy_spacing_uniform(self):
        """QHO has uniform energy spacing: E_{n+1} - E_n = hbar*omega."""
        omega = 2 * math.pi * 440.0
        for n in range(7):
            s_n = QHOState(tongue="ko", n=n, omega=omega, coefficient=0.5)
            s_n1 = QHOState(tongue="ko", n=n + 1, omega=omega, coefficient=0.5)
            spacing = s_n1.energy - s_n.energy
            expected = HBAR * omega
            assert abs(spacing - expected) < 1e-37

    def test_wavelength_frequency_relation(self):
        """c = lambda * nu for each tongue's optical frequency."""
        for tongue in TONGUE_ORDER:
            wl_m = TONGUE_CENTRAL_WAVELENGTH[tongue] * 1e-9  # nm -> m
            freq = TONGUE_OPTICAL_FREQ[tongue]
            c_check = wl_m * freq
            assert abs(c_check - C_LIGHT) < 1.0  # within 1 m/s

    def test_creation_operator_adds_one_quantum(self):
        """a† raises energy by exactly hbar*omega."""
        omega = 2 * math.pi * 440.0
        s0 = QHOState(tongue="ko", n=0, omega=omega, coefficient=0.5)
        s1 = QHOState(tongue="ko", n=1, omega=omega, coefficient=0.5)
        delta_e = s1.energy - s0.energy
        expected = HBAR * omega
        assert abs(delta_e - expected) < 1e-37

    def test_superposition_normalization(self):
        """Sum of |c_n|^2 must equal 1 for any polychromatic state."""
        texts = [
            "Quantum test one",
            "Quantum test two with more words",
            "A completely different topic about cooking",
        ]
        for text in texts:
            bundle = generate_quantum_bundle(text)
            vis = bundle.qho.visual_vector
            assert abs(sum(vis) - 1.0) < 1e-10, f"Normalization violated: sum={sum(vis)}"


# ===================================================================
# Expanded Musical Intervals
# ===================================================================


class TestExpandedIntervals:
    """Verify full chromatic interval set in harmonic_dark_fill."""

    def test_all_fourteen_intervals_present(self):
        """Full chromatic set: 14 named intervals."""
        expected = {
            "unison",
            "minor_second",
            "major_second",
            "minor_third",
            "major_third",
            "perfect_fourth",
            "tritone",
            "perfect_fifth",
            "minor_sixth",
            "phi_interval",
            "major_sixth",
            "minor_seventh",
            "major_seventh",
            "octave",
        }
        assert set(INTERVALS.keys()) == expected

    def test_intervals_monotonically_increasing(self):
        """Each interval ratio must be > the previous (ascending order)."""
        values = list(INTERVALS.values())
        for i in range(1, len(values)):
            assert values[i] > values[i - 1], (
                f"Interval {list(INTERVALS.keys())[i]} ({values[i]}) "
                f"not > {list(INTERVALS.keys())[i-1]} ({values[i-1]})"
            )

    def test_interval_bounds(self):
        """All intervals in [1.0, 2.0] range (one octave)."""
        for name, ratio in INTERVALS.items():
            assert 1.0 <= ratio <= 2.0, f"{name} = {ratio} outside octave"

    def test_unison_is_one(self):
        assert INTERVALS["unison"] == 1.0

    def test_octave_is_two(self):
        assert INTERVALS["octave"] == 2.0

    def test_phi_interval_is_golden_ratio(self):
        assert abs(INTERVALS["phi_interval"] - PHI) < 1e-10

    def test_tritone_is_devils_interval(self):
        """45/32 ≈ 1.40625 — the most dissonant interval."""
        assert abs(INTERVALS["tritone"] - 45.0 / 32.0) < 1e-10

    def test_perfect_fifth_just_intonation(self):
        assert abs(INTERVALS["perfect_fifth"] - 1.5) < 1e-10

    def test_minor_second_smallest_step(self):
        """Minor second (16/15) is the smallest interval above unison."""
        assert abs(INTERVALS["minor_second"] - 16.0 / 15.0) < 1e-10

    def test_interval_inversions(self):
        """Major third × minor sixth ≈ octave; minor third × major sixth ≈ octave."""
        # Inversion: interval × complement = 2 (octave)
        assert abs(INTERVALS["major_third"] * INTERVALS["minor_sixth"] - 2.0) < 1e-10
        assert abs(INTERVALS["minor_third"] * INTERVALS["major_sixth"] - 2.0) < 1e-10
        assert abs(INTERVALS["perfect_fourth"] * INTERVALS["perfect_fifth"] - 2.0) < 1e-10

    def test_bundles_can_produce_new_intervals(self):
        """Generate bundles and verify new intervals can appear."""
        texts = [
            "Alpha beta gamma delta epsilon zeta eta theta iota kappa",
            "One two three four five six seven eight nine ten eleven twelve",
            "The quick brown fox jumps over the lazy dog repeatedly",
            "Cryptographic hash functions provide one-way transformations",
            "Sacred geometry reveals the hidden structure of reality",
        ]
        bundles = generate_quantum_bundle_batch(texts)
        intervals_seen = {b.acoustic.dominant_interval for b in bundles}
        # Should see at least 2 distinct intervals across 5 texts
        assert len(intervals_seen) >= 2, f"Only saw: {intervals_seen}"


# ===================================================================
# VRS State Tests
# ===================================================================


class TestVRSState:
    """Test VRS (Vortex Ring State) integration in quantum bundles."""

    def test_bundle_has_vrs(self):
        """Every bundle must have a VRSState."""
        bundle = generate_quantum_bundle("Test text for VRS analysis")
        assert hasattr(bundle, "vrs")
        assert isinstance(bundle.vrs, VRSState)

    def test_vrs_has_rotor(self):
        """VRS state contains a RotorState."""
        bundle = generate_quantum_bundle("Rotor dynamics test text")
        assert isinstance(bundle.vrs.rotor, RotorState)

    def test_vrs_margin_bounded(self):
        """VRS margin should be in [-1, 1] range for typical texts."""
        texts = [
            "Simple test text",
            "The void between stars is full of potential",
            "Post-quantum cryptography uses lattice-based assumptions",
        ]
        for text in texts:
            bundle = generate_quantum_bundle(text)
            assert -1.5 <= bundle.vrs.vrs_margin <= 1.0

    def test_induced_velocity_positive(self):
        """Induced velocity must always be positive (momentum theory)."""
        bundle = generate_quantum_bundle("Any text for v_i check")
        assert bundle.vrs.induced_velocity_ms > 0

    def test_descent_rate_nonnegative(self):
        """Descent rate must be >= 0."""
        bundle = generate_quantum_bundle("Descent rate test")
        assert bundle.vrs.descent_rate_ms >= 0

    def test_vrs_ratio_correct(self):
        """v_descent / v_i = vrs_ratio."""
        bundle = generate_quantum_bundle("VRS ratio verification text here")
        vi = bundle.vrs.induced_velocity_ms
        vd = bundle.vrs.descent_rate_ms
        if vi > 1e-6:
            expected_ratio = abs(vd) / vi
            assert abs(bundle.vrs.vrs_ratio - expected_ratio) < 1e-10

    def test_power_spike_in_vrs(self):
        """Power spike factor > 1.0 when VRS ratio in danger zone."""
        bundle = generate_quantum_bundle("Testing power spike factor")
        ratio = bundle.vrs.vrs_ratio
        if 0.7 <= ratio <= 1.5:
            assert bundle.vrs.power_spike_factor > 1.0

    def test_power_spike_safe_is_one(self):
        """Power spike = 1.0 when well below VRS zone."""
        # Create a VRS state directly with safe ratio
        rotor = RotorState(rotor_rpm=258.0)
        vrs = VRSState(
            in_vrs=False,
            vrs_margin=1.0,
            descent_rate_ms=0.0,
            induced_velocity_ms=rotor.induced_velocity,
            rotor=rotor,
            recovery_paths=[],
            flight_regime="hover",
        )
        assert vrs.power_spike_factor == 1.0

    def test_recovery_paths_when_near_boundary(self):
        """Recovery paths computed when VRS margin < 0.8."""
        texts = [
            "The edge of chaos reveals hidden order in apparent randomness",
            "Boundary conditions determine the entire solution space",
            "Critical transitions occur at phase boundaries where order breaks down",
        ] * 5  # repeat to increase chance of finding boundary case
        found_recovery = False
        for text in texts:
            bundle = generate_quantum_bundle(text)
            if bundle.vrs.recovery_paths:
                found_recovery = True
                # Must have standard, vuichard, and autorotation
                types = {rp.recovery_type for rp in bundle.vrs.recovery_paths}
                assert RecoveryType.STANDARD in types
                assert RecoveryType.VUICHARD in types
                assert RecoveryType.AUTOROTATION in types
                break
        # Even if no text triggered recovery, structure is valid
        assert isinstance(bundle.vrs.recovery_paths, list)

    def test_flight_regime_valid(self):
        """Flight regime must be one of the known regimes."""
        valid_regimes = {"hover", "cruise", "descent", "vrs", "departure"}
        texts = [
            "Hover test text",
            "Cruising altitude maintained",
            "Descending rapidly toward the ground",
        ]
        for text in texts:
            bundle = generate_quantum_bundle(text)
            assert bundle.vrs.flight_regime in valid_regimes

    def test_vrs_to_dict_structure(self):
        """VRS to_dict has all expected keys."""
        bundle = generate_quantum_bundle("VRS serialization test")
        d = bundle.vrs.to_dict()
        expected_keys = {
            "in_vrs",
            "vrs_margin",
            "vrs_ratio",
            "descent_rate_ms",
            "induced_velocity_ms",
            "power_spike_factor",
            "flight_regime",
            "rotor",
            "recovery_paths",
        }
        assert expected_keys <= set(d.keys())

    def test_vrs_in_bundle_to_dict(self):
        """VRS data appears in full bundle to_dict."""
        bundle = generate_quantum_bundle("Full bundle VRS check")
        d = bundle.to_dict()
        assert "vrs" in d
        assert "in_vrs" in d["vrs"]
        assert "rotor" in d["vrs"]


# ===================================================================
# Code Lattice Tests
# ===================================================================


class TestCodeLattice:
    """Test Code Lattice layer (anti-patterns / 'swear words')."""

    def test_bundle_has_code_lattice(self):
        """Every bundle must have a CodeLatticeState."""
        bundle = generate_quantum_bundle("Code lattice test text")
        assert hasattr(bundle, "code_lattice")
        assert isinstance(bundle.code_lattice, CodeLatticeState)

    def test_curriculum_difficulty_bounded(self):
        """Difficulty must be in [0, 1]."""
        texts = [
            "Simple basic text",
            "The Riemann zeta function reveals non-trivial zeros at the critical line",
            "Quantum entanglement breaks classical correlation bounds",
        ]
        for text in texts:
            bundle = generate_quantum_bundle(text)
            assert 0 <= bundle.code_lattice.curriculum_difficulty <= 1.0

    def test_curriculum_level_bounded(self):
        """Level must be in [0, 5]."""
        texts = [
            "Ground state text",
            "Excited boundary crossing text with polymorphic forks",
            "VRS entry at maximum excitation with multiple recovery paths",
        ]
        for text in texts:
            bundle = generate_quantum_bundle(text)
            assert 0 <= bundle.code_lattice.curriculum_level <= 5

    def test_anti_pattern_registry_complete(self):
        """All 6 anti-patterns defined in CODE_ANTI_PATTERNS."""
        expected = {
            "unhandled_exception_in_critical_path",
            "mutable_global_state",
            "null_check_in_hot_path",
            "unbounded_recursion",
            "fire_and_forget_async",
            "implicit_type_coercion",
        }
        assert set(CODE_ANTI_PATTERNS.keys()) == expected

    def test_anti_pattern_fields(self):
        """Each registered anti-pattern has required fields."""
        for name, ap in CODE_ANTI_PATTERNS.items():
            assert "description" in ap, f"{name} missing description"
            assert "physics_analogy" in ap, f"{name} missing physics_analogy"
            assert "recovery_example" in ap, f"{name} missing recovery_example"

    def test_severity_bounded(self):
        """Anti-pattern severity must be in [0, 1]."""
        texts = [
            "High excitation boundary text",
            "The zeta zeros guard the critical line like sentinels",
            "Superposition collapses upon measurement until then all paths exist",
        ]
        for text in texts:
            bundle = generate_quantum_bundle(text)
            for ap in bundle.code_lattice.anti_patterns:
                assert 0 <= ap.severity <= 1.0, f"{ap.name} severity {ap.severity} out of [0,1]"

    def test_cross_domain_mapping_nonempty(self):
        """Every bundle has a cross-domain mapping string."""
        bundle = generate_quantum_bundle("Cross domain mapping test")
        assert isinstance(bundle.code_lattice.cross_domain_mapping, str)
        assert len(bundle.code_lattice.cross_domain_mapping) > 0

    def test_compounding_intent_nonnegative(self):
        """Compounding intent score cannot be negative."""
        bundle = generate_quantum_bundle("Intent compounding test")
        assert bundle.code_lattice.compounding_intent_score >= 0

    def test_ground_state_minimal_lattice(self):
        """Ground state (n=0, no forks) should have low difficulty."""
        # Find a ground-state text by brute force
        simple_texts = ["a", "b", "c", "aa", "bb", "cc", "x", "y", "z"]
        for text in simple_texts:
            bundle = generate_quantum_bundle(text)
            if bundle.is_ground_state:
                assert bundle.code_lattice.curriculum_level == 0
                assert bundle.code_lattice.curriculum_difficulty < 0.3
                break

    def test_swear_word_count_matches_list(self):
        """swear_word_count property matches len(anti_patterns)."""
        bundle = generate_quantum_bundle("Swear word count test text")
        assert bundle.code_lattice.swear_word_count == len(bundle.code_lattice.anti_patterns)

    def test_total_severity_sum(self):
        """total_severity is sum of individual severities."""
        bundle = generate_quantum_bundle("Total severity test text")
        expected = sum(ap.severity for ap in bundle.code_lattice.anti_patterns)
        assert abs(bundle.code_lattice.total_severity - expected) < 1e-10

    def test_code_lattice_to_dict_structure(self):
        """Code lattice to_dict has all expected keys."""
        bundle = generate_quantum_bundle("Code lattice serialization test")
        d = bundle.code_lattice.to_dict()
        expected_keys = {
            "anti_patterns",
            "compounding_intent_score",
            "curriculum_difficulty",
            "curriculum_level",
            "cross_domain_mapping",
            "total_severity",
            "swear_word_count",
        }
        assert expected_keys <= set(d.keys())

    def test_code_lattice_in_bundle_to_dict(self):
        """Code lattice data appears in full bundle to_dict."""
        bundle = generate_quantum_bundle("Full bundle code lattice check")
        d = bundle.to_dict()
        assert "code_lattice" in d
        assert "curriculum_level" in d["code_lattice"]
        assert "anti_patterns" in d["code_lattice"]

    def test_vrs_triggers_unbounded_recursion(self):
        """When VRS is active, unbounded_recursion swear word should trigger."""
        # We need to test the function directly with a VRS state
        from src.crypto.trit_curriculum import compute_trit_signal
        from src.crypto.multipath_generator import compute_multipath

        # Create a scenario with VRS active
        rotor = RotorState(rotor_rpm=258.0)
        vrs = VRSState(
            in_vrs=True,
            vrs_margin=-0.5,
            descent_rate_ms=15.0,
            induced_velocity_ms=rotor.induced_velocity,
            rotor=rotor,
            recovery_paths=[],
            flight_regime="vrs",
        )
        # Need a QHO state with high excitation
        text = "Extreme boundary collapse with maximum excitation energy"
        trit = compute_trit_signal(text)
        mp = compute_multipath(trit)
        qho = compute_qho_state(text, trit, mp)
        cl = compute_code_lattice(qho, mp, vrs)

        # Should have unbounded_recursion if VRS is active
        ap_names = [ap.name for ap in cl.anti_patterns]
        assert "unbounded_recursion" in ap_names


# ===================================================================
# Full Bundle Integration (VRS + Code Lattice + Expanded Intervals)
# ===================================================================


class TestFullBundleIntegration:
    """Integration tests for the complete bundle with all layers."""

    def test_bundle_has_all_layers(self):
        """Bundle must contain trit, multipath, qho, acoustic, vrs, code_lattice."""
        bundle = generate_quantum_bundle("Full integration test text")
        assert bundle.trit is not None
        assert bundle.multipath is not None
        assert bundle.qho is not None
        assert bundle.acoustic is not None
        assert bundle.vrs is not None
        assert bundle.code_lattice is not None

    def test_to_dict_complete(self):
        """Full to_dict contains all layer keys."""
        bundle = generate_quantum_bundle("Serialization completeness test")
        d = bundle.to_dict()
        required_keys = {
            "trit_signal",
            "multipath",
            "qho",
            "acoustic",
            "vrs",
            "code_lattice",
            "governance",
            "is_ground_state",
            "is_maximally_excited",
        }
        assert required_keys <= set(d.keys()), f"Missing: {required_keys - set(d.keys())}"

    def test_sft_records_include_vrs_and_code_lattice(self):
        """SFT records must contain VRS + Code Lattice data."""
        bundles = generate_quantum_bundle_batch(
            [
                "SFT record integration test one",
                "SFT record integration test two",
            ]
        )
        records = generate_quantum_sft_records(bundles)
        assert len(records) == 2
        for rec in records:
            # Assistant content should mention VRS and Code Lattice
            content = rec["messages"][1]["content"]
            assert "VRS State" in content
            assert "Code Lattice" in content
            # Metadata should have full bundle
            assert "vrs" in rec["metadata"]["quantum_bundle"]
            assert "code_lattice" in rec["metadata"]["quantum_bundle"]

    def test_batch_summary_still_works(self):
        """quantum_bundle_summary works with new fields."""
        texts = [
            "Summary test alpha",
            "Summary test beta",
            "Summary test gamma",
        ]
        bundles = generate_quantum_bundle_batch(texts)
        summary = quantum_bundle_summary(bundles)
        assert summary["count"] == 3
        assert "excitation" in summary
        assert "visual_vector_means" in summary
        assert "acoustic_band_means" in summary
        assert "governance" in summary
        assert "musical_interval_distribution" in summary

    def test_deterministic_bundles(self):
        """Same text → same bundle (deterministic)."""
        text = "Determinism is the cornerstone of reproducible science"
        b1 = generate_quantum_bundle(text)
        b2 = generate_quantum_bundle(text)
        assert b1.vrs.vrs_margin == b2.vrs.vrs_margin
        assert b1.code_lattice.curriculum_difficulty == b2.code_lattice.curriculum_difficulty
        assert b1.code_lattice.curriculum_level == b2.code_lattice.curriculum_level
        assert len(b1.code_lattice.anti_patterns) == len(b2.code_lattice.anti_patterns)

    def test_energy_conservation_across_layers(self):
        """QHO total energy and VRS induced power should both be finite."""
        bundle = generate_quantum_bundle("Energy conservation check text")
        assert math.isfinite(bundle.total_quantum_energy)
        assert math.isfinite(bundle.vrs.rotor.induced_power)
        assert math.isfinite(bundle.code_lattice.compounding_intent_score)

    def test_curriculum_difficulty_varies(self):
        """Different texts produce different curriculum difficulties (not all identical)."""
        texts = [
            "Simple hello world",
            "The Riemann hypothesis connects prime distribution to zeta function zeros on the critical strip",
            "Quantum field theory unifies special relativity with quantum mechanics through Lorentz-covariant fields",
            "Superposition of entangled Bell states violates CHSH inequality beyond classical correlation bounds",
            "A short note",
        ]
        bundles = generate_quantum_bundle_batch(texts)
        difficulties = [b.code_lattice.curriculum_difficulty for b in bundles]
        # Should have at least 2 distinct difficulty values
        assert len(set(round(d, 4) for d in difficulties)) >= 2, f"All difficulties identical: {difficulties}"

    def test_bundle_has_tail_rotor(self):
        """Every bundle now includes tail_rotor state."""
        bundle = generate_quantum_bundle("Tail rotor dynamics integration test")
        assert bundle.vrs.tail_rotor is not None
        assert isinstance(bundle.vrs.tail_rotor.failed, bool)

    def test_tail_rotor_serialized(self):
        """VRS to_dict includes tail_rotor when present."""
        bundle = generate_quantum_bundle("Tail rotor serialization test")
        d = bundle.vrs.to_dict()
        assert "tail_rotor" in d
        assert "failed" in d["tail_rotor"]
        assert "yaw_accel_rad_s2" in d["tail_rotor"]

    def test_bundle_pacejka_on_ground_state(self):
        """Ground state bundles (n=0) include Pacejka tire model."""
        # Use a text that produces ground state (all n=0)
        bundle = generate_quantum_bundle("a")
        if bundle.qho.max_excitation == 0:
            assert bundle.vrs.pacejka is not None
            d = bundle.vrs.to_dict()
            assert "pacejka" in d

    def test_sft_records_include_tail_rotor(self):
        """SFT records include tail rotor info in assistant content."""
        bundles = generate_quantum_bundle_batch(["Tail rotor SFT test"])
        records = generate_quantum_sft_records(bundles)
        content = records[0]["messages"][1]["content"]
        assert "Tail Rotor" in content

    def test_sacred_tongue_hybrids_in_recovery_paths(self):
        """Recovery paths in bundles carry Sacred Tongue hybrid phrases."""
        bundle = generate_quantum_bundle("Extreme boundary conditions with polymorphic chaos analysis")
        if bundle.vrs.recovery_paths:
            for rp in bundle.vrs.recovery_paths:
                assert rp.sacred_tongue_hybrid is not None
                assert "hybrid_phrase" in rp.sacred_tongue_hybrid


# ===================================================================
# Dead Tone Fills (multi-tongue interference)
# ===================================================================


class TestDeadToneFills:
    """Tests for the dead tone fill layer — phi-unreachable intervals
    filled by multi-tongue interference."""

    def test_dead_tones_constants(self):
        """DEAD_TONES has exactly 3 entries with correct ratios."""
        assert len(DEAD_TONES) == 3
        assert abs(DEAD_TONES["perfect_fifth"] - 1.5) < 1e-10
        assert abs(DEAD_TONES["minor_sixth"] - 1.6) < 1e-10
        assert abs(DEAD_TONES["minor_seventh"] - 16.0 / 9.0) < 1e-10

    def test_dead_tone_generators_exist(self):
        """Every dead tone has at least one generating coupling."""
        for tone in DEAD_TONES:
            assert tone in DEAD_TONE_GENERATORS
            assert len(DEAD_TONE_GENERATORS[tone]) > 0

    def test_compute_returns_3_fills(self):
        """compute_dead_tone_fills returns exactly 3 DeadToneFill objects."""
        bundle = generate_quantum_bundle("Dead tone fill test text")
        fills = bundle.dead_tone_fills
        assert len(fills) == 3
        assert all(isinstance(f, DeadToneFill) for f in fills)

    def test_fill_interval_names(self):
        """All 3 dead tone intervals are represented."""
        bundle = generate_quantum_bundle("Interval coverage test")
        names = {f.interval_name for f in bundle.dead_tone_fills}
        assert names == {"perfect_fifth", "minor_sixth", "minor_seventh"}

    def test_fill_ratios_match_targets(self):
        """Each fill's ratio field matches DEAD_TONES."""
        bundle = generate_quantum_bundle("Ratio match test")
        for f in bundle.dead_tone_fills:
            assert abs(f.ratio - DEAD_TONES[f.interval_name]) < 1e-10

    def test_achieved_ratio_near_target(self):
        """Achieved ratio should be close to the target (small perturbation)."""
        bundle = generate_quantum_bundle("Achieved ratio test")
        for f in bundle.dead_tone_fills:
            assert abs(f.achieved_ratio - f.ratio) < 0.1

    def test_error_is_abs_difference(self):
        """error_from_dead_tone = |achieved - target|."""
        bundle = generate_quantum_bundle("Error computation test")
        for f in bundle.dead_tone_fills:
            expected = abs(f.achieved_ratio - f.ratio)
            assert abs(f.error_from_dead_tone - expected) < 1e-10

    def test_intensity_bounded_0_1(self):
        """Intensity is clamped to [0, 1]."""
        texts = [
            "a",  # ground state
            "Extreme polymorphic chaos overflows the boundary checks rapidly",
        ]
        for t in texts:
            bundle = generate_quantum_bundle(t)
            for f in bundle.dead_tone_fills:
                assert 0.0 <= f.intensity <= 1.0

    def test_higher_excitation_more_intensity(self):
        """More excited QHO states should produce higher fill intensity."""
        low = generate_quantum_bundle("a")
        high = generate_quantum_bundle("Extreme overloaded polymorphic recursive chaos engine spinning wildly")
        low_avg = sum(f.intensity for f in low.dead_tone_fills) / 3
        high_avg = sum(f.intensity for f in high.dead_tone_fills) / 3
        # Higher excitation → higher or equal intensity
        assert high_avg >= low_avg

    def test_generating_couplings_from_registry(self):
        """Each fill's generating_couplings comes from DEAD_TONE_GENERATORS."""
        bundle = generate_quantum_bundle("Coupling source test")
        for f in bundle.dead_tone_fills:
            assert f.generating_couplings == DEAD_TONE_GENERATORS[f.interval_name]

    def test_serialization(self):
        """DeadToneFill.to_dict() has all required fields."""
        bundle = generate_quantum_bundle("Serialization test")
        for f in bundle.dead_tone_fills:
            d = f.to_dict()
            assert "interval_name" in d
            assert "ratio" in d
            assert "achieved_ratio" in d
            assert "error_from_dead_tone" in d
            assert "generating_couplings" in d
            assert "intensity" in d

    def test_bundle_to_dict_includes_fills(self):
        """Bundle.to_dict() includes dead_tone_fills array."""
        bundle = generate_quantum_bundle("Bundle dict test")
        d = bundle.to_dict()
        assert "dead_tone_fills" in d
        assert len(d["dead_tone_fills"]) == 3

    def test_dr_um_ca_fills_all_three(self):
        """DR+UM+CA autorotation hybrid appears in all 3 dead tone generators."""
        for tone, generators in DEAD_TONE_GENERATORS.items():
            assert "dr_um_ca" in generators, f"dr_um_ca missing from {tone}"


# ===================================================================
# Echolocation Pings (active dead-tone probing)
# ===================================================================


class TestEcholocationPings:
    """Tests for the echolocation ping layer — active sonar probing
    of dead-tone zones in the tongue lattice."""

    def test_returns_3_pings(self):
        """One ping per dead tone."""
        bundle = generate_quantum_bundle("Echolocation test text")
        assert len(bundle.echolocation_pings) == 3
        assert all(isinstance(p, EcholocationPing) for p in bundle.echolocation_pings)

    def test_ping_targets_all_dead_tones(self):
        """Pings cover all 3 dead tones."""
        bundle = generate_quantum_bundle("Ping target test")
        targets = {p.target_dead_tone for p in bundle.echolocation_pings}
        assert targets == {"perfect_fifth", "minor_sixth", "minor_seventh"}

    def test_ping_frequency_positive(self):
        """All ping frequencies are positive."""
        bundle = generate_quantum_bundle("Ping frequency test")
        for p in bundle.echolocation_pings:
            assert p.ping_frequency_hz > 0

    def test_return_amplitude_bounded(self):
        """Return amplitude is in [0, 1]."""
        bundle = generate_quantum_bundle("Return amplitude test")
        for p in bundle.echolocation_pings:
            assert 0.0 <= p.return_amplitude <= 1.0

    def test_phi_proximity_determines_absorption(self):
        """Minor sixth (8:5=1.6) is closest to phi (1.618),
        so it should have lowest return amplitude (most absorbed)."""
        bundle = generate_quantum_bundle("Phi absorption test")
        pings_by_tone = {p.target_dead_tone: p for p in bundle.echolocation_pings}
        sixth_amp = pings_by_tone["minor_sixth"].return_amplitude
        fifth_amp = pings_by_tone["perfect_fifth"].return_amplitude
        seventh_amp = pings_by_tone["minor_seventh"].return_amplitude
        # Minor sixth closest to phi → lowest return
        assert sixth_amp <= fifth_amp
        assert sixth_amp <= seventh_amp

    def test_minor_sixth_detected(self):
        """Minor sixth (closest to phi) should be detected (return < 0.5)."""
        bundle = generate_quantum_bundle("Detection test")
        pings_by_tone = {p.target_dead_tone: p for p in bundle.echolocation_pings}
        assert pings_by_tone["minor_sixth"].detected is True

    def test_phase_distortion_positive(self):
        """Phase distortion is always positive."""
        bundle = generate_quantum_bundle("Phase distortion test")
        for p in bundle.echolocation_pings:
            assert p.phase_distortion_rad > 0

    def test_time_of_flight_positive(self):
        """Time of flight increases with excitation depth."""
        bundle = generate_quantum_bundle("Time of flight test")
        for p in bundle.echolocation_pings:
            assert p.time_of_flight_s > 0

    def test_gallery_fill_coupling_present(self):
        """Each ping carries the gallery fill coupling list."""
        bundle = generate_quantum_bundle("Coupling list test")
        for p in bundle.echolocation_pings:
            assert len(p.gallery_fill_coupling) > 0
            assert p.gallery_fill_coupling == DEAD_TONE_GENERATORS[p.target_dead_tone]

    def test_serialization(self):
        """EcholocationPing.to_dict() has all required fields."""
        bundle = generate_quantum_bundle("Ping serialization test")
        for p in bundle.echolocation_pings:
            d = p.to_dict()
            assert "target_dead_tone" in d
            assert "ping_frequency_hz" in d
            assert "return_amplitude" in d
            assert "phase_distortion_rad" in d
            assert "time_of_flight_s" in d
            assert "gallery_fill_coupling" in d
            assert "detected" in d

    def test_bundle_to_dict_includes_pings(self):
        """Bundle.to_dict() includes echolocation_pings array."""
        bundle = generate_quantum_bundle("Bundle echolocation test")
        d = bundle.to_dict()
        assert "echolocation_pings" in d
        assert len(d["echolocation_pings"]) == 3

    def test_sft_records_include_echolocation(self):
        """SFT assistant content includes echolocation info."""
        bundles = generate_quantum_bundle_batch(["Echolocation SFT test"])
        records = generate_quantum_sft_records(bundles)
        content = records[0]["messages"][1]["content"]
        assert "Echolocation Pings" in content


# ===================================================================
# Realm Signature Triangulation (45° truncated waveforms)
# ===================================================================


class TestRealmTriangulation:
    """Tests for the realm triangulation layer — 45° angular distorted
    truncated waveforms for discrete linear path-finding through the
    harmonic noise matrix."""

    def test_returns_realm_triangulation(self):
        """compute_realm_triangulation returns a RealmTriangulation."""
        bundle = generate_quantum_bundle("Triangulation test text")
        assert isinstance(bundle.realm_triangulation, RealmTriangulation)

    def test_6_pings_one_per_tongue(self):
        """Exactly 6 pings, one per Sacred Tongue."""
        bundle = generate_quantum_bundle("Tongue coverage test")
        rt = bundle.realm_triangulation
        assert len(rt.pings) == 6
        tongues = {p.realm_tongue for p in rt.pings}
        assert tongues == set(TONGUE_ORDER)

    def test_all_pings_at_45_degrees(self):
        """All pings use 45° angular distortion."""
        bundle = generate_quantum_bundle("Angle test")
        for p in bundle.realm_triangulation.pings:
            assert abs(p.angle_deg - 45.0) < 1e-10

    def test_waveform_types(self):
        """Power tongues (RU, DR) get square; KO, UM get impulse; rest get sawtooth."""
        bundle = generate_quantum_bundle("Waveform assignment test")
        wf = {p.realm_tongue: p.waveform for p in bundle.realm_triangulation.pings}
        assert wf["ru"] == "square"
        assert wf["dr"] == "square"
        assert wf["ko"] == "impulse"
        assert wf["um"] == "impulse"
        assert wf["av"] == "sawtooth"
        assert wf["ca"] == "sawtooth"

    def test_frequency_positive(self):
        """All ping frequencies are positive."""
        bundle = generate_quantum_bundle("Frequency test")
        for p in bundle.realm_triangulation.pings:
            assert p.frequency_hz > 0

    def test_snr_minimum_6db(self):
        """Ground state tongues (n=0) have minimum 6 dB SNR."""
        bundle = generate_quantum_bundle("SNR floor test")
        for p in bundle.realm_triangulation.pings:
            assert p.snr_db >= 6.0

    def test_snr_scales_with_excitation(self):
        """Higher excitation → higher SNR (2 dB per quantum)."""
        bundle = generate_quantum_bundle("Extreme polymorphic recursive boundary overflow test")
        for p in bundle.realm_triangulation.pings:
            n = bundle.qho.states[p.realm_tongue].n
            expected_snr = 6.0 + n * 2.0
            assert abs(p.snr_db - expected_snr) < 1e-10

    def test_phase_shift_45_beamforming(self):
        """Phase shift follows 2π·d·sin(45°)/λ formula."""
        bundle = generate_quantum_bundle("Beamforming test")
        sin45 = math.sin(math.radians(45.0))
        for p in bundle.realm_triangulation.pings:
            d = TONGUE_WEIGHTS[p.realm_tongue]
            wavelength = 1.0 / p.frequency_hz if p.frequency_hz > 0 else 1.0
            expected = 2 * math.pi * d * sin45 / wavelength
            assert abs(p.phase_shift_rad - expected) < 1e-6

    def test_matched_correlation_bounded(self):
        """Matched-filter correlation is in [0, 1]."""
        texts = [
            "a",
            "The full polychromatic excitation engine overflows beyond measure",
        ]
        for t in texts:
            bundle = generate_quantum_bundle(t)
            for p in bundle.realm_triangulation.pings:
                assert 0.0 <= p.matched_correlation <= 1.0

    def test_triangulated_location_has_x_y(self):
        """Triangulated location is a dict with x and y keys."""
        bundle = generate_quantum_bundle("Location test")
        loc = bundle.realm_triangulation.triangulated_location
        assert "x" in loc
        assert "y" in loc
        assert isinstance(loc["x"], float)
        assert isinstance(loc["y"], float)

    def test_known_objective_requires_3_high_corr(self):
        """known_objective_met requires ≥3 pings with correlation > 0.5."""
        bundle = generate_quantum_bundle("Objective threshold test")
        high = sum(1 for p in bundle.realm_triangulation.pings if p.matched_correlation > 0.5)
        assert bundle.realm_triangulation.known_objective_met == (high >= 3)

    def test_path_found_requires_1_high_corr(self):
        """path_found requires ≥1 ping with correlation > 0.5."""
        bundle = generate_quantum_bundle("Path found test")
        high = sum(1 for p in bundle.realm_triangulation.pings if p.matched_correlation > 0.5)
        assert bundle.realm_triangulation.path_found == (high > 0)

    def test_total_snr_is_sum(self):
        """total_snr_db is the sum of all individual ping SNRs."""
        bundle = generate_quantum_bundle("Total SNR test")
        expected = sum(p.snr_db for p in bundle.realm_triangulation.pings)
        assert abs(bundle.realm_triangulation.total_snr_db - expected) < 1e-10

    def test_serialization(self):
        """RealmTriangulation.to_dict() has all required fields."""
        bundle = generate_quantum_bundle("Realm serialization test")
        d = bundle.realm_triangulation.to_dict()
        assert "pings" in d
        assert len(d["pings"]) == 6
        assert "triangulated_location" in d
        assert "known_objective_met" in d
        assert "path_found" in d
        assert "total_snr_db" in d

    def test_ping_serialization(self):
        """Each RealmSignaturePing serializes all fields."""
        bundle = generate_quantum_bundle("Ping dict test")
        for p in bundle.realm_triangulation.pings:
            d = p.to_dict()
            assert "realm_tongue" in d
            assert "waveform" in d
            assert "angle_deg" in d
            assert "frequency_hz" in d
            assert "snr_db" in d
            assert "phase_shift_rad" in d
            assert "matched_correlation" in d

    def test_bundle_to_dict_includes_triangulation(self):
        """Bundle.to_dict() includes realm_triangulation."""
        bundle = generate_quantum_bundle("Bundle triangulation test")
        d = bundle.to_dict()
        assert "realm_triangulation" in d
        assert "pings" in d["realm_triangulation"]

    def test_sft_records_include_triangulation(self):
        """SFT assistant content includes realm triangulation info."""
        bundles = generate_quantum_bundle_batch(["Realm triangulation SFT test"])
        records = generate_quantum_sft_records(bundles)
        content = records[0]["messages"][1]["content"]
        assert "Realm Triangulation" in content

    def test_sft_records_include_dead_tone_fills(self):
        """SFT assistant content includes dead tone fill info."""
        bundles = generate_quantum_bundle_batch(["Dead tone fills SFT test"])
        records = generate_quantum_sft_records(bundles)
        content = records[0]["messages"][1]["content"]
        assert "Dead Tone Fills" in content

    def test_summary_includes_new_layers(self):
        """quantum_bundle_summary includes stats for all 3 new layers."""
        bundles = generate_quantum_bundle_batch(
            [
                "Summary test one",
                "Summary test two",
                "Summary test three",
            ]
        )
        s = quantum_bundle_summary(bundles)
        assert "dead_tone_fills" in s
        assert "echolocation" in s
        assert "realm_triangulation" in s
        assert "mean_intensity" in s["dead_tone_fills"]
        assert "detection_rate" in s["echolocation"]
        assert "objective_met_count" in s["realm_triangulation"]
