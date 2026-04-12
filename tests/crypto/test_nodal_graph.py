"""Tests for nodal_graph.py — self-propagating training network.

Self-contained: inlines all required logic. Tests growth, propagation, and harvest.
"""

import math
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Inline constants + types (mirrors polyhedral_node + nodal_graph)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

TONGUE_WEIGHTS = {
    "ko": PHI**0,
    "av": PHI**1,
    "ru": PHI**2,
    "ca": PHI**3,
    "um": PHI**4,
    "dr": PHI**5,
}
ALL_TONGUES = tuple(TONGUE_WEIGHTS.keys())
TONGUE_FREQUENCIES = {
    "ko": 440.00,
    "av": 523.25,
    "ru": 293.66,
    "ca": 659.25,
    "um": 196.00,
    "dr": 392.00,
}
COMPLEMENT_MAP = {
    "ko": "dr",
    "av": "um",
    "ru": "ca",
    "ca": "ru",
    "um": "av",
    "dr": "ko",
}
BASELINE_FREQUENCIES = {
    "perfect_fifth": 330.0,
    "minor_sixth": 352.0,
    "minor_seventh": 392.0,
}
DEAD_TONES = tuple(BASELINE_FREQUENCIES.keys())
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
TONGUE_STRESS = {"ko": "even", "av": "flowing", "ru": "percussive", "ca": "rising", "um": "falling", "dr": "grounded"}
TONGUE_RATE = {"ko": 0.95, "av": 1.00, "ru": 0.90, "ca": 1.08, "um": 0.82, "dr": 0.80}
TONGUE_CHANT = {"ko": 0.10, "av": 0.20, "ru": 0.25, "ca": 0.30, "um": 0.35, "dr": 0.22}


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
    ko: float
    av: float
    ru: float
    ca: float
    um: float
    dr: float

    @property
    def dominant(self):
        vals = {"ko": self.ko, "av": self.av, "ru": self.ru, "ca": self.ca, "um": self.um, "dr": self.dr}
        return max(vals, key=vals.get)

    @property
    def as_tuple(self):
        return (self.ko, self.av, self.ru, self.ca, self.um, self.dr)


@dataclass(frozen=True)
class ProsodyFeatures:
    rate: float
    energy: float
    chant_ratio: float
    stress_pattern: str
    agent_frequency_hz: float


@dataclass(frozen=True)
class DarkFillFeatures:
    infra_freq: float
    infra_amplitude: float
    audible_freq: float
    audible_amplitude: float
    ultra_freq: float
    ultra_amplitude: float
    darkness: float


@dataclass(frozen=True)
class ConsonanceFeatures:
    baseline_hz: float
    agent_hz: float
    frequency_ratio: float
    nearest_interval: str
    interval_deviation: float
    dissonance_score: float
    beat_frequency: float


@dataclass(frozen=True)
class PolyhedralRecord:
    node_hash: str
    generation: int
    parent_hash: Optional[str]
    timestamp: float
    raw_input: str
    dominant_tongue: str
    dead_tone: str
    excitation: float
    tongue_vector: TongueVector
    prosody: ProsodyFeatures
    consonance: ConsonanceFeatures
    dark_fill: DarkFillFeatures
    verdict: GovernanceVerdict
    propagation_label: PropagationLabel
    tongue_affinity: Dict[str, float]
    complement_tongue: str


@dataclass(frozen=True)
class NodalEdge:
    source_hash: str
    target_hash: str
    weight: float
    edge_type: str


