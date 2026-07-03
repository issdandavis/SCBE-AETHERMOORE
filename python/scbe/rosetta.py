"""Verified Rosetta stone: a song in the tokenizer -> aligned code in many languages, PROVEN
equal by running each (not just emitted), with the song read back out of the core.

Like math notation: a fixed set of symbols is universal ONLY because the lookup table -- what
each symbol means -- is the same everywhere. A German and a Japanese mathematician read the
same integral sign because the meaning is standardized, not because either language is more
powerful. This is that, for code:

    tokenizer song  --(a MODE = the symbol lookup table)-->  CA opcode names -> bytes (the core)
                    --(polyglot emit)-->                     source in every language face
                    --(conformance: RUN each face)-->        PROOF the lookup table means the
                                                             same thing in each language --
                                                             catching false-friends (round(2.5)
                                                             is 2.0 in Python but 3.0 in JS/Rust)
                    --(invert the mode's scale)-->           the song, read back out (bijective)

The MODE is the symbol set: ``coding`` plays note letters (C=add, E=mul); ``ca`` plays your
conlang words (bip'a=add, bip'i=mul) -- same opcode core, different keys, like solfege vs note
names. "Verified" means the face was actually executed and AGREED with the Python reference; a
face with no local toolchain is honestly reported emitted-but-unverified, never claimed --
because a symbol set you have not checked everywhere is exactly where the round(2.5) trap lives.

Honesty firewall (conlang_macros example, 2026-06-27):
- conlang_macros registered as level=6 verified language face.
- Artifact hash: 5117a81c6dc6bf2f6594862e728fd9b149a9835a1938172ac22fb8cf51e1efb1
- Caveat: emitted-to-8 faces is NOT claimed as executed-on-8.
- Binds-to core (ca_word_for_opcode / instrument), emits-to provenance, executed-on = narrow verified set only.
- BOM/UTF handled at transference_gate adapter level.
See artifacts/ai_brain/conlang_macros_claim_manifest.json and gate_reports.
Run it on a box (or CI) with more compilers and the verified count rises.

    python -m python.scbe.rosetta "C E"                    # note song -> every face, run the local ones
    python -m python.scbe.rosetta "bip'a bip'i" --mode ca  # play it in your tokenizer
    python -m python.scbe.rosetta --benchmark              # verified Rosetta coverage over a suite
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence, Tuple

from . import polyglot as P
from . import polyglot_conformance as C


def _pad3(case: Sequence[float]) -> Tuple[float, float, float]:
    xs = [float(x) for x in case]
    while len(xs) < 3:
        xs.append(0.0)
    return (xs[0], xs[1], xs[2])


def _decode(song: str, mode: str = "coding") -> Tuple[List[int], str, bool]:
    """Song -> op bytes, the song read back out via the mode's lookup table, and exactness."""
    from .instrument import notes_to_ops, scale

    ops = notes_to_ops(song, mode)
    ob = [P.NAME_TO_BYTE[o] for o in ops]
    op_to_key = {op: key for key, op in scale(mode).items()}
    back = " ".join(op_to_key.get(P.BYTE_TO_NAME[b], "?") for b in ob)
    return ob, back, (back == " ".join(song.replace(",", " ").split()))


def rosetta(song: str, mode: str = "coding", cases: Optional[Sequence[Sequence[float]]] = None) -> dict:
    """Manifest one song across every language face, run the ones with a toolchain, read it back."""
    op_bytes, song_back, bijective = _decode(song, mode)
    names = [P.BYTE_TO_NAME.get(b, "0x%02x" % b) for b in op_bytes]
    bad = [n for n in names if n not in P.SCALAR_OPS]
    if bad:
        raise ValueError("song uses non-portable ops %s; only the scalar core emits to all faces" % bad)
    depth = 3  # the stack starts with the 3 inputs
    for n in names:
        need = 1 if n in P.FUNC1 else 2  # unary ops pop 1, everything else pops 2
        if depth < need:
            raise ValueError("song underflows the stack at op %r (needs %d operands, %d on stack)" % (n, need, depth))
        depth = depth - need + 1
    runs = [_pad3(c) for c in (cases or [(2.0, 3.0, 4.0)])]
    conf = C.conformance(op_bytes, runs)
    status = {r.lang: r.status for r in conf["results"]}
    faces: Dict[str, dict] = {}
    for lang in P.languages():
        try:
            faces[lang] = {"status": status.get(lang, "EMITTED"), "source": P.emit(op_bytes, lang)}
        except Exception as exc:  # a face that cannot carry these ops
            faces[lang] = {"status": "EMIT_ERROR", "source": "ERROR: %s" % exc}
    s = conf["summary"]
    return {
        "song": song,
        "mode": mode,
        "ops": names,
        "op_bytes": op_bytes,
        "song_back": song_back,
        "bijective": bijective,
        "cases": [list(c) for c in runs],
        "reference": conf["reference"],
        "verified": s["verified_agree"],
        "runnable": s["runnable_backends"] - 1,
        "disagree": s["disagree"],
        "total_faces": len(P.languages()),
        "faces": faces,
    }


