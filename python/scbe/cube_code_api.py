"""cube_code_api — the JSON face of the cube front door, so AGENTS can code by tokens.

Same engine as `frontdoor.render`, but returns structured data instead of a terminal panel:
a token stream -> the one CA-opcode strand -> every language face + the REAL cross-face-execution
verdict (SEAL/REJECT/FLAG). This is what AetherDesk exposes so any AI can use the cube as a
verified coding interface.

    python -m python.scbe.cube_code_api "+ sqrt * inc /" --langs python,javascript,rust
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import bijective_dna as DNA
from . import polyglot as P
from .frontdoor import _exec_verify, tokens_to_program, tongue_spell


def cube_code(text: str, langs: Sequence[str] = ("python", "javascript"), tongue: str = "ko") -> dict:
    names, prog = tokens_to_program(text, tongue)
    rep = DNA.verify(names)
    exec_v = _exec_verify(prog) or {}
    seal = DNA.seal(prog) if getattr(DNA, "_HAVE_SEAL", False) else []
    acc = 0
    for w in seal:
        acc ^= w  # XOR-fold the sealed strand into one fingerprint (same as the front door)

    faces = {}
    for lang in langs:
        try:
            faces[lang] = P.emit(prog, lang, runnable=True)
        except Exception as e:  # a face may be emit-only without a local toolchain
            faces[lang] = "// emit unavailable: %s" % type(e).__name__

    verdict = exec_v.get("verdict")
    return {
        "ok": True,
        "schema": "scbe_cube_code_v0",
        "tokens": names,
        "tongue": tongue_spell(prog, tongue),
        "strand": ["%02x" % b for b in prog],
        "faces": faces,
        "verify": {
            "exec_verdict": verdict,                  # SEAL (green) / REJECT (faces diverge) / FLAG (review)
            "exec_ok": verdict == "SEAL",             # the ONE trust bit: real cross-face execution agreed
            "exec_reason": exec_v.get("reason", ""),
            "exec_checked": exec_v.get("checked", 0),
            "faces_struct": "%d/%d" % (rep.get("faces_agree", 0), rep.get("faces_total", 0)),
            "faces_agree": bool(rep.get("all_faces_agree")),
            "seekable": bool(rep.get("seekable")),
            "sealed": bool(rep.get("seal_roundtrip", True)),
            "geoseal": "%016x" % acc if seal else "-",
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cube code: tokens -> verified polyglot code (JSON).")
    ap.add_argument("tokens", help="the token stream, e.g. \"+ sqrt * inc /\"")
    ap.add_argument("--langs", default="python,javascript", help="comma list of language faces")
    ap.add_argument("--tongue", default="ko", help="Sacred Tongue to spell with")
    a = ap.parse_args(argv)
    try:
        langs = tuple(x.strip() for x in a.langs.split(",") if x.strip())
        out = cube_code(a.tokens, langs, a.tongue)
    except Exception as e:  # never crash the caller; return a structured error
        out = {"ok": False, "schema": "scbe_cube_code_v0", "error": "%s: %s" % (type(e).__name__, e)}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
