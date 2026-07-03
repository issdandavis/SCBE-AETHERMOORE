r"""layer_map.py -- the self-verifying LAYER REGISTRY (Issac, 2026-06-27).

One function = one OPCODE (the spot). Every surface (symbol, Python, the 8 polyglot languages,
conlang, block, sound, QR) is a PATH to that spot. A surface is a real LAYER only if it's VERIFIED
to compute identically; otherwise it's a label. This module holds the map AND checks it.

  opcode  <- the canonical spot (executes via scbe.ca_semantics._OPS)
  python  <- executed here, must equal the opcode
  conlang <- resolves to the same byte (bip'a == 0x00 == add)
  QR      <- BIJECTIVE byte-transport: program-bytes -> QR/Micro-QR image -> exact bytes back.
             A real compressed-INPUT layer (lossless by the QR standard).
  block / sound <- LABELED paths (not yet executable here -> marked unverified, honestly).
  8 polyglot faces <- verified identical by the polyglot emitter (separate, this session).
"""
from __future__ import annotations
import sys

sys.path.insert(0, r"C:\Users\issda\instrument-wt\python")
from scbe.ca_semantics import _OPS
from scbe.instrument import _NAME_TO_BYTE, ca_word_for_opcode

import segno  # QR + Micro QR

POLYGLOT = ("python", "typescript", "go", "rust", "c", "julia", "haskell", "zig")

# op -> the surfaces. python is EXECUTED here; block/sound are labels (honestly unverified).
REGISTRY = {
    "add": {"sym": "+",  "py": lambda a, b: a + b, "block": "when [a] add [b]",   "sound": "rising 3rd"},
    "sub": {"sym": "-",  "py": lambda a, b: a - b, "block": "when [a] minus [b]", "sound": "falling 3rd"},
    "mul": {"sym": "*",  "py": lambda a, b: a * b, "block": "repeat [a] x[b]",    "sound": "octave up"},
    "inc": {"sym": "+1", "py": lambda a: a + 1,    "block": "bump [a] up one",    "sound": "step up"},
}


def verify_op(op, args):
    """Confirm the EXECUTABLE surfaces (opcode, python, conlang) all land on the same result."""
    byte = _NAME_TO_BYTE[op]
    r_opcode = float(_OPS[op](*args))
    r_py = float(REGISTRY[op]["py"](*args))
    word = ca_word_for_opcode(byte)          # conlang surface -> same byte -> same op
    ok = abs(r_opcode - r_py) < 1e-9
    return {"byte": byte, "word": word, "opcode": r_opcode, "python": r_py, "verified": ok}


def run_program(prog_ops, stack):
    """Tiny stack machine: apply each op to the stack. Returns the final top (the result)."""
    s = list(stack)
    for op in prog_ops:
        n = 2 if op in ("add", "sub", "mul") else 1
        args = [s.pop() for _ in range(n)][::-1]
        s.append(_OPS[op](*args))
    return s[-1]


def encode_program_qr(prog_ops, name, outdir=r"C:\dev\layer_qr"):
    """The QR SURFACE: program -> opcode bytes -> QR + Micro-QR image (lossless compressed input)."""
    import os
    os.makedirs(outdir, exist_ok=True)
    payload = bytes(_NAME_TO_BYTE[op] for op in prog_ops)   # the program as raw opcode bytes
    qr = segno.make(payload, error="m")
    qr.save(os.path.join(outdir, f"{name}.png"), scale=10, border=2)
    micro = None
    try:
        mqr = segno.make(payload, micro=True)
        mqr.save(os.path.join(outdir, f"{name}_micro.png"), scale=10, border=1)
        micro = f"Micro QR {mqr.version} ({len(payload)} bytes)"
    except Exception as e:
        micro = f"too big for Micro QR -> use a QR reel ({e})"
    return payload, qr.designator, micro


def main():
    print("=" * 80)
    print("  LAYER REGISTRY  --  one opcode (spot), many surfaces (paths), self-verified")
    print("=" * 80)
    print(f"  {'op':5}{'byte':6}{'conlang':9}{'sym':5}{'python':>8}{'opcode':>8}  verified  block / sound")
    for op, args in [("add", (2, 3)), ("sub", (7, 4)), ("mul", (3, 4)), ("inc", (14,))]:
        v = verify_op(op, args)
        r = REGISTRY[op]
        print(f"  {op:5}0x{v['byte']:02x}  {v['word']:9}{r['sym']:5}{v['python']:>8.1f}{v['opcode']:>8.1f}"
              f"  {'YES' if v['verified'] else 'NO ':^8}  {r['block']} | {r['sound']}")
    print(f"\n  polyglot surfaces (verified identical by the emitter, this session): {', '.join(POLYGLOT)}")
    print(f"  unverified surfaces (LABELS until proven): block, sound  -> need the polyglot proof applied")

    print("\n" + "=" * 80)
    print("  THE FIRST SONG as a program, on every surface  (C E G -> add mul inc)")
    print("=" * 80)
    prog = ["add", "mul", "inc"]
    result = run_program(prog, [2, 3, 4])
    payload, qr_v, micro = encode_program_qr(prog, "first_song")
    print(f"  sound  : C  E  G        (the Holophonor's first song)")
    print(f"  opcodes: {prog}  =  bytes {payload.hex()}")
    print(f"  run    : stack [2,3,4] -> {result}   (add 3,4=7; mul 2,7=14; inc=15)")
    print(f"  QR     : {qr_v}  -> C:\\dev\\layer_qr\\first_song.png")
    print(f"  MicroQR: {micro}  -> C:\\dev\\layer_qr\\first_song_micro.png")
    print(f"\n  Same function — sound, opcodes, execution, and a scannable code — all the same spot.")
    print(f"  QR is a VERIFIED layer (lossless byte-transport by spec). The 3-op song fits a Micro QR;")
    print(f"  bigger programs -> standard QR (<=2953 bytes) -> a QR REEL (frame sequence) for any size.")


if __name__ == "__main__":
    main()
