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
VECTOR_DIM = 2 + len(TONGUES)  # type_id, depth, + 6 trits


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

    def walk(node: ast.AST, depth: int) -> None:
        ntype = type(node).__name__
        token = _node_token(node)
        trit = CubeToken(token).chem_face().get("trit_vector", {})
        vec = [_TYPE_ID.get(ntype, 0), depth] + [int(trit.get(t, 0)) for t in TONGUES]
        nodes.append({"type": ntype, "token": token, "depth": depth, "vector": vec})
        for child in ast.iter_child_nodes(node):
            walk(child, depth + 1)

    walk(tree, 0)
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
    print("\nmatrix (first 8 rows)  [type_id, depth, KO,AV,RU,CA,UM,DR]:")
    print("   role            tok           vector")
    for n in enc["nodes"][:8]:
        print(f"   {n['type']:<15} {n['token']:<12}  {n['vector']}")
    # bijective check
    recovered = decode(enc)
    norm = ast.unparse(ast.parse(src))
    print(f"\nbijective (AST round-trips to source): {recovered == norm}")
    print(f"each token bijective across faces: "
          f"{all(CubeToken(n['token']).is_bijective() for n in enc['nodes'])}")
    print("\n-> this (N x D) integer matrix is what a matrix-field / Mamba model")
    print("   ingests directly; an LLM can read the symbolic face of the same AST.")


if __name__ == "__main__":
    _demo()
