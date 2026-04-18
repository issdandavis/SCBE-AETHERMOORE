"""Tests for the Tri-Bundle DNA Encoder — 3×3×3 braided signal architecture."""

from src.crypto.tri_bundle import (
    PHI,
    BUNDLE_SCALE,
    TONGUE_WEIGHTS,
    TONGUE_FREQUENCIES,
    TONGUE_PAIRS,
    Trit,
    LightStrand,
    SoundStrand,
    MathStrand,
    InnerBundle,
    TriBundleCluster,
    encode_byte,
    encode_bytes,
    encode_text,
    encode_polyglot,
    encode_polyglot_text,
    find_convergence_points,
    convergence_summary,
    _intent_from_byte,
    _convergence_trit,
)

# ===================================================================
# Constants
# ===================================================================


class TestConstants:
    def test_phi_value(self):
        assert abs(PHI - 1.6180339887) < 1e-6

    def test_tongue_weights_are_phi_powers(self):
        codes = ["ko", "av", "ru", "ca", "um", "dr"]
        for i, code in enumerate(codes):
            expected = PHI**i
            assert abs(TONGUE_WEIGHTS[code] - expected) < 1e-6, f"{code} weight wrong"

    def test_bundle_scale_is_3_phi_cubed(self):
        expected = (3**PHI) ** 3
        assert abs(BUNDLE_SCALE - expected) < 0.01

    def test_bundle_scale_approximately_207(self):
        assert 200 < BUNDLE_SCALE < 210

    def test_six_tongues(self):
        assert len(TONGUE_WEIGHTS) == 6
        assert len(TONGUE_FREQUENCIES) == 6

    def test_three_tongue_pairs(self):
        assert len(TONGUE_PAIRS) == 3
        assert TONGUE_PAIRS[0] == ("ko", "av")
        assert TONGUE_PAIRS[1] == ("ru", "ca")
        assert TONGUE_PAIRS[2] == ("um", "dr")


# ===================================================================
# Trit Logic
# ===================================================================


class TestTrit:
    def test_intent_low_bytes_negative(self):
        for b in range(0, 85):
            assert _intent_from_byte(b) == Trit.MINUS

    def test_intent_mid_bytes_neutral(self):
        for b in range(85, 170):
            assert _intent_from_byte(b) == Trit.ZERO

    def test_intent_high_bytes_positive(self):
        for b in range(170, 256):
            assert _intent_from_byte(b) == Trit.PLUS

    def test_convergence_trit_close(self):
        assert _convergence_trit(0.5) == Trit.PLUS

    def test_convergence_trit_far(self):
        assert _convergence_trit(5.0) == Trit.MINUS

    def test_convergence_trit_neutral(self):
        assert _convergence_trit(2.0) == Trit.ZERO


# ===================================================================
# Sub-strands
# ===================================================================


class TestSubStrands:
    def test_light_strand_tuple(self):
        ls = LightStrand(presence=1, weight=1.618, intent=Trit.PLUS)
        t = ls.as_tuple()
        assert len(t) == 3
        assert t[0] == 1.0
        assert abs(t[1] - 1.618) < 1e-6
        assert t[2] == 1.0

    def test_sound_strand_tuple(self):
        ss = SoundStrand(frequency=440.0, amplitude=0.75, phase=1.5)
        t = ss.as_tuple()
        assert len(t) == 3
        assert t[0] == 440.0
        assert t[1] == 0.75
        assert t[2] == 1.5

    def test_math_strand_tuple(self):
        ms = MathStrand(value=2.5, operation=42, result=Trit.ZERO)
        t = ms.as_tuple()
        assert len(t) == 3
        assert t[0] == 2.5
        assert t[1] == 42.0
        assert t[2] == 0.0


# ===================================================================
# Inner Bundle
# ===================================================================


