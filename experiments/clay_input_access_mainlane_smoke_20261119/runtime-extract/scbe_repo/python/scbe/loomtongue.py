"""loomtongue: play a FULL program (loops, branches) in your conlang -- the bridge between the
tokenizer and loomflow's control flow.

The Rosetta tokenizer plays scalar NOTES; loomflow plays full programs but in plain assembly.
This bridges them: every loomflow OPCODE gets its canonical Cassisivadan word from the SAME
generator the scalar tokenizer uses (ca_word_for_opcode), so the words stay coherent across both
layers -- add is "bip'a" here exactly as in the note mode. A program is written verbs-in-the-tongue
(opcodes are conlang words) with operands (slot/label names, numbers) as plain identifiers -- the
nouns. It translates to a loomflow program, runs across every language face, and reads back out
in the conlang (bijective).

    bop'a acc 0 / bop'a i 1 / bop'a n 5          # const acc 0 / const i 1 / const n 5
    bop'i loop / klik'o t i n / bop'u t end      # label loop / le t i n / brz t end
    bip'a acc acc i / bip'mi i / bop'o loop       # add acc acc i / inc i / jmp loop
    bop'i end / bop'y acc / bop'ta               # label end / print acc / halt   -> 15

Control-flow opcodes (const/mov/label/jmp/brz/print/halt) live on the conlang's unused LOGIC band
(0x10+), so they get clean "bop'" words without colliding with the arithmetic "bip'"/comparison
"klik'" families.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from . import loomflow as L

# loomflow opcode -> the byte whose Cassisivadan word names it. Arithmetic/comparison/inc/dec
# reuse their real CA bytes (so the words match the scalar tokenizer); control flow takes the
# unused LOGIC band 0x10+.
_BYTE: Dict[str, int] = {
    "add": 0x00,
    "sub": 0x01,
    "mul": 0x02,
    "div": 0x03,
    "eq": 0x20,
    "ne": 0x21,
    "lt": 0x22,
    "le": 0x23,
    "gt": 0x24,
    "ge": 0x25,
    "inc": 0x0B,
    "dec": 0x0C,
    "const": 0x10,
    "mov": 0x11,
    "label": 0x12,
    "jmp": 0x13,
    "brz": 0x14,
    "print": 0x15,
    "halt": 0x16,
}


def _build_lexicon() -> Tuple[Dict[str, str], Dict[str, str]]:
    from .instrument import ca_word_for_opcode

    word_for = {op: ca_word_for_opcode(b) for op, b in _BYTE.items()}
    op_for = {w: op for op, w in word_for.items()}
    if len(op_for) != len(word_for):
        raise RuntimeError("conlang opcode words collide: %s" % word_for)
    return word_for, op_for


WORD_FOR_OP, OP_FOR_WORD = _build_lexicon()


def _strip(line: str) -> str:
    return line.split(";", 1)[0].split("#", 1)[0].strip()


def from_tongue(text: str):
    """A conlang program (opcode words + plain operands) -> a loomflow program."""
    asm = []
    for raw in text.splitlines():
        line = _strip(raw)
        if not line:
            continue
        parts = line.split()
        word = parts[0]
        if word not in OP_FOR_WORD:
            raise ValueError("unknown conlang opcode %r (verbs are %s)" % (word, ", ".join(sorted(OP_FOR_WORD))))
        asm.append(" ".join([OP_FOR_WORD[word]] + parts[1:]))
    return L.parse("\n".join(asm))


def to_tongue(prog: Sequence) -> str:
    """A loomflow program -> the conlang text that produces it (the song, read back out)."""
    return "\n".join(" ".join([WORD_FOR_OP[op]] + list(args)) for op, args in prog)


def _normalize(text: str) -> str:
    return "\n".join(" ".join(s.split()) for s in (_strip(ln) for ln in text.splitlines()) if s)


def verify_tongue(text: str, faces: Sequence[str] = ("python", "javascript", "rust", "c")) -> dict:
    """Translate the conlang program, run it across faces, and read the song back out."""
    prog = from_tongue(text)
    res = L.verify(prog, faces)
    res["song_back"] = to_tongue(prog)
    res["bijective"] = _normalize(res["song_back"]) == _normalize(text)
    return res


# the loomflow examples, expressed in the conlang (generated, so they are always exact)
CONLANG_EXAMPLES = {name: to_tongue(L.parse(src)) for name, src in L.EXAMPLES.items()}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="scbe-loomtongue", description="play a full (branching) program in your conlang")
    ap.add_argument("example", nargs="?", default="sum_1_to_5", choices=sorted(CONLANG_EXAMPLES))
    ap.add_argument("--show", action="store_true", help="print the conlang program source")
    a = ap.parse_args(list(argv) if argv is not None else None)
    song = CONLANG_EXAMPLES[a.example]
    if a.show:
        print(song)
        return 0
    r = verify_tongue(song)
    print("LOOMTONGUE  %s  (a real loop, in the conlang)  reference=%s" % (a.example, r["reference"]))
    print("  song (conlang): %s" % " / ".join(song.splitlines()))
    print(
        "  verified faces: %d  ->  %s   bijective(read-back)=%s"
        % (r["verified_count"], ", ".join(r["verified"]) or "(none)", r["bijective"])
    )
    for lang in sorted(r["results"]):
        d = r["results"][lang]
        print("    %-12s %-12s value=%s" % (lang, d["status"], d["value"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
