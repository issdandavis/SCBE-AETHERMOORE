"""particle_chem -- a chemistry substrate where the AI CANNOT write a wrong reaction.

The thesis (Issac's): an AI lives in tokens and can't perceive an electron. So you give it a
symbolic substrate that encodes chemistry's REAL invariants and ENFORCES them -- conservation
isn't a fact to remember, it's a rule the substrate rejects violations of. That rejection IS depth.

This is particle accounting, the honest version:
  * protons  -> which element (proton count == atomic number Z). Conserved <=> atoms conserved.
  * electrons-> charge (electrons = protons - charge). Conserved <=> charge conserved.
  * a reaction is a rearrangement that MUST conserve every element and total charge.

What it does, all stdlib-only, no fabrication:
  - parse a formula (with parens + charge): "Ca(OH)2", "SO4^2-", "C3H8"
  - build a Species and read its protons / electrons / charge
  - VERIFY a reaction: per-element + charge ledger; PASS only if everything balances, else REJECT
    with exactly what's off and by how much
  - BALANCE a skeleton ("C3H8 + O2 -> CO2 + H2O") by solving the conservation constraints
  - track electron transfer in redox (who loses/gains electrons)
"""

from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from math import gcd
from typing import Dict, List, Optional, Tuple

# proton count (Z) -- which element a nucleus IS. (common subset; unknown element -> honest error)
PERIODIC: Dict[str, int] = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18, "K": 19, "Ca": 20,
    "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30,
    "Ga": 31, "Ge": 32, "As": 33, "Se": 34, "Br": 35, "Kr": 36, "Ag": 47, "Sn": 50, "I": 53, "Ba": 56,
    "Pt": 78, "Au": 79, "Hg": 80, "Pb": 82, "U": 92,
}


# ---- formula parsing (element counts + charge), supports parens ----------
def _parse_group(s: str) -> Counter:
    counts: Counter = Counter()
    i = 0
    while i < len(s):
        if s[i] == "(":
            depth, j = 1, i + 1
            while j < len(s) and depth > 0:
                depth += (s[j] == "(") - (s[j] == ")")
                j += 1
            inner = s[i + 1 : j - 1]
            k, num = j, ""
            while k < len(s) and s[k].isdigit():
                num += s[k]; k += 1
            mult = int(num) if num else 1
            for el, c in _parse_group(inner).items():
                counts[el] += c * mult
            i = k
        else:
            m = re.match(r"([A-Z][a-z]?)(\d*)", s[i:])
            if not m or not m.group(1):
                raise ValueError("bad formula near %r" % s[i:])
            el = m.group(1)
            if el not in PERIODIC:
                raise ValueError("unknown element %r (add its proton count to PERIODIC)" % el)
            counts[el] += int(m.group(2)) if m.group(2) else 1
            i += m.end()
    return counts


def parse_formula(s: str) -> Tuple[Counter, int]:
    s = s.strip()
    charge = 0
    m = re.search(r"\^?(\d*)([+-])$", s)
    if m and (m.group(1) or m.group(2)):
        mag = int(m.group(1)) if m.group(1) else 1
        charge = mag if m.group(2) == "+" else -mag
        s = s[: m.start()]
    return _parse_group(s), charge


@dataclass
class Species:
    formula: str
    composition: Counter
    charge: int

    @property
    def protons(self) -> int:
        return sum(PERIODIC[el] * c for el, c in self.composition.items())

    @property
    def electrons(self) -> int:
        return self.protons - self.charge  # electrons removed = positive charge


def species(s: str) -> Species:
    comp, ch = parse_formula(s)
    return Species(s, comp, ch)


# ---- reaction parsing ----------------------------------------------------
def _parse_side(side: str) -> List[Tuple[int, str]]:
    terms = []
    for part in re.split(r"\s+\+\s+", side.strip()):  # split on " + " so charge '+' survives
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(\d+)\s+(.+)", part)
        if m:
            terms.append((int(m.group(1)), m.group(2).strip()))
        else:
            terms.append((1, part))
    return terms


def parse_reaction(s: str) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
    left, right = re.split(r"->|=>|=", s, maxsplit=1)
    return _parse_side(left), _parse_side(right)


# ---- the VERIFIER: conservation ledger, reject fakes ---------------------
def verify(reaction: str) -> Dict:
    L, R = parse_reaction(reaction)

    def tally(side):
        el, charge = Counter(), 0
        for coeff, f in side:
            sp = species(f)
            for e, c in sp.composition.items():
                el[e] += coeff * c
            charge += coeff * sp.charge
        return el, charge

    le, lc = tally(L)
    re_, rc = tally(R)
    elements = sorted(set(le) | set(re_))
    ledger = [(e, le[e], re_[e], le[e] - re_[e]) for e in elements]
    atoms_ok = all(d == 0 for *_, d in ledger)
    charge_ok = lc == rc
    return {
        "balanced": atoms_ok and charge_ok,
        "ledger": ledger,            # (element, left_atoms, right_atoms, diff)  -- protons conserved per element
        "charge": (lc, rc),          # electrons conserved <=> charge conserved
        "atoms_ok": atoms_ok,
        "charge_ok": charge_ok,
    }


