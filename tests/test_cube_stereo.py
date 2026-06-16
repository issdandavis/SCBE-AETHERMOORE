"""Tests for the 3D-glasses stereo combiner (two AST lenses -> one view)."""

from python.scbe.cube_stereo import stereo_encode
from python.scbe.ast_cube_encoder import VECTOR_DIM

SRC = "def f(x):\n    y = x + 1\n    return y\n"


def test_lenses_fully_lock():
    s = stereo_encode(SRC)
    assert s["lock_ratio"] == 1.0  # both lenses see the same node everywhere
    assert s["lens_a_count"] == s["lens_b_count"] == s["node_count"]


def test_stereo_vector_is_concatenation():
    s = stereo_encode(SRC)
    # 4 relation dims (lens A) + VECTOR_DIM (lens B)
    assert s["stereo_width"] == 4 + VECTOR_DIM
    assert all(len(row) == s["stereo_width"] for row in s["stereo_matrix"])


def test_both_lenses_present_per_token():
    t = stereo_encode(SRC)["tokens"][1]
    assert "lens_a_relation" in t and "lens_b_location" in t and "lens_b_faces" in t
    assert set(t["lens_a_relation"]) == {"parent", "field", "child_index", "depth"}


def test_handles_nontrivial_code():
    src = "class A:\n    def m(self, n):\n        return [i*i for i in range(n)]\n"
    s = stereo_encode(src)
    assert s["node_count"] > 8 and s["lock_ratio"] == 1.0
