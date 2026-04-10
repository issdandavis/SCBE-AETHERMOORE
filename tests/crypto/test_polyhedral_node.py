"""Tests for polyhedral_node.py — dense multi-view training record generator.

Self-contained: inlines all logic. Tests the full alphabet.
"""

import math
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Inline constants and logic (mirrors src/crypto/polyhedral_node.py)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
TAU = 2.0 * math.pi

TONGUE_WEIGHTS = {
    "ko": PHI ** 0, "av": PHI ** 1, "ru": PHI ** 2,
    "ca": PHI ** 3, "um": PHI ** 4, "dr": PHI ** 5,
}
ALL_TONGUES = tuple(TONGUE_WEIGHTS.keys())

TONGUE_FREQUENCIES = {
    "ko": 440.00, "av": 523.25, "ru": 293.66,
    "ca": 659.25, "um": 196.00, "dr": 392.00,
}

COMPLEMENT_MAP = {
    "ko": "dr", "av": "um", "ru": "ca",
    "ca": "ru", "um": "av", "dr": "ko",
}

BASELINE_FREQUENCIES = {
    "perfect_fifth": 330.0, "minor_sixth": 352.0, "minor_seventh": 392.0,
}
DEAD_TONES = tuple(BASELINE_FREQUENCIES.keys())

RATIO_DISSONANCE = {
    "unison": (1.0, 0.00), "octave": (2.0, 0.02),
    "perfect_fifth": (3.0/2.0, 0.05), "perfect_fourth": (4.0/3.0, 0.08),
    "major_third": (5.0/4.0, 0.12), "minor_third": (6.0/5.0, 0.15),
    "major_sixth": (5.0/3.0, 0.18), "minor_sixth": (8.0/5.0, 0.22),
    "major_second": (9.0/8.0, 0.30), "minor_seventh": (16.0/9.0, 0.35),
    "major_seventh": (15.0/8.0, 0.55), "phi_interval": (PHI, 0.40),
    "tritone": (45.0/32.0, 0.75), "minor_second": (16.0/15.0, 0.90),
}

ALLOW_THRESHOLD = 0.25
QUARANTINE_THRESHOLD = 0.50
ESCALATE_THRESHOLD = 0.75

TONGUE_STRESS = {
    "ko": "even", "av": "flowing", "ru": "percussive",
    "ca": "rising", "um": "falling", "dr": "grounded",
}
TONGUE_RATE = {
    "ko": 0.95, "av": 1.00, "ru": 0.90,
    "ca": 1.08, "um": 0.82, "dr": 0.80,
}
TONGUE_CHANT = {
    "ko": 0.10, "av": 0.20, "ru": 0.25,
    "ca": 0.30, "um": 0.35, "dr": 0.22,
}


class PropagationLabel(Enum):
    POSITIVE = "positive"
    BOUNDARY = "boundary"
    NEGATIVE = "negative"
    TERMINAL = "terminal"


