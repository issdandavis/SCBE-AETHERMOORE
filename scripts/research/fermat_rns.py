#!/usr/bin/env python3
"""fermat_rns.py — Residue Number System over Fermat primes, with overflow detection.

Exact, carry-free, parallel integer arithmetic: an integer is carried as its
residues mod a set of coprime moduli; add/sub/mul act INDEPENDENTLY per channel;
reconstruction is via CRT. This is the real home of the Fermat/integer-exactness
lever (see nested_integer_ruler.py, fermat_ntt_readout.py): the prime/coprime
structure is genuinely load-bearing — non-coprime moduli cannot reconstruct.

THE HARD PART (why naive RNS can't detect overflow):
  With only the working moduli (product M_info), x and x + M_info have IDENTICAL
  residues. So after an op you cannot tell whether the true result wrapped. You
  MUST add information. Standard fix = a REDUNDANT modulus (redundant RNS / RRNS):
  carry one extra coprime modulus so the uniquely-recoverable range grows to
  M_total = M_info * m_redundant. Then the true result is still recoverable when
  it exceeds the *legal* range M_info, so overflow is DETECTABLE by reconstructing
  and checking against the legal range.

On-theme design: working range from the small Fermat primes (3,5,17,257), and the
big Fermat prime 65537 as the overflow SENTINEL (the "terminal macro-unit" guard).

  legal range  = balanced [-M_info/2, M_info/2],  M_info = 3*5*17*257 = 65535
  guard range  = M_total = 65535 * 65537 = (2^16-1)(2^16+1) = 2^32 - 1 = 4,294,967,295
  detection valid while |true result| <= M_total/2; beyond that even the guard
  wraps (documented bound, flagged honestly — no silent lie).

Usage:  PYTHONPATH=. python scripts/research/fermat_rns.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import reduce
from math import gcd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nth_prime_baseline_gate import simple_sieve  # noqa: E402  (prime context only)


def _prod(xs) -> int:
    return reduce(lambda a, b: a * b, xs, 1)


def crt(residues: tuple[int, ...], moduli: tuple[int, ...]) -> int:
    """Reconstruct in [0, prod(moduli)); requires pairwise-coprime moduli."""
    M = _prod(moduli)
    total = 0
    for r, m in zip(residues, moduli):
        Mi = M // m
        total += r * Mi * pow(Mi, -1, m)
    return total % M


@dataclass(frozen=True)
class RNSValue:
    residues: tuple[int, ...]
    overflow: bool = False  # set when a producing op exceeded the legal range


class FermatRNS:
    """Redundant RNS: small Fermat primes for range, 65537 as the overflow guard."""

    INFO_MODULI = (3, 5, 17, 257)
    GUARD = 65537  # Fermat F4 — the overflow sentinel
    MODULI = INFO_MODULI + (GUARD,)

    def __init__(self) -> None:
        assert self._pairwise_coprime(self.MODULI), "RNS moduli must be pairwise coprime"
        self.M_info = _prod(self.INFO_MODULI)  # legal dynamic range
        self.M_total = _prod(self.MODULI)  # recoverable (guarded) range
        self.legal_lo = -(self.M_info // 2)
        self.legal_hi = self.M_info // 2

    @staticmethod
    def _pairwise_coprime(mods) -> bool:
        return all(gcd(mods[i], mods[j]) == 1 for i in range(len(mods)) for j in range(i + 1, len(mods)))

    def is_legal(self, value: int) -> bool:
        return self.legal_lo <= value <= self.legal_hi

    def encode(self, x: int) -> RNSValue:
        if not self.is_legal(x):
            raise ValueError(f"{x} outside legal RNS range [{self.legal_lo}, {self.legal_hi}]")
        return RNSValue(tuple(x % m for m in self.MODULI))

    def decode(self, v: RNSValue) -> int:
        """Exact balanced reconstruction over the guarded range [-M_total/2, M_total/2)."""
        u = crt(v.residues, self.MODULI)  # in [0, M_total)
        return u - self.M_total if u > self.M_total // 2 else u

    def _binop(self, a: RNSValue, b: RNSValue, op) -> RNSValue:
        res = tuple(op(ra, rb) % m for ra, rb, m in zip(a.residues, b.residues, self.MODULI))
        out = RNSValue(res)
        true_val = self.decode(out)  # exact while |true_val| <= M_total/2
        return RNSValue(res, overflow=not self.is_legal(true_val))

    def add(self, a: RNSValue, b: RNSValue) -> RNSValue:
        return self._binop(a, b, lambda x, y: x + y)

    def sub(self, a: RNSValue, b: RNSValue) -> RNSValue:
        return self._binop(a, b, lambda x, y: x - y)

    def mul(self, a: RNSValue, b: RNSValue) -> RNSValue:
        return self._binop(a, b, lambda x, y: x * y)

    def detection_safe(self, true_result: int) -> bool:
        """Overflow detection is reliable only while the true result fits the guard range."""
        return abs(true_result) <= self.M_total // 2


# --------------------------------------------------------------------------- #
# Self-checks + report
# --------------------------------------------------------------------------- #
def _self_check() -> None:
    r = FermatRNS()

    # round-trip exact for legal values (incl. negatives via balanced CRT)
    for x in (0, 1, -1, 32767, -32767, 12345, -9999):
        assert r.decode(r.encode(x)) == x, f"round-trip failed for {x}"

    # carry-free exact arithmetic, in range -> no overflow, correct value
    a, b = r.encode(20000), r.encode(12000)
    s = r.add(a, b)  # 32000 in range
    assert not s.overflow and r.decode(s) == 32000

    # overflow DETECTED when true result leaves legal range, and recovered exactly
    big = r.add(r.encode(30000), r.encode(30000))  # 60000 > 32767
    assert big.overflow and r.decode(big) == 60000, "overflow must be flagged AND exactly recovered"

    mbig = r.mul(r.encode(30000), r.encode(20000))  # 6e8 >> legal, < M_total/2
    assert mbig.overflow and r.decode(mbig) == 600_000_000

    # the NULL: WITHOUT the guard modulus, the same overflow is INVISIBLE. Info-only
    # balanced reconstruction silently MIS-reconstructs (and can raise no flag).
    info = FermatRNS.INFO_MODULI
    M_info = _prod(info)
    x = 60000  # a legal sum (30000+30000) that exceeds the balanced legal range
    u = crt(tuple(x % m for m in info), info)
    info_balanced = u - M_info if u > M_info // 2 else u
    assert info_balanced != x, "info-only must silently mis-reconstruct — guard is load-bearing"
    # the guarded RNS recovers it exactly AND flags overflow
    guarded = r.add(r.encode(30000), r.encode(30000))
    assert guarded.overflow and r.decode(guarded) == x

    # detection bound is honest: beyond M_total/2 even the guard wraps
    assert not r.detection_safe(r.M_total)  # too big to detect reliably

    # non-coprime moduli can't form an RNS
    assert not FermatRNS._pairwise_coprime((4, 6))


def main() -> int:
    _self_check()
    r = FermatRNS()
    print("FERMAT RESIDUE NUMBER SYSTEM — exact carry-free arithmetic + overflow detection")
    print("=" * 78)
    print(f"  working moduli {r.INFO_MODULI}  guard {r.GUARD} (Fermat F4)")
    print(
        f"  legal range = [{r.legal_lo}, {r.legal_hi}]  (M_info={r.M_info});  " f"guarded range M_total={r.M_total:,}\n"
    )

    print("[1] carry-free parallel arithmetic (each channel independent, no carry between them)")
    a, b = r.encode(12345), r.encode(-678)
    print(f"    12345 -> residues {a.residues}")
    print(f"     -678 -> residues {b.residues}")
    s, p = r.add(a, b), r.mul(a, b)
    print(f"    add: residues {s.residues} -> decode {r.decode(s)}  (exact {12345 + -678}, overflow={s.overflow})")
    print(f"    mul: residues {p.residues} -> decode {r.decode(p)}  (exact {12345 * -678}, overflow={p.overflow})")

    print("\n[2] overflow DETECTION — result leaves legal range but is still recovered exactly")
    cases = [(30000, 30000, "add"), (30000, 20000, "mul"), (32767, 1, "add")]
    for x, y, opname in cases:
        op = {"add": r.add, "mul": r.mul}[opname]
        out = op(r.encode(x), r.encode(y))
        true = x + y if opname == "add" else x * y
        flag = "OVERFLOW" if out.overflow else "ok"
        print(f"    {x} {opname} {y} = {r.decode(out)}  (true {true})  -> {flag}")

    print("\n[3] NULL — without the 65537 guard, the SAME overflow is invisible (silent wrap)")
    info = FermatRNS.INFO_MODULI
    M_info = _prod(info)
    x = 60000
    u = crt(tuple(x % m for m in info), info)
    info_balanced = u - M_info if u > M_info // 2 else u
    print(f"    info-only RNS reconstructs 60000 as {info_balanced} (silent, wrong) — no flag possible")
    g = r.add(r.encode(30000), r.encode(30000))
    print(f"    with 65537 guard: decode={r.decode(g)} (correct), overflow={g.overflow}")

    print("\n[4] detection bound (honest): reliable only while |result| <= M_total/2 = {:,}".format(r.M_total // 2))
    print("    beyond that even the guard wraps — flagged via detection_safe(), not silently trusted")

    print("\n--- VERDICT ---")
    print("  Exact carry-free parallel integer arithmetic over coprime Fermat moduli (RNS).")
    print("  Overflow is UNDETECTABLE without redundancy; the 65537 guard makes it detectable")
    print("  AND keeps the true result exactly recoverable. Coprimality is load-bearing;")
    print("  the guard's range is the price. This is the integer-exactness lever doing real work.")
    print("\n  self-checks: round-trip, carry-free ops, overflow detect+recover, null, bound — all passed")
    return 0


def _op_payload(op_name: str, a: int, b: int) -> dict:
    """Exact RNS op result as a structured, JSON-serializable payload."""
    r = FermatRNS()
    ra, rb = r.encode(a), r.encode(b)
    op = {"add": r.add, "sub": r.sub, "mul": r.mul}[op_name]
    out = op(ra, rb)
    true = {"add": a + b, "sub": a - b, "mul": a * b}[op_name]
    decoded = r.decode(out)
    return {
        "ok": True,
        "op": op_name,
        "a": a,
        "b": b,
        "a_residues": list(ra.residues),
        "b_residues": list(rb.residues),
        "result_residues": list(out.residues),
        "decoded": decoded,
        "exact_true": true,
        "exact": decoded == true and r.detection_safe(true),
        "overflow": out.overflow,
        "detection_safe": r.detection_safe(true),
        "moduli": list(r.MODULI),
        "guard": r.GUARD,
        "legal_range": [r.legal_lo, r.legal_hi],
        "guarded_range": r.M_total,
    }


def cli(argv: list[str]) -> int:
    """Arg-driven entry point so `scbe rns ...` is a real tool, not just a demo."""
    p = argparse.ArgumentParser(
        prog="scbe rns",
        description="Exact carry-free RNS arithmetic over Fermat primes, with overflow detection.",
    )
    sub = p.add_subparsers(dest="cmd")
    pr = sub.add_parser("report", help="Run self-checks and print the capability report")
    pr.add_argument("--json", action="store_true")
    pe = sub.add_parser("encode", help="Encode an integer to RNS residues")
    pe.add_argument("value", type=int)
    pe.add_argument("--json", action="store_true")
    for name in ("add", "sub", "mul"):
        ps = sub.add_parser(name, help=f"Exact {name} of two integers via RNS (overflow-detected)")
        ps.add_argument("a", type=int)
        ps.add_argument("b", type=int)
        ps.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.cmd in (None, "report"):
        if getattr(args, "json", False):
            r = FermatRNS()
            _self_check()
            print(
                json.dumps(
                    {
                        "ok": True,
                        "tool": "fermat_rns",
                        "info_moduli": list(r.INFO_MODULI),
                        "guard": r.GUARD,
                        "legal_range": [r.legal_lo, r.legal_hi],
                        "guarded_range": r.M_total,
                        "self_checks": "passed",
                    },
                    indent=2,
                )
            )
            return 0
        return main()

    if args.cmd == "encode":
        r = FermatRNS()
        try:
            v = r.encode(args.value)
        except ValueError as exc:
            out = {"ok": False, "error": str(exc)}
            print(json.dumps(out, indent=2) if args.json else f"error: {exc}")
            return 2
        if args.json:
            print(
                json.dumps(
                    {"ok": True, "value": args.value, "residues": list(v.residues), "moduli": list(r.MODULI)}, indent=2
                )
            )
        else:
            print(f"{args.value} -> residues {v.residues}  (moduli {r.MODULI})")
        return 0

    # add / sub / mul
    try:
        payload = _op_payload(args.cmd, args.a, args.b)
    except ValueError as exc:
        out = {"ok": False, "error": str(exc)}
        print(json.dumps(out, indent=2) if args.json else f"error: {exc}")
        return 2
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        flag = "OVERFLOW (detected, exact)" if payload["overflow"] else "ok"
        print(
            f"{payload['a']} {payload['op']} {payload['b']} = {payload['decoded']}  (true {payload['exact_true']})  -> {flag}"
        )
        print(f"  result residues {payload['result_residues']}  moduli {payload['moduli']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli(sys.argv[1:]))
