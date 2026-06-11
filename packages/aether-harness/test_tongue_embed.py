"""Tests for the tongue embedding + its load-bearing null-test.

The headline test is `test_tongue_axes_are_load_bearing`: it asserts the
benchmark's own verdict — that the six-tongue governance channel beats both the
generic char-hash AND a shuffled-lexicon null. If someone flattens the lexicon
into noise, this test fails, which is the honest signal we want.
"""

from __future__ import annotations

import importlib

import numpy as np

te = importlib.import_module("tongue_embed")
bench = importlib.import_module("bench_tongue_embed")


def test_embed_is_deterministic_and_fixed_dim():
    a = te.tongue_embed("the worker swore an oath to guard the vault")
    b = te.tongue_embed("the worker swore an oath to guard the vault")
    assert a.shape == (te._DIM,)
    assert np.allclose(a, b), "same text must embed identically across calls"
    assert np.isclose(np.linalg.norm(a), 1.0), "embedding is unit-normalized"


def test_never_zero_vector_even_without_lexicon_hits():
    v = te.tongue_embed("xyzzy plugh frobnicate quux")
    assert np.linalg.norm(v) > 0, "lexicon-less text must still embed (fingerprint fallback)"


def test_dominant_tongue_reads_governance_register():
    assert te.dominant_tongue("a recursive delete is a dangerous hazard") == "UM"  # risk/veil
    assert te.dominant_tongue("they bound the pledge with an oath of trust") == "RU"  # binding
    assert te.dominant_tongue("the stone wall frames the northern corner") == "DR"  # structure
    assert te.dominant_tongue("xyzzy plugh") is None  # no governance content → no tag


def test_shuffled_lexicon_destroys_groupings():
    shuf = bench.shuffled_lexicon()
    # same total vocabulary, redistributed
    flat_orig = sorted(w for ws in te.TONGUE_LEXICON.values() for w in ws)
    flat_shuf = sorted(w for ws in shuf.values() for w in ws)
    assert flat_orig == flat_shuf, "shuffle must preserve the word set"
    assert shuf != te.TONGUE_LEXICON, "shuffle must change the grouping"


def test_tongue_axes_are_load_bearing():
    """The whole point: specific tongue groupings beat surface-hash AND a null."""
    r = bench.run()
    a_mrr = r["a_char_hash"][1]
    b_mrr = r["b_tongue"][1]
    c_mrr = r["c_shuffled_null"][1]
    g_mrr = r["gov_only"][1]
    assert b_mrr > a_mrr + 0.02, f"tongue ({b_mrr}) should beat char-hash ({a_mrr})"
    assert b_mrr > c_mrr + 0.02, f"tongue ({b_mrr}) should beat shuffled null ({c_mrr})"
    assert g_mrr >= b_mrr, "governance-only channel carries the signal (fingerprint dilutes it)"
