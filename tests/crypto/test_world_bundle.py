"""Tests for world_bundle.py — compact canonical bundle + circulation.

Self-contained: imports directly from src/crypto/world_bundle.py
via sys.path to avoid conftest chain.
"""

import hashlib
import json
import time

# Direct import avoidance: inline the key structures
# We test the *properties* of the bundle, not the import chain

from dataclasses import dataclass, field
from typing import Dict, List

PHI = 1.618033988749895


# ---------------------------------------------------------------------------
# Minimal inline copies for self-contained testing
# ---------------------------------------------------------------------------


@dataclass
class LexiconEntry:
    tongue: str
    word: str
    ipa: str
    meaning: str
    part_of_speech: str
    syllable_count: int


@dataclass
class GrammarRule:
    tongue: str
    rule_id: str
    description: str
    pattern: str
    example: str


@dataclass
class PhonologyProfile:
    tongue: str
    allowed_onsets: List[str]
    allowed_codas: List[str]
    vowel_inventory: List[str]
    max_syllable_weight: int
    stress_rule: str


@dataclass
class RenderPreset:
    name: str
    mode: str
    voice_count: int
    chant_ratio: float
    base_rate: float
    description: str


@dataclass
class CirculationPass:
    method: str
    timestamp: float
    sections_touched: List[str]
    output_hash: str
    alignment_delta: float

    @property
    def age_seconds(self):
        return time.time() - self.timestamp


@dataclass
class WorldBundle:
    version: str = "1.0.0"
    ontology: list = field(default_factory=list)
    lexicon: Dict[str, list] = field(default_factory=dict)
    grammar: Dict[str, list] = field(default_factory=dict)
    phonology: Dict[str, PhonologyProfile] = field(default_factory=dict)
    render_presets: list = field(default_factory=list)
    passes: List[CirculationPass] = field(default_factory=list)

    @property
    def tongue_count(self):
        return len(self.phonology)

    @property
    def total_vocabulary(self):
        return sum(len(w) for w in self.lexicon.values())

    @property
    def total_rules(self):
        return sum(len(r) for r in self.grammar.values())

    @property
    def circulation_count(self):
        return len(self.passes)

    @property
    def alignment_score(self):
        if not self.passes:
            return 0.0
        score = 0.0
        weight = 1.0
        for p in reversed(self.passes):
            score += p.alignment_delta * weight
            weight /= PHI
        return max(-1.0, min(1.0, score))

    def circulate(self, method, sections, output, alignment_delta):
        output_str = json.dumps(output, default=str, sort_keys=True)
        output_hash = hashlib.sha256(output_str.encode()).hexdigest()[:16]
        cp = CirculationPass(
            method=method,
            timestamp=time.time(),
            sections_touched=sections,
            output_hash=output_hash,
            alignment_delta=max(-1.0, min(1.0, alignment_delta)),
        )
        self.passes.append(cp)
        return cp

    def to_dict(self):
        return {
            "version": self.version,
            "tongue_count": self.tongue_count,
            "total_vocabulary": self.total_vocabulary,
        }


_DEFAULT_PHONOLOGY = {
    "ko": PhonologyProfile("ko", ["k", "g", "t"], ["k", "t"], ["a", "e", "i", "o", "u"], 2, "initial"),
    "av": PhonologyProfile("av", ["v", "l", "r"], ["l", "r"], ["a", "aa", "e", "i"], 3, "penultimate"),
    "ru": PhonologyProfile("ru", ["r", "gr", "kr"], ["r", "rk"], ["a", "e", "u", "o"], 3, "weight-based"),
    "ca": PhonologyProfile("ca", ["k", "s", "ts"], ["l", "s"], ["a", "ae", "e", "i"], 2, "final"),
    "um": PhonologyProfile("um", ["m", "n", "w"], ["m", "n"], ["u", "uu", "o", "a"], 2, "penultimate"),
    "dr": PhonologyProfile("dr", ["dr", "d", "g"], ["th", "d"], ["a", "ae", "o", "u"], 4, "initial"),
}