class GovernanceVerdict(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass(frozen=True)
class TongueVector:
    ko: float; av: float; ru: float; ca: float; um: float; dr: float

    @property
    def dominant(self):
        vals = {"ko": self.ko, "av": self.av, "ru": self.ru,
                "ca": self.ca, "um": self.um, "dr": self.dr}
        return max(vals, key=vals.get)

    @property
    def as_tuple(self):
        return (self.ko, self.av, self.ru, self.ca, self.um, self.dr)

    @property
    def norm(self):
        return math.sqrt(sum(v * v for v in self.as_tuple))

    @property
    def phi_weighted_norm(self):
        weights = list(TONGUE_WEIGHTS.values())
        return math.sqrt(sum((v * w) ** 2 for v, w in zip(self.as_tuple, weights)))


@dataclass(frozen=True)
class ProsodyFeatures:
    rate: float; energy: float; chant_ratio: float
    stress_pattern: str; agent_frequency_hz: float


@dataclass(frozen=True)
class DarkFillFeatures:
    infra_freq: float; infra_amplitude: float
    audible_freq: float; audible_amplitude: float
    ultra_freq: float; ultra_amplitude: float
    darkness: float


@dataclass(frozen=True)
class ConsonanceFeatures:
    baseline_hz: float; agent_hz: float; frequency_ratio: float
    nearest_interval: str; interval_deviation: float
    dissonance_score: float; beat_frequency: float


@dataclass(frozen=True)
class PolyhedralRecord:
    node_hash: str; generation: int; parent_hash: Optional[str]; timestamp: float
    raw_input: str; dominant_tongue: str; dead_tone: str; excitation: float
    tongue_vector: TongueVector; prosody: ProsodyFeatures
    consonance: ConsonanceFeatures; dark_fill: DarkFillFeatures
    verdict: GovernanceVerdict; propagation_label: PropagationLabel
    tongue_affinity: Dict[str, float]; complement_tongue: str


def compute_tongue_vector(raw_input, dominant_tongue):
    activations = {t: 0.0 for t in ALL_TONGUES}
    data = raw_input.encode("utf-8", errors="replace")
    if len(data) == 0:
        activations[dominant_tongue] = 1.0
        return TongueVector(**activations)
    for byte_val in data:
        for i, tongue in enumerate(ALL_TONGUES):
            threshold = (TONGUE_WEIGHTS[tongue] / TONGUE_WEIGHTS["dr"]) * 255
            if byte_val >= threshold:
                activations[tongue] += 1.0 / len(data)
    activations[dominant_tongue] = min(1.0, activations[dominant_tongue] + 0.3)
    max_val = max(activations.values()) or 1.0
    activations = {t: v / max_val for t, v in activations.items()}
    return TongueVector(**activations)


def compute_prosody(dominant_tongue, excitation):
    base_rate = TONGUE_RATE[dominant_tongue]
    rate = max(0.5, min(2.0, base_rate + 0.02 * (excitation - 3.0)))
    energy = max(0.0, min(1.0, 0.4 + 0.06 * excitation))
    chant_ratio = TONGUE_CHANT[dominant_tongue]
    stress = TONGUE_STRESS[dominant_tongue]
    base_freq = TONGUE_FREQUENCIES[dominant_tongue]
    agent_hz = base_freq * (1.0 + 0.05 * (excitation - 3.0))
    agent_hz = max(20.0, min(20000.0, agent_hz))
    return ProsodyFeatures(rate=rate, energy=energy, chant_ratio=chant_ratio,
                           stress_pattern=stress, agent_frequency_hz=agent_hz)


def normalize_ratio(f_a, f_b):
    if f_a <= 0 or f_b <= 0: return 1.0
    ratio = max(f_a, f_b) / min(f_a, f_b)
    while ratio >= 2.0: ratio /= 2.0
    while ratio < 1.0: ratio *= 2.0
    return ratio


def nearest_consonance(ratio):
    best_name, best_dev, best_dis = "tritone", float("inf"), 0.75
    for name, (ref, dis) in RATIO_DISSONANCE.items():
        dev = abs(ratio - ref)
        if dev < best_dev:
            best_dev, best_name, best_dis = dev, name, dis
    return best_name, best_dev, best_dis


def compute_consonance(agent_hz, dead_tone, tolerance=0.03):
    baseline_hz = BASELINE_FREQUENCIES[dead_tone]
    ratio = normalize_ratio(baseline_hz, agent_hz)
    name, deviation, base_dis = nearest_consonance(ratio)
    if deviation <= tolerance:
        score = base_dis
    else:
        score = min(1.0, base_dis + min(1.0, deviation / 0.05) * 0.5)
    return ConsonanceFeatures(
        baseline_hz=baseline_hz, agent_hz=agent_hz, frequency_ratio=ratio,
        nearest_interval=name, interval_deviation=deviation,
        dissonance_score=score, beat_frequency=abs(baseline_hz - agent_hz))


def dissonance_to_verdict(score):
    if score < ALLOW_THRESHOLD: return GovernanceVerdict.ALLOW
    elif score < QUARANTINE_THRESHOLD: return GovernanceVerdict.QUARANTINE
    elif score < ESCALATE_THRESHOLD: return GovernanceVerdict.ESCALATE
    else: return GovernanceVerdict.DENY


def verdict_to_label(verdict):
    if verdict == GovernanceVerdict.ALLOW: return PropagationLabel.POSITIVE
    elif verdict == GovernanceVerdict.QUARANTINE: return PropagationLabel.BOUNDARY
    elif verdict == GovernanceVerdict.ESCALATE: return PropagationLabel.NEGATIVE
    else: return PropagationLabel.TERMINAL


def compute_dark_fill(raw_input, dominant_tongue, darkness=0.5):
    complement = COMPLEMENT_MAP[dominant_tongue]
    base_freq = TONGUE_FREQUENCIES[complement]
    weight = TONGUE_WEIGHTS[complement]
    infra_freq = max(0.01, min(20.0, base_freq / 1000.0))
    h = hashlib.sha256(raw_input.encode("utf-8", errors="replace") + complement.encode())
    hash_val = int.from_bytes(h.digest()[:4], "big")
    ultra_freq = 20000.0 + (hash_val / (2**32 - 1)) * 980000.0
    return DarkFillFeatures(
        infra_freq=round(infra_freq, 6), infra_amplitude=round(darkness * 0.8, 6),
        audible_freq=round(base_freq, 4), audible_amplitude=round(darkness * 0.6, 6),
        ultra_freq=round(ultra_freq, 2), ultra_amplitude=round(darkness * (weight / TONGUE_WEIGHTS["dr"]) * 0.9, 6),
        darkness=darkness)


def compute_tongue_affinity(tongue_vector):
    vals = tongue_vector.as_tuple
    affinity = {}
    for i, tongue in enumerate(ALL_TONGUES):
        pure = [0.0] * 6
        pure[i] = 1.0
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(vals, pure)))
        affinity[tongue] = max(0.0, 1.0 - dist / math.sqrt(6))
    return affinity


