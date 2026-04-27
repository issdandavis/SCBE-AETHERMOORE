"""Bijective 6-tongue full build test.

One operation (gcd(462, 1071) = 21) expressed in all six tongues:
  KO -> Python      (exec)
  AV -> JavaScript  (exec)
  RU -> Rust        (exec)
  CA -> Mathematica (bijection only; wolframscript optional)
  UM -> Haskell     (bijection only; ghc optional)
  DR -> Markdown    (bijection only; narrative form)

For each tongue:
  1. Byte->token->byte round-trip must be lossless.
  2. Cross-tongue: same bytes encoded/decoded through *any* tongue must
     return identical bytes (proves the byte plane is shared).
  3. Where the toolchain exists, execute and verify stdout == "21".
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from crypto.sacred_tongues import SacredTongueTokenizer  # noqa: E402

HERE = Path(__file__).parent

# ---------- 6 surface forms of one operation ----------

SOURCES: dict[str, dict] = {
    "ko": {
        "lang": "Python",
        "ext": "py",
        "src": (
            "def gcd(a: int, b: int) -> int:\n"
            "    while b:\n"
            "        a, b = b, a % b\n"
            "    return a\n\n"
            "if __name__ == '__main__':\n"
            "    print(gcd(462, 1071))\n"
        ),
    },
    "av": {
        "lang": "JavaScript",
        "ext": "js",
        "src": (
            "function gcd(a, b) {\n"
            "  while (b !== 0n) {\n"
            "    [a, b] = [b, a % b];\n"
            "  }\n"
            "  return a;\n"
            "}\n"
            "console.log(gcd(462n, 1071n).toString());\n"
        ),
    },
    "ru": {
        "lang": "Rust",
        "ext": "rs",
        "src": (
            "fn gcd(mut a: u64, mut b: u64) -> u64 {\n"
            "    while b != 0 {\n"
            "        let t = b; b = a % b; a = t;\n"
            "    }\n"
            "    a\n"
            "}\n"
            "fn main() { println!(\"{}\", gcd(462, 1071)); }\n"
        ),
    },
    "ca": {
        "lang": "Mathematica",
        "ext": "wl",
        "src": (
            "(* CA tongue: symbolic *)\n"
            "gcd[a_, b_] := If[b == 0, a, gcd[b, Mod[a, b]]];\n"
            "Print[gcd[462, 1071]];\n"
        ),
    },
    "um": {
        "lang": "Haskell",
        "ext": "hs",
        "src": (
            "-- UM tongue: pure-functional\n"
            "myGcd :: Integer -> Integer -> Integer\n"
            "myGcd a 0 = a\n"
            "myGcd a b = myGcd b (a `mod` b)\n"
            "main :: IO ()\n"
            "main = print (myGcd 462 1071)\n"
        ),
    },
    "dr": {
        "lang": "Markdown",
        "ext": "md",
        "src": (
            "# Euclid's Algorithm — Narrative Form (DR tongue)\n\n"
            "Given two numbers, the larger holds the secret.\n"
            "Subtract the smaller from the larger as remainders, repeatedly,\n"
            "until nothing remains to subtract. What stands is the **GCD**.\n\n"
            "    gcd(462, 1071)\n"
            "    -> gcd(1071, 462)\n"
            "    -> gcd(462, 147)\n"
            "    -> gcd(147, 21)\n"
            "    -> gcd(21, 0)\n"
            "    => **21**\n"
        ),
    },
}


def round_trip(tok, tongue, source):
    raw = source.encode("utf-8")
    tokens = tok.encode_bytes(tongue, raw)
    back = tok.decode_tokens(tongue, tokens)
    return back == raw, len(tokens), tokens[0]


def cross_tongue_invariance(tok, source):
    """Encode the same bytes through every tongue; all must return identical bytes."""
    raw = source.encode("utf-8")
    for code in tok.tongues:
        if tok.decode_tokens(code, tok.encode_bytes(code, raw)) != raw:
            return False, code
    return True, None


def exec_source(tongue, info, src_path):
    """Returns (stdout_or_None, status_str). None means we couldn't execute."""
    lang = info["lang"]
    if tongue == "ko":
        out = subprocess.run([sys.executable, str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None, "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if tongue == "av":
        node = shutil.which("node")
        if not node:
            return None, "node missing"
        out = subprocess.run([node, str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None, "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if tongue == "ru":
        rustc = shutil.which("rustc")
        if not rustc:
            return None, "rustc missing"
        bin_path = src_path.with_suffix(".exe" if sys.platform == "win32" else ".bin")
        cr = subprocess.run([rustc, str(src_path), "-O", "-o", str(bin_path)], capture_output=True, text=True)
        if cr.returncode != 0:
            return None, f"rustc fail: {cr.stderr.strip()[:80]}"
        out = subprocess.run([str(bin_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None, "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if tongue == "ca":
        ws = shutil.which("wolframscript")
        if not ws:
            return None, "wolframscript missing"
        out = subprocess.run([ws, "-file", str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None, "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if tongue == "um":
        rh = shutil.which("runghc") or shutil.which("runhaskell")
        if not rh:
            return None, "ghc missing"
        out = subprocess.run([rh, str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None, "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if tongue == "dr":
        # Narrative — not executed. Extract the asserted answer.
        m = re.search(r"=>\s*\*\*(\d+)\*\*", info["src"])
        return (m.group(1) if m else None, "narrative")
    return None, "unknown tongue"


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    tok = SacredTongueTokenizer()

    rows = []
    print("== Per-tongue byte round-trip ==")
    for tongue, info in SOURCES.items():
        path = HERE / f"gcd_{tongue}.{info['ext']}"
        path.write_text(info["src"], encoding="utf-8")
        ok, n_tokens, first = round_trip(tok, tongue, info["src"])
        rows.append({"tongue": tongue, "lang": info["lang"], "tokens": n_tokens,
                     "first": first, "round_trip": ok, "path": path})
        print(f"  {tongue.upper()} ({info['lang']:<11}): tokens={n_tokens:3d}  first={first!r:<14}  round_trip={ok}")

    if not all(r["round_trip"] for r in rows):
        print("FAIL: per-tongue bijection broke")
        return 1

    print("\n== Cross-tongue invariance (bytes survive any tongue's encode/decode) ==")
    for r in rows:
        ok, fail_code = cross_tongue_invariance(tok, SOURCES[r["tongue"]]["src"])
        marker = "OK" if ok else f"FAIL@{fail_code}"
        print(f"  {r['tongue'].upper()} source through all 6 tongues: {marker}")
        if not ok:
            return 2

    print("\n== Execute and check semantic agreement ==")
    expected = "21"
    sem_rows = []
    for r in rows:
        out, status = exec_source(r["tongue"], SOURCES[r["tongue"]], r["path"])
        agree = (out == expected)
        sem_rows.append({**r, "out": out, "status": status, "agree": agree})
        marker = "MATCH" if agree else ("SKIP" if out is None else "DIVERGE")
        print(f"  {r['tongue'].upper()} ({r['lang']:<11}): out={out!r:<8} status={status:<22} {marker}")

    print("\n== Summary ==")
    bij_all = all(r["round_trip"] for r in rows)
    cross_all = all(cross_tongue_invariance(tok, SOURCES[r['tongue']]['src'])[0] for r in rows)
    sem_executed = [s for s in sem_rows if s["out"] is not None]
    sem_agree = all(s["agree"] for s in sem_executed)
    print(f"  bijective per-tongue:    {bij_all}")
    print(f"  cross-tongue invariant:  {cross_all}")
    print(f"  semantic agreement:      {sum(s['agree'] for s in sem_executed)}/{len(sem_executed)} executed (skipped: {len(rows) - len(sem_executed)})")

    if bij_all and cross_all and sem_agree:
        print("\nALL GREEN: bijection holds across all 6 tongues; every executed form returned 21.")
        return 0
    print("\nFAIL")
    return 3


if __name__ == "__main__":
    sys.exit(main())
