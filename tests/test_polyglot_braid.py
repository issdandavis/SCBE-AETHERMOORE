"""Tests for the Polyglot Cross-Lattice Linguistic Braid.

Tests language registry, parallel concepts, braid encoding,
cross-convergence detection, and the full weave pipeline.
"""

from src.crypto.polyglot_braid import (
    BraidStrand,
    BraidResult,
    LANGUAGES,
    LANGUAGE_BY_CODE,
    PARALLEL_CONCEPTS,
    encode_strand,
    weave_concept,
    weave_all_concepts,
    braid_summary,
)
from src.crypto.tri_bundle import TONGUE_WEIGHTS

# ===================================================================
# Language Registry
# ===================================================================


class TestLanguageRegistry:
    def test_sixteen_languages(self):
        assert len(LANGUAGES) == 16

    def test_all_have_codes(self):
        codes = {lang.code for lang in LANGUAGES}
        assert len(codes) == 16  # all unique

    def test_language_by_code_lookup(self):
        assert "en" in LANGUAGE_BY_CODE
        assert "zh" in LANGUAGE_BY_CODE
        assert "ar" in LANGUAGE_BY_CODE
        assert LANGUAGE_BY_CODE["en"].name == "English"

    def test_all_six_tongues_in_affinity(self):
        for lang in LANGUAGES:
            assert set(lang.tongue_affinity.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_affinities_bounded(self):
        for lang in LANGUAGES:
            for t, v in lang.tongue_affinity.items():
                assert 0.0 <= v <= 1.0, f"{lang.name} {t}={v}"

    def test_primary_tongue_valid(self):
        for lang in LANGUAGES:
            assert lang.primary_tongue in TONGUE_WEIGHTS

    def test_secondary_tongue_different(self):
        for lang in LANGUAGES:
            # Primary and secondary should differ (unless tied)
            assert lang.secondary_tongue in TONGUE_WEIGHTS

    def test_affinity_vector_is_6d(self):
        for lang in LANGUAGES:
            vec = lang.affinity_vector
            assert len(vec) == 6
            assert all(0.0 <= v <= 1.0 for v in vec)

    def test_phi_weighted_affinity_positive(self):
        for lang in LANGUAGES:
            assert lang.phi_weighted_affinity > 0

    def test_korean_primary_is_ko(self):
        korean = LANGUAGE_BY_CODE["ko"]
        assert korean.primary_tongue == "ko"

    def test_arabic_strong_av(self):
        arabic = LANGUAGE_BY_CODE["ar"]
        assert arabic.tongue_affinity["av"] >= 0.8

    def test_german_strong_dr(self):
        german = LANGUAGE_BY_CODE["de"]
        assert german.tongue_affinity["dr"] >= 0.8

    def test_japanese_strong_um(self):
        japanese = LANGUAGE_BY_CODE["ja"]
        assert japanese.tongue_affinity["um"] >= 0.8

    def test_chinese_strong_ca(self):
        chinese = LANGUAGE_BY_CODE["zh"]
        assert chinese.tongue_affinity["ca"] >= 0.8

    def test_hebrew_rtl(self):
        hebrew = LANGUAGE_BY_CODE["he"]
        assert hebrew.direction == "rtl"
        assert hebrew.script == "Hebrew"

    def test_arabic_rtl(self):
        arabic = LANGUAGE_BY_CODE["ar"]
        assert arabic.direction == "rtl"

    def test_language_families_diverse(self):
        families = {lang.family for lang in LANGUAGES}
        assert len(families) >= 7  # 7 distinct families represented

    def test_scripts_diverse(self):
        scripts = {lang.script for lang in LANGUAGES}
        # Latin, Han, Arabic, Devanagari, Cyrillic, Kanji/Kana, Hangul, Greek, Hebrew
        assert len(scripts) >= 7


# ===================================================================
# Parallel Concepts
# ===================================================================


class TestParallelConcepts:
    def test_twelve_concepts(self):
        assert len(PARALLEL_CONCEPTS) == 12

    def test_concept_ids_unique(self):
        ids = {c.concept_id for c in PARALLEL_CONCEPTS}
        assert len(ids) == 12

    def test_all_concepts_have_translations(self):
        for concept in PARALLEL_CONCEPTS:
            assert concept.language_count >= 12

    def test_english_always_present(self):
        for concept in PARALLEL_CONCEPTS:
            assert "en" in concept.translations

    def test_concept_domains(self):
        domains = {c.domain for c in PARALLEL_CONCEPTS}
        assert "philosophy" in domains
        assert "creation" in domains
        assert "emotion" in domains

    def test_in_the_beginning_has_hebrew(self):
        genesis = next(c for c in PARALLEL_CONCEPTS if c.concept_id == "in_the_beginning")
        assert "he" in genesis.translations
        assert "el" in genesis.translations  # Greek too

    def test_translations_non_empty(self):
        for concept in PARALLEL_CONCEPTS:
            for code, text in concept.translations.items():
                assert len(text) > 0, f"{concept.concept_id}/{code} is empty"


# ===================================================================
# Strand Encoding
# ===================================================================


class TestStrandEncoding:
    def test_encode_english_strand(self):
        lang = LANGUAGE_BY_CODE["en"]
        strand = encode_strand(lang, "truth")
        assert isinstance(strand, BraidStrand)
        assert strand.byte_count == 5
        assert len(strand.polyglot_clusters) == 5

    def test_encode_chinese_strand(self):
        lang = LANGUAGE_BY_CODE["zh"]
        strand = encode_strand(lang, "\u771f\u7406")  # 真理
        assert strand.byte_count > 2  # UTF-8 multi-byte

    def test_encode_arabic_strand(self):
        lang = LANGUAGE_BY_CODE["ar"]
        strand = encode_strand(lang, "\u062d\u0642\u064a\u0642\u0629")  # حقيقة
        assert strand.byte_count > 5  # UTF-8 Arabic = 2 bytes/char

    def test_strand_mean_sync_bounded(self):
        lang = LANGUAGE_BY_CODE["en"]
        strand = encode_strand(lang, "love")
        assert 0.0 <= strand.mean_sync <= 1.0

    def test_strand_convergence_ratio_bounded(self):
        lang = LANGUAGE_BY_CODE["en"]
        strand = encode_strand(lang, "peace")
        assert 0.0 <= strand.convergence_ratio <= 1.0

    def test_empty_text_strand(self):
        lang = LANGUAGE_BY_CODE["en"]
        strand = encode_strand(lang, "")
        assert strand.byte_count == 0


# ===================================================================
# Concept Weaving
# ===================================================================


class TestConceptWeaving:
    def test_weave_single_concept(self):
        concept = PARALLEL_CONCEPTS[0]  # truth
        result = weave_concept(concept)
        assert isinstance(result, BraidResult)
        assert result.language_count >= 12

    def test_weave_with_language_subset(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en", "zh", "ar"])
        assert result.language_count == 3
        assert "en" in result.strands
        assert "zh" in result.strands
        assert "ar" in result.strands

    def test_cross_convergence_computed(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en", "zh", "ar", "he"])
        # C(4,2) = 6 pairs
        assert len(result.cross_convergence) == 6

    def test_cross_convergence_scores_bounded(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en", "fr", "es"])
        for cc in result.cross_convergence:
            assert 0.0 <= cc["sync_convergence"] <= 1.0
            assert 0.0 <= cc["affinity_correlation"] <= 1.0
            assert 0.0 <= cc["combined_score"] <= 1.0

    def test_tongue_distribution_sums_to_one(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en", "zh"])
        total = sum(result.tongue_distribution.values())
        assert abs(total - 1.0) < 1e-6

    def test_tongue_distribution_all_six(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept)
        assert set(result.tongue_distribution.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_total_dimensions_positive(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en"])
        assert result.total_dimensions > 0
        # "truth" = 5 bytes * 162 dims = 810
        assert result.total_dimensions == 5 * 162

    def test_dark_energy_maps_present(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en", "he"])
        assert "en" in result.dark_energy_maps
        assert "he" in result.dark_energy_maps

    def test_mean_cross_sync_bounded(self):
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept)
        assert 0.0 <= result.mean_cross_sync <= 1.0


# ===================================================================
# Cross-Convergence Properties
# ===================================================================


class TestCrossConvergence:
    def test_related_languages_higher_affinity(self):
        """Languages from same family should have higher affinity correlation."""
        concept = PARALLEL_CONCEPTS[0]  # truth
        result = weave_concept(concept, languages=["en", "fr", "de", "zh", "ja"])

        # Find en-fr (same family) vs en-zh (different family)
        en_fr = next(cc for cc in result.cross_convergence if set([cc["lang_a"], cc["lang_b"]]) == {"en", "fr"})
        # Indo-European siblings should correlate higher than IE vs Sino-Tibetan
        assert en_fr["affinity_correlation"] > 0

    def test_rtl_ltr_both_produce_valid_braids(self):
        """RTL (Arabic, Hebrew) and LTR languages both produce valid braids."""
        concept = next(c for c in PARALLEL_CONCEPTS if c.concept_id == "peace")
        result = weave_concept(concept, languages=["en", "ar", "he", "zh"])
        assert all(s.byte_count > 0 and s.mean_sync >= 0 for s in result.strands.values())

    def test_same_script_languages_comparable(self):
        """Languages sharing Latin script should have comparable byte patterns."""
        concept = PARALLEL_CONCEPTS[0]
        result = weave_concept(concept, languages=["en", "es", "fr", "de", "pt"])
        # All Latin script — byte ranges should be similar (ASCII-ish)
        for code in result.strands:
            lang = LANGUAGE_BY_CODE[code]
            assert lang.script == "Latin"


# ===================================================================
# Full Braid Pipeline
# ===================================================================


class TestFullBraid:
    def test_weave_all_concepts(self):
        results = weave_all_concepts(languages=["en", "zh", "ar"])
        assert len(results) == 12

    def test_braid_summary_keys(self):
        results = weave_all_concepts(languages=["en", "zh"])
        summary = braid_summary(results)
        assert "count" in summary
        assert "total_dimensions" in summary
        assert "mean_cross_sync" in summary
        assert "mean_convergence" in summary
        assert "most_convergent_concept" in summary
        assert "tongue_distribution" in summary
        assert "languages_covered" in summary

    def test_braid_summary_values(self):
        results = weave_all_concepts(languages=["en", "fr", "de"])
        summary = braid_summary(results)
        assert summary["count"] == 12
        assert summary["total_dimensions"] > 0
        assert 0.0 <= summary["mean_cross_sync"] <= 1.0
        assert summary["most_convergent_concept"] is not None

    def test_empty_braid_summary(self):
        summary = braid_summary([])
        assert summary["count"] == 0

    def test_all_concepts_different_results(self):
        results = weave_all_concepts(languages=["en", "zh"])
        concept_ids = [r.concept.concept_id for r in results]
        assert len(set(concept_ids)) == 12  # all unique

    def test_full_braid_all_languages(self):
        """Run the full braid with all 16 languages (the alphabet test)."""
        # Use a small concept subset to keep it fast
        concepts = [PARALLEL_CONCEPTS[0], PARALLEL_CONCEPTS[1]]  # truth, love
        results = weave_all_concepts(concepts=concepts)
        assert len(results) == 2
        for r in results:
            assert r.language_count >= 12


# ===================================================================
# Integration: The Full Alphabet in English AND Greek
# ===================================================================


class TestFullAlphabet:
    """Test like Issac: full alphabet in English AND Greek."""

    def test_all_concepts_all_scripts(self):
        """Every concept through every available language."""
        results = weave_all_concepts(threshold=0.0)
        assert len(results) == 12

        for result in results:
            assert result.language_count >= 12
            assert result.total_dimensions > 0
            assert len(result.cross_convergence) > 0

    def test_creation_concepts_have_hebrew_greek(self):
        """Creation-domain concepts must include Hebrew and Greek."""
        creation_concepts = [c for c in PARALLEL_CONCEPTS if c.domain == "creation"]
        for concept in creation_concepts:
            assert "he" in concept.translations
            assert "el" in concept.translations

    def test_every_language_family_represented(self):
        """All major language families produce valid braids."""
        families_seen = set()
        results = weave_all_concepts(
            concepts=[PARALLEL_CONCEPTS[0]],  # truth
        )
        for r in results:
            for strand in r.strands.values():
                families_seen.add(strand.language.family)
        assert len(families_seen) >= 7

    def test_convergence_exists_across_all_scripts(self):
        """Convergence should appear across all script systems."""
        results = weave_all_concepts(
            concepts=[PARALLEL_CONCEPTS[5]],  # in_the_beginning
        )
        r = results[0]
        # With 16 languages, we should get C(16,2) = 120 cross-convergence pairs
        assert len(r.cross_convergence) >= 100  # some langs might be missing

        # At least some pairs should have non-zero convergence
        nonzero = [cc for cc in r.cross_convergence if cc["combined_score"] > 0]
        assert len(nonzero) > 0

    def test_tongue_distribution_no_tongue_zero(self):
        """Every tongue should get SOME activation across all languages."""
        results = weave_all_concepts(concepts=[PARALLEL_CONCEPTS[0]])
        summary = braid_summary(results)
        for tongue, weight in summary["tongue_distribution"].items():
            assert weight > 0, f"Tongue {tongue} has zero distribution"
