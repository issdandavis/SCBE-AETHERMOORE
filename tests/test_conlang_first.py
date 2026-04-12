"""Tests for the Conlang-First Sacred Tongue SFT Generator.

Tests the conlang-first pipeline: grammar lessons, lullabies,
story-to-tongue mapping, tongue comparisons, and pipeline ordering.
Validates that all Sacred Tongues use FULL NAMES (never abbreviations).
"""

import json
import math
import re
import pytest
from pathlib import Path

# We test via the generator functions directly
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.generate_conlang_first_sft import (
    TONGUE_FULL_NAMES,
    TONGUE_DOMAINS,
    TONGUE_MUSICAL_NOTES,
    STORY_TONGUE_MAP,
    SYSTEM_PROMPT,
    make_record,
    generate_grammar_lessons,
    generate_lullaby_records,
    generate_story_lesson_records,
    generate_tongue_comparison_records,
    generate_pipeline_order_record,
)
from src.crypto.sacred_tongues import TONGUES, TongueSpec
from src.crypto.tri_bundle import TONGUE_WEIGHTS, PHI
from src.crypto.harmonic_dark_fill import TONGUE_AUDIBLE_FREQ


# ===================================================================
# Full Name Policy — NEVER abbreviate the conlangs
# ===================================================================

class TestFullNamePolicy:
    """Sacred Tongues must always use full names, never abbreviations."""

    FULL_NAMES = {"Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"}

    def test_all_six_tongues_have_full_names(self):
        assert len(TONGUE_FULL_NAMES) == 6
        assert set(TONGUE_FULL_NAMES.values()) == self.FULL_NAMES

    def test_all_six_tongues_have_domains(self):
        assert set(TONGUE_DOMAINS.keys()) == set(TONGUES.keys())

    def test_all_six_tongues_have_musical_notes(self):
        assert set(TONGUE_MUSICAL_NOTES.keys()) == set(TONGUES.keys())

    def test_system_prompt_uses_full_names(self):
        for name in self.FULL_NAMES:
            assert name in SYSTEM_PROMPT, f"System prompt missing full name: {name}"

    def test_system_prompt_no_bare_abbreviations(self):
        """No standalone 'KO', 'AV', 'RU', 'CA', 'UM', 'DR' as labels."""
        # These abbreviations should not appear as standalone tongue references
        # (they can appear in compound contexts like "440 Hz, A4")
        for abbr in ["— KO:", "— AV:", "— RU:", "— CA:", "— UM:", "— DR:"]:
            assert abbr not in SYSTEM_PROMPT

    def test_full_names_match_tongue_specs(self):
        for code, spec in TONGUES.items():
            assert TONGUE_FULL_NAMES[code] == spec.name


# ===================================================================
# Grammar Lessons
# ===================================================================

class TestGrammarLessons:
    @pytest.fixture
    def lessons(self):
        return generate_grammar_lessons()

    def test_eighteen_lessons(self, lessons):
        assert len(lessons) == 18  # 3 per tongue × 6 tongues

    def test_three_per_tongue(self, lessons):
        types = [r["metadata"]["record_type"] for r in lessons]
        assert types.count("grammar_introduction") == 6
        assert types.count("grammar_vocabulary") == 6
        assert types.count("grammar_phonetics") == 6

    def test_all_have_system_prompt(self, lessons):
        for r in lessons:
            assert r["messages"][0]["role"] == "system"
            assert r["messages"][0]["content"] == SYSTEM_PROMPT

    def test_all_have_three_messages(self, lessons):
        for r in lessons:
            assert len(r["messages"]) == 3
            assert r["messages"][1]["role"] == "user"
            assert r["messages"][2]["role"] == "assistant"

    def test_intro_mentions_256_words(self, lessons):
        intros = [r for r in lessons if r["metadata"]["record_type"] == "grammar_introduction"]
        for r in intros:
            assert "256" in r["messages"][2]["content"]

    def test_vocab_shows_prefixes_and_suffixes(self, lessons):
        vocabs = [r for r in lessons if r["metadata"]["record_type"] == "grammar_vocabulary"]
        for r in vocabs:
            content = r["messages"][2]["content"]
            assert "prefixes" in content.lower() or "Prefixes" in content
            assert "suffixes" in content.lower() or "Suffixes" in content

    def test_phonetics_has_practice_phrase(self, lessons):
        phonetics = [r for r in lessons if r["metadata"]["record_type"] == "grammar_phonetics"]
        for r in phonetics:
            assert "Practice" in r["messages"][2]["content"] or "practice" in r["messages"][2]["content"]

    def test_every_lesson_uses_full_tongue_name(self, lessons):
        for r in lessons:
            concept_id = r["metadata"]["concept_id"]
            code = concept_id.split("_")[1]  # e.g. "grammar_ko_intro" → "ko"
            full_name = TONGUE_FULL_NAMES[code]
            content = r["messages"][2]["content"]
            assert full_name in content, f"Missing {full_name} in {concept_id}"

    def test_intro_mentions_phi_weight(self, lessons):
        intros = [r for r in lessons if r["metadata"]["record_type"] == "grammar_introduction"]
        for r in intros:
            content = r["messages"][2]["content"]
            assert "Phi weight" in content or "phi" in content.lower()

    def test_intro_mentions_harmonic_frequency(self, lessons):
        intros = [r for r in lessons if r["metadata"]["record_type"] == "grammar_introduction"]
        for r in intros:
            content = r["messages"][2]["content"]
            assert "Hz" in content

    def test_vocab_shows_encoding_rule(self, lessons):
        vocabs = [r for r in lessons if r["metadata"]["record_type"] == "grammar_vocabulary"]
        for r in vocabs:
            content = r["messages"][2]["content"]
            assert "0x" in content  # byte encoding examples

    def test_all_lessons_have_metadata(self, lessons):
        for r in lessons:
            meta = r["metadata"]
            assert meta["source"] == "conlang_first_generator"
            assert "content_hash" in meta
            assert len(meta["content_hash"]) == 16


