"""
Tongue Roles — the semantic layer of the Six Sacred Tongues
===========================================================

Source of truth lifted from the Spiral Engine game (game/spiral-engine):
each tongue is not just a byte alphabet, it is a SEMANTIC ROLE in a tiny
programming language. Combining two tongues "compiles" a composed operation
keyword1(keyword2()) — exactly the game's spell crafting, and the cube's
"combine faces" at the meaning level.

This gives the cube faces real meaning (control / IO / scope / math /
security / transform), which is what the AST-vector faces were missing.
"""

from __future__ import annotations

from typing import Dict, List

# canonical tongue -> {name, role, keyword, glyph}
TONGUE_ROLE: Dict[str, Dict[str, str]] = {
    "KO": {"name": "Kor'aelin", "role": "Control Flow", "keyword": "loop", "glyph": "ᚲ"},
    "AV": {"name": "Avali", "role": "Input/Output", "keyword": "sense", "glyph": "ᚨ"},
    "RU": {"name": "Runethic", "role": "Scope/Context", "keyword": "area", "glyph": "ᚱ"},
    "CA": {"name": "Cassisivadan", "role": "Math/Logic", "keyword": "calc", "glyph": "ᚳ"},
    "UM": {"name": "Umbroth", "role": "Security", "keyword": "ward", "glyph": "ᚢ"},
    "DR": {"name": "Draumric", "role": "Transforms", "keyword": "morph", "glyph": "ᛞ"},
}
TONGUES: List[str] = list(TONGUE_ROLE)


def role(tongue: str) -> str:
    return TONGUE_ROLE[tongue.upper()]["role"]


def keyword(tongue: str) -> str:
    return TONGUE_ROLE[tongue.upper()]["keyword"]


def compile_pair(outer: str, inner: str) -> Dict[str, str]:
    """A 2-tongue program: outer(inner()) — the game's spell, as semantics."""
    o, i = outer.upper(), inner.upper()
    ro, ri = TONGUE_ROLE[o], TONGUE_ROLE[i]
    return {
        "outer": o,
        "inner": i,
        "program": f"{ro['keyword']}({ri['keyword']}())",
        "semantics": f"{ro['role']} of {ri['role']}",
        "glyphs": ro["glyph"] + ri["glyph"],
    }


def all_pairs() -> List[Dict[str, str]]:
    """All 36 two-tongue programs."""
    return [compile_pair(a, b) for a in TONGUES for b in TONGUES]


def _demo() -> None:
    print("Tongue Roles — the 6 faces, with meaning\n")
    for t, spec in TONGUE_ROLE.items():
        print(f"  {spec['glyph']} {t}  {spec['name']:<13} {spec['role']:<14} keyword: {spec['keyword']}")
    print(f"\n  36 two-tongue programs (e.g.):")
    for pair in (
        compile_pair("CA", "CA"),
        compile_pair("RU", "CA"),
        compile_pair("UM", "KO"),
        compile_pair("AV", "DR"),
    ):
        print(f"    {pair['glyphs']}  {pair['program']:<16} = {pair['semantics']}")


if __name__ == "__main__":
    _demo()