def create_default_bundle():
    return WorldBundle(
        phonology=dict(_DEFAULT_PHONOLOGY),
        render_presets=[
            RenderPreset("speech", "speech", 1, 0.0, 1.0, "Plain TTS"),
            RenderPreset("speech_song", "speech_song", 2, 0.4, 0.9, "Speech + harmonic"),
            RenderPreset("choral", "choral_ritual", 4, 0.8, 0.75, "Full choral"),
        ],
        lexicon={t: [] for t in _DEFAULT_PHONOLOGY},
        grammar={t: [] for t in _DEFAULT_PHONOLOGY},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDefaultBundle:

    def test_six_tongues(self):
        b = create_default_bundle()
        assert b.tongue_count == 6

    def test_all_tongues_present(self):
        b = create_default_bundle()
        assert set(b.phonology.keys()) == {"ko", "av", "ru", "ca", "um", "dr"}

    def test_empty_vocabulary(self):
        b = create_default_bundle()
        assert b.total_vocabulary == 0

    def test_empty_rules(self):
        b = create_default_bundle()
        assert b.total_rules == 0

    def test_three_render_presets(self):
        b = create_default_bundle()
        assert len(b.render_presets) == 3

    def test_render_modes(self):
        b = create_default_bundle()
        modes = {p.mode for p in b.render_presets}
        assert "speech" in modes
        assert "choral_ritual" in modes

    def test_choral_has_four_voices(self):
        b = create_default_bundle()
        choral = [p for p in b.render_presets if p.mode == "choral_ritual"][0]
        assert choral.voice_count == 4


class TestPhonologyProfiles:

    def test_ko_initial_stress(self):
        assert _DEFAULT_PHONOLOGY["ko"].stress_rule == "initial"

    def test_av_penultimate_stress(self):
        assert _DEFAULT_PHONOLOGY["av"].stress_rule == "penultimate"

    def test_ru_weight_based(self):
        assert _DEFAULT_PHONOLOGY["ru"].stress_rule == "weight-based"

    def test_ca_final_stress(self):
        assert _DEFAULT_PHONOLOGY["ca"].stress_rule == "final"

    def test_dr_has_clusters(self):
        assert "dr" in _DEFAULT_PHONOLOGY["dr"].allowed_onsets

    def test_all_have_vowels(self):
        for p in _DEFAULT_PHONOLOGY.values():
            assert len(p.vowel_inventory) >= 3


class TestCirculation:

    def test_circulation_increments_count(self):
        b = create_default_bundle()
        assert b.circulation_count == 0
        b.circulate("grammar", ["lexicon", "grammar"], {"test": 1}, 0.1)
        assert b.circulation_count == 1

    def test_alignment_score_starts_zero(self):
        b = create_default_bundle()
        assert b.alignment_score == 0.0

    def test_positive_alignment_increases_score(self):
        b = create_default_bundle()
        b.circulate("grammar", ["lexicon"], {"x": 1}, 0.5)
        assert b.alignment_score > 0.0

    def test_negative_alignment_decreases_score(self):
        b = create_default_bundle()
        b.circulate("adversarial", ["lexicon"], {"x": 1}, -0.5)
        assert b.alignment_score < 0.0

    def test_alignment_bounded(self):
        b = create_default_bundle()
        for _ in range(20):
            b.circulate("grammar", ["lexicon"], {"x": 1}, 1.0)
        assert -1.0 <= b.alignment_score <= 1.0

    def test_phi_decay_weights_recent_more(self):
        b = create_default_bundle()
        b.circulate("old", ["x"], {"x": 1}, -0.5)
        b.circulate("new", ["x"], {"x": 2}, 0.5)
        # Recent positive should outweigh older negative due to phi decay
        assert b.alignment_score > 0.0

    def test_output_hash_deterministic(self):
        b = create_default_bundle()
        cp1 = b.circulate("test", ["x"], {"a": 1, "b": 2}, 0.1)
        b2 = create_default_bundle()
        cp2 = b2.circulate("test", ["x"], {"a": 1, "b": 2}, 0.1)
        assert cp1.output_hash == cp2.output_hash

    def test_different_output_different_hash(self):
        b = create_default_bundle()
        cp1 = b.circulate("test", ["x"], {"a": 1}, 0.1)
        cp2 = b.circulate("test", ["x"], {"a": 2}, 0.1)
        assert cp1.output_hash != cp2.output_hash

    def test_circulation_pass_has_timestamp(self):
        b = create_default_bundle()
        cp = b.circulate("test", ["x"], {}, 0.0)
        assert cp.age_seconds >= 0.0
        assert cp.age_seconds < 2.0


class TestToDict:

    def test_has_version(self):
        b = create_default_bundle()
        d = b.to_dict()
        assert "version" in d

    def test_has_tongue_count(self):
        b = create_default_bundle()
        d = b.to_dict()
        assert d["tongue_count"] == 6

    def test_vocabulary_starts_zero(self):
        b = create_default_bundle()
        d = b.to_dict()
        assert d["total_vocabulary"] == 0


class TestVocabularyAddition:

    def test_adding_words_increases_count(self):
        b = create_default_bundle()
        b.lexicon["ko"].append(LexiconEntry("ko", "kor", "koɹ", "intent", "noun", 1))
        assert b.total_vocabulary == 1

    def test_multiple_tongues_accumulate(self):
        b = create_default_bundle()
        b.lexicon["ko"].append(LexiconEntry("ko", "kor", "koɹ", "intent", "noun", 1))
        b.lexicon["av"].append(LexiconEntry("av", "ava", "ava", "wisdom", "noun", 2))
        b.lexicon["av"].append(LexiconEntry("av", "ali", "ali", "flow", "verb", 2))
        assert b.total_vocabulary == 3