# ===================================================================
# Lullaby Records
# ===================================================================

class TestLullabies:
    @pytest.fixture
    def lullabies(self):
        return generate_lullaby_records()

    def test_eight_lullabies(self, lullabies):
        assert len(lullabies) == 8  # 2 shared + 6 per-tongue

    def test_six_tongue_lullaby_exists(self, lullabies):
        ids = [r["metadata"]["concept_id"] for r in lullabies]
        assert "lullaby_six_tongues" in ids

    def test_phi_counting_song_exists(self, lullabies):
        ids = [r["metadata"]["concept_id"] for r in lullabies]
        assert "lullaby_phi_counting" in ids

    def test_six_goodnight_lullabies(self, lullabies):
        goodnights = [r for r in lullabies if "goodnight" in r["metadata"]["concept_id"]]
        assert len(goodnights) == 6

    def test_six_tongue_lullaby_has_all_names(self, lullabies):
        lullaby = next(r for r in lullabies if r["metadata"]["concept_id"] == "lullaby_six_tongues")
        content = lullaby["messages"][2]["content"]
        for name in TONGUE_FULL_NAMES.values():
            assert name in content, f"Six Tongue Lullaby missing {name}"

    def test_six_tongue_lullaby_has_frequencies(self, lullabies):
        lullaby = next(r for r in lullabies if r["metadata"]["concept_id"] == "lullaby_six_tongues")
        content = lullaby["messages"][2]["content"]
        assert "440" in content
        assert "523" in content
        assert "294" in content or "293" in content
        assert "659" in content
        assert "196" in content
        assert "392" in content

    def test_phi_counting_has_weights(self, lullabies):
        phi_song = next(r for r in lullabies if r["metadata"]["concept_id"] == "lullaby_phi_counting")
        content = phi_song["messages"][2]["content"]
        # Should show all 6 phi weights
        assert "1.000" in content
        assert "1.618" in content
        assert "2.618" in content
        assert "4.236" in content
        assert "6.854" in content
        assert "11.09" in content or "11.090" in content

    def test_goodnight_has_actual_tokens(self, lullabies):
        goodnights = [r for r in lullabies if "goodnight" in r["metadata"]["concept_id"]]
        for r in goodnights:
            content = r["messages"][2]["content"]
            # Should contain apostrophe-joined tokens
            assert "'" in content

    def test_all_lullabies_correct_type(self, lullabies):
        for r in lullabies:
            assert r["metadata"]["record_type"] == "lullaby"


# ===================================================================
# Story Lessons
# ===================================================================

