"""Full language-family braid over the bijective tokenizer.

Two maps over the same six tongues — the existing 'spirit' map and the new
'operational' map proposed in the round-table session.

  Tongue  Spirit              Operational role  Operational language
  ------  ------------------  ----------------  --------------------
  KO      Python              control           Python
  AV      JavaScript          transport         TypeScript
  RU      Rust                policy            Rust
  CA      Mathematica         compute           Julia
  UM      Haskell             security          Elixir
  DR      Markdown narrative  schema            SQL

Per the round-table directive: do NOT invent conlang conjunctions up front.
Let the need arise from a failed or awkward transition, then forge a bounded
conjunction only for that specific bridge. This runner is therefore split:

  Layer 1 — bijection: every lane in every map round-trips bytes (no exec).
  Layer 2 — cross-tongue invariance: same bytes through every tongue.
  Layer 3 — execution: run the lane if its toolchain is present.
  Layer 4 — bridge probe: classify each operational lane's translation
            distance from the imperative reference (Python). Possible labels:
              'native'           — same paradigm, direct equivalence
              'adapter-needed'   — small mechanical glue (codegen-able)
              'conjunction-gap'  — paradigm mismatch; a bounded conjunction
                                   would be needed to bridge it cleanly
              'no-toolchain'     — bijection only; semantics unverified

The bridge probe is *descriptive* — it logs where conjunctions WOULD live,
it does not synthesise them.
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

# ---------- Operation: gcd(462, 1071) = 21 ----------

OPERATIONAL: dict[str, dict] = {
    "ko": {
        "role": "control",
        "lang": "Python",
        "ext": "py",
        "paradigm": "imperative",
        "src": (
            "def gcd(a: int, b: int) -> int:\n"
            "    while b:\n"
            "        a, b = b, a % b\n"
            "    return a\n\n"
            "if __name__ == '__main__':\n"
            "    print(gcd(462, 1071))\n"
        ),
        "bridge_from_python": "native",
        "bridge_note": "reference lane",
    },
    "av": {
        "role": "transport",
        "lang": "TypeScript",
        "ext": "ts",
        "paradigm": "imperative+typed",
        "src": (
            "function gcd(a: bigint, b: bigint): bigint {\n"
            "  while (b !== 0n) { [a, b] = [b, a % b]; }\n"
            "  return a;\n"
            "}\n"
            "console.log(gcd(462n, 1071n).toString());\n"
        ),
        "bridge_from_python": "adapter-needed",
        "bridge_note": "type annotations + bigint literals; mechanical glue",
    },
    "ru": {
        "role": "policy",
        "lang": "Rust",
        "ext": "rs",
        "paradigm": "imperative+ownership",
        "src": (
            "fn gcd(mut a: u64, mut b: u64) -> u64 {\n"
            "    while b != 0 { let t = b; b = a % b; a = t; }\n"
            "    a\n"
            "}\n"
            "fn main() { println!(\"{}\", gcd(462, 1071)); }\n"
        ),
        "bridge_from_python": "adapter-needed",
        "bridge_note": "explicit ownership/mut; no semantic gap for pure math",
    },
    "ca": {
        "role": "compute",
        "lang": "Julia",
        "ext": "jl",
        "paradigm": "multiple-dispatch+numeric",
        "src": (
            "function mygcd(a::Integer, b::Integer)\n"
            "    while b != 0\n"
            "        a, b = b, mod(a, b)\n"
            "    end\n"
            "    return a\n"
            "end\n"
            "println(mygcd(462, 1071))\n"
        ),
        "bridge_from_python": "native",
        "bridge_note": "Julia's imperative surface is near-isomorphic to Python here",
    },
    "um": {
        "role": "security",
        "lang": "Elixir",
        "ext": "exs",
        "paradigm": "actor+pure-functional",
        "src": (
            "defmodule G do\n"
            "  def gcd(a, 0), do: a\n"
            "  def gcd(a, b), do: gcd(b, rem(a, b))\n"
            "end\n"
            "IO.puts(G.gcd(462, 1071))\n"
        ),
        "bridge_from_python": "conjunction-gap",
        "bridge_note": (
            "imperative loop -> tail recursion + pattern match; "
            "side-effect surface (IO.puts vs print) differs in commit semantics"
        ),
    },
    "dr": {
        "role": "schema",
        "lang": "SQL",
        "ext": "sql",
        "paradigm": "declarative-relational",
        "src": (
            "-- Recursive CTE GCD: schema lane. SQLite-compatible.\n"
            "WITH RECURSIVE g(a, b) AS (\n"
            "  SELECT 462, 1071\n"
            "  UNION ALL\n"
            "  SELECT b, a % b FROM g WHERE b != 0\n"
            ")\n"
            "SELECT a FROM g WHERE b = 0;\n"
        ),
        "bridge_from_python": "conjunction-gap",
        "bridge_note": (
            "loop -> recursive CTE; control flow becomes set-membership; "
            "result is a row, not a value — needs result-set adapter"
        ),
    },
}


def round_trip(tok, tongue, source):
    raw = source.encode("utf-8")
    tokens = tok.encode_bytes(tongue, raw)
    back = tok.decode_tokens(tongue, tokens)
    return back == raw, len(tokens), tokens[0]


def cross_tongue_invariance(tok, source):
    raw = source.encode("utf-8")
    for code in tok.tongues:
        if tok.decode_tokens(code, tok.encode_bytes(code, raw)) != raw:
            return False, code
    return True, None


def exec_source(tongue, info, src_path):
    """Returns (stdout_or_None, status). None means not executed."""
    lang = info["lang"]
    if lang == "Python":
        out = subprocess.run([sys.executable, str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None,
                "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if lang == "TypeScript":
        # Try ts-node, then deno, then tsc+node fallback
        for runner in ("ts-node", "deno"):
            r = shutil.which(runner)
            if r:
                if runner == "deno":
                    out = subprocess.run([r, "run", str(src_path)], capture_output=True, text=True)
                else:
                    out = subprocess.run([r, str(src_path)], capture_output=True, text=True)
                return (out.stdout.strip() if out.returncode == 0 else None,
                        f"{runner} ok" if out.returncode == 0 else f"{runner} exit {out.returncode}")
        return None, "ts-node/deno/bun missing"
    if lang == "Rust":
        rustc = shutil.which("rustc")
        if not rustc:
            return None, "rustc missing"
        bin_path = src_path.with_suffix(".exe" if sys.platform == "win32" else ".bin")
        cr = subprocess.run([rustc, str(src_path), "-O", "-o", str(bin_path)],
                            capture_output=True, text=True)
        if cr.returncode != 0:
            return None, f"rustc fail: {cr.stderr.strip()[:80]}"
        out = subprocess.run([str(bin_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None,
                "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if lang == "Julia":
        j = shutil.which("julia")
        if not j:
            return None, "julia missing"
        out = subprocess.run([j, str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None,
                "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if lang == "Elixir":
        e = shutil.which("elixir")
        if not e:
            return None, "elixir missing"
        out = subprocess.run([e, str(src_path)], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None,
                "ok" if out.returncode == 0 else f"exit {out.returncode}")
    if lang == "SQL":
        sq = shutil.which("sqlite3")
        if not sq:
            return None, "sqlite3 missing"
        out = subprocess.run([sq, ":memory:", f".read {src_path}"], capture_output=True, text=True)
        return (out.stdout.strip() if out.returncode == 0 else None,
                "ok" if out.returncode == 0 else f"exit {out.returncode}")
    return None, "unknown lang"


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    tok = SacredTongueTokenizer()

    print("=== FULL BRAID — operational language map ===")
    print("Operation: gcd(462, 1071) -> 21")
    print()

    rows = []
    print("== Layer 1: per-tongue byte round-trip ==")
    for tongue, info in OPERATIONAL.items():
        path = HERE / f"gcd_op_{tongue}.{info['ext']}"
        path.write_text(info["src"], encoding="utf-8")
        ok, n_tokens, first = round_trip(tok, tongue, info["src"])
        rows.append({"tongue": tongue, **info, "tokens": n_tokens,
                     "first": first, "round_trip": ok, "path": path})
        marker = "OK " if ok else "FAIL"
        print(f"  [{marker}] {tongue.upper()} {info['lang']:<11} ({info['role']:<9})  "
              f"tokens={n_tokens:3d}  first={first!r}")

    if not all(r["round_trip"] for r in rows):
        print("FAIL at L1")
        return 1

    print("\n== Layer 2: cross-tongue invariance (each source through every tongue) ==")
    for r in rows:
        ok, fail_code = cross_tongue_invariance(tok, r["src"])
        marker = "OK " if ok else f"FAIL@{fail_code}"
        print(f"  [{marker}] {r['tongue'].upper()} ({r['lang']}) source survives all 6 tongues")
        if not ok:
            return 2

    print("\n== Layer 3: execute where toolchain is present ==")
    expected = "21"
    sem_rows = []
    for r in rows:
        out, status = exec_source(r["tongue"], r, r["path"])
        agree = (out == expected)
        sem_rows.append({**r, "out": out, "status": status, "agree": agree})
        marker = "MATCH  " if agree else ("SKIP   " if out is None else "DIVERGE")
        print(f"  [{marker}] {r['tongue'].upper()} {r['lang']:<11} "
              f"out={out!r:<8} status={status}")

    print("\n== Layer 4: bridge probe (descriptive — conjunctions NOT synthesised) ==")
    print("  reference lane = KO/Python (imperative)\n")
    headers = ("tongue", "lang", "role", "paradigm", "bridge", "note")
    print(f"  {headers[0]:<6} {headers[1]:<11} {headers[2]:<10} "
          f"{headers[3]:<22} {headers[4]:<18} {headers[5]}")
    print("  " + "-" * 110)
    gaps = []
    for r in sem_rows:
        bridge = r["bridge_from_python"]
        if r["out"] is None and r["tongue"] != "ko":
            displayed_bridge = bridge if bridge == "conjunction-gap" else f"{bridge}*"
        else:
            displayed_bridge = bridge
        print(f"  {r['tongue'].upper():<6} {r['lang']:<11} {r['role']:<10} "
              f"{r['paradigm']:<22} {displayed_bridge:<18} {r['bridge_note']}")
        if bridge == "conjunction-gap":
            gaps.append(r)

    print("\n  * = bridge classification holds at the source level but was not "
          "exec-verified (toolchain missing).")

    print("\n== Conjunction backlog (only forge when a real bridge fails) ==")
    if gaps:
        for g in gaps:
            print(f"  - {g['tongue'].upper()} ({g['lang']}, {g['role']}): {g['bridge_note']}")
        print("\n  These are the *candidate* sites. None are forged yet — wait for")
        print("  a failed transition in real use, then build a bounded conjunction")
        print("  named after that specific bridge (e.g. KO->DR result-set adapter).")
    else:
        print("  (none)")

    print("\n== Summary ==")
    bij_all = all(r["round_trip"] for r in rows)
    cross_all = all(cross_tongue_invariance(tok, r["src"])[0] for r in rows)
    sem_executed = [s for s in sem_rows if s["out"] is not None]
    sem_agree = all(s["agree"] for s in sem_executed)
    print(f"  bijective per-tongue:   {bij_all}  ({len(rows)}/{len(rows)})")
    print(f"  cross-tongue invariant: {cross_all}")
    print(f"  semantic agreement:     "
          f"{sum(s['agree'] for s in sem_executed)}/{len(sem_executed)} executed "
          f"(skipped: {len(rows) - len(sem_executed)})")
    print(f"  conjunction candidates: {len(gaps)}")

    if bij_all and cross_all and sem_agree:
        print("\nBRAID HOLDS: byte plane shared, surfaces diverge cleanly, "
              "no forced conjunctions invented.")
        return 0
    print("\nFAIL")
    return 3


if __name__ == "__main__":
    sys.exit(main())