def compute_node_hash(raw_input, dominant_tongue, dead_tone):
    payload = f"{raw_input}|{dominant_tongue}|{dead_tone}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def generate_record(raw_input, dominant_tongue="ko", dead_tone="perfect_fifth",
                    excitation=3.0, generation=0, parent_hash=None):
    tongue_vec = compute_tongue_vector(raw_input, dominant_tongue)
    prosody = compute_prosody(dominant_tongue, excitation)
    consonance = compute_consonance(prosody.agent_frequency_hz, dead_tone)
    dark_fill = compute_dark_fill(raw_input, dominant_tongue)
    affinity = compute_tongue_affinity(tongue_vec)
    verdict = dissonance_to_verdict(consonance.dissonance_score)
    label = verdict_to_label(verdict)
    return PolyhedralRecord(
        node_hash=compute_node_hash(raw_input, dominant_tongue, dead_tone),
        generation=generation, parent_hash=parent_hash, timestamp=time.time(),
        raw_input=raw_input, dominant_tongue=dominant_tongue, dead_tone=dead_tone,
        excitation=excitation, tongue_vector=tongue_vec, prosody=prosody,
        consonance=consonance, dark_fill=dark_fill, verdict=verdict,
        propagation_label=label, tongue_affinity=affinity,
        complement_tongue=COMPLEMENT_MAP[dominant_tongue])


def generate_multi_tongue_records(raw_input, dead_tone="perfect_fifth",
                                   excitation=3.0, generation=0, parent_hash=None):
    return [generate_record(raw_input, t, dead_tone, excitation, generation, parent_hash)
            for t in ALL_TONGUES]


