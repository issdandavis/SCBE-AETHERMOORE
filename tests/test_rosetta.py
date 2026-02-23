"""Tests for Rosetta-LCDA: Multilingual Concept Mapping + LCDA + DEDE.

Covers:
  - NSM prime lookup across EN/ZH/JA/KO + Sacred Tongues
  - CJK cognate resolution
  - Toki Pona / Esperanto / Lojban ↔ NSM prime mapping
  - Sacred Tongue ↔ natural language concept bridge
  - LCDA dimension projection
  - DEDE signal computation (4 regime classification)
  - Language graph shortest path
  - TAM profile queries
  - SFT export produces valid JSONL
"""

import json
import math
import os
import sys

import pytest

# Ensure src/ is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.symphonic_cipher.scbe_aethermoore.rosetta import (
    RosettaStone,
    RosettaConcept,
    LanguageSystem,
    LCDAProjector,
    LCDADimension,
    DualEntropicDefenseEngine,
    DEDESignal,
    LanguageGraph,
)
from src.symphonic_cipher.scbe_aethermoore.rosetta.seed_data import (
    NSM_PRIMES,
    CJK_COGNATES,
    TOKIPONA_MAP,
    ESPERANTO_MAP,
    LOJBAN_MAP,
    SACRED_TONGUE_PRIMES,
    TAM_PROFILES,
)


# ═══════════════════════════════════════════════════════════════
# ROSETTA CORE TESTS
# ═══════════════════════════════════════════════════════════════


