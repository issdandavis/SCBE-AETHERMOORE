"""
Cube Stereo — two encoder lenses, one 3D view
=============================================

Use two AST lenses like the two lenses of 3D glasses: each sees the same
AST, and overlaying them gives DEPTH neither lens has alone.

  * Lens A — RELATION/structure: explicit graph links (parent, field,
             child_index, depth). "Where does this node sit in the graph."
  * Lens B — SEMANTIC/location: discriminative 6-face trits + a 6-D
             hyper-structure LOCATION VECTOR (from ast_cube_encoder).
             "What this node means + its nested address."

Both walk the AST in pre-order, so node i in each lens is the same node.
stereo_encode() registers them, reports the stereo LOCK (do both lenses see
the same node?), and concatenates per node into one stereoscopic vector:

    stereo_vector = lensA.relation_vec  ++  lensB.vector

NOTE: Lens A is implemented inline here so this module is self-contained. The
moment Codex's richer python/scbe/ast_cube_vectors.py lands on this tree, swap
_relation_lens() for encode_python_source() — same registration, more detail.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from python.scbe.ast_cube_encoder import encode as encode_location  # lens B

_FIELD_ID: Dict[str, int] = {}


def _field_id(field: str) -> int:
    return _FIELD_ID.setdefault(field, len(_FIELD_ID) + 1)


def _relation_lens(source: str) -> List[Dict[str, Any]]:
    """Lens A: emit per-node graph relations in pre-order (matches lens B order)."""
    tree = ast.parse(source)
    out: List[Dict[str, Any]] = []

    def walk(node: ast.AST, parent: Optional[int], field: str,
             child_index: int, depth: int) -> None:
        idx = len(out)
        out.append({
            "index": idx,
            "node_type": type(node).__name__,
            "parent": parent,
            "field": field,
            "child_index": child_index,
            "depth": depth,
            # compact relation vector for the stereo stack
            "relation_vec": [(parent + 1) if parent is not None else 0,
                             child_index, depth, _field_id(field)],
        })
        ci = 0
        for fname, value in ast.iter_fields(node):
            values = value if isinstance(value, list) else [value]
            for child in values:
                if isinstance(child, ast.AST):
                    walk(child, idx, fname, ci, depth + 1)
                    ci += 1

    walk(tree, None, "root", 0, 0)
    return out


def stereo_encode(source: str) -> Dict[str, Any]:
    lens_a = _relation_lens(source)
    enc_b = encode_location(source)
    nodes_b = enc_b["nodes"]

    n = min(len(lens_a), len(nodes_b))
    stereo: List[Dict[str, Any]] = []
    locked = 0
    for i in range(n):
        a, b = lens_a[i], nodes_b[i]
        ok = (a["node_type"] == b["type"])
        locked += int(ok)
        stereo.append({
            "index": i,
            "node_type": a["node_type"],
            "token": b["token"],
            "locked": ok,                       # do both lenses see the same node?
            "lens_a_relation": {k: a[k] for k in ("parent", "field", "child_index", "depth")},
            "lens_b_faces": b["face_trits"],
            "roles": b.get("roles", []),        # Sacred-Tongue roles this node plays
            "lens_b_location": b["location"],
            "stereo_vector": a["relation_vec"] + b["vector"],
        })

    width = len(stereo[0]["stereo_vector"]) if stereo else 0
    return {
        "tokens": stereo,
        "stereo_matrix": [t["stereo_vector"] for t in stereo],
        "stereo_width": width,
        "node_count": n,
        "lock_ratio": locked / n if n else 0.0,  # 1.0 = lenses fully registered
        "lens_a_count": len(lens_a),
        "lens_b_count": len(nodes_b),
        "face_legend": enc_b.get("face_legend", {}),  # face axis -> Sacred-Tongue role
    }


def _demo() -> None:
    src = (
        "def score(x, k):\n"
        "    total = 0\n"
        "    for i in range(k):\n"
        "        total = total + x * i\n"
        "    return total\n"
    )
    s = stereo_encode(src)
    print("Cube Stereo - two lenses, one 3D view\n")
    print(f"  nodes: {s['node_count']}   stereo vector width: {s['stereo_width']}"
          f"  (lensA relation + lensB vector)")
    print(f"  lens LOCK (same node in both): {s['lock_ratio']*100:.0f}%"
          f"   [A={s['lens_a_count']} B={s['lens_b_count']}]")
    print("  faces carry Sacred-Tongue roles: "
          + ", ".join(f"{t}={r}" for t, r in s["face_legend"].items()))
    print("\n  first 6 tokens through both lenses:")
    print("   node           tok        | active roles                   | lensB location")
    for t in s["tokens"][:6]:
        roles = ", ".join(t["roles"]) or "-"
        print(f"   {t['node_type']:<14} {t['token']:<10} | {roles:<30} | {t['lens_b_location']}")
    print(f"\n  one stereoscopic vector (node 1): {s['tokens'][1]['stereo_vector']}")


if __name__ == "__main__":
    _demo()