def generate_full_sweep(raw_input, excitation=3.0, generation=0, parent_hash=None):
    records = []
    for t in ALL_TONGUES:
        for tone in DEAD_TONES:
            records.append(generate_record(raw_input, t, tone, excitation, generation, parent_hash))
    return records


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTongueVector:

    def test_six_dimensions(self):
        v = compute_tongue_vector("hello", "ko")
        assert len(v.as_tuple) == 6

    def test_dominant_boosted(self):
        for t in ALL_TONGUES:
            v = compute_tongue_vector("test", t)
            assert v.dominant == t or getattr(v, t) > 0

    def test_normalized_to_one(self):
        v = compute_tongue_vector("hello world", "av")
        assert max(v.as_tuple) <= 1.0

    def test_all_non_negative(self):
        v = compute_tongue_vector("test data", "ru")
        assert all(val >= 0.0 for val in v.as_tuple)

    def test_empty_input_activates_dominant(self):
        v = compute_tongue_vector("", "ca")
        assert v.ca == 1.0

    def test_norm_positive(self):
        v = compute_tongue_vector("data", "ko")
        assert v.norm > 0

    def test_phi_weighted_norm_gt_norm(self):
        v = compute_tongue_vector("data", "ko")
        assert v.phi_weighted_norm >= v.norm

    def test_all_tongues_produce_valid_vector(self):
        for t in ALL_TONGUES:
            v = compute_tongue_vector("test input", t)
            assert len(v.as_tuple) == 6
            assert all(0.0 <= val <= 1.0 for val in v.as_tuple)


class TestProsody:

    def test_rate_bounded(self):
        for t in ALL_TONGUES:
            p = compute_prosody(t, 3.0)
            assert 0.5 <= p.rate <= 2.0

    def test_energy_bounded(self):
        for t in ALL_TONGUES:
            p = compute_prosody(t, 3.0)
            assert 0.0 <= p.energy <= 1.0

    def test_energy_increases_with_excitation(self):
        lo = compute_prosody("ko", 0.0)
        hi = compute_prosody("ko", 10.0)
        assert hi.energy > lo.energy

    def test_energy_floor_negative_excitation(self):
        p = compute_prosody("ko", -100.0)
        assert p.energy >= 0.0

    def test_rate_floor_negative_excitation(self):
        p = compute_prosody("av", -50.0)
        assert p.rate >= 0.5

    def test_chant_ratio_matches_tongue(self):
        for t in ALL_TONGUES:
            p = compute_prosody(t, 3.0)
            assert p.chant_ratio == TONGUE_CHANT[t]

    def test_stress_pattern_matches_tongue(self):
        for t in ALL_TONGUES:
            p = compute_prosody(t, 3.0)
            assert p.stress_pattern == TONGUE_STRESS[t]

    def test_agent_frequency_positive(self):
        for t in ALL_TONGUES:
            p = compute_prosody(t, 3.0)
            assert 20.0 <= p.agent_frequency_hz <= 20000.0

    def test_agent_frequency_clamped_extreme(self):
        p = compute_prosody("ko", 1000.0)
        assert p.agent_frequency_hz <= 20000.0
        p = compute_prosody("um", -1000.0)
        assert p.agent_frequency_hz >= 20.0


class TestConsonance:

    def test_all_dead_tones_work(self):
        for tone in DEAD_TONES:
            c = compute_consonance(440.0, tone)
            assert 0.0 <= c.dissonance_score <= 1.0

    def test_unison_scores_low(self):
        c = compute_consonance(330.0, "perfect_fifth")
        assert c.dissonance_score < ALLOW_THRESHOLD

    def test_ratio_in_octave_range(self):
        for f in [100, 200, 440, 660, 1000]:
            c = compute_consonance(float(f), "perfect_fifth")
            assert 1.0 <= c.frequency_ratio < 2.0

    def test_beat_frequency_correct(self):
        c = compute_consonance(340.0, "perfect_fifth")
        assert abs(c.beat_frequency - 10.0) < 0.01