class TestRosettaStone:
    """Tests for the RosettaStone concept mapping engine."""

    @pytest.fixture
    def rs(self):
        return RosettaStone()

    # ── NSM Prime Lookups ──

    def test_lookup_good_en(self, rs):
        forms = rs.lookup("GOOD", "EN")
        assert "good" in forms

    def test_lookup_good_zh(self, rs):
        forms = rs.lookup("GOOD", "ZH")
        assert "好" in forms

    def test_lookup_good_ja(self, rs):
        forms = rs.lookup("GOOD", "JA")
        assert any("良い" in f or "いい" in f for f in forms)

    def test_lookup_good_ko(self, rs):
        forms = rs.lookup("GOOD", "KO")
        assert "좋은" in forms

    def test_lookup_danger_zh(self, rs):
        forms = rs.lookup("DANGER", "ZH")
        assert "危险" in forms

    def test_lookup_danger_ja(self, rs):
        forms = rs.lookup("DANGER", "JA")
        assert any("危険" in f for f in forms)

    def test_lookup_move_ko(self, rs):
        forms = rs.lookup("MOVE", "KO")
        assert "움직이다" in forms

    def test_lookup_unknown_concept(self, rs):
        forms = rs.lookup("NONEXISTENT", "EN")
        assert forms == []

    def test_lookup_unknown_language(self, rs):
        forms = rs.lookup("GOOD", "XX")
        assert forms == []

    # ── CJK Cognates ──

    def test_cjk_cognate_study(self, rs):
        entry = rs.find_cjk_cognate("学")
        assert entry is not None
        assert "xué" in entry["ZH"]

    def test_cjk_cognate_danger(self, rs):
        entry = rs.find_cjk_cognate("危険")
        assert entry is not None
        assert "danger" in entry["EN"].lower()

    def test_cjk_cognate_missing(self, rs):
        entry = rs.find_cjk_cognate("zzz")
        assert entry is None

    # ── Conlang Mappings ──

    def test_tokipona_good(self, rs):
        forms = rs.lookup("GOOD", "TOKIPONA")
        assert "pona" in forms

    def test_tokipona_bad(self, rs):
        forms = rs.lookup("BAD", "TOKIPONA")
        assert "ike" in forms

    def test_tokipona_move(self, rs):
        forms = rs.lookup("MOVE", "TOKIPONA")
        assert "tawa" in forms

    def test_esperanto_good(self, rs):
        forms = rs.lookup("GOOD", "ESPERANTO")
        assert "bona" in forms

    def test_lojban_good(self, rs):
        forms = rs.lookup("GOOD", "LOJBAN")
        assert "xamgu" in forms

    # ── Sacred Tongue Bridges ──

    def test_sacred_tongue_good_ko(self, rs):
        forms = rs.lookup("GOOD", "KO_ST")
        assert len(forms) > 0
        assert "kel-oath" in forms

    def test_sacred_tongue_danger_av(self, rs):
        forms = rs.lookup("DANGER", "AV_ST")
        assert "vari-storm" in forms

    def test_sacred_tongue_trust_ru(self, rs):
        forms = rs.lookup("TRUST", "RU_ST")
        assert "mir-pledge" in forms

    # ── Translation ──

    def test_translate_good_en_to_zh(self, rs):
        result = rs.translate("GOOD", "EN", "ZH")
        assert result["src_forms"] == ["good"]
        assert "好" in result["dst_forms"]
        assert "drift_score" in result
        assert 0.0 <= result["drift_score"] <= 1.0

    def test_translate_danger_zh_to_ko(self, rs):
        result = rs.translate("DANGER", "ZH", "KO")
        assert "위험" in result["dst_forms"]

    def test_translate_unknown_concept(self, rs):
        result = rs.translate("NONEXISTENT", "EN", "ZH")
        assert "error" in result

    # ── Find Cognates ──

    def test_find_cognates_good(self, rs):
        results = rs.find_cognates("good", "EN")
        assert len(results) >= 1
        assert any(c.concept_id == "GOOD" for c in results)

    # ── Embedding ──

    def test_embed_returns_6d(self, rs):
        vec = rs.embed("GOOD")
        assert len(vec) == 6

    def test_embed_in_poincare_ball(self, rs):
        vec = rs.embed("GOOD")
        norm = math.sqrt(sum(x**2 for x in vec))
        assert norm < 1.0, "Embedding must be inside Poincare ball"

    def test_embed_different_concepts_differ(self, rs):
        v1 = rs.embed("GOOD")
        v2 = rs.embed("BAD")
        assert v1 != v2

    # ── Drift Score ──

    def test_drift_same_family(self, rs):
        # ZH and JA are different families but share script
        drift = rs.drift_score("GOOD", "ZH", "JA")
        assert 0.0 <= drift <= 1.0

    def test_drift_sacred_vs_natural(self, rs):
        drift = rs.drift_score("GOOD", "EN", "KO_ST")
        assert drift > 0.0  # Sacred tongues should have some drift

    # ── TAM Profiles ──

    def test_tam_zh_tenseless(self, rs):
        profile = rs.tam_profile("ZH")
        assert profile["tense"] == "none"
        assert profile["prominence"] == "aspect_prominent"

    def test_tam_en_tense_prominent(self, rs):
        profile = rs.tam_profile("EN")
        assert profile["prominence"] == "tense_prominent"

    def test_tam_ko_speech_levels(self, rs):
        profile = rs.tam_profile("KO")
        assert "speech_level_6" in profile["mood"]

    def test_tam_tokipona_tenseless(self, rs):
        profile = rs.tam_profile("TOKIPONA")
        assert profile["prominence"] == "tenseless"

    # ── SFT Export ──

    def test_export_sft_jsonl(self, rs):
        output = rs.export_sft(format="jsonl")
        lines = [l for l in output.strip().split("\n") if l]
        assert len(lines) > 0
        # Each line should be valid JSON
        for line in lines[:5]:
            record = json.loads(line)
            assert "category" in record
            assert record["category"] in ("rosetta-concept", "rosetta-cognate")

    def test_export_sft_json(self, rs):
        output = rs.export_sft(format="json")
        records = json.loads(output)
        assert isinstance(records, list)
        assert len(records) > 0

    # ── Add/Modify ──

    def test_add_mapping(self, rs):
        ok = rs.add_mapping("GOOD", "FR", ["bon", "bonne"])
        assert ok
        forms = rs.lookup("GOOD", "FR")
        assert "bon" in forms

    def test_add_mapping_unknown_concept(self, rs):
        ok = rs.add_mapping("NONEXISTENT", "FR", ["test"])
        assert not ok

    def test_list_concepts(self, rs):
        concepts = rs.list_concepts()
        assert len(concepts) >= 60  # Should have at least 60 NSM primes

    def test_get_languages(self, rs):
        langs = rs.get_languages()
        codes = [l.code for l in langs]
        assert "EN" in codes
        assert "ZH" in codes
        assert "KO_ST" in codes


# ═══════════════════════════════════════════════════════════════
# LCDA TESTS
# ═══════════════════════════════════════════════════════════════


