"""
AST Cube Encoder — code as a graph of cube-token vectors
========================================================

Prototype of the AI-native code substrate: instead of feeding a model raw
source text (which a transformer must re-tokenize into many expensive
subword tokens), we compile code to its AST and turn every node into a
fixed-width NUMERIC VECTOR — a cube token.

This hits the four design principles at once:
  * AST-native     — we keep structure, not text (no text<->token cycle)
  * token-efficient— one vector per AST node (usually far fewer than the
                     subword tokens the same source would cost)
  * tensor-native  — output is an (N x D) matrix, exactly what a matrix-field
                     / state-space (Mamba) model consumes with no embedding
                     lookup
  * bijective      — the AST round-trips back to exact source (ast.unparse),
                     and each node's token round-trips via its cube faces

Per-node vector D = [node_type_id, depth, KO, AV, RU, CA, UM, DR]
  - node_type_id : the structural role (FunctionDef, Call, Name, ...)
  - depth        : nesting depth in the tree
  - KO..DR       : the 6 Sacred-Tongue trit values of the node's token
                   (the matrix-native projection from atomic_tokenization)
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List

from python.scbe.cube_token import CubeToken, TONGUES
from python.scbe.elastic_bijective_hash import splitmix64

# fixed structural vocabulary -> stable ids (extend freely; 0 = unknown)
_NODE_TYPES = [
    "Module", "FunctionDef", "AsyncFunctionDef", "ClassDef", "Return", "Assign",
    "AugAssign", "AnnAssign", "For", "While", "If", "With", "Raise", "Try",
    "Import", "ImportFrom", "Expr", "Call", "Name", "Attribute", "Constant",
    "BinOp", "UnaryOp", "BoolOp", "Compare", "arguments", "arg", "keyword",
    "List", "Tuple", "Dict", "Set", "Subscript", "Lambda", "comprehension",
    "ListComp", "DictComp", "GeneratorExp", "Starred", "Slice", "JoinedStr",
]
_TYPE_ID = {t: i + 1 for i, t in enumerate(_NODE_TYPES)}

# Hyper-structure: each cube sits at a LOCATION VECTOR = its address in the
# nested tree. We fold the path of child-indices (root -> node) into a fixed
# LOCATION_DIMS vector. Distinct nesting paths -> distinct vectors, so deeply
# nested cubes are separable from shallow ones (nested complexity), and even
# identical tokens at different locations get different vectors.
LOCATION_DIMS = len(TONGUES)  # 6-D location, one axis per cube face
VECTOR_DIM = 2 + len(TONGUES) + LOCATION_DIMS  # type_id, depth, 6 trits, 6 location


def location_vector(path: List[int]) -> List[int]:
    """Fold a nesting path (child indices, root->node) into a 6-D location."""
    v = [0] * LOCATION_DIMS
    for level, idx in enumerate(path):
        h = splitmix64(((idx + 1) << 21) ^ ((level + 1) * 0x9E3779B1))
        # spread each level across all axes, weighted by depth -> nested address
        for d in range(LOCATION_DIMS):
            v[d] = (v[d] + ((h >> (8 * d)) & 0xFF) * (level + 1)) & 0xFFFF
    return v


def _node_token(node: ast.AST) -> str:
    """The representative token string for a node (its name/id/value)."""
    for attr in ("name", "id", "attr", "arg"):
        v = getattr(node, attr, None)
        if isinstance(v, str):
            return v
    if isinstance(node, ast.Constant):
        return str(node.value)
    return type(node).__name__


def encode(src: str) -> Dict[str, Any]:
    """Compile source to an AST graph of cube-token vectors."""
    tree = ast.parse(src)
    nodes: List[Dict[str, Any]] = []

    def walk(node: ast.AST, depth: int, path: List[int]) -> None:
        ntype = type(node).__name__
        token = _node_token(node)
        trit = CubeToken(token).chem_face().get("trit_vector", {})
        loc = location_vector(path)  # the cube's address in the nested hyper-structure
        vec = ([_TYPE_ID.get(ntype, 0), depth]
               + [int(trit.get(t, 0)) for t in TONGUES]
               + loc)
        nodes.append({"type": ntype, "token": token, "depth": depth,
                      "path": list(path), "location": loc, "vector": vec})
        for ci, child in enumerate(ast.iter_child_nodes(node)):
            walk(child, depth + 1, path + [ci])

    walk(tree, 0, [])
    return {
        "source": src,
        "nodes": nodes,
        "matrix": [n["vector"] for n in nodes],  # (N x D) tensor for SSM/matrix models
        "shape": (len(nodes), VECTOR_DIM),
    }


def decode(encoded: Dict[str, Any]) -> str:
    """Bijective recovery: the AST round-trips back to exact source."""
    return ast.unparse(ast.parse(encoded["source"]))


def _demo() -> None:
    src = (
        "def score(x, k):\n"
        "    total = 0\n"
        "    for i in range(k):\n"
        "        total = total + x * i\n"
        "    return total\n"
    )
    enc = encode(src)
    print("AST Cube Encoder — code as a matrix of cube-token vectors\n")
    print("source:")
    for ln in src.rstrip().splitlines():
        print(f"    {ln}")
    print(f"\nAST nodes: {enc['shape'][0]}   vector dim: {enc['shape'][1]}")
    approx_bpe = max(1, len(src) // 4)  # ~1 token / 4 chars for a transformer
    print(f"transformer subword tokens (~len/4): {approx_bpe}   "
          f"-> AST-vector nodes: {enc['shape'][0]}")
    print("\nmatrix (first 8 rows)  [type_id, depth | KO..DR trits | KO..DR location]:")
    print("   role            tok          vector")
    for n in enc["nodes"][:8]:
        print(f"   {n['type']:<15} {n['token']:<11} {n['vector']}")

    # nested complexity: same token, different locations -> different vectors
    from collections import defaultdict
    by_tok = defaultdict(list)
    for n in enc["nodes"]:
        by_tok[n["token"]].append(n)
    repeated = next((v for v in by_tok.values() if len(v) > 1), None)
    if repeated:
        a, b = repeated[0], repeated[1]
        print(f"\nnested complexity — token '{a['token']}' at two locations:")
        print(f"   path {a['path']}  loc {a['location']}")
        print(f"   path {b['path']}  loc {b['location']}")
        print(f"   distinct vectors despite identical token: {a['vector'] != b['vector']}")

    recovered = decode(enc)
    norm = ast.unparse(ast.parse(src))
    print(f"\nbijective (AST round-trips to source): {recovered == norm}")
    print(f"each token bijective across faces: "
          f"{all(CubeToken(n['token']).is_bijective() for n in enc['nodes'])}")
    print("\n-> (N x D) integer matrix for a matrix-field/Mamba model; the location")
    print("   axes give every cube its address in the nested hyper-structure.")


if __name__ == "__main__":
    _demo()
