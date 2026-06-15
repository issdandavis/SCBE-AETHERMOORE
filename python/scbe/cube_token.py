"""
Cube Token — one token, many purposes (the Rubik's-cube tokenizer)
==================================================================

Goal: every token is a Rubik's cube. It is ONE bijective object, but it
has many faces, and each face is a different *decoder* of the same token:

    * 6 TONGUE faces  -> 6 coding languages
        KO=python  AV=javascript  RU=rust  CA=mathematica  UM=haskell  DR=markdown
      (each is the bijective Sacred-Tongue encoding of the token's bytes)
    * CHEM face       -> chemistry language (element, semantic class, 6-tongue
                         trit vector) via atomic_tokenization
    * GOV face        -> governance read (semantic class + band)

The cube is BIJECTIVE: rotate to any tongue face and you can rotate back —
from a single face you recover the exact original token. No information is
lost in any rotation. No shapes/geometry — pure symbol projection.

Cubes are stored/retrieved through the Elastic Bijective Hash, so a whole
token space is held losslessly and looked up fast even when nearly full.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from python.scbe.elastic_bijective_hash import ElasticBijectiveHash

# tongue -> coding language binding (from atomic-tokenizer-chemistry-unified note)
TONGUE_LANGUAGE: Dict[str, str] = {
    "KO": "python",
    "AV": "javascript",
    "RU": "rust",
    "CA": "mathematica",
    "UM": "haskell",
    "DR": "markdown",
}
TONGUES = list(TONGUE_LANGUAGE.keys())


def _tongue_encode(tongue: str, raw: bytes) -> str:
    from scbe import encode_bytes  # root unified CLI module
    return encode_bytes(tongue, raw)


def _tongue_decode(tongue: str, tokens: str) -> bytes:
    from scbe import decode_tokens
    return decode_tokens(tongue, tokens)


@dataclass
class CubeToken:
    """One token; many faces. Each face is a lossless projection."""

    token: str

    @property
    def raw(self) -> bytes:
        return self.token.encode("utf-8")

    # ---- the 6 tongue faces (coding-language decoders) ----
    def face(self, tongue: str) -> str:
        """Rotate to one tongue face -> that coding language's encoding."""
        return _tongue_encode(tongue.upper(), self.raw)

    def code_faces(self) -> Dict[str, Dict[str, str]]:
        return {
            t: {"language": TONGUE_LANGUAGE[t], "tokens": self.face(t)}
            for t in TONGUES
        }

    # ---- chemistry face ----
    def chem_face(self, language: Optional[str] = None) -> Dict[str, Any]:
        try:
            from python.scbe.atomic_tokenization import map_token_to_atomic_state
            st = map_token_to_atomic_state(self.token, language=language)
            return {
                "semantic_class": st.semantic_class,
                "element": st.element.symbol,
                "Z": st.element.Z,
                "valence": st.element.valence,
                "trit_vector": st.tau.as_dict(),
                "negative_state": st.negative_state,
            }
        except Exception as e:  # chem face is optional
            return {"error": f"{type(e).__name__}: {e}"}

    # ---- governance face ----
    def gov_face(self) -> Dict[str, Any]:
        chem = self.chem_face()
        return {
            "semantic_class": chem.get("semantic_class", "UNKNOWN"),
            "tier": "ALLOW" if not chem.get("negative_state") else "QUARANTINE",
        }

    # ---- the bijection: recover the whole cube from any single face ----
    @classmethod
    def from_face(cls, tongue: str, tokens: str) -> "CubeToken":
        raw = _tongue_decode(tongue.upper(), tokens)
        return cls(raw.decode("utf-8", errors="replace"))

    def is_bijective(self) -> bool:
        """Every face round-trips back to the exact token."""
        return all(CubeToken.from_face(t, self.face(t)).token == self.token for t in TONGUES)


class CubeRegistry:
    """A token space of cubes, stored losslessly in the Elastic Bijective Hash."""

    def __init__(self, bits: int = 16) -> None:
        self.table = ElasticBijectiveHash(bits=bits)

    def add(self, token: str) -> CubeToken:
        cube = CubeToken(token)
        self.table.put(token, cube)
        return cube

    def get(self, token: str) -> Optional[CubeToken]:
        return self.table.get(token)

    def __len__(self) -> int:
        return self.table.count


def _demo() -> None:
    tok = "bind"
    cube = CubeToken(tok)
    print(f"Cube token: '{tok}'  — one object - many faces\n")
    print("  CODING-LANGUAGE faces (rotate the cube):")
    for t, f in cube.code_faces().items():
        print(f"    {t} / {f['language']:<11} {f['tokens']}")
    print("\n  CHEMISTRY face:")
    chem = cube.chem_face()
    for k in ("semantic_class", "element", "Z", "valence", "negative_state"):
        print(f"    {k:<15} {chem.get(k)}")
    print(f"    trit_vector     {chem.get('trit_vector')}")
    print("\n  GOVERNANCE face:")
    print(f"    {cube.gov_face()}")
    print("\n  BIJECTIVE - recover the token from a single face:")
    ru = cube.face("RU")
    back = CubeToken.from_face("RU", ru).token
    print(f"    RU face -> '{ru}' -> recovered '{back}'   bijective_all_faces={cube.is_bijective()}")

    print("\n  Stored & retrieved through the Elastic Bijective Hash:")
    reg = CubeRegistry(bits=12)
    for w in ["bind", "parse", "release", "compile", "seal", "merge"]:
        reg.add(w)
    got = reg.get("release")
    print(f"    registry has {len(reg)} cubes; get('release').face('CA') = {got.face('CA')}")


if __name__ == "__main__":
    _demo()