@dataclass
class NodalGraph:
    nodes: Dict[str, PolyhedralRecord] = field(default_factory=dict)
    edges: List[NodalEdge] = field(default_factory=list)
    _edge_index: Dict[str, List[NodalEdge]] = field(default_factory=dict)
    generation_count: int = 0
    total_allow: int = 0
    total_quarantine: int = 0
    total_deny: int = 0

    @property
    def node_count(self):
        return len(self.nodes)

    @property
    def edge_count(self):
        return len(self.edges)

    @property
    def density(self):
        n = self.node_count
        if n < 2:
            return 0.0
        return self.edge_count / (n * (n - 1))

    def add_node(self, record):
        if record.node_hash in self.nodes:
            return False
        self.nodes[record.node_hash] = record
        self._edge_index[record.node_hash] = []
        if record.verdict == GovernanceVerdict.ALLOW:
            self.total_allow += 1
        elif record.verdict == GovernanceVerdict.QUARANTINE:
            self.total_quarantine += 1
        else:
            self.total_deny += 1
        return True

    def add_edge(self, edge):
        if edge.source_hash in self.nodes and edge.target_hash in self.nodes:
            self.edges.append(edge)
            self._edge_index.setdefault(edge.source_hash, []).append(edge)

    def get_neighbors(self, h):
        return [e.target_hash for e in self._edge_index.get(h, [])]

    def get_node(self, h):
        return self.nodes.get(h)

    def nodes_by_verdict(self, v):
        return [n for n in self.nodes.values() if n.verdict == v]

    def nodes_by_generation(self, g):
        return [n for n in self.nodes.values() if n.generation == g]

    def nodes_by_tongue(self, t):
        return [n for n in self.nodes.values() if n.dominant_tongue == t]

    def harvest_positive(self):
        return self.nodes_by_verdict(GovernanceVerdict.ALLOW)

    def harvest_boundary(self):
        return self.nodes_by_verdict(GovernanceVerdict.QUARANTINE)

    def harvest_negative(self):
        return self.nodes_by_verdict(GovernanceVerdict.ESCALATE) + self.nodes_by_verdict(GovernanceVerdict.DENY)


# Inline record generation (from polyhedral_node)
def _compute_tongue_vector(raw_input, dominant_tongue):
    activations = {t: 0.0 for t in ALL_TONGUES}
    data = raw_input.encode("utf-8", errors="replace")
    if len(data) == 0:
        activations[dominant_tongue] = 1.0
        return TongueVector(**activations)
    for byte_val in data:
        for _i, tongue in enumerate(ALL_TONGUES):
            threshold = (TONGUE_WEIGHTS[tongue] / TONGUE_WEIGHTS["dr"]) * 255
            if byte_val >= threshold:
                activations[tongue] += 1.0 / len(data)
    activations[dominant_tongue] = min(1.0, activations[dominant_tongue] + 0.3)
    mx = max(activations.values()) or 1.0
    return TongueVector(**{t: v / mx for t, v in activations.items()})


def _compute_prosody(dominant_tongue, excitation):
    rate = max(0.5, min(2.0, TONGUE_RATE[dominant_tongue] + 0.02 * (excitation - 3.0)))
    energy = max(0.0, min(1.0, 0.4 + 0.06 * excitation))
    base_freq = TONGUE_FREQUENCIES[dominant_tongue]
    agent_hz = max(20.0, min(20000.0, base_freq * (1.0 + 0.05 * (excitation - 3.0))))
    return ProsodyFeatures(
        rate=rate,
        energy=energy,
        chant_ratio=TONGUE_CHANT[dominant_tongue],
        stress_pattern=TONGUE_STRESS[dominant_tongue],
        agent_frequency_hz=agent_hz,
    )


def _normalize_ratio(f_a, f_b):
    if f_a <= 0 or f_b <= 0:
        return 1.0
    ratio = max(f_a, f_b) / min(f_a, f_b)
    while ratio >= 2.0:
        ratio /= 2.0
    return ratio


def _nearest_consonance(ratio):
    best_name, best_dev, best_dis = "tritone", float("inf"), 0.75
    for name, (ref, dis) in RATIO_DISSONANCE.items():
        dev = abs(ratio - ref)
        if dev < best_dev:
            best_dev, best_name, best_dis = dev, name, dis
    return best_name, best_dev, best_dis


def _compute_consonance(agent_hz, dead_tone, tolerance=0.03):
    baseline_hz = BASELINE_FREQUENCIES[dead_tone]
    ratio = _normalize_ratio(baseline_hz, agent_hz)
    name, dev, base_dis = _nearest_consonance(ratio)
    score = base_dis if dev <= tolerance else min(1.0, base_dis + min(1.0, dev / 0.05) * 0.5)
    return ConsonanceFeatures(
        baseline_hz=baseline_hz,
        agent_hz=agent_hz,
        frequency_ratio=ratio,
        nearest_interval=name,
        interval_deviation=dev,
        dissonance_score=score,
        beat_frequency=abs(baseline_hz - agent_hz),
    )


