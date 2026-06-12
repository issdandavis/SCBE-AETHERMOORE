#!/usr/bin/env python3
"""mason_solve — derive a stone's chisel-fills BACKWARD from the verifier.

The smaller the model, the smaller its decision must be. A stone's BODY is
pre-synthesized structure no one can bisect (inverting "passes all asserts" over
arbitrary code is program synthesis — the wall). But a stone's chisel-FILLS are
scalars and literals of a known FORM, and the resident's request already names
the answer it wants. So for the fill part we do not ASK a model to generate; we
SOLVE backward from the request — the answer whose form we know:

  1. invert  — read the template for `SYMBOL = __H_HOLE__`, then read the request
               for `assert SYMBOL == literal` and pin the hole (read-off), or for
               `SYMBOL >= literal` and BINARY-SEARCH the integer against the real
               verifier (a genuine reverse search, log-step convergence).
  2. harvest — for fills the request constrains only behaviourally (operator
               sets, precedence tables, coordinate lists), harvest candidate
               literals straight from the request text — the verifier already
               contains the numbers and tokens it checks against — then CONFIRM
               each candidate by real execution in place. The oracle disambiguates.
  3. residue — what neither pins nor harvests-and-confirms is the irreducible
               part. Hand THAT (and usually only that — the stone choice) to a model.

Every "solved" fill is confirmed by the same real-execution verifier the mason
uses to seal a stone; nothing is trusted because it parsed. Deterministic,
model-free, and honest about what it cannot solve.

Run:
  python scripts/tools/mason_solve.py calc_core [--json]
  python scripts/tools/mason_solve.py --all
"""

from __future__ import annotations

import argparse
import ast
import itertools
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mason  # noqa: E402

# Bounds keep the joint search honest: a fill we cannot solve cheaply is RESIDUE,
# not an excuse to brute-force forever.
MAX_CANDIDATES_PER_HOLE = 16
MAX_JOINT_COMBOS = 8000
BISECT_HI = 1 << 24


def hole_symbols(piece: mason.Piece) -> dict[str, str]:
    """Map each chisel-hole to the variable symbol its template assigns it to.

    Finds lines of the form `SYMBOL = ... __H_HOLE__ ...` so an `assert SYMBOL ==`
    in the request can be traced back to the hole that controls it.
    """
    out: dict[str, str] = {}
    for hole in piece.holes:
        pat = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*.*__H_" + re.escape(hole) + r"__", re.M)
        m = pat.search(piece.template)
        if m:
            out[hole] = m.group(1)
    return out


def pin_from_request(symbol: str, acceptance: str) -> tuple[str, object] | None:
    """If the request compares `symbol` to a literal, return (op, literal).

    op is 'eq' (read-off), 'ge', or 'le' (binary-searchable). None if the request
    never constrains the symbol directly.
    """
    try:
        tree = ast.parse(acceptance)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == symbol):
            continue
        op = node.ops[0]
        try:
            val = ast.literal_eval(node.comparators[0])
        except Exception:
            continue
        if isinstance(op, ast.Eq):
            return ("eq", val)
        if isinstance(op, (ast.GtE, ast.Gt)):
            return ("ge", val)
        if isinstance(op, (ast.LtE, ast.Lt)):
            return ("le", val)
    return None


def harvest(acceptance: str) -> tuple[list[int], list[object], str]:
    """Pull candidate literals out of the request: ints, collections, op-chars.

    The verifier text is the answer's neighbourhood — the integers it checks, the
    token lists it expects, the single-char operators inside those lists. We grab
    them as candidates and let real execution confirm which are right.
    """
    ints: set[int] = set()
    colls: list[object] = []
    chars: set[str] = set()
    seen: list[str] = []
    try:
        tree = ast.parse(acceptance)
    except SyntaxError:
        return [], [], ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                ints.add(v)
            elif isinstance(v, str) and len(v) == 1 and not v.isalnum() and not v.isspace():
                chars.add(v)
        elif isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
            try:
                val = ast.literal_eval(node)
            except Exception:
                continue
            key = repr(val)
            if key not in seen:
                seen.append(key)
                colls.append(val)
    return sorted(ints), colls, "".join(sorted(chars))