class TestStoryLessons:
    @pytest.fixture
    def lessons(self):
        return generate_story_lesson_records()

    def test_ten_story_lessons(self, lessons):
        assert len(lessons) == 10

    def test_all_stories_mapped(self, lessons):
        ids = {r["metadata"]["concept_id"] for r in lessons}
        for filename in STORY_TONGUE_MAP:
            expected_id = f"story_{filename.replace('.md', '')}"
            assert expected_id in ids, f"Missing story: {filename}"

    def test_each_lesson_mentions_tongue_by_full_name(self, lessons):
        for r in lessons:
            content = r["messages"][2]["content"]
            # At least one full tongue name should appear
            has_full_name = any(name in content for name in TONGUE_FULL_NAMES.values())
            assert has_full_name, f"No full tongue name in {r['metadata']['concept_id']}"

    def test_three_golem_houses_maps_to_draumric(self, lessons):
        golem = next(r for r in lessons if "three-golem-houses" in r["metadata"]["concept_id"])
        assert "Draumric" in golem["messages"][2]["content"]

    def test_raven_maps_to_koraelin(self, lessons):
        raven = next(r for r in lessons if "raven" in r["metadata"]["concept_id"])
        assert "Kor'aelin" in raven["messages"][2]["content"]

    def test_goldilocks_maps_to_runethic(self, lessons):
        goldi = next(r for r in lessons if "goldilocks" in r["metadata"]["concept_id"])
        assert "Runethic" in goldi["messages"][2]["content"]

    def test_ant_maps_to_avali(self, lessons):
        ant = next(r for r in lessons if "ant" in r["metadata"]["concept_id"])
        assert "Avali" in ant["messages"][2]["content"]

    def test_fizzle_maps_to_cassisivadan(self, lessons):
        fizzle = next(r for r in lessons if "fizzle" in r["metadata"]["concept_id"])
        assert "Cassisivadan" in fizzle["messages"][2]["content"]

    def test_tortoise_maps_to_umbroth(self, lessons):
        tortoise = next(r for r in lessons if "tortoise" in r["metadata"]["concept_id"])
        assert "Umbroth" in tortoise["messages"][2]["content"]

    def test_counting_rhymes_mentions_all_tongues(self, lessons):
        counting = next(r for r in lessons if "counting-rhymes" in r["metadata"]["concept_id"])
        content = counting["messages"][2]["content"]
        for name in TONGUE_FULL_NAMES.values():
            assert name in content

    def test_story_lessons_have_pre_tokenizer_exercise(self, lessons):
        single_tongue = [r for r in lessons
                         if STORY_TONGUE_MAP.get(
                             r["metadata"]["concept_id"].replace("story_", "") + ".md"
                         ) is not None]
        for r in single_tongue:
            content = r["messages"][2]["content"]
            # Should mention pre-tokenizer exercise or the full tongue pipeline
            has_exercise = "tokeniz" in content.lower() or "exercise" in content.lower()
            assert has_exercise, f"No exercise in {r['metadata']['concept_id']}"


# ===================================================================
# Tongue Comparisons
# ===================================================================

class TestTongueComparisons:
    @pytest.fixture
    def comparisons(self):
        return generate_tongue_comparison_records()

    def test_seven_comparison_records(self, comparisons):
        assert len(comparisons) == 7  # 1 interval map + 6 cross-tongue

    def test_interval_map_exists(self, comparisons):
        ids = [r["metadata"]["concept_id"] for r in comparisons]
        assert "tongue_intervals" in ids

    def test_six_cross_tongue_records(self, comparisons):
        cross = [r for r in comparisons if r["metadata"]["concept_id"].startswith("cross_")]
        assert len(cross) == 6

    def test_interval_map_mentions_all_tongues(self, comparisons):
        intervals = next(r for r in comparisons if r["metadata"]["concept_id"] == "tongue_intervals")
        content = intervals["messages"][2]["content"]
        for name in TONGUE_FULL_NAMES.values():
            assert name in content

    def test_cross_tongue_shows_byte_0x48(self, comparisons):
        cross = [r for r in comparisons if r["metadata"]["concept_id"].startswith("cross_")]
        for r in cross:
            content = r["messages"][2]["content"]
            assert "0x48" in content

    def test_cross_tongue_shows_all_six_encodings(self, comparisons):
        cross = [r for r in comparisons if r["metadata"]["concept_id"].startswith("cross_")]
        for r in cross:
            content = r["messages"][2]["content"]
            # Should show tokens from all 6 tongues
            assert content.count("'") >= 6  # at least 6 apostrophe-joined tokens

    def test_interval_map_mentions_voice_leading(self, comparisons):
        intervals = next(r for r in comparisons if r["metadata"]["concept_id"] == "tongue_intervals")
        content = intervals["messages"][2]["content"]
        assert "voice" in content.lower() or "Tymoczko" in content


# ===================================================================
# Pipeline Order
# ===================================================================