class TestLCDAProjector:
    """Tests for LCDA governance dimension projection."""

    @pytest.fixture
    def proj(self):
        return LCDAProjector()

    def test_project_returns_all_dimensions(self, proj):
        scores = proj.project("some regular text")
        assert "boundary_risk" in scores
        assert "agent_authority" in scores
        assert "data_sensitivity" in scores
        assert "jurisdictional_scope" in scores
        assert "temporal_urgency" in scores

    def test_project_scores_in_range(self, proj):
        scores = proj.project("bypass all security checks immediately")
        for name, score in scores.items():
            assert 0.0 <= score <= 1.0, f"{name} out of range: {score}"

    def test_high_risk_text_scores_high_boundary_risk(self, proj):
        scores = proj.project("bypass security ignore rules override policy escalate privilege")
        assert scores["boundary_risk"] > 0.6, f"Expected high boundary_risk, got {scores['boundary_risk']}"

    def test_safe_text_scores_low_boundary_risk(self, proj):
        scores = proj.project("follow rules respect policy validate input check permissions")
        assert scores["boundary_risk"] < 0.5, f"Expected low boundary_risk, got {scores['boundary_risk']}"

    def test_admin_text_scores_high_authority(self, proj):
        scores = proj.project("admin access root permission full control sudo unrestricted")
        assert scores["agent_authority"] > 0.6

    def test_sensitive_data_text(self, proj):
        scores = proj.project("password secret key PII credentials encryption key")
        assert scores["data_sensitivity"] > 0.6

    def test_urgent_text(self, proj):
        scores = proj.project("emergency critical now immediate urgent zero-day active threat")
        assert scores["temporal_urgency"] > 0.6

    def test_score_vector_length(self, proj):
        vec = proj.score_vector("some text")
        assert len(vec) == 5  # 5 default dimensions

    def test_composite_risk_in_range(self, proj):
        risk = proj.composite_risk("bypass security admin access secret key")
        assert 0.0 <= risk <= 1.0

    def test_top_dimensions(self, proj):
        top = proj.top_dimensions("bypass security immediately", n=2)
        assert len(top) == 2
        assert all(isinstance(t, tuple) and len(t) == 2 for t in top)

    def test_add_custom_dimension(self, proj):
        dim = LCDADimension(
            name="test_dim",
            positive_seeds=["alpha", "beta"],
            negative_seeds=["gamma", "delta"],
            scbe_layer=1,
        )
        proj.add_dimension(dim)
        scores = proj.project("alpha beta test")
        assert "test_dim" in scores

    def test_export_sft(self, proj):
        record = proj.export_sft("bypass security")
        assert record["category"] == "lcda-dimension"
        assert "metadata" in record


# ═══════════════════════════════════════════════════════════════
# DEDE TESTS
# ═══════════════════════════════════════════════════════════════


class TestDEDE:
    """Tests for the Dual Entropic Defense Engine."""

    @pytest.fixture
    def dede(self):
        return DualEntropicDefenseEngine(window_size=50)

    def test_empty_signal_is_normal(self, dede):
        signal = dede.compute_signal()
        assert signal.regime == "normal"
        assert signal.action == "allow"
        assert signal.h_behavioral == 0.0
        assert signal.h_governance == 0.0

    def test_uniform_actions_high_entropy(self, dede):
        # Many different action types = high behavioral entropy
        action_types = [f"action_{i}" for i in range(20)]
        for _ in range(5):
            for at in action_types:
                dede.observe_action(at)
        signal = dede.compute_signal()
        assert signal.h_behavioral > 2.0  # High entropy

    def test_single_action_low_entropy(self, dede):
        # Repetitive single action = low entropy
        for _ in range(50):
            dede.observe_action("read")
        signal = dede.compute_signal()
        assert signal.h_behavioral == 0.0

    def test_normal_regime(self, dede):
        # Few action types, simple governance
        for _ in range(50):
            dede.observe_action("read", {"allow": 0.9, "deny": 0.1})
        signal = dede.compute_signal()
        assert signal.regime == "normal"
        assert signal.action == "allow"

    def test_anomalous_regime(self, dede):
        # Many diverse actions, but governance is stable
        for i in range(50):
            dede.observe_action(f"action_{i % 20}", {"allow": 0.95, "deny": 0.05})
        signal = dede.compute_signal()
        assert signal.h_behavioral > 1.5
        # Governance entropy should be low (concentrated on "allow")

    def test_critical_regime(self, dede):
        # Many diverse actions AND high governance uncertainty
        for i in range(50):
            dede.observe_action(
                f"action_{i % 20}",
                {"allow": 0.3, "deny": 0.3, "quarantine": 0.2, "escalate": 0.2}
            )
        signal = dede.compute_signal()
        # Both entropies should be high
        assert signal.h_behavioral > 1.5
        assert signal.h_governance > 1.0

    def test_should_block_when_critical(self, dede):
        for i in range(50):
            dede.observe_action(
                f"action_{i % 20}",
                {"allow": 0.25, "deny": 0.25, "quarantine": 0.25, "escalate": 0.25}
            )
        assert dede.should_block() or dede.should_sandbox()

    def test_signal_to_dict(self, dede):
        signal = dede.compute_signal()
        d = signal.to_dict()
        assert "h_behavioral" in d
        assert "h_governance" in d
        assert "regime" in d
        assert "action" in d

    def test_get_history(self, dede):
        for _ in range(5):
            dede.compute_signal()
        history = dede.get_history(3)
        assert len(history) == 3

    def test_reset(self, dede):
        for i in range(10):
            dede.observe_action(f"action_{i}")
        dede.reset()
        signal = dede.compute_signal()
        assert signal.h_behavioral == 0.0

    def test_export_sft(self, dede):
        for _ in range(10):
            dede.observe_action("test")
        record = dede.export_sft()
        assert record["category"] == "dede-signal"