def _prec_tables(ops: str) -> list[str]:
    """Canonical precedence tables over the harvested operators (residue case).

    Pure inversion can't read a precedence dict out of the request — it's implied
    by RPN orderings, not written. So we offer the small canonical space and let
    the verifier confirm the one that reproduces every ordering.
    """
    arith = [c for c in ops if c in "+-*/%^"]
    if not arith:
        return []
    high = set("*/%^")
    std = {c: (2 if c in high else 1) for c in arith}
    flat = {c: 1 for c in arith}
    return [repr(std), repr(flat)]


def candidates_for(hole: str, piece: mason.Piece, acceptance: str, ints: list[int], colls: list[object], ops: str):
    """Ordered candidate FILL-strings for one hole, most-likely first.

    A fill is whatever str()'s into valid source at the hole: an int, a bare
    collection literal (repr), or a char-run that sits inside the template quotes.
    """
    out: list[object] = []
    # collection-shaped fills first (repr -> valid list/tuple/dict source)
    for c in colls:
        out.append(repr(c))
    # the harvested operator run, for holes used inside quotes like set('__H__')
    if ops:
        out.append(ops)
    # canonical precedence tables for dict-shaped holes
    out.extend(_prec_tables(ops))
    # integers
    out.extend(ints)
    # de-dup, preserve order, cap
    seen: set[str] = set()
    uniq: list[object] = []
    for c in out:
        k = repr(c)
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq[:MAX_CANDIDATES_PER_HOLE]


def bisect_int(piece, placed, acceptance, hole, other_fills, sense, lo=0, hi=BISECT_HI):
    """Smallest int for `hole` that makes the request pass, by binary search.

    Honors `SYMBOL >= literal`-style monotone constraints: the verifier is the
    oracle, the bisection converges in ~log2(hi) real executions. sense='ge'
    searches for the least passing value; 'le' the greatest.
    """

    def passes(val: int) -> bool:
        fills = dict(other_fills)
        fills[hole] = val
        try:
            chiseled = piece.chisel(fills)
        except Exception:
            return False
        code = "\n\n".join(placed + [chiseled])
        ok, _ = mason._verify(code, acceptance)
        return ok

    if sense == "le":
        # mirror: find greatest passing by bisecting the negated predicate
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if passes(mid):
                best, lo = mid, mid + 1
            else:
                hi = mid - 1
        return best
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if passes(mid):
            best, hi = mid, mid - 1
        else:
            lo = mid + 1
    return best


def solve_slot(slot: mason.Slot, piece: mason.Piece, placed: list[str]) -> dict:
    """Solve every chisel-fill for one slot backward from its request.

    Returns the solved fills, the method each hole took (invert/bisect/harvest/
    canonical), whether the slot's acceptance passes in place, and any residue.
    """
    holes = list(piece.holes)
    method: dict[str, str] = {}
    if not holes:
        ok, detail = mason._verify("\n\n".join(placed + [piece.chisel({})]), slot.acceptance)
        return {"fills": {}, "method": {}, "solved": ok, "detail": detail, "residue": []}

    symbols = hole_symbols(piece)
    ints, colls, ops = harvest(slot.acceptance)

    pinned: dict[str, object] = {}
    free: list[str] = []
    for hole in holes:
        sym = symbols.get(hole)
        pin = pin_from_request(sym, slot.acceptance) if sym else None
        if pin and pin[0] == "eq":
            pinned[hole] = pin[1]
            method[hole] = f"invert(=={pin[1]!r})"
        elif pin and pin[0] in ("ge", "le"):
            val = bisect_int(
                piece, placed, slot.acceptance, hole, {h: pinned.get(h, 1) for h in holes if h != hole}, pin[0]
            )
            if val is not None:
                pinned[hole] = val
                method[hole] = f"bisect({pin[0]}{pin[1]!r})->{val}"
            else:
                free.append(hole)
        else:
            free.append(hole)

    # joint search over whatever invert/bisect did not pin: harvested + canonical,
    # confirmed by real execution. Pinned holes contribute a single value.
    cand_lists = []
    for hole in holes:
        if hole in pinned:
            cand_lists.append([pinned[hole]])
        else:
            cand_lists.append(candidates_for(hole, piece, slot.acceptance, ints, colls, ops))

    combos = 1
    for cl in cand_lists:
        combos *= max(1, len(cl))
    if combos > MAX_JOINT_COMBOS:
        return {
            "fills": {},
            "method": method,
            "solved": False,
            "detail": f"search too large ({combos} combos)",
            "residue": free,
        }

    last = ""
    for choice in itertools.product(*cand_lists):
        fills = dict(zip(holes, choice))
        try:
            chiseled = piece.chisel(fills)
        except Exception as exc:
            last = f"chisel: {exc}"
            continue
        ok, detail = mason._verify("\n\n".join(placed + [chiseled]), slot.acceptance)
        last = detail
        if ok:
            for hole in free:
                method.setdefault(hole, "harvest+confirm")
            return {"fills": fills, "method": method, "solved": True, "detail": "", "residue": []}
    return {"fills": {}, "method": method, "solved": False, "detail": last, "residue": free or holes}