# ---- the BALANCER: solve conservation for integer coefficients ----------
def _nullspace(M: List[List[Fraction]]) -> Optional[List[Fraction]]:
    rows, cols = len(M), len(M[0]) if M else 0
    A = [r[:] for r in M]
    pivots: Dict[int, int] = {}
    r = 0
    for c in range(cols):
        piv = next((rr for rr in range(r, rows) if A[rr][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        pv = A[r][c]
        A[r] = [x / pv for x in A[r]]
        for rr in range(rows):
            if rr != r and A[rr][c] != 0:
                f = A[rr][c]
                A[rr] = [a - f * b for a, b in zip(A[rr], A[r])]
        pivots[c] = r
        r += 1
    free = [c for c in range(cols) if c not in pivots]
    if not free:
        return None
    fc = free[0]
    x = [Fraction(0)] * cols
    x[fc] = Fraction(1)
    for c, rr in pivots.items():
        x[c] = -A[rr][fc]
    return x


def balance(skeleton: str) -> Tuple[Optional[str], str]:
    L, R = parse_reaction(skeleton)
    forms = [f for _, f in L] + [f for _, f in R]
    nL = len(L)
    objs = [species(f) for f in forms]
    elements = sorted(set().union(*[set(o.composition) for o in objs]))
    M: List[List[Fraction]] = []
    for e in elements:
        M.append([Fraction(o.composition.get(e, 0) * (1 if i < nL else -1)) for i, o in enumerate(objs)])
    M.append([Fraction(o.charge * (1 if i < nL else -1)) for i, o in enumerate(objs)])  # charge row
    x = _nullspace(M)
    if x is None:
        return None, "no free coefficient (already determined or inconsistent)"
    lcm = 1
    for v in x:
        lcm = lcm * v.denominator // gcd(lcm, v.denominator)
    ints = [int(v * lcm) for v in x]
    g = 0
    for v in ints:
        g = gcd(g, abs(v))
    if g:
        ints = [v // g for v in ints]
    if all(v < 0 for v in ints):
        ints = [-v for v in ints]
    if any(v <= 0 for v in ints):
        return None, "ambiguous skeleton (needs more constraints)"

    def fmt(coeffs, terms):
        return " + ".join((f"{c} " if c != 1 else "") + f for c, (_, f) in zip(coeffs, terms))

    balanced = fmt(ints[:nL], L) + " -> " + fmt(ints[nL:], R)
    return balanced, "coeffs " + str(ints)


# ---- demo ----------------------------------------------------------------
def _show(reaction: str):
    v = verify(reaction)
    mark = "PASS  (conserved)" if v["balanced"] else "REJECT (NOT conserved)"
    print("  %-40s -> %s" % (reaction, mark))
    if not v["balanced"]:
        for e, l, r, d in v["ledger"]:
            if d != 0:
                print("      element %s: left=%d right=%d  OFF BY %+d" % (e, l, r, d))
        if not v["charge_ok"]:
            print("      charge: left=%+d right=%+d  NOT conserved" % v["charge"])


if __name__ == "__main__":
    print("=== BALANCER: solve conservation for the coefficients ===")
    for sk in ["C3H8 + O2 -> CO2 + H2O", "H2 + O2 -> H2O", "Fe + O2 -> Fe2O3", "Al + HCl -> AlCl3 + H2"]:
        b, info = balance(sk)
        print("  %-30s =>  %s" % (sk, b or ("(can't: " + info + ")")))

    print("\n=== VERIFIER: real reactions PASS, fakes get REJECTED ===")
    _show("C3H8 + 5 O2 -> 3 CO2 + 4 H2O")   # balanced combustion
    _show("H2 + O2 -> H2O")                  # fake: oxygen not conserved
    _show("2 Na + Cl2 -> 2 NaCl")            # balanced
    _show("C + O2 -> CO2 + H2O")             # fake: hydrogen appears from nothing

    print("\n=== CHARGE / electron transfer (redox) ===")
    _show("Fe + Cu^2+ -> Fe^2+ + Cu")        # balanced redox (2 electrons transferred)
    _show("Fe + Cu^2+ -> Fe^3+ + Cu")        # fake: charge not conserved
    print("\n  particle ledger for Fe + Cu^2+ -> Fe^2+ + Cu:")
    for f in ["Fe", "Cu^2+", "Fe^2+", "Cu"]:
        sp = species(f)
        print("    %-6s protons=%-3d electrons=%-3d charge=%+d" % (f, sp.protons, sp.electrons, sp.charge))