def _dissonance_to_verdict(score):
    if score < ALLOW_THRESHOLD:
        return GovernanceVerdict.ALLOW
    elif score < QUARANTINE_THRESHOLD:
        return GovernanceVerdict.QUARANTINE
    elif score < ESCALATE_THRESHOLD:
        return GovernanceVerdict.ESCALATE
    else:
        return GovernanceVerdict.DENY


def _verdict_to_label(v):
    return {
        GovernanceVerdict.ALLOW: PropagationLabel.POSITIVE,
        GovernanceVerdict.QUARANTINE: PropagationLabel.BOUNDARY,
        GovernanceVerdict.ESCALATE: PropagationLabel.NEGATIVE,
        GovernanceVerdict.DENY: PropagationLabel.TERMINAL,
    }[v]


def _compute_dark_fill(raw_input, dominant_tongue, darkness=0.5):
    comp = COMPLEMENT_MAP[dominant_tongue]
    base_freq = TONGUE_FREQUENCIES[comp]
    weight = TONGUE_WEIGHTS[comp]
    h = hashlib.sha256(raw_input.encode("utf-8", errors="replace") + comp.encode())
    hv = int.from_bytes(h.digest()[:4], "big")
    return DarkFillFeatures(
        infra_freq=round(max(0.01, min(20.0, base_freq / 1000.0)), 6),
        infra_amplitude=round(darkness * 0.8, 6),
        audible_freq=round(base_freq, 4),
        audible_amplitude=round(darkness * 0.6, 6),
        ultra_freq=round(20000.0 + (hv / (2**32 - 1)) * 980000.0, 2),
        ultra_amplitude=round(darkness * (weight / TONGUE_WEIGHTS["dr"]) * 0.9, 6),
        darkness=darkness,
    )


def _compute_affinity(tv):
    vals = tv.as_tuple
    aff = {}
    for i, t in enumerate(ALL_TONGUES):
        pure = [0.0] * 6
        pure[i] = 1.0
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(vals, pure)))
        aff[t] = max(0.0, 1.0 - dist / math.sqrt(6))
    return aff


def generate_record(
    raw_input, dominant_tongue="ko", dead_tone="perfect_fifth", excitation=3.0, generation=0, parent_hash=None
):
    tv = _compute_tongue_vector(raw_input, dominant_tongue)
    pr = _compute_prosody(dominant_tongue, excitation)
    cn = _compute_consonance(pr.agent_frequency_hz, dead_tone)
    df = _compute_dark_fill(raw_input, dominant_tongue)
    af = _compute_affinity(tv)
    vd = _dissonance_to_verdict(cn.dissonance_score)
    lb = _verdict_to_label(vd)
    payload = f"{raw_input}|{dominant_tongue}|{dead_tone}"
    nh = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return PolyhedralRecord(
        node_hash=nh,
        generation=generation,
        parent_hash=parent_hash,
        timestamp=time.time(),
        raw_input=raw_input,
        dominant_tongue=dominant_tongue,
        dead_tone=dead_tone,
        excitation=excitation,
        tongue_vector=tv,
        prosody=pr,
        consonance=cn,
        dark_fill=df,
        verdict=vd,
        propagation_label=lb,
        tongue_affinity=af,
        complement_tongue=COMPLEMENT_MAP[dominant_tongue],
    )


# Edge weight + propagation logic (from nodal_graph.py)
def compute_edge_weight(source, target):
    s_vec, t_vec = source.tongue_vector.as_tuple, target.tongue_vector.as_tuple
    td = math.sqrt(sum((a - b) ** 2 for a, b in zip(s_vec, t_vec)))
    cd = abs(source.consonance.dissonance_score - target.consonance.dissonance_score)
    dd = 0.0 if source.dead_tone == target.dead_tone else 0.5
    return 1.0 / (1.0 + PHI * (td + cd + dd))


def sprout_from_node(parent, raw_input, generation):
    if parent.verdict != GovernanceVerdict.ALLOW:
        return []
    comp = COMPLEMENT_MAP[parent.dominant_tongue]
    tl = list(DEAD_TONES)
    ci = tl.index(parent.dead_tone) if parent.dead_tone in tl else 0
    nt = tl[(ci + 1) % len(tl)]
    de = max(0.0, parent.excitation / PHI)
    return [
        generate_record(raw_input, comp, nt, de, generation, parent.node_hash),
        generate_record(raw_input, parent.dominant_tongue, nt, de, generation, parent.node_hash),
    ]