class TestInnerBundle:
    def test_as_vector_is_9_elements(self):
        bundle = InnerBundle(
            strand_a=(1.0, 2.0, 3.0),
            strand_b=(4.0, 5.0, 6.0),
            strand_c=(7.0, 8.0, 9.0),
            bundle_type="light",
        )
        vec = bundle.as_vector()
        assert len(vec) == 9
        assert vec == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)

    def test_inner_braid_hash_is_32_bytes(self):
        bundle = InnerBundle(
            strand_a=(1.0, 0.0, 0.0),
            strand_b=(0.0, 0.0, 0.0),
            strand_c=(0.0, 0.0, 0.0),
            bundle_type="test",
        )
        h = bundle.inner_braid_hash()
        assert len(h) == 32

    def test_inner_braid_hash_is_deterministic(self):
        bundle = InnerBundle(
            strand_a=(1.0, 2.0, 3.0),
            strand_b=(4.0, 5.0, 6.0),
            strand_c=(7.0, 8.0, 9.0),
            bundle_type="light",
        )
        assert bundle.inner_braid_hash() == bundle.inner_braid_hash()

    def test_inner_braid_hash_order_dependent(self):
        """Non-commutativity: swapping strands changes the hash."""
        b1 = InnerBundle(
            strand_a=(1.0, 0.0, 0.0),
            strand_b=(0.0, 1.0, 0.0),
            strand_c=(0.0, 0.0, 1.0),
            bundle_type="test",
        )
        b2 = InnerBundle(
            strand_a=(0.0, 1.0, 0.0),  # swapped a and b
            strand_b=(1.0, 0.0, 0.0),
            strand_c=(0.0, 0.0, 1.0),
            bundle_type="test",
        )
        assert b1.inner_braid_hash() != b2.inner_braid_hash()

    def test_different_bundle_type_different_hash(self):
        args = dict(
            strand_a=(1.0, 0.0, 0.0),
            strand_b=(0.0, 0.0, 0.0),
            strand_c=(0.0, 0.0, 0.0),
        )
        b1 = InnerBundle(**args, bundle_type="light")
        b2 = InnerBundle(**args, bundle_type="sound")
        assert b1.inner_braid_hash() != b2.inner_braid_hash()


# ===================================================================
# TriBundleCluster
# ===================================================================


class TestTriBundleCluster:
    def test_as_vector_is_27_elements(self):
        cluster = encode_byte(0x42, "ko")
        vec = cluster.as_vector()
        assert len(vec) == 27

    def test_cluster_id_is_32_bytes(self):
        cluster = encode_byte(0x42, "ko")
        assert len(cluster.cluster_id()) == 32

    def test_cluster_id_deterministic(self):
        c1 = encode_byte(0x42, "ko", position=5)
        c2 = encode_byte(0x42, "ko", position=5)
        assert c1.cluster_id() == c2.cluster_id()

    def test_different_bytes_different_ids(self):
        c1 = encode_byte(0x42, "ko")
        c2 = encode_byte(0x43, "ko")
        assert c1.cluster_id() != c2.cluster_id()

    def test_different_tongues_different_ids(self):
        c1 = encode_byte(0x42, "ko")
        c2 = encode_byte(0x42, "av")
        assert c1.cluster_id() != c2.cluster_id()

    def test_different_positions_different_ids(self):
        c1 = encode_byte(0x42, "ko", position=0)
        c2 = encode_byte(0x42, "ko", position=1)
        assert c1.cluster_id() != c2.cluster_id()

    def test_effective_states(self):
        cluster = encode_byte(0x42, "ko")
        assert abs(cluster.effective_states - BUNDLE_SCALE) < 1e-6

    def test_energy_is_positive(self):
        cluster = encode_byte(0x42, "ko")
        assert cluster.energy() > 0

    def test_sync_score_bounded(self):
        cluster = encode_byte(0x42, "ko")
        score = cluster.synchronization_score()
        assert 0.0 <= score <= 1.0

    def test_cluster_id_hex_is_64_chars(self):
        cluster = encode_byte(0x42, "ko")
        assert len(cluster.cluster_id_hex()) == 64


# ===================================================================
# Encoding functions
# ===================================================================


class TestEncoding:
    def test_encode_byte_all_tongues(self):
        """Every tongue produces a valid cluster for every byte."""
        for tongue in TONGUE_WEIGHTS:
            for byte_val in (0, 1, 127, 128, 255):
                cluster = encode_byte(byte_val, tongue)
                assert cluster.tongue_code == tongue
                assert len(cluster.as_vector()) == 27

    def test_encode_bytes_length(self):
        data = b"hello"
        clusters = encode_bytes(data, "ko")
        assert len(clusters) == 5

    def test_encode_bytes_positions_sequential(self):
        clusters = encode_bytes(b"abc", "av")
        assert [c.position for c in clusters] == [0, 1, 2]

    def test_encode_text_utf8(self):
        clusters = encode_text("love", "ko")
        assert len(clusters) == 4
        # 'l' = 0x6C
        assert clusters[0].tongue_code == "ko"

    def test_encode_text_unicode(self):
        """UTF-8 multi-byte chars produce more clusters than chars."""
        clusters = encode_text("\u00e9", "ru")  # é = 2 bytes in UTF-8
        assert len(clusters) == 2


# ===================================================================
# Polyglot encoding
# ===================================================================


