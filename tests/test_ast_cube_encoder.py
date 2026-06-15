"""Tests for the AST cube encoder (code -> matrix of cube-token vectors)."""
import ast
from python.scbe.ast_cube_encoder import encode, decode, VECTOR_DIM


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
    def test_ast_round_trips_to_source(self):
        enc = encode(SRC)
        assert decode(enc) == ast.unparse(ast.parse(SRC))

    def test_nontrivial_code(self):
        src = "class A:\n    def m(self, n):\n        return [i*i for i in range(n)]\n"
        enc = encode(src)
        assert enc["shape"][0] > 5
        assert decode(enc) == ast.unparse(ast.parse(src))


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
        assert decode(enc) == ast.unparse(ast.parse(src))