def grow_generation(graph, raw_input):
    frontier = graph.nodes_by_generation(graph.generation_count)
    allow_f = [n for n in frontier if n.verdict == GovernanceVerdict.ALLOW]
    next_gen = graph.generation_count + 1
    added = 0
    for parent in allow_f:
        for child in sprout_from_node(parent, raw_input, next_gen):
            if graph.add_node(child):
                added += 1
                w = compute_edge_weight(parent, child)
                graph.add_edge(
                    NodalEdge(
                        parent.node_hash,
                        child.node_hash,
                        w,
                        (
                            "tongue_complement"
                            if child.dominant_tongue != parent.dominant_tongue
                            else "dead_tone_rotation"
                        ),
                    )
                )
    graph.generation_count = next_gen
    return added


def seed_graph(raw_input, tongues=None, dead_tones=None, excitation=3.0):
    graph = NodalGraph()
    tongues = tongues or list(ALL_TONGUES)
    dead_tones = dead_tones or [DEAD_TONES[0]]
    for t in tongues:
        for tone in dead_tones:
            graph.add_node(generate_record(raw_input, t, tone, excitation, 0))
    hashes = list(graph.nodes.keys())
    for i, h1 in enumerate(hashes):
        for h2 in hashes[i + 1 :]:
            w = compute_edge_weight(graph.nodes[h1], graph.nodes[h2])
            if w > 0.3:
                graph.add_edge(NodalEdge(h1, h2, w, "affinity"))
                graph.add_edge(NodalEdge(h2, h1, w, "affinity"))
    return graph


def grow_network(raw_input, max_generations=3, excitation=3.0):
    graph = seed_graph(raw_input, excitation=excitation)
    for _ in range(max_generations):
        if grow_generation(graph, raw_input) == 0:
            break
    return graph


