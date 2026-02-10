"""
Tests for HyperbolicRAG: k-NN retrieval in the Poincare ball with d* cost gating.
"""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.ai_brain.hyperbolic_rag import (
    HyperbolicRAG,
    HyperbolicRAGConfig,
    RAGCandidate,
    RAGResult,
    project_to_ball,
)
from src.geoseal import TONGUE_PHASES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_candidate(id: str, embedding, tongue=None, metadata=None):
    return RAGCandidate(id=id, embedding=embedding, tongue=tongue, metadata=metadata)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_default_config(self):
        rag = HyperbolicRAG()
        config = rag.config
        assert config.max_k == 20
        assert config.cost_threshold == 1.5
        assert config.min_phase_alignment == 0.0
        assert config.phase_weight == 2.0

    def test_custom_config(self):
        config = HyperbolicRAGConfig(max_k=5, cost_threshold=2.0)
        rag = HyperbolicRAG(config)
        assert rag.config.max_k == 5
        assert rag.config.cost_threshold == 2.0


# ---------------------------------------------------------------------------
# Basic retrieval
# ---------------------------------------------------------------------------


class TestBasicRetrieval:
    def test_empty_candidates(self):
        rag = HyperbolicRAG()
        results = rag.retrieve([0.1, 0.2], [])
        assert results == []

    def test_sorted_by_distance(self):
        config = HyperbolicRAGConfig(cost_threshold=10.0)
        rag = HyperbolicRAG(config)
        query = [0.1, 0.1, 0.1, 0.1]
        candidates = [
            make_candidate("far", [5.0, 5.0, 5.0, 5.0]),
            make_candidate("near", [0.15, 0.12, 0.11, 0.09]),
            make_candidate("mid", [1.0, 1.0, 1.0, 1.0]),
        ]
        results = rag.retrieve(query, candidates)
        assert len(results) > 0
        for i in range(1, len(results)):
            assert results[i].distance >= results[i - 1].distance

    def test_max_k_limit(self):
        config = HyperbolicRAGConfig(max_k=2, cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [
            make_candidate("a", [0.1, 0.2]),
            make_candidate("b", [0.2, 0.1]),
            make_candidate("c", [0.3, 0.1]),
            make_candidate("d", [0.4, 0.1]),
        ]
        results = rag.retrieve([0.1, 0.1], candidates)
        assert len(results) <= 2

    def test_metadata_preserved(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("a", [0.12, 0.11], metadata={"source": "doc1"})]
        results = rag.retrieve([0.1, 0.1], candidates)
        assert len(results) == 1
        assert results[0].metadata == {"source": "doc1"}


# ---------------------------------------------------------------------------
# d* cost gating
# ---------------------------------------------------------------------------


class TestCostGating:
    def test_gates_far_candidates(self):
        config = HyperbolicRAGConfig(cost_threshold=0.5)
        rag = HyperbolicRAG(config)
        candidates = [
            make_candidate("near", [0.12, 0.11]),
            make_candidate("far", [100.0, 100.0]),
        ]
        results = rag.retrieve([0.1, 0.1], candidates)
        ids = [r.id for r in results]
        assert "far" not in ids

    def test_gated_visible_in_retrieve_all(self):
        config = HyperbolicRAGConfig(cost_threshold=0.5)
        rag = HyperbolicRAG(config)
        candidates = [
            make_candidate("near", [0.12, 0.11]),
            make_candidate("far", [100.0, 100.0]),
        ]
        all_results = rag.retrieve_all([0.1, 0.1], candidates)
        assert len(all_results) == 2
        gated = [r for r in all_results if r.gated]
        assert len(gated) >= 1

    def test_gated_trust_is_zero(self):
        config = HyperbolicRAGConfig(cost_threshold=0.5)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("far", [100.0, 100.0])]
        all_results = rag.retrieve_all([0.1, 0.1], candidates)
        assert all_results[0].gated is True
        assert all_results[0].trust_score == 0


# ---------------------------------------------------------------------------
# Phase alignment
# ---------------------------------------------------------------------------


class TestPhaseAlignment:
    def test_same_tongue_full_phase(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("same", [0.12, 0.11], tongue="KO")]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        assert results[0].phase_score == 1.0

    def test_opposite_tongue_low_phase(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("opp", [0.12, 0.11], tongue="CA")]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        assert results[0].phase_score < 0.5

    def test_null_tongue_zero_phase(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("none", [0.12, 0.11])]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        assert results[0].phase_score == 0.0

    def test_min_phase_alignment_gating(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0, min_phase_alignment=0.9)
        rag = HyperbolicRAG(config)
        candidates = [
            make_candidate("same", [0.12, 0.11], tongue="KO"),
            make_candidate("diff", [0.12, 0.11], tongue="CA"),
        ]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        assert len(results) == 1
        assert results[0].id == "same"


# ---------------------------------------------------------------------------
# Trust scoring
# ---------------------------------------------------------------------------


class TestTrustScoring:
    def test_positive_trust_for_ungated(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("a", [0.12, 0.11], tongue="KO")]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        assert results[0].trust_score > 0

    def test_closer_has_higher_trust(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [
            make_candidate("near", [0.12, 0.11], tongue="KO"),
            make_candidate("far", [2.0, 2.0], tongue="KO"),
        ]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        near = next(r for r in results if r.id == "near")
        far = next(r for r in results if r.id == "far")
        assert near.trust_score > far.trust_score

    def test_phase_mismatch_penalizes_trust(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [
            make_candidate("same_tongue", [0.12, 0.11], tongue="KO"),
            make_candidate("diff_tongue", [0.12, 0.11], tongue="CA"),
        ]
        results = rag.retrieve([0.1, 0.1], candidates, query_tongue="KO")
        same = next(r for r in results if r.id == "same_tongue")
        diff = next(r for r in results if r.id == "diff_tongue")
        assert same.trust_score > diff.trust_score


# ---------------------------------------------------------------------------
# Sacred Tongues coverage
# ---------------------------------------------------------------------------


class TestSacredTongues:
    def test_all_six_tongues(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        for tongue in tongues:
            candidates = [make_candidate(f"c_{tongue}", [0.12, 0.11], tongue=tongue)]
            results = rag.retrieve([0.1, 0.1], candidates, query_tongue=tongue)
            assert len(results) == 1
            assert results[0].phase_score == 1.0


# ---------------------------------------------------------------------------
# Projection helper
# ---------------------------------------------------------------------------


class TestProjection:
    def test_project_to_ball_bounds(self):
        result = project_to_ball([10.0, -10.0, 5.0])
        for x in result:
            assert -1.0 < x < 1.0

    def test_project_zero(self):
        result = project_to_ball([0.0, 0.0])
        assert result == [0.0, 0.0]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_zero_query(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        results = rag.retrieve([0, 0], [make_candidate("a", [0.1, 0.1])])
        assert len(results) == 1

    def test_single_dimension(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        results = rag.retrieve([0.1], [make_candidate("a", [0.2])])
        assert len(results) == 1

    def test_high_dimensional(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        dim = 64
        query = [0.01] * dim
        candidates = [make_candidate("a", [0.02] * dim)]
        results = rag.retrieve(query, candidates)
        assert len(results) == 1

    def test_no_query_tongue(self):
        config = HyperbolicRAGConfig(cost_threshold=100.0)
        rag = HyperbolicRAG(config)
        candidates = [make_candidate("a", [0.12, 0.11], tongue="KO")]
        results = rag.retrieve([0.1, 0.1], candidates)
        assert results[0].phase_score == 0.0