class TestDarkFill:

    def test_three_bands(self):
        df = compute_dark_fill("test", "ko")
        assert df.infra_freq > 0
        assert df.audible_freq > 0
        assert df.ultra_freq > 0

    def test_infra_in_range(self):
        for t in ALL_TONGUES:
            df = compute_dark_fill("test", t)
            assert 0.01 <= df.infra_freq <= 20.0

    def test_audible_is_complement_freq(self):
        df = compute_dark_fill("test", "ko")
        assert df.audible_freq == TONGUE_FREQUENCIES["dr"]

    def test_ultra_in_range(self):
        for t in ALL_TONGUES:
            df = compute_dark_fill("test", t)
            assert 20000.0 <= df.ultra_freq <= 1000000.0

    def test_amplitudes_bounded(self):
        df = compute_dark_fill("test", "ko")
        assert 0.0 <= df.infra_amplitude <= 1.0
        assert 0.0 <= df.audible_amplitude <= 1.0
        assert 0.0 <= df.ultra_amplitude <= 1.0

    def test_deterministic(self):
        df1 = compute_dark_fill("test", "ko")
        df2 = compute_dark_fill("test", "ko")
        assert df1.ultra_freq == df2.ultra_freq


class TestTongueAffinity:

    def test_six_entries(self):
        v = compute_tongue_vector("test", "ko")
        aff = compute_tongue_affinity(v)
        assert len(aff) == 6

    def test_all_bounded(self):
        v = compute_tongue_vector("test", "ko")
        aff = compute_tongue_affinity(v)
        for val in aff.values():
            assert 0.0 <= val <= 1.0

    def test_dominant_has_high_affinity(self):
        v = TongueVector(ko=1.0, av=0.0, ru=0.0, ca=0.0, um=0.0, dr=0.0)
        aff = compute_tongue_affinity(v)
        assert aff["ko"] > aff["dr"]


class TestNodeHash:

    def test_deterministic(self):
        h1 = compute_node_hash("test", "ko", "perfect_fifth")
        h2 = compute_node_hash("test", "ko", "perfect_fifth")
        assert h1 == h2

    def test_different_input_different_hash(self):
        h1 = compute_node_hash("test1", "ko", "perfect_fifth")
        h2 = compute_node_hash("test2", "ko", "perfect_fifth")
        assert h1 != h2

    def test_different_tongue_different_hash(self):
        h1 = compute_node_hash("test", "ko", "perfect_fifth")
        h2 = compute_node_hash("test", "av", "perfect_fifth")
        assert h1 != h2

    def test_different_tone_different_hash(self):
        h1 = compute_node_hash("test", "ko", "perfect_fifth")
        h2 = compute_node_hash("test", "ko", "minor_sixth")
        assert h1 != h2

    def test_length(self):
        h = compute_node_hash("test", "ko", "perfect_fifth")
        assert len(h) == 16