def solve_build(schematic: mason.Schematic, pieces: dict) -> dict:
    """Build a schematic with every fill solved backward — the model never gives a fill.

    Mirrors mason.build's verify-in-place flow, but the chisel values come from the
    solver, not the pack's declared `fills`. A slot the solver cannot crack is
    reported as residue and halts (honest: that fill is the model's job).
    """
    placed: list[str] = []
    log: list[dict] = []
    for slot in schematic.slots:
        piece = pieces[slot.piece]
        res = solve_slot(slot, piece, placed)
        row = {
            "slot": slot.name,
            "stone": piece.name,
            "solved": res["solved"],
            "fills": res["fills"],
            "method": res["method"],
        }
        if res["solved"]:
            placed.append(piece.chisel(res["fills"]))
            log.append(row)
        else:
            row["residue"] = res["residue"]
            row["detail"] = res["detail"]
            log.append(row)
            return {
                "schema_version": "scbe_mason_solve_v1",
                "schematic": schematic.name,
                "slots_solved": sum(1 for r in log if r["solved"]),
                "slots_total": len(schematic.slots),
                "town_complete": False,
                "halted_at": slot.name,
                "log": log,
            }

    ok, detail = mason._verify("\n\n".join(placed).rstrip("\n"), schematic.integration)
    return {
        "schema_version": "scbe_mason_solve_v1",
        "schematic": schematic.name,
        "slots_solved": sum(1 for r in log if r["solved"]),
        "slots_total": len(schematic.slots),
        "town_complete": ok,
        "integration_detail": "" if ok else detail,
        "log": log,
    }


def _print_human(result: dict) -> None:
    print(f"=== mason_solve · solving '{result['schematic']}' backward from the verifier ===\n")
    for row in result["log"]:
        if row["solved"]:
            methods = ", ".join(f"{h}:{m}" for h, m in row["method"].items()) or "(no holes)"
            print(f"  solved {row['slot']:10s} <- {row['stone']:14s}  {methods}")
            if row["fills"]:
                print(f"         fills {row['fills']}")
        else:
            print(f"  RESIDUE {row['slot']:10s} <- {row['stone']:14s}  hand to model: {row.get('residue')}")
            print(f"          {row.get('detail', '')}")
    print()
    if result["town_complete"]:
        n, total = result["slots_solved"], result["slots_total"]
        print(f"  SOLVED BACKWARD — {n}/{total} fills derived, model never asked; integration passed")
    else:
        print(f"  HALTED — {result['slots_solved']}/{result['slots_total']} slots solved backward")
        if result.get("halted_at"):
            print(f"  residue at '{result['halted_at']}' is the model's job (the irreducible part)")
        elif result.get("integration_detail"):
            print(f"  integration failed: {result['integration_detail']}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="mason_solve", description="Solve stone chisel-fills backward from the verifier.")
    ap.add_argument("schematic", nargs="?", help="schematic to solve (default: all)")
    ap.add_argument("--all", action="store_true", help="solve every registered schematic")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    names = sorted(mason.REGISTRY) if (args.all or not args.schematic) else [args.schematic]
    results = []
    for name in names:
        if name not in mason.REGISTRY:
            print(f"unknown schematic: {name}", file=sys.stderr)
            return 2
        schematic, pieces, _ = mason.REGISTRY[name]
        results.append(solve_build(schematic, pieces))

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], indent=2))
    else:
        for r in results:
            _print_human(r)
            print()
    return 0 if all(r["town_complete"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
