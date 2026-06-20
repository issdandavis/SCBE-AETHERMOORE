"""Verified Rosetta view: one song -> many language faces, proven equal by running each.

Like math notation, the symbols (notes, or conlang words) are universal only because the
lookup table means the same thing everywhere -- so we RUN each face rather than trust it. The
Python reference + structure + bijection are checked unconditionally; the JavaScript agreement
is checked only when node is present (skip otherwise, never faked).
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import polyglot as P  # noqa: E402
from python.scbe.rosetta import benchmark, rosetta  # noqa: E402

_HAVE_NODE = shutil.which("node") is not None


def test_note_song_manifests_runs_and_reads_back():
    r = rosetta("C E", mode="coding")  # add, mul over [2,3,4] -> (3+4) then *2 = 14
    assert r["ops"] == ["add", "mul"]
    assert r["reference"][0] == 14.0  # verified by executing the python reference
    assert r["bijective"] is True
    assert r["song_back"] == "C E"
    assert set(r["faces"]) == set(P.languages())
    assert len(r["faces"]) == 18
    assert r["faces"]["python"]["status"] == "REFERENCE"
    # no face is ever marked verified (AGREE) without actually running
    for f in r["faces"].values():
        if f["status"] in ("NO_TOOLCHAIN", "NO_RUNNER", "EMITTED", "EMIT_ERROR"):
            assert f["status"] != "AGREE"


def test_tokenizer_mode_plays_the_conlang_and_round_trips():
    r = rosetta("bip'a bip'i", mode="ca")  # the same program, written in the conlang
    assert r["ops"] == ["add", "mul"]
    assert r["reference"][0] == 14.0
    assert r["bijective"] is True
    assert r["song_back"] == "bip'a bip'i"


def test_underflow_song_raises_clearly_not_crash():
    with pytest.raises(ValueError, match="underflows the stack"):
        rosetta("C E D")  # three binary ops over a 3-slot stack


def test_unknown_symbol_raises():
    with pytest.raises(ValueError, match="note 'Z'"):
        rosetta("C Z")


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_javascript_face_is_actually_verified():
    r = rosetta("C E")
    assert r["faces"]["javascript"]["status"] == "AGREE"  # ran and agreed with python
    assert "javascript" not in r["disagree"]


def test_benchmark_reports_honest_verified_coverage():
    b = benchmark(["C E", "C C"], mode="coding")
    assert b["songs"] == 2
    assert b["total_faces"] == 18
    assert "python" in b["verified_face_list"]  # the reference always counts
    assert b["verified_faces"] >= 1
    # a face is 'verified' only if it actually ran with no disagreement
    for lang in b["verified_face_list"]:
        d = b["per_language"][lang]
        assert d["ran"] > 0 and d["disagree"] == 0
