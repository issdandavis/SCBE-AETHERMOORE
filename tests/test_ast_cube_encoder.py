"""Tests for the AST cube encoder (code -> matrix of cube-token vectors)."""

import ast
import pytest

from python.scbe.ast_cube_encoder import (
    VECTOR_DIM,
    decode,
    decode_ast_normalized,
    encode,
    verify_bijective_layer,
)

SRC = "def f(x):\n    y = x + 1\n    return y\n"


class TestEncode:
    def test_matrix_shape(self):
        enc = encode(SRC)
        n = enc["shape"][0]
        assert enc["shape"][1] == VECTOR_DIM
        assert len(enc["matrix"]) == n == len(enc["nodes"])
        assert all(len(row) == VECTOR_DIM for row in enc["matrix"])

    def test_all_ints(self):
        enc = encode(SRC)
        assert all(isinstance(v, int) for row in enc["matrix"] for v in row)

    def test_has_function_and_name_nodes(self):
        types = {n["type"] for n in encode(SRC)["nodes"]}
        assert "FunctionDef" in types and "Name" in types and "Return" in types


class TestBijective:
    def test_exact_source_round_trips(self):
        enc = encode(SRC)
        assert decode(enc) == SRC
        assert verify_bijective_layer(enc)

    def test_nontrivial_code(self):
        src = "class A:\n    def m(self, n):\n        return [i*i for i in range(n)]\n"
        enc = encode(src)
        assert enc["shape"][0] > 5
        assert decode(enc) == src
        assert decode_ast_normalized(enc) == ast.unparse(ast.parse(src))

    @pytest.mark.parametrize(
        "src",
        [
            "def f( x ):\n    # keep comment\n    return  x+1\n",
            "def f(x):\r\n\treturn x + 1\r\n",
            "name = 'Δ-token-🧪'\n",
            "x = 1",
        ],
    )
    def test_bijective_layer_handles_source_edge_cases(self, src):
        enc = encode(src)
        assert decode(enc) == src
        assert verify_bijective_layer(enc)
        assert enc["bijective"]["byte_count"] == len(src.encode("utf-8"))

    def test_tampered_source_lane_fails_verification(self):
        enc = encode("x = 1\n")
        enc["bijective"] = dict(enc["bijective"])
        enc["bijective"]["source_utf8_b64"] = encode("x = 2\n")["bijective"]["source_utf8_b64"]
        assert not verify_bijective_layer(enc)
        with pytest.raises(ValueError, match="hash mismatch"):
            decode(enc)


class TestHyperStructureLocation:
    def test_location_dims_in_vector(self):
        from python.scbe.ast_cube_encoder import LOCATION_DIMS, location_vector

        assert len(location_vector([0, 1, 2])) == LOCATION_DIMS
        assert location_vector([]) == [0] * LOCATION_DIMS  # root has no path

    def test_distinct_paths_distinct_locations(self):
        from python.scbe.ast_cube_encoder import location_vector

        assert location_vector([0, 1]) != location_vector([1, 0])
        assert location_vector([0]) != location_vector([0, 0])

    def test_same_token_different_location_different_vector(self):
        # 'x' appears as a param and nested in the expression
        src = "def f(x):\n    return (x + (x * x))\n"
        nodes = [n for n in encode(src)["nodes"] if n["token"] == "x"]
        assert len(nodes) >= 2
        vecs = {tuple(n["vector"]) for n in nodes}
        assert len(vecs) == len(nodes)  # all distinct via location

    def test_still_bijective(self):
        src = "def f(x):\n    return (x + (x * x))\n"
        enc = encode(src)
        assert decode(enc) == src
        assert decode_ast_normalized(enc) == ast.unparse(ast.parse(src))


class TestFaceSignal:
    def test_face_trits_are_ast_semantic_not_collapsed(self):
        src = "def f(x):\n" "    if x > 0:\n" "        return x + 1\n" "    return {'x': x}\n"
        enc = encode(src)
        faces = {tuple(n["vector"][2:8]) for n in enc["nodes"]}
        assert len(faces) >= 6

    def test_computation_and_control_activate_different_faces(self):
        enc = encode("if x > 0:\n    y = x + 1\n")
        by_type = {n["type"]: n for n in enc["nodes"]}

        # canonical tongue roles: control flow -> KO, math/logic -> CA, transform -> DR
        assert by_type["If"]["face_trits"]["KO"] == 1
        assert by_type["BinOp"]["face_trits"]["CA"] == 1
        assert by_type["Assign"]["face_trits"]["DR"] == 1

    def test_faces_carry_canonical_tongue_roles(self):
        from python.scbe.ast_cube_encoder import FACE_LEGEND

        assert FACE_LEGEND["KO"] == "Control Flow"
        assert FACE_LEGEND["UM"] == "Security"
        assert FACE_LEGEND["CA"] == "Math/Logic"

        enc = encode("import os\ntry:\n    raise ValueError()\nexcept Exception:\n    pass\n")
        by_type = {n["type"]: n for n in enc["nodes"]}
        # security-relevant nodes light the Security (UM) face
        assert by_type["Raise"]["face_trits"]["UM"] == 1
        assert by_type["Import"]["face_trits"]["UM"] == 1
        # the payload self-documents its face axes, and nodes expose readable roles
        assert enc["face_legend"]["DR"] == "Transforms"
        assert "Security" in by_type["Raise"]["roles"]

    def test_name_context_changes_face_signal(self):
        enc = encode("x = x + 1\n")
        names = [n for n in enc["nodes"] if n["type"] == "Name" and n["token"] == "x"]

        assert len(names) == 2
        assert names[0]["face_trits"] != names[1]["face_trits"]


class TestFastPath:
    def test_encode_matrix_matches_encode(self):
        from python.scbe.ast_cube_encoder import encode, encode_matrix

        for src in [
            "x = 1\n",
            "def f(a, b):\n    return a + b * 2\n",
            "class A:\n    def m(self, n):\n        return [i for i in range(n)]\n",
        ]:
            assert encode_matrix(src)["matrix"] == encode(src)["matrix"]

    def test_encode_matrix_bijective(self):
        from python.scbe.ast_cube_encoder import encode_matrix, decode

        src = "# c\r\ndef f():\treturn '🧪'\n"
        assert decode(encode_matrix(src)) == src

    def test_face_memoization_used(self):
        from python.scbe.ast_cube_encoder import encode, _FACE_CACHE

        _FACE_CACHE.clear()
        encode("a = b + c\nd = a + b\n")
        assert len(_FACE_CACHE) > 0  # repeated tokens cached
