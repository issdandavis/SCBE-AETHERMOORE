"""
cube_faces — one token core, every surface a different use (the Rubik's cube).

A token is ONE bijective object. Rotate it to any face and you get a different
decoder of the same core — and you can always rotate back (no information lost).
This assembles every face from the real engines, so the cube is real, not a mock:

  * core        — the raw bytes / hex (the single object every face decodes)
  * chemistry   — CubeToken.chem_face: semantic class -> element -> 6-channel trit
  * roles       — that trit read as control/IO/scope/math/security/transform (tongue_roles)
  * code        — CubeToken.code_faces: the 6 Sacred-Tongue coding-language faces
  * governance  — CubeToken.gov_face: semantic class + ALLOW/QUARANTINE band
  * wolfram     — each byte is an elementary cellular-automaton rule + complexity class

`bijective` proves every face round-trips back to the exact token.
"""

from __future__ import annotations

from typing import Any, Dict, List

try:
    from python.scbe.cube_token import CubeToken
    from python.scbe.wolfram_face import token_rule as _wolfram_rule
    from python.scbe.tongue_roles import TONGUE_ROLE
    from python.scbe.atomic_tokenization import chemical_element, parse_formula
except ModuleNotFoundError:  # pragma: no cover - direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from python.scbe.cube_token import CubeToken
    from python.scbe.wolfram_face import token_rule as _wolfram_rule
    from python.scbe.tongue_roles import TONGUE_ROLE
    from python.scbe.atomic_tokenization import chemical_element, parse_formula


def _raw_bytes(cube: CubeToken) -> bytes:
    r = cube.raw
    return r if isinstance(r, (bytes, bytearray)) else r()


def _wolfram_face(raw: bytes) -> Dict[str, Any]:
    """Each byte of the token is an elementary CA rule with a complexity class."""
    rules = []
    for b in list(raw)[:8]:
        info = _wolfram_rule(b)
        rules.append({
            "byte": b, "rule": info["rule"], "class": info["class"],
            "class_name": info["class_name"], "universal": info["universal"],
        })
    return {"per_byte_rules": rules, "any_universal": any(r["universal"] for r in rules)}


def _role_face(chem: Dict[str, Any]) -> List[str]:
    """Read the chemistry trit vector as the Sacred-Tongue roles it lights."""
    tv = chem.get("trit_vector", {})
    return [TONGUE_ROLE[t]["role"] for t in TONGUE_ROLE if tv.get(t, 0) > 0]


def all_faces(token: str) -> Dict[str, Any]:
    """One core token, decoded through every face of the cube (bijective)."""
    cube = CubeToken(token)
    raw = _raw_bytes(cube)
    chem = dict(cube.chem_face())
    real = chemical_element(token)
    if real is not None:
        chem["real_element"] = {
            "symbol": real.symbol, "Z": real.Z, "group": real.group,
            "period": real.period, "valence": real.valence,
            "electronegativity": real.electronegativity,
        }
    composition = parse_formula(token)
    if composition and len(composition) > 1:
        chem["composition"] = composition
    return {
        "token": token,
        "core": {"hex": raw.hex(), "bytes": list(raw), "byte_count": len(raw)},
        "faces": {
            "chemistry": chem,
            "roles": _role_face(chem),
            "code": cube.code_faces(),
            "governance": cube.gov_face(),
            "wolfram": _wolfram_face(raw),
        },
        "bijective": cube.is_bijective(),
    }


def _demo() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    for tok in ("loop", "ward", "calc"):
        f = all_faces(tok)
        print(f"\n=== cube: '{tok}'  (core {f['core']['hex']}, bijective={f['bijective']}) ===")
        ch = f["faces"]["chemistry"]
        print(f"  chemistry : {ch['semantic_class']} -> {ch['element']} "
              f"(Z={ch['Z']}, val={ch['valence']})  trit={ch['trit_vector']}")
        print(f"  roles     : {', '.join(f['faces']['roles']) or '-'}")
        print(f"  governance: {f['faces']['governance']}")
        wf = f["faces"]["wolfram"]
        print("  wolfram   : " + " ".join(f"{r['byte']}={r['class']}" for r in wf["per_byte_rules"])
              + f"  (universal={wf['any_universal']})")
        print(f"  code (KO) : python -> {f['faces']['code']['KO']['tokens']}")


if __name__ == "__main__":
    _demo()