_MARK = {
    "REFERENCE": "reference",
    "AGREE": "verified (ran + agreed)",
    "DISAGREE": "DIVERGES",
    "NO_TOOLCHAIN": "emitted (no toolchain here)",
    "NO_RUNNER": "emitted (no runner)",
    "ERROR": "run error",
    "EMITTED": "emitted",
    "EMIT_ERROR": "emit error",
}


def render(r: dict, show_source: Sequence[str] = ("python",)) -> str:
    lines = [
        "ROSETTA STONE  song=%r  (mode=%s)" % (r["song"], r["mode"]),
        "  ops: %s   ->  read back: %r   bijective=%s" % (" ".join(r["ops"]), r["song_back"], r["bijective"]),
        "  reference value(s): %s   verified: %d/%d faces  (%d runnable here)%s"
        % (
            r["reference"],
            r["verified"],
            r["total_faces"],
            r["runnable"],
            ("   DIVERGES: " + ", ".join(r["disagree"])) if r["disagree"] else "",
        ),
        "  " + "-" * 60,
    ]
    for lang in sorted(r["faces"]):
        lines.append("  %-12s %s" % (lang, _MARK.get(r["faces"][lang]["status"], r["faces"][lang]["status"])))
    for lang in show_source:
        if lang in r["faces"]:
            lines.append("  " + "-" * 60)
            lines.append("  [%s face]" % lang)
            for ln in r["faces"][lang]["source"].splitlines():
                lines.append("    " + ln)
    return "\n".join(lines)


def benchmark(songs: Sequence[str], mode: str = "coding", cases: Optional[Sequence[Sequence[float]]] = None) -> dict:
    """Run a suite of songs across all faces; report verified Rosetta coverage + any divergences."""
    t0 = time.perf_counter()
    per_lang: Dict[str, Dict[str, int]] = {}
    disagreements: List[dict] = []
    rows = []
    for song in songs:
        r = rosetta(song, mode, cases=cases)
        rows.append({"song": song, "verified": r["verified"], "bijective": r["bijective"]})
        for lang, f in r["faces"].items():
            d = per_lang.setdefault(lang, {"ran": 0, "agree": 0, "disagree": 0, "unverified": 0})
            st = f["status"]
            if st == "REFERENCE":
                d["ran"] += 1
            elif st == "AGREE":
                d["ran"] += 1
                d["agree"] += 1
            elif st == "DISAGREE":
                d["ran"] += 1
                d["disagree"] += 1
                disagreements.append({"song": song, "lang": lang})
            else:
                d["unverified"] += 1
    elapsed = round(time.perf_counter() - t0, 2)
    verified = sorted(lang for lang, d in per_lang.items() if d["ran"] > 0 and d["disagree"] == 0)
    return {
        "songs": len(songs),
        "mode": mode,
        "total_faces": len(P.languages()),
        "verified_faces": len(verified),
        "verified_face_list": verified,
        "disagreements": disagreements,
        "per_language": per_lang,
        "elapsed_s": elapsed,
        "rows": rows,
    }


_DEFAULT_SUITE = ["C E", "C C", "C D", "E E", "C G", "C G E"]  # valid add/mul/sub/inc combos (note mode)


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="scbe-rosetta", description="verified Rosetta stone: one song, many proven-equal faces"
    )
    ap.add_argument("song", nargs="?", help="a song: notes like 'C E', or tokenizer words with --mode ca")
    ap.add_argument("--mode", default="coding", help="the symbol set: 'coding' (notes) or 'ca' (your conlang)")
    ap.add_argument("--benchmark", action="store_true", help="run a suite and report verified Rosetta coverage")
    ap.add_argument("--source", default="python", help="comma-separated faces to print in full")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.benchmark:
        b = benchmark(_DEFAULT_SUITE, mode="coding")
        print("ROSETTA BENCHMARK  %d songs x %d faces  (%ss)" % (b["songs"], b["total_faces"], b["elapsed_s"]))
        print(
            "  verified faces: %d/%d  ->  %s"
            % (b["verified_faces"], b["total_faces"], ", ".join(b["verified_face_list"]))
        )
        if b["disagreements"]:
            print("  DIVERGENCES: " + ", ".join("%s@%r" % (d["lang"], d["song"]) for d in b["disagreements"]))
        for lang in sorted(b["per_language"]):
            d = b["per_language"][lang]
            print(
                "    %-12s ran=%d agree=%d disagree=%d unverified=%d"
                % (lang, d["ran"], d["agree"], d["disagree"], d["unverified"])
            )
        return 0
    song = a.song or ("bip'a bip'i" if a.mode == "ca" else "C E")
    print(render(rosetta(song, mode=a.mode), show_source=tuple(a.source.split(","))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
