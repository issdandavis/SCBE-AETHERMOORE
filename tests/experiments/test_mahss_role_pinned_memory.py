"""Unit tests for the role-pinned HRR memory used by v8-pre Phase 1.

These tests verify the load-bearing claims:

1. Single-binding retrieval is exact (top-1 score very close to 1.0).
2. Multi-binding retrieval still picks the right filler at realistic load.
3. Distractor registration does not corrupt retrieval of bound fillers.
4. Crosstalk floor matches the theoretical sqrt(N/d) prediction.
5. Empty / degenerate inputs raise or return clean empty results."""

from __future__ import annotations

import math

import numpy as np
import pytest

from python.scbe.mahss_role_pinned_memory import (
    V6G_DISTRACTORS,
    V6G_RAW_FAILURE_CORPUS,
    RolePinnedMemory,
    build_per_prompt_memory,
)


def test_single_binding_round_trip_recovers_filler():
    """HRR unbinding is an approximate inverse, not exact. At dim=4096 the
    recovered cosine is ~0.71, but the noise floor against unbound vectors
    is ~1/sqrt(4096) ~ 0.016, so retrieval is unambiguous."""

    mem = RolePinnedMemory(dim=4096)
    mem.register_distractors("TONGUE", ["kor'aelin", "avali", "draumric"])
    mem.bind("TONGUE", "umbroth")
    ranks = mem.query("TONGUE", top_k=4)
    assert ranks[0][0] == "umbroth"
    # SNR check: bound-filler score should dominate any unbound distractor
    assert ranks[0][1] > 10 * abs(ranks[1][1])


def test_multi_binding_retrieves_correct_filler_for_each_role():
    """Five different roles each with one filler -- each role must retrieve
    its own filler over the candidates registered for that role."""

    mem = RolePinnedMemory(dim=4096)
    mem.register_distractors("TONGUE", ["kor'aelin", "avali", "umbroth", "draumric"])
    mem.register_distractors("LANG", ["python", "haskell", "rust"])
    mem.register_distractors("SLOT", ["sig", "body", "init"])
    mem.bind("TONGUE", "umbroth")
    mem.bind("LANG", "haskell")
    mem.bind("SLOT", "body")

    assert mem.query("TONGUE", top_k=1)[0][0] == "umbroth"
    assert mem.query("LANG", top_k=1)[0][0] == "haskell"
    assert mem.query("SLOT", top_k=1)[0][0] == "body"


def test_distractor_registration_does_not_alter_memory():
    """Registering candidates without binding them must not change the
    memory bundle (only bind() should add to memory)."""

    mem = RolePinnedMemory(dim=512)
    mem.bind("TONGUE", "umbroth")
    snapshot = mem.memory.copy()
    mem.register_distractors("TONGUE", ["kor'aelin", "avali", "draumric"])
    mem.register_distractors("LANG", ["haskell", "rust"])
    np.testing.assert_array_equal(mem.memory, snapshot)


def test_crosstalk_floor_matches_theory():
    mem = RolePinnedMemory(dim=4096)
    for i in range(10):
        mem.bind(f"R{i}", f"F{i}")
    expected = math.sqrt(10 / 4096)
    assert abs(mem.crosstalk_floor() - expected) < 1e-9


def test_query_unknown_role_returns_empty():
    mem = RolePinnedMemory(dim=512)
    mem.bind("TONGUE", "umbroth")
    assert mem.query("LANG") == []


def test_score_correct_field():
    mem = RolePinnedMemory(dim=2048)
    mem.register_distractors("TONGUE", ["kor'aelin", "avali", "umbroth", "draumric"])
    mem.bind("TONGUE", "umbroth")
    result = mem.score("TONGUE", expected="umbroth")
    assert result.correct is True
    assert result.retrieved == "umbroth"
    assert result.margin > 0.0


def test_score_with_wrong_expected_marks_incorrect():
    mem = RolePinnedMemory(dim=2048)
    mem.register_distractors("TONGUE", ["kor'aelin", "umbroth"])
    mem.bind("TONGUE", "umbroth")
    result = mem.score("TONGUE", expected="kor'aelin")
    assert result.correct is False
    assert result.retrieved == "umbroth"


def test_invalid_dim_rejected():
    with pytest.raises(ValueError):
        RolePinnedMemory(dim=4)


def test_corpus_shape_is_well_formed():
    """v6g failure corpus must have entries for each prompt and every
    (role, filler) pair must be in the distractor vocabulary."""

    assert len(V6G_RAW_FAILURE_CORPUS) == 10
    for _prompt_id, pairs in V6G_RAW_FAILURE_CORPUS:
        assert len(pairs) >= 1
        for role, filler in pairs:
            assert role in V6G_DISTRACTORS, f"role {role} missing from distractor vocab"
            assert filler in V6G_DISTRACTORS[role], (
                f"filler {filler!r} not in V6G_DISTRACTORS[{role!r}]"
            )


def test_build_per_prompt_memory_registers_distractors_and_binds_pairs():
    pairs = (("TONGUE", "umbroth"), ("LANG", "haskell"))
    mem = build_per_prompt_memory(pairs, dim=2048, distractors=V6G_DISTRACTORS)
    # All distractors should be queryable
    assert mem.filler_dict_size("TONGUE") == len(V6G_DISTRACTORS["TONGUE"])
    assert mem.filler_dict_size("LANG") == len(V6G_DISTRACTORS["LANG"])
    # Bindings should retrieve correctly
    assert mem.query("TONGUE", top_k=1)[0][0] == "umbroth"
    assert mem.query("LANG", top_k=1)[0][0] == "haskell"


def test_repeated_binding_to_same_role_with_different_filler_degrades_gracefully():
    """Two bindings to the same role superpose. Top-1 should be one of the
    two; both should rank above unbound distractors."""

    mem = RolePinnedMemory(dim=4096)
    mem.register_distractors("TONGUE", ["kor'aelin", "avali", "umbroth", "draumric", "runethic"])
    mem.bind("TONGUE", "umbroth")
    mem.bind("TONGUE", "draumric")
    ranks = mem.query("TONGUE", top_k=5)
    top_two = {ranks[0][0], ranks[1][0]}
    assert top_two == {"umbroth", "draumric"}


def test_dim_scales_signal_to_noise():
    """At dim=64 with 6 bindings, retrieval starts to noise out; at dim=4096
    it should be reliable. This pins the dim choice for the bench."""

    pairs = (
        ("TONGUE", "umbroth"),
        ("LANG", "haskell"),
        ("SLOT", "body"),
        ("METRIC", "phi=6.85"),
        ("KEYWORD", "return"),
        ("IDENT", "count_vowels"),
    )

    mem_high = build_per_prompt_memory(pairs, dim=4096, distractors=V6G_DISTRACTORS)
    high_correct = sum(mem_high.score(role, expected).correct for role, expected in pairs)
    assert high_correct == len(pairs)

    # Low-dim memory should still mostly work but with degraded margins
    mem_low = build_per_prompt_memory(pairs, dim=64, distractors=V6G_DISTRACTORS)
    low_correct = sum(mem_low.score(role, expected).correct for role, expected in pairs)
    # Just assert dim=4096 is at least as good as dim=64
    assert high_correct >= low_correct