class TestPolyglot:
    def test_polyglot_produces_6_clusters_per_position(self):
        pcs = encode_polyglot(b"A")
        assert len(pcs) == 1
        assert len(pcs[0].clusters) == 6

    def test_polyglot_text(self):
        pcs = encode_polyglot_text("hi")
        assert len(pcs) == 2

    def test_full_vector_is_162_elements(self):
        pcs = encode_polyglot(b"X")
        vec = pcs[0].full_vector()
        assert len(vec) == 162  # 6 tongues × 27 dimensions

    def test_global_sync_bounded(self):
        pcs = encode_polyglot(b"Z")
        sync = pcs[0].global_sync()
        assert 0.0 <= sync <= 1.0

    def test_sync_matrix_has_15_pairs(self):
        """C(6,2) = 15 tongue pairs."""
        pcs = encode_polyglot(b"Q")
        matrix = pcs[0].synchronization_matrix()
        assert len(matrix) == 15

    def test_active_tongues_returns_list(self):
        pcs = encode_polyglot(b"\xff")
        active = pcs[0].active_tongues(threshold=0.0)
        assert isinstance(active, list)
        # With threshold 0.0, all tongues should be "active" (amplitude >= 0)
        assert len(active) == 6

    def test_byte_val_preserved(self):
        pcs = encode_polyglot(b"\x42")
        assert pcs[0].byte_val == 0x42


# ===================================================================
# Convergence detection
# ===================================================================


class TestConvergence:
    def test_find_convergence_points(self):
        pcs = encode_polyglot_text("love")
        points = find_convergence_points(pcs, threshold=0.0)
        # With threshold 0, everything should converge
        assert len(points) == 4

    def test_convergence_summary_keys(self):
        pcs = encode_polyglot_text("truth")
        summary = convergence_summary(pcs)
        assert "count" in summary
        assert "mean_sync" in summary
        assert "dimensions_per_position" in summary
        assert summary["dimensions_per_position"] == 162
        assert summary["bundle_scale"] == BUNDLE_SCALE

    def test_convergence_summary_empty(self):
        summary = convergence_summary([])
        assert summary["count"] == 0


# ===================================================================
# Non-commutativity (the key property)
# ===================================================================


class TestNonCommutativity:
    def test_outer_braid_order_matters(self):
        """Swapping Light and Sound bundles changes cluster identity."""
        c = encode_byte(0x42, "ko")
        # Build a cluster with swapped light/sound
        swapped = TriBundleCluster(
            light=c.sound,  # sound in light's slot
            sound=c.light,  # light in sound's slot
            math=c.math,
            tongue_code="ko",
            position=0,
        )
        assert c.cluster_id() != swapped.cluster_id()

    def test_same_data_same_id(self):
        """Identical construction = identical identity."""
        c1 = encode_byte(0x42, "ko", position=7)
        c2 = encode_byte(0x42, "ko", position=7)
        assert c1.cluster_id() == c2.cluster_id()
        assert c1.as_vector() == c2.as_vector()


# ===================================================================
# Integration: E=MC² pipeline sketch
# ===================================================================


class TestIntegration:
    def test_full_pipeline_love_in_all_tongues(self):
        """Encode 'love' through all 6 tongues, check convergence."""
        pcs = encode_polyglot_text("love")
        assert len(pcs) == 4

        # Each position has 162 dimensions
        for pc in pcs:
            assert len(pc.full_vector()) == 162

        # Summary should be valid
        summary = convergence_summary(pcs)
        assert summary["count"] == 4
        assert 0.0 <= summary["mean_sync"] <= 1.0

    def test_different_words_different_convergence(self):
        """'love' and 'hate' should produce different sync patterns."""
        love_pcs = encode_polyglot_text("love")
        hate_pcs = encode_polyglot_text("hate")

        love_syncs = [pc.global_sync() for pc in love_pcs]
        hate_syncs = [pc.global_sync() for pc in hate_pcs]

        # They should not be identical (different bytes → different patterns)
        assert love_syncs != hate_syncs

    def test_cluster_ids_unique_across_sequence(self):
        """Every position in a word should have a unique cluster ID."""
        pcs = encode_polyglot_text("truth")
        ids = set()
        for pc in pcs:
            for tongue, cluster in pc.clusters.items():
                cid = cluster.cluster_id_hex()
                assert cid not in ids, f"Duplicate cluster ID at pos {pc.position}, tongue {tongue}"
                ids.add(cid)
        # 5 positions × 6 tongues = 30 unique IDs
        assert len(ids) == 30