class TestGenerateRecord:

    def test_returns_polyhedral_record(self):
        r = generate_record("hello world", "ko", "perfect_fifth", 3.0)
        assert isinstance(r, PolyhedralRecord)

    def test_all_tongues_produce_records(self):
        for t in ALL_TONGUES:
            r = generate_record("test", t, "perfect_fifth", 3.0)
            assert r.dominant_tongue == t
            assert r.complement_tongue == COMPLEMENT_MAP[t]

    def test_all_dead_tones_produce_records(self):
        for tone in DEAD_TONES:
            r = generate_record("test", "ko", tone, 3.0)
            assert r.dead_tone == tone

    def test_governance_verdict_present(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        assert isinstance(r.verdict, GovernanceVerdict)
        assert isinstance(r.propagation_label, PropagationLabel)

    def test_frozen(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        try:
            r.raw_input = "changed"
            assert False, "should be frozen"
        except AttributeError:
            pass

    def test_generation_zero_no_parent(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0, generation=0)
        assert r.generation == 0
        assert r.parent_hash is None

    def test_generation_with_parent(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0,
                            generation=2, parent_hash="abc123")
        assert r.generation == 2
        assert r.parent_hash == "abc123"

    def test_tongue_affinity_has_six_entries(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        assert len(r.tongue_affinity) == 6

    def test_all_features_populated(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        assert r.tongue_vector.norm > 0
        assert r.prosody.rate > 0
        assert r.prosody.energy >= 0
        assert r.consonance.frequency_ratio >= 1.0
        assert r.dark_fill.infra_freq > 0
        assert r.dark_fill.audible_freq > 0
        assert r.dark_fill.ultra_freq > 0


class TestVerdictToLabel:

    def test_allow_is_positive(self):
        assert verdict_to_label(GovernanceVerdict.ALLOW) == PropagationLabel.POSITIVE

    def test_quarantine_is_boundary(self):
        assert verdict_to_label(GovernanceVerdict.QUARANTINE) == PropagationLabel.BOUNDARY

    def test_escalate_is_negative(self):
        assert verdict_to_label(GovernanceVerdict.ESCALATE) == PropagationLabel.NEGATIVE

    def test_deny_is_terminal(self):
        assert verdict_to_label(GovernanceVerdict.DENY) == PropagationLabel.TERMINAL


class TestMultiTongueRecords:

    def test_produces_six_records(self):
        records = generate_multi_tongue_records("test")
        assert len(records) == 6

    def test_all_tongues_represented(self):
        records = generate_multi_tongue_records("test")
        tongues = {r.dominant_tongue for r in records}
        assert tongues == set(ALL_TONGUES)

    def test_all_have_verdicts(self):
        records = generate_multi_tongue_records("test")
        for r in records:
            assert isinstance(r.verdict, GovernanceVerdict)


class TestFullSweep:

    def test_produces_18_records(self):
        records = generate_full_sweep("test")
        assert len(records) == 18  # 6 tongues × 3 dead tones

    def test_all_combinations_present(self):
        records = generate_full_sweep("test")
        combos = {(r.dominant_tongue, r.dead_tone) for r in records}
        assert len(combos) == 18

    def test_all_governed(self):
        records = generate_full_sweep("test")
        for r in records:
            assert 0.0 <= r.consonance.dissonance_score <= 1.0
            assert isinstance(r.verdict, GovernanceVerdict)


class TestComplementPairs:

    def test_complement_is_symmetric(self):
        for t in ALL_TONGUES:
            comp = COMPLEMENT_MAP[t]
            assert COMPLEMENT_MAP[comp] == t

    def test_complement_different_from_self(self):
        for t in ALL_TONGUES:
            assert COMPLEMENT_MAP[t] != t

    def test_record_complement_correct(self):
        for t in ALL_TONGUES:
            r = generate_record("test", t)
            assert r.complement_tongue == COMPLEMENT_MAP[t]


class TestExtremeExcitation:

    def test_very_high_excitation(self):
        r = generate_record("test", "ko", "perfect_fifth", 100.0)
        assert r.prosody.energy <= 1.0
        assert r.prosody.rate <= 2.0
        assert isinstance(r.verdict, GovernanceVerdict)

    def test_very_low_excitation(self):
        r = generate_record("test", "ko", "perfect_fifth", -100.0)
        assert r.prosody.energy >= 0.0
        assert r.prosody.rate >= 0.5
        assert isinstance(r.verdict, GovernanceVerdict)

    def test_zero_excitation(self):
        r = generate_record("test", "ko", "perfect_fifth", 0.0)
        assert 0.0 <= r.prosody.energy <= 1.0

    def test_all_tongues_extreme(self):
        for t in ALL_TONGUES:
            for ex in [-100.0, 0.0, 100.0]:
                r = generate_record("test", t, "perfect_fifth", ex)
                assert 0.0 <= r.prosody.energy <= 1.0
                assert 0.5 <= r.prosody.rate <= 2.0
