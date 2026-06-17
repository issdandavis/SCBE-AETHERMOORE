"""Rust<->Python atomic-chem FACE parity for the AST cube encoder.

The Rust encoder (rust/ast_cube) ports python/scbe/atomic_tokenization.py's
atomic-chem face base: classify_token_semantic(token) -> SemanticClass -> tau,
overlaid by the structural FACE_RULES. This test asserts that, for the same
source, Rust assigns every node the SAME (type_id, 6 face trits) as the Python
encoder.

Comparison is by MULTISET, not sequence: Rust does not emit Python's operator
(Add/Lt/...), context (Load/Store/Del), alias, or withitem nodes (they are enum
fields in the Rust parser, not AST nodes), and orders some children differently.
Those differences shift node POSITIONS (and the location columns) but not the
face VALUES — which is exactly what this test pins down.

Skips automatically if the release binary is not built.
"""

import json
import os
import subprocess
from collections import Counter

import pytest

from python.scbe.ast_cube_encoder import encode, _TYPE_ID

EXE = os.path.join("rust", "ast_cube", "target", "release", "ast_cube.exe")

# Node types the Rust walk does not emit (operators/contexts/alias/withitem/match).
_EXCLUDE = set(
    """Add Sub Mult MatMult Div Mod Pow LShift RShift BitOr BitXor BitAnd FloorDiv
    Invert Not UAdd USub And Or Eq NotEq Lt LtE Gt GtE Is IsNot In NotIn
    Load Store Del alias withitem match_case MatchValue MatchSingleton MatchSequence
    MatchMapping MatchClass MatchStar MatchAs MatchOr TypeVar ParamSpec TypeVarTuple""".split()
)

_SAMPLE = [
    "python/scbe/ast_cube_encoder.py",
    "python/scbe/cube_token.py",
    "python/scbe/tongue_roles.py",
    "python/scbe/atomic_tokenization.py",
]


def _py_face_bag(src):
    bag = Counter()
    for n in encode(src)["nodes"]:
        if n["type"] in _EXCLUDE:
            continue
        bag[(_TYPE_ID.get(n["type"], 0), tuple(n["vector"][2:8]))] += 1
    return bag


def _rust_face_bag(path):
    out = subprocess.run([os.path.abspath(EXE), path], capture_output=True, text=True)
    rows = json.loads(out.stdout)["matrix"]
    return Counter((r[0], tuple(r[2:8])) for r in rows)


@pytest.mark.skipif(not os.path.exists(EXE), reason="rust ast_cube release binary not built")
@pytest.mark.parametrize("path", _SAMPLE)
def test_rust_faces_match_python(path):
    if not os.path.exists(path):
        pytest.skip(f"missing {path}")
    src = open(path, encoding="utf-8").read()
    if " match " in src or "\n    case " in src:
        pytest.skip("rust drops match subtrees")
    assert _py_face_bag(src) == _rust_face_bag(os.path.abspath(path))
