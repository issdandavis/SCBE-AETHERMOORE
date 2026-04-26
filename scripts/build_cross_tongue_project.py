"""Cross-Tongue Bijective Project Builder.

Builds a project consisting of multiple algorithms, each implemented in all
six Sacred Tongues (KO/AV/RU/CA/UM/DR), and proves a dual bijection:

  Layer 1 — byte-level bijection
      For every (algorithm, tongue), source.encode("utf-8") survives a
      round-trip through SacredTongueTokenizer.encode_bytes / decode_tokens.

  Layer 2 — cross-tongue byte invariance
      For every source, encoding/decoding through *any* tongue returns the
      original bytes (proves the byte plane is shared, not tongue-specific).

  Layer 3 — slot-aligned semantic bijection
      Every algorithm declares an ordered list of slot names (e.g. sig, body
      or sig, init, loop_open, loop_body, ret). The slot list must be
      identical across all six tongues. An edit at slot k in any tongue
      maps to slot k in every other tongue (bijective edit propagation).

Outputs a sealed bundle to artifacts/cross_tongue_projects/<project>/bundle.json
containing per-tongue source per algorithm, the encoded token streams
("tokenizer seals"), the slot manifest, and the bijection proofs.

Usage:
    python scripts/build_cross_tongue_project.py
    python scripts/build_cross_tongue_project.py --project arithmetic_basics
    python scripts/build_cross_tongue_project.py --out artifacts/cross_tongue_projects/foo
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crypto.sacred_tongues import SacredTongueTokenizer  # noqa: E402

TONGUE_ORDER = ("ko", "av", "ru", "ca", "um", "dr")
SPIRIT_LANGS = {
    "ko": "Python",
    "av": "JavaScript",
    "ru": "Rust",
    "ca": "Mathematica",
    "um": "Haskell",
    "dr": "Markdown",
}


@dataclass
class SlottedImpl:
    """One algorithm in one tongue, decomposed into ordered slots."""

    tongue: str
    slots: Dict[str, str] = field(default_factory=dict)

    def render(self, slot_order: List[str]) -> str:
        return "".join(self.slots[name] for name in slot_order)


@dataclass
class Algorithm:
    """One algorithm with slot manifest + per-tongue slotted implementations."""

    name: str
    slot_order: List[str]
    impls: Dict[str, SlottedImpl] = field(default_factory=dict)


# ---------- Built-in project specs ----------


def _add_spec() -> Algorithm:
    algo = Algorithm(name="add", slot_order=["sig", "body"])
    algo.impls["ko"] = SlottedImpl("ko", {
        "sig": "def add(a: int, b: int) -> int:\n",
        "body": "    return a + b\n",
    })
    algo.impls["av"] = SlottedImpl("av", {
        "sig": "function add(a, b) {\n",
        "body": "  return a + b;\n}\n",
    })
    algo.impls["ru"] = SlottedImpl("ru", {
        "sig": "fn add(a: i64, b: i64) -> i64 {\n",
        "body": "    a + b\n}\n",
    })
    algo.impls["ca"] = SlottedImpl("ca", {
        "sig": "add[a_, b_] := \n",
        "body": "  a + b;\n",
    })
    algo.impls["um"] = SlottedImpl("um", {
        "sig": "add :: Integer -> Integer -> Integer\n",
        "body": "add a b = a + b\n",
    })
    algo.impls["dr"] = SlottedImpl("dr", {
        "sig": "## add(a, b)\n",
        "body": "Return the sum: a + b => a+b.\n",
    })
    return algo


def _sum_list_spec() -> Algorithm:
    algo = Algorithm(
        name="sum_list",
        slot_order=["sig", "init", "loop_open", "loop_body", "ret"],
    )
    algo.impls["ko"] = SlottedImpl("ko", {
        "sig": "def sum_list(xs):\n",
        "init": "    total = 0\n",
        "loop_open": "    for x in xs:\n",
        "loop_body": "        total += x\n",
        "ret": "    return total\n",
    })
    algo.impls["av"] = SlottedImpl("av", {
        "sig": "function sumList(xs) {\n",
        "init": "  let total = 0;\n",
        "loop_open": "  for (const x of xs) {\n",
        "loop_body": "    total += x;\n",
        "ret": "  }\n  return total;\n}\n",
    })
    algo.impls["ru"] = SlottedImpl("ru", {
        "sig": "fn sum_list(xs: &[i64]) -> i64 {\n",
        "init": "    let mut total: i64 = 0;\n",
        "loop_open": "    for x in xs {\n",
        "loop_body": "        total += *x;\n",
        "ret": "    }\n    total\n}\n",
    })
    algo.impls["ca"] = SlottedImpl("ca", {
        "sig": "sumList[xs_List] := Module[{total},\n",
        "init": "  total = 0;\n",
        "loop_open": "  Do[\n",
        "loop_body": "    total = total + xs[[i]],\n",
        "ret": "    {i, 1, Length[xs]}]; total]\n",
    })
    algo.impls["um"] = SlottedImpl("um", {
        "sig": "sumList :: [Integer] -> Integer\n",
        "init": "sumList xs = go 0 xs where\n",
        "loop_open": "  go acc [] = acc\n",
        "loop_body": "  go acc (y:ys) = go (acc + y) ys\n",
        "ret": "-- tail-recursive accumulator returns total\n",
    })
    algo.impls["dr"] = SlottedImpl("dr", {
        "sig": "## sum_list(xs)\n",
        "init": "Start with total = 0.\n",
        "loop_open": "For each element x in xs:\n",
        "loop_body": "  add x to total.\n",
        "ret": "Return total.\n",
    })
    return algo


def _is_palindrome_spec() -> Algorithm:
    algo = Algorithm(name="is_palindrome", slot_order=["sig", "body"])
    algo.impls["ko"] = SlottedImpl("ko", {
        "sig": "def is_palindrome(s: str) -> bool:\n",
        "body": "    return s == s[::-1]\n",
    })
    algo.impls["av"] = SlottedImpl("av", {
        "sig": "function isPalindrome(s) {\n",
        "body": "  return s === s.split('').reverse().join('');\n}\n",
    })
    algo.impls["ru"] = SlottedImpl("ru", {
        "sig": "fn is_palindrome(s: &str) -> bool {\n",
        "body": "    s.chars().eq(s.chars().rev())\n}\n",
    })
    algo.impls["ca"] = SlottedImpl("ca", {
        "sig": "isPalindrome[s_String] := \n",
        "body": "  s === StringReverse[s];\n",
    })
    algo.impls["um"] = SlottedImpl("um", {
        "sig": "isPalindrome :: String -> Bool\n",
        "body": "isPalindrome s = s == reverse s\n",
    })
    algo.impls["dr"] = SlottedImpl("dr", {
        "sig": "## is_palindrome(s)\n",
        "body": "True when s reads the same forward and reversed.\n",
    })
    return algo


PROJECT_SPECS: Dict[str, List[Algorithm]] = {
    "arithmetic_basics": [_add_spec(), _sum_list_spec(), _is_palindrome_spec()],
}


# ---------- Bijection probes ----------


def byte_round_trip(tok: SacredTongueTokenizer, tongue: str, src: str) -> Tuple[bool, int]:
    raw = src.encode("utf-8")
    tokens = tok.encode_bytes(tongue, raw)
    back = tok.decode_tokens(tongue, tokens)
    return back == raw, len(tokens)


def cross_tongue_invariance(tok: SacredTongueTokenizer, src: str) -> Tuple[bool, str | None]:
    raw = src.encode("utf-8")
    for code in TONGUE_ORDER:
        if tok.decode_tokens(code, tok.encode_bytes(code, raw)) != raw:
            return False, code
    return True, None


def slot_alignment_proof(algo: Algorithm) -> Tuple[bool, str | None]:
    """Every tongue must declare the same ordered slot list with no missing slots."""
    expected = list(algo.slot_order)
    for code in TONGUE_ORDER:
        impl = algo.impls.get(code)
        if impl is None:
            return False, f"missing tongue {code}"
        actual = list(impl.slots.keys())
        if actual != expected:
            return False, f"slot order drift in {code}: {actual} != {expected}"
    return True, None


# ---------- Bundle construction ----------


def build_bundle(project_name: str, algos: List[Algorithm]) -> Dict:
    tok = SacredTongueTokenizer()

    bundle: Dict = {
        "project": project_name,
        "tongue_order": list(TONGUE_ORDER),
        "spirit_languages": SPIRIT_LANGS,
        "algorithms": [],
        "bijection_proofs": {
            "byte_round_trip": {},
            "cross_tongue_invariance": {},
            "slot_alignment": {},
        },
        "summary": {},
    }

    all_byte_ok = True
    all_cross_ok = True
    all_slot_ok = True

    for algo in algos:
        slot_ok, slot_err = slot_alignment_proof(algo)
        bundle["bijection_proofs"]["slot_alignment"][algo.name] = {
            "ok": slot_ok,
            "expected": algo.slot_order,
            "error": slot_err,
        }
        if not slot_ok:
            all_slot_ok = False

        per_tongue_round_trip: Dict[str, Dict] = {}
        per_tongue_cross: Dict[str, Dict] = {}
        impls_export: Dict[str, Dict] = {}

        for code in TONGUE_ORDER:
            impl = algo.impls[code]
            src = impl.render(algo.slot_order)
            raw = src.encode("utf-8")

            ok_bytes, n_tokens = byte_round_trip(tok, code, src)
            tokens = tok.encode_bytes(code, raw)
            sha = hashlib.sha256(raw).hexdigest()

            per_tongue_round_trip[code] = {
                "ok": ok_bytes,
                "n_tokens": n_tokens,
                "sha256": sha,
            }
            if not ok_bytes:
                all_byte_ok = False

            ok_cross, fail_at = cross_tongue_invariance(tok, src)
            per_tongue_cross[code] = {"ok": ok_cross, "fail_at": fail_at}
            if not ok_cross:
                all_cross_ok = False

            impls_export[code] = {
                "language": SPIRIT_LANGS[code],
                "slots": impl.slots,
                "rendered": src,
                "tokenizer_seal": tokens,
                "sha256": sha,
            }

        bundle["bijection_proofs"]["byte_round_trip"][algo.name] = per_tongue_round_trip
        bundle["bijection_proofs"]["cross_tongue_invariance"][algo.name] = per_tongue_cross

        bundle["algorithms"].append({
            "name": algo.name,
            "slot_order": algo.slot_order,
            "implementations": impls_export,
        })

    bundle["summary"] = {
        "n_algorithms": len(algos),
        "n_tongues": len(TONGUE_ORDER),
        "byte_round_trip_all_ok": all_byte_ok,
        "cross_tongue_invariance_all_ok": all_cross_ok,
        "slot_alignment_all_ok": all_slot_ok,
        "all_green": all_byte_ok and all_cross_ok and all_slot_ok,
    }
    return bundle


def write_bundle(bundle: Dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = out_dir / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=False), encoding="utf-8")
    return bundle_path


def print_summary(bundle: Dict) -> None:
    s = bundle["summary"]
    print(f"== Cross-Tongue Project: {bundle['project']} ==")
    print(f"  algorithms: {s['n_algorithms']}, tongues: {s['n_tongues']}")
    print(f"  byte round-trip:        {s['byte_round_trip_all_ok']}")
    print(f"  cross-tongue invariant: {s['cross_tongue_invariance_all_ok']}")
    print(f"  slot alignment:         {s['slot_alignment_all_ok']}")
    print(f"  ALL GREEN:              {s['all_green']}")
    for algo in bundle["algorithms"]:
        name = algo["name"]
        sizes = {
            code: bundle["bijection_proofs"]["byte_round_trip"][name][code]["n_tokens"]
            for code in TONGUE_ORDER
        }
        size_line = " ".join(f"{c.upper()}={sizes[c]}" for c in TONGUE_ORDER)
        print(f"    {name:<16} slots={algo['slot_order']}  tokens: {size_line}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default="arithmetic_basics", choices=sorted(PROJECT_SPECS))
    ap.add_argument("--out", default=None, help="Output directory (default: artifacts/cross_tongue_projects/<project>)")
    args = ap.parse_args()

    algos = PROJECT_SPECS[args.project]
    bundle = build_bundle(args.project, algos)

    out_dir = Path(args.out) if args.out else ROOT / "artifacts" / "cross_tongue_projects" / args.project
    bundle_path = write_bundle(bundle, out_dir)

    print_summary(bundle)
    print(f"\nbundle: {bundle_path}")
    return 0 if bundle["summary"]["all_green"] else 1


if __name__ == "__main__":
    sys.exit(main())
