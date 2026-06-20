"""Honest differential conformance for the polyglot multi-backend compiler.

The point of these tests is the HONESTY of the harness, not a claim that all backends
agree. The Python reference and the labeling of unverified backends are checked
unconditionally; the cross-language agreement and the round-divergence catch are checked
only when the toolchain is actually present (skip otherwise) -- never faked.
"""

import shutil

import pytest

from python.scbe import polyglot as P
from python.scbe.polyglot_conformance import conformance

_HAVE_NODE = shutil.which("node") is not None


def _status(rep, lang):
    return next(r.status for r in rep["results"] if r.lang == lang)


def _values(rep, lang):
    return next(r.values for r in rep["results"] if r.lang == lang)


def test_python_reference_is_computed_in_process():
    # mul gt == (a > b*c) ? 1 : 0  -- a real decision, evaluated by the reference
    rep = conformance(P.program_bytes("mul", "gt"), [(2.0, 3.0, 4.0), (10.0, 3.0, 2.0)])
    assert rep["reference"] == [0.0, 1.0]
    assert _status(rep, "python") == "REFERENCE"


def test_unverified_backends_are_never_marked_agree():
    rep = conformance(P.program_bytes("add"), [(2.0, 3.0, 4.0)])
    for r in rep["results"]:
        if r.status in ("NO_RUNNER", "NO_TOOLCHAIN", "ERROR"):
            assert not r.values  # nothing claimed for a backend that did not run
    # a backend with no runner implemented (haskell here) is labeled, not agreed
    assert _status(rep, "haskell") == "NO_RUNNER"


def test_summary_counts_are_consistent():
    rep = conformance(P.program_bytes("add"), [(2.0, 3.0, 4.0)])
    s = rep["summary"]
    # you can never verify more backends than actually ran (minus the reference itself)
    assert s["verified_agree"] <= s["runnable_backends"] - 1
    unverified = sum(1 for r in rep["results"] if r.status in ("NO_RUNNER", "NO_TOOLCHAIN", "ERROR"))
    assert s["emitted_unverified"] == unverified
    assert s["total_backends"] == len(P.languages())


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_javascript_agrees_on_a_portable_decision():
    rep = conformance(P.program_bytes("mul", "gt"), [(2.0, 3.0, 4.0), (10.0, 3.0, 2.0)])
    assert _status(rep, "javascript") == "AGREE"
    assert _values(rep, "javascript") == [0.0, 1.0]


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_round_half_even_divergence_is_caught_not_hidden():
    # Python rounds 2.5 -> 2.0 (half-to-even); JS Math.round(2.5) -> 3.0 (half-up).
    rep = conformance(P.program_bytes("round"), [(2.0, 3.0, 2.5)])
    assert rep["reference"] == [2.0]
    assert _status(rep, "javascript") == "DISAGREE"
    assert _values(rep, "javascript") == [3.0]
    assert "javascript" in rep["summary"]["disagree"]