class TestPipelineOrder:
    @pytest.fixture
    def pipeline(self):
        return generate_pipeline_order_record()

    def test_one_record(self, pipeline):
        assert len(pipeline) == 1

    def test_correct_type(self, pipeline):
        assert pipeline[0]["metadata"]["record_type"] == "pipeline_order"

    def test_four_phases(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content
        assert "Phase 4" in content

    def test_tokenizer_is_last(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        # Phase 4 should mention tokenizer
        phase4_pos = content.index("Phase 4")
        tokenize_pos = content.index("Tokenize", phase4_pos)
        assert tokenize_pos > phase4_pos

    def test_stories_before_tokenizer(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        stories_pos = content.index("Stories")
        tokenize_pos = content.index("THEN Tokenize")
        assert stories_pos < tokenize_pos

    def test_grammar_before_stories(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        grammar_pos = content.index("Learn the Language")
        stories_pos = content.index("Stories and Songs")
        assert grammar_pos < stories_pos

    def test_mentions_all_six_tongues(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        for name in TONGUE_FULL_NAMES.values():
            assert name in content

    def test_mentions_story_mappings(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        assert "Three Golem Houses" in content
        assert "Draumric" in content
        assert "Raven" in content
        assert "Kor'aelin" in content

    def test_mentions_162_dimensions(self, pipeline):
        content = pipeline[0]["messages"][2]["content"]
        assert "162" in content


# ===================================================================
# Record Format
# ===================================================================

class TestRecordFormat:
    def test_make_record_structure(self):
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        record = make_record(messages, "test_id", "test_type")
        assert record["messages"] == messages
        assert record["metadata"]["source"] == "conlang_first_generator"
        assert record["metadata"]["concept_id"] == "test_id"
        assert record["metadata"]["record_type"] == "test_type"
        assert "timestamp" in record["metadata"]
        assert "content_hash" in record["metadata"]

    def test_content_hash_deterministic(self):
        messages = [{"role": "user", "content": "same"}]
        r1 = make_record(messages, "a", "b")
        r2 = make_record(messages, "a", "b")
        assert r1["metadata"]["content_hash"] == r2["metadata"]["content_hash"]

    def test_content_hash_changes_with_content(self):
        m1 = [{"role": "user", "content": "alpha"}]
        m2 = [{"role": "user", "content": "beta"}]
        r1 = make_record(m1, "a", "b")
        r2 = make_record(m2, "a", "b")
        assert r1["metadata"]["content_hash"] != r2["metadata"]["content_hash"]


# ===================================================================
# Integration: Full Pipeline
# ===================================================================

class TestFullPipeline:
    """Run the full generator and verify the complete output."""

    @pytest.fixture(scope="class")
    def all_records(self):
        records = []
        records.extend(generate_grammar_lessons())
        records.extend(generate_lullaby_records())
        records.extend(generate_story_lesson_records())
        records.extend(generate_tongue_comparison_records())
        records.extend(generate_pipeline_order_record())
        return records

    def test_total_record_count(self, all_records):
        assert len(all_records) == 44

    def test_all_records_valid_json(self, all_records):
        for r in all_records:
            # Verify it can round-trip through JSON
            json_str = json.dumps(r, ensure_ascii=False)
            parsed = json.loads(json_str)
            assert parsed["messages"] == r["messages"]

    def test_no_duplicate_concept_ids(self, all_records):
        ids = [r["metadata"]["concept_id"] for r in all_records]
        # concept_ids can repeat across record_types, but combo should be unique
        combos = [(r["metadata"]["concept_id"], r["metadata"]["record_type"]) for r in all_records]
        assert len(combos) == len(set(combos))

    def test_all_records_have_system_message(self, all_records):
        for r in all_records:
            assert r["messages"][0]["role"] == "system"

    def test_record_type_distribution(self, all_records):
        types = {}
        for r in all_records:
            rt = r["metadata"]["record_type"]
            types[rt] = types.get(rt, 0) + 1
        assert types["grammar_introduction"] == 6
        assert types["grammar_vocabulary"] == 6
        assert types["grammar_phonetics"] == 6
        assert types["lullaby"] == 8
        assert types["story_lesson"] == 10
        assert types["tongue_comparison"] == 7
        assert types["pipeline_order"] == 1

    def test_no_abbreviation_in_any_assistant_message(self, all_records):
        """No assistant message should use standalone abbreviations for tongues."""
        # Check that full names appear and bare abbreviations don't serve as labels
        bare_patterns = [
            "the KO tongue", "the AV tongue", "the RU tongue",
            "the CA tongue", "the UM tongue", "the DR tongue",
        ]
        for r in all_records:
            content = r["messages"][2]["content"]
            for pattern in bare_patterns:
                assert pattern not in content, (
                    f"Found abbreviation '{pattern}' in {r['metadata']['concept_id']}"
                )

    def test_every_tongue_covered(self, all_records):
        """Every tongue should appear in at least one record's assistant content."""
        for name in TONGUE_FULL_NAMES.values():
            found = any(
                name in r["messages"][2]["content"]
                for r in all_records
            )
            assert found, f"{name} not found in any record"
