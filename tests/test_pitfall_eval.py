"""Tests for pitfall_eval -- the held-out eval with headroom for the pitfall classes better_corpus teaches.

Two contracts:
1. Every eval item DISCRIMINATES (the reference passes, the naive pitfall solution fails) -- execution
   verified, so the set provably has headroom for the taught skill.
2. The eval is DISJOINT from the better_corpus training traces (different function names) -- no
   teaching-to-the-test; a lift measured here is a real generalization to new instances of the class.
"""

from __future__ import annotations

import re

from python.helm.better_corpus import PITFALLS
from python.helm.pitfall_eval import EVAL, discriminates, discriminating, eval_problems


def _func_names(code_blobs):
    names = set()
    for blob in code_blobs:
        names.update(re.findall(r"def\s+(\w+)\s*\(", blob))
    return names


def test_every_eval_item_discriminates_pitfall_from_fix():
    # the whole point: a model that makes the pitfall fails, one that avoids it passes -- verified by running
    for it in EVAL:
        d = discriminates(it)
        assert d["ref_passes"], "%s: reference must pass its tests" % it["name"]
        assert d["naive_fails"], "%s: naive pitfall solution must FAIL (else no headroom)" % it["name"]
    assert len(discriminating()) == len(EVAL)


def test_eval_is_disjoint_from_better_corpus_training():
    # no teaching-to-the-test: the eval problems are NEW instances of the taught classes, not the trained
    # functions. Their function names must not overlap the training traces' function names.
    train_names = _func_names([p["buggy"] for p in PITFALLS] + [p["fix"] for p in PITFALLS])
    eval_names = _func_names([it["ref"] for it in EVAL] + [it["naive"] for it in EVAL])
    overlap = train_names & eval_names
    assert not overlap, "eval reuses trained function(s): %s" % sorted(overlap)


def test_eval_problems_are_mbpp_shaped_and_complete():
    probs = eval_problems()
    assert len(probs) == len(EVAL)  # all discriminate, so all exported
    for p in probs:
        assert set(p) >= {"task_id", "text", "test_list"}
        assert p["task_id"].startswith("pitfalleval_")
        assert p["text"] and p["test_list"]


def test_eval_task_ids_unique():
    ids = [p["task_id"] for p in eval_problems()]
    assert len(ids) == len(set(ids))