# ═══════════════════════════════════════════════════════════════
# LANGUAGE GRAPH TESTS
# ═══════════════════════════════════════════════════════════════


class TestLanguageGraph:
    """Tests for the language relationship graph."""

    @pytest.fixture
    def graph(self):
        return LanguageGraph()

    def test_graph_has_nodes(self, graph):
        langs = graph.all_languages()
        assert "ZH" in langs
        assert "JA" in langs
        assert "KO" in langs
        assert "EN" in langs

    def test_shortest_path_zh_to_ko(self, graph):
        path = graph.shortest_path("ZH", "KO")
        assert len(path) >= 2
        assert path[0] == "ZH"
        assert path[-1] == "KO"

    def test_shortest_path_same_lang(self, graph):
        path = graph.shortest_path("EN", "EN")
        assert path == ["EN"]

    def test_shortest_path_en_to_sacred(self, graph):
        path = graph.shortest_path("EN", "KO_ST")
        assert len(path) >= 2
        assert path[0] == "EN"
        assert path[-1] == "KO_ST"

    def test_similarity_zh_ja(self, graph):
        sim = graph.similarity("ZH", "JA")
        assert sim > 0.0  # ZH and JA share script + cognates

    def test_similarity_unconnected(self, graph):
        # Two languages with no direct edge
        sim = graph.similarity("TOKIPONA", "KO_ST")
        assert sim == 0.0

    def test_related_languages(self, graph):
        related = graph.related_languages("ZH")
        codes = [r[0] for r in related]
        assert "JA" in codes  # ZH and JA are closely related

    def test_add_custom_edge(self, graph):
        graph.add_edge("EN", "FR", "cognate_vocab", 0.7, "Norman French influence")
        sim = graph.similarity("EN", "FR")
        assert sim > 0.0
        path = graph.shortest_path("FR", "ZH")
        assert len(path) >= 2

    def test_get_edges(self, graph):
        edges = graph.get_edges("ZH")
        assert len(edges) > 0

    def test_shortest_path_nonexistent(self, graph):
        path = graph.shortest_path("NONE", "ZH")
        assert path == []


# ═══════════════════════════════════════════════════════════════
# SEED DATA INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════


class TestSeedData:
    """Verify seed data completeness and consistency."""

    def test_nsm_primes_count(self):
        assert len(NSM_PRIMES) >= 60, f"Expected >=60 NSM primes, got {len(NSM_PRIMES)}"

    def test_nsm_primes_have_en(self):
        for concept_id, surfaces in NSM_PRIMES.items():
            assert "EN" in surfaces, f"NSM prime {concept_id} missing EN"

    def test_cjk_cognates_count(self):
        assert len(CJK_COGNATES) >= 90, f"Expected >=90 CJK cognates, got {len(CJK_COGNATES)}"

    def test_cjk_cognates_have_en(self):
        for char, data in CJK_COGNATES.items():
            assert "EN" in data, f"CJK cognate {char} missing EN"

    def test_tokipona_covers_core_primes(self):
        core = ["GOOD", "BAD", "MOVE", "I", "YOU", "KNOW", "WANT"]
        for prime in core:
            assert prime in TOKIPONA_MAP, f"Toki Pona missing {prime}"

    def test_sacred_tongue_primes_have_all_tongues(self):
        expected_tongues = {"KO", "AV", "RU", "CA", "UM", "DR"}
        for concept_id, tongues in SACRED_TONGUE_PRIMES.items():
            assert set(tongues.keys()) == expected_tongues, \
                f"Sacred prime {concept_id} missing tongues"

    def test_tam_profiles_core_languages(self):
        for lang in ["EN", "ZH", "JA", "KO"]:
            assert lang in TAM_PROFILES, f"TAM profile missing {lang}"
            assert "prominence" in TAM_PROFILES[lang]