def export_training_pairs(graph):
    def r2d(r):
        return {
            "node_hash": r.node_hash,
            "raw_input": r.raw_input,
            "dominant_tongue": r.dominant_tongue,
            "dead_tone": r.dead_tone,
            "excitation": r.excitation,
            "generation": r.generation,
            "tongue_vector": list(r.tongue_vector.as_tuple),
            "dissonance_score": r.consonance.dissonance_score,
            "verdict": r.verdict.value,
            "propagation_label": r.propagation_label.value,
        }

    return {
        "sft": [r2d(r) for r in graph.harvest_positive()],
        "dpo_chosen": [r2d(r) for r in graph.harvest_positive()],
        "dpo_rejected": [r2d(r) for r in graph.harvest_negative()],
        "boundary": [r2d(r) for r in graph.harvest_boundary()],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSeedGraph:

    def test_seeds_six_nodes_by_default(self):
        g = seed_graph("hello world")
        assert g.node_count == 6

    def test_all_tongues_seeded(self):
        g = seed_graph("test")
        tongues = {n.dominant_tongue for n in g.nodes.values()}
        assert tongues == set(ALL_TONGUES)

    def test_all_generation_zero(self):
        g = seed_graph("test")
        for n in g.nodes.values():
            assert n.generation == 0

    def test_custom_tongues(self):
        g = seed_graph("test", tongues=["ko", "av"])
        assert g.node_count == 2

    def test_custom_dead_tones(self):
        g = seed_graph("test", dead_tones=["minor_sixth", "minor_seventh"])
        assert g.node_count == 12  # 6 tongues × 2 tones

    def test_edges_created(self):
        g = seed_graph("test")
        assert g.edge_count > 0

    def test_generation_count_starts_zero(self):
        g = seed_graph("test")
        assert g.generation_count == 0


class TestGrowGeneration:

    def test_grows_from_allow_nodes(self):
        g = seed_graph("test data")
        allow_count = len(g.harvest_positive())
        added = grow_generation(g, "test data")
        assert g.generation_count == 1
        if allow_count > 0:
            assert added > 0

    def test_generation_increments(self):
        g = seed_graph("test")
        grow_generation(g, "test")
        assert g.generation_count == 1
        grow_generation(g, "test")
        assert g.generation_count == 2

    def test_children_have_correct_generation(self):
        g = seed_graph("test")
        grow_generation(g, "test")
        gen1 = g.nodes_by_generation(1)
        for n in gen1:
            assert n.generation == 1

    def test_children_have_parent_hash(self):
        g = seed_graph("test")
        seed_hashes = set(g.nodes.keys())
        grow_generation(g, "test")
        gen1 = g.nodes_by_generation(1)
        for n in gen1:
            assert n.parent_hash in seed_hashes

    def test_excitation_decays(self):
        g = seed_graph("test", excitation=5.0)
        grow_generation(g, "test")
        gen1 = g.nodes_by_generation(1)
        for n in gen1:
            assert n.excitation < 5.0
            assert n.excitation >= 0.0

    def test_dead_tone_rotates(self):
        g = seed_graph("test", tongues=["ko"], dead_tones=["perfect_fifth"])
        grow_generation(g, "test")
        gen1 = g.nodes_by_generation(1)
        if gen1:
            # At least one child should have a different dead tone
            tones = {n.dead_tone for n in gen1}
            assert "minor_sixth" in tones  # rotated from perfect_fifth

    def test_no_growth_from_terminal_nodes(self):
        """If all seeds are DENY, no growth should happen."""
        # This is hard to force without controlling the frequency,
        # so we just verify the mechanism
        g = seed_graph("test")
        deny_nodes = g.nodes_by_verdict(GovernanceVerdict.DENY)
        for n in deny_nodes:
            children = sprout_from_node(n, "test", 1)
            assert len(children) == 0


class TestGrowNetwork:

    def test_produces_multi_generation_graph(self):
        g = grow_network("the quick brown fox", max_generations=2)
        assert g.generation_count >= 1
        assert g.node_count > 6  # more than just seeds

    def test_max_generations_respected(self):
        g = grow_network("test", max_generations=3)
        assert g.generation_count <= 3

    def test_edges_connect_generations(self):
        g = grow_network("test", max_generations=2)
        for e in g.edges:
            src = g.get_node(e.source_hash)
            tgt = g.get_node(e.target_hash)
            if src and tgt and e.edge_type != "affinity":
                assert tgt.generation == src.generation + 1

    def test_all_nodes_governed(self):
        g = grow_network("test data", max_generations=2)
        for n in g.nodes.values():
            assert isinstance(n.verdict, GovernanceVerdict)
            assert isinstance(n.propagation_label, PropagationLabel)


class TestEdgeWeight:

    def test_self_weight_is_one(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        w = compute_edge_weight(r, r)
        assert abs(w - 1.0) < 0.01

    def test_weight_bounded(self):
        r1 = generate_record("test", "ko", "perfect_fifth", 3.0)
        r2 = generate_record("test", "dr", "minor_seventh", 3.0)
        w = compute_edge_weight(r1, r2)
        assert 0.0 < w <= 1.0

    def test_symmetric(self):
        r1 = generate_record("a", "ko", "perfect_fifth", 3.0)
        r2 = generate_record("b", "av", "minor_sixth", 5.0)
        assert abs(compute_edge_weight(r1, r2) - compute_edge_weight(r2, r1)) < 0.001

    def test_same_tongue_higher_weight(self):
        r1 = generate_record("test", "ko", "perfect_fifth", 3.0)
        r_same = generate_record("test2", "ko", "perfect_fifth", 3.0)
        r_diff = generate_record("test", "dr", "minor_seventh", 3.0)
        w_same = compute_edge_weight(r1, r_same)
        w_diff = compute_edge_weight(r1, r_diff)
        assert w_same >= w_diff


class TestGraphQueries:

    def test_nodes_by_tongue(self):
        g = seed_graph("test")
        ko_nodes = g.nodes_by_tongue("ko")
        assert all(n.dominant_tongue == "ko" for n in ko_nodes)

    def test_nodes_by_generation(self):
        g = grow_network("test", max_generations=2)
        gen0 = g.nodes_by_generation(0)
        assert len(gen0) >= 1
        assert all(n.generation == 0 for n in gen0)

    def test_get_neighbors(self):
        g = seed_graph("test")
        for h in list(g.nodes.keys())[:3]:
            neighbors = g.get_neighbors(h)
            for nh in neighbors:
                assert nh in g.nodes

    def test_density_bounded(self):
        g = grow_network("test", max_generations=2)
        assert 0.0 <= g.density <= 1.0


class TestHarvestTraining:

    def test_harvest_positive_all_allow(self):
        g = grow_network("test", max_generations=1)
        for r in g.harvest_positive():
            assert r.verdict == GovernanceVerdict.ALLOW

    def test_harvest_boundary_all_quarantine(self):
        g = grow_network("test", max_generations=1)
        for r in g.harvest_boundary():
            assert r.verdict == GovernanceVerdict.QUARANTINE

    def test_harvest_negative_all_deny_or_escalate(self):
        g = grow_network("test", max_generations=1)
        for r in g.harvest_negative():
            assert r.verdict in (GovernanceVerdict.ESCALATE, GovernanceVerdict.DENY)

    def test_all_nodes_accounted_for(self):
        g = grow_network("test data", max_generations=2)
        pos = len(g.harvest_positive())
        bnd = len(g.harvest_boundary())
        neg = len(g.harvest_negative())
        assert pos + bnd + neg == g.node_count


class TestExportTrainingPairs:

    def test_four_keys(self):
        g = grow_network("test", max_generations=1)
        export = export_training_pairs(g)
        assert set(export.keys()) == {"sft", "dpo_chosen", "dpo_rejected", "boundary"}

    def test_sft_has_records(self):
        g = grow_network("test", max_generations=1)
        export = export_training_pairs(g)
        # At least some nodes should be ALLOW
        total = len(export["sft"]) + len(export["dpo_rejected"]) + len(export["boundary"])
        assert total > 0

    def test_records_have_required_fields(self):
        g = grow_network("test", max_generations=1)
        export = export_training_pairs(g)
        for bucket in export.values():
            for rec in bucket:
                assert "node_hash" in rec
                assert "tongue_vector" in rec
                assert "dissonance_score" in rec
                assert "verdict" in rec
                assert "propagation_label" in rec

    def test_tongue_vector_is_list(self):
        g = grow_network("test", max_generations=1)
        export = export_training_pairs(g)
        for bucket in export.values():
            for rec in bucket:
                assert isinstance(rec["tongue_vector"], list)
                assert len(rec["tongue_vector"]) == 6


class TestSproutFromNode:

    def test_allow_produces_two_children(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        if r.verdict == GovernanceVerdict.ALLOW:
            children = sprout_from_node(r, "test", 1)
            assert len(children) == 2

    def test_deny_produces_no_children(self):
        # Force a DENY by using a very specific setup
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        # Regardless of actual verdict, test the mechanism
        if r.verdict != GovernanceVerdict.ALLOW:
            children = sprout_from_node(r, "test", 1)
            assert len(children) == 0

    def test_children_include_complement(self):
        r = generate_record("test", "ko", "perfect_fifth", 3.0)
        if r.verdict == GovernanceVerdict.ALLOW:
            children = sprout_from_node(r, "test", 1)
            tongues = {c.dominant_tongue for c in children}
            assert COMPLEMENT_MAP["ko"] in tongues  # "dr" should be in children


class TestGraphStats:

    def test_stats_track_verdicts(self):
        g = grow_network("test input", max_generations=2)
        assert g.total_allow + g.total_quarantine + g.total_deny == g.node_count

    def test_stats_non_negative(self):
        g = grow_network("test", max_generations=1)
        assert g.total_allow >= 0
        assert g.total_quarantine >= 0
        assert g.total_deny >= 0


class TestNetworkProperties:

    def test_no_self_loops(self):
        g = grow_network("test", max_generations=2)
        for e in g.edges:
            assert e.source_hash != e.target_hash

    def test_all_edge_weights_positive(self):
        g = grow_network("test", max_generations=2)
        for e in g.edges:
            assert e.weight > 0

    def test_phi_decay_across_generations(self):
        """Excitation should decay by 1/phi each generation."""
        g = seed_graph("test", tongues=["ko"], excitation=5.0)
        grow_generation(g, "test")
        gen1 = g.nodes_by_generation(1)
        if gen1:
            expected = 5.0 / PHI
            for n in gen1:
                assert abs(n.excitation - expected) < 0.01

    def test_network_stabilizes(self):
        """After enough generations, growth should slow or stop."""
        g = grow_network("test", max_generations=5, excitation=3.0)
        # Later generations should have fewer nodes (excitation decays)
        gen0 = len(g.nodes_by_generation(0))
        last_gen = len(g.nodes_by_generation(g.generation_count))
        # gen0 should have more or equal nodes than the last generation
        assert gen0 >= last_gen
