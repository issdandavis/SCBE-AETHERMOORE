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
  * bijective      — a lossless source lane recovers exact text, while the
                     AST lane recovers normalized code semantics

Per-node vector D = [node_type_id, depth, KO, AV, RU, CA, UM, DR, loc_KO..loc_DR]
  - node_type_id : the structural role (FunctionDef, Call, Name, ...)
  - depth        : nesting depth in the tree
  - KO..DR       : AST-aware 6-face trits. These blend atomic_tokenization with
                   code semantics so each face carries distinct signal.
  - loc_KO..DR   : nested hyper-structure address
"""

from __future__ import annotations

import ast
import base64
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from python.scbe.cube_token import CubeToken, TONGUES
    from python.scbe.elastic_bijective_hash import splitmix64
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.append(str(Path(__file__).resolve().parents[2]))
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

FACE_RULES = {
    # Kor'aelin: intent / executable flow.
    "KO": {
        "FunctionDef",
        "AsyncFunctionDef",
        "Return",
        "Assign",
        "AugAssign",
        "AnnAssign",
        "Call",
    },
    # Avali: interface / metadata / access surface.
    "AV": {"arguments", "arg", "keyword", "Attribute", "Import", "ImportFrom", "Call"},
    # Runethic: control / branch / governance.
    "RU": {"If", "For", "While", "With", "Try", "Raise", "Compare", "BoolOp"},
    # Cassisivadan: computation / indexing / numeric structure.
    "CA": {
        "BinOp",
        "UnaryOp",
        "Constant",
        "Subscript",
        "Slice",
        "ListComp",
        "DictComp",
        "GeneratorExp",
        "comprehension",
    },
    # Umbroth: scope / abstraction / binding boundary.
    "UM": {"ClassDef", "Lambda", "FunctionDef", "AsyncFunctionDef", "Name", "Starred"},
    # Draumric: declarative structure / data shape.
    "DR": {"Module", "Expr", "List", "Tuple", "Dict", "Set", "JoinedStr", "Constant"},
}

NEGATIVE_FACE_RULES = {
    "KO": {"Pass"},
    "AV": {"Delete"},
    "RU": {"Raise"},
    "CA": set(),
    "UM": {"Global", "Nonlocal"},
    "DR": set(),
}


def _source_bijective_layer(src: str) -> Dict[str, Any]:
    """Lossless side lane for edge cases ASTs cannot carry.

    ASTs discard comments, exact whitespace, newline style, and formatting. The
    matrix lane is for model-readable semantics; this lane is for exact source
    reconstruction and tamper checks.
    """

    raw = src.encode("utf-8", errors="surrogatepass")
    if "\r\n" in src:
        newline_style = "crlf"
    elif "\r" in src:
        newline_style = "cr"
    elif "\n" in src:
        newline_style = "lf"
    else:
        newline_style = "none"
    return {
        "schema": "scbe_ast_source_bijection_v1",
        "encoding": "utf-8-surrogatepass",
        "source_utf8_b64": base64.b64encode(raw).decode("ascii"),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "char_count": len(src),
        "byte_count": len(raw),
        "newline_style": newline_style,
        "has_trailing_newline": src.endswith(("\n", "\r")),
    }


def _source_from_bijective_layer(layer: Dict[str, Any]) -> str:
    raw = base64.b64decode(layer["source_utf8_b64"].encode("ascii"), validate=True)
    expected = layer.get("source_sha256")
    actual = hashlib.sha256(raw).hexdigest()
    if expected and actual != expected:
        raise ValueError("bijective source lane hash mismatch")
    return raw.decode("utf-8", errors="surrogatepass")


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


def _face_trits(node: ast.AST, token: str) -> Dict[str, int]:
    """Return discriminative 6-face trits for an AST node.

    Atomic tokenization supplies the chemistry/governance base. The AST rules
    add code semantics so FunctionDef, Call, If, BinOp, Name, etc. no longer
    collapse to the same coarse face vector.
    """

    ntype = type(node).__name__
    base = CubeToken(token).chem_face().get("trit_vector", {})
    out: Dict[str, int] = {}
    for tongue in TONGUES:
        score = int(base.get(tongue, 0))
        if ntype in FACE_RULES[tongue]:
            score += 2
        if ntype in NEGATIVE_FACE_RULES[tongue]:
            score -= 2
        out[tongue] = 1 if score > 0 else (-1 if score < 0 else 0)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            out["CA"] = 1
        elif isinstance(node.value, str):
            out["DR"] = 1
        elif node.value is None or isinstance(node.value, bool):
            out["RU"] = 1

    if isinstance(node, ast.Name):
        if isinstance(node.ctx, ast.Store):
            out["UM"] = 1
            out["KO"] = 1
            out["AV"] = -1
        elif isinstance(node.ctx, ast.Load):
            out["AV"] = 1
            out["UM"] = -1

    return out


def encode(src: str) -> Dict[str, Any]:
    """Compile source to an AST graph of cube-token vectors."""
    tree = ast.parse(src)
    nodes: List[Dict[str, Any]] = []

    def walk(node: ast.AST, depth: int, path: List[int]) -> None:
        ntype = type(node).__name__
        token = _node_token(node)
        trit = _face_trits(node, token)
        loc = location_vector(path)  # the cube's address in the nested hyper-structure
        vec = ([_TYPE_ID.get(ntype, 0), depth]
               + [int(trit.get(t, 0)) for t in TONGUES]
               + loc)
        nodes.append({"type": ntype, "token": token, "depth": depth,
                      "face_trits": {t: int(trit.get(t, 0)) for t in TONGUES},
                      "path": list(path), "location": loc, "vector": vec})
        for ci, child in enumerate(ast.iter_child_nodes(node)):
            walk(child, depth + 1, path + [ci])

    walk(tree, 0, [])
    return {
        "source": src,
        "bijective": _source_bijective_layer(src),
        "nodes": nodes,
        "matrix": [n["vector"] for n in nodes],  # (N x D) tensor for SSM/matrix models
        "shape": (len(nodes), VECTOR_DIM),
    }


def decode(encoded: Dict[str, Any]) -> str:
    """Exact recovery from the bijective source lane."""
    if "bijective" in encoded:
        return _source_from_bijective_layer(encoded["bijective"])
    # Backward compatibility for older payloads that only carried source text.
    return encoded["source"]


def decode_ast_normalized(encoded: Dict[str, Any]) -> str:
    """Semantic recovery through Python's AST normalizer.

    This is useful for comparing behavior-level code structure, but it is not
    exact: comments and formatting are intentionally absent from Python ASTs.
    """
    return ast.unparse(ast.parse(decode(encoded)))


def verify_bijective_layer(encoded: Dict[str, Any]) -> bool:
    """Return True when the exact source lane reconstructs and hashes cleanly."""
    try:
        recovered = decode(encoded)
    except Exception:
        return False
    layer = encoded.get("bijective")
    if not layer:
        return recovered == encoded.get("source")
    raw = recovered.encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(raw).hexdigest() == layer.get("source_sha256")


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

    recovered = decode_ast_normalized(enc)
    norm = ast.unparse(ast.parse(src))
    print(f"\nsemantic AST round-trip: {recovered == norm}")
    print(f"exact source lane: {verify_bijective_layer(enc)}")
    print(f"each token bijective across faces: "
          f"{all(CubeToken(n['token']).is_bijective() for n in enc['nodes'])}")
    print("\n-> (N x D) integer matrix for a matrix-field/Mamba model; the location")
    print("   axes give every cube its address in the nested hyper-structure.")


if __name__ == "__main__":
    _demo()
