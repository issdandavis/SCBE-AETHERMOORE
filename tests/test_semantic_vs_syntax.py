"""Surface spelling != semantics: the executed counter-measurement to the mountain map.

Proves, by running, that the mountain map's identical-spelling metric anti-correlates with
the computation: identical `==` diverges (Python value-equality vs JS coercion), unalike
map/comprehension converges. The python-side facts are unconditional; the JS comparison runs
only when node is present (skip otherwise, never faked).
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "mountain_map"))

import semantic_vs_syntax as S  # noqa: E402

_HAVE_NODE = shutil.which("node") is not None
M = S.measure()


def test_python_side_facts_hold_unconditionally():
    # `1 == "1"` is value-inequality in Python; doubling a list is [2,4,6]
    assert M["case1_same_spelling_eq"]["python"] is False
    assert M["case2_diff_spelling_map"]["python"] == [2, 4, 6]


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_identical_spelling_diverges_in_meaning():
    c = M["case1_same_spelling_eq"]
    assert c["javascript"] is True  # JS coercion: 1 == "1" is true
    assert c["semantics_diverge"] is True  # same glyph `==`, different result


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_different_spelling_converges_in_computation():
    c = M["case2_diff_spelling_map"]
    assert c["javascript"] == [2, 4, 6]
    assert c["computation_converges"] is True  # unalike spelling, identical result
