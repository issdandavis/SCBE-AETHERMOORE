"""machine_crystal_pne_chem.py -- two capabilities ported into the canonical p/n/e cube.

The canonical machine_crystal_pne_cube validates GIVEN species. These two add the front end it
lacked (proven first in the dev scratch C:\\dev\\chem_crystal.py, ported here, collision-safe):

  * balance(skeleton)         -- solve conservation for the coefficients:
                                 "C3H8 + O2 -> CO2 + H2O" -> "C3H8 + 5 O2 -> 3 CO2 + 4 H2O".
                                 The cube checks balance; this FINDS it. Backed by the vendored
                                 particle_chem (Issac's conservation solver).
  * valence_feasible(formula) -- structural sanity gate: rejects atom-balanced-but-impossible
                                 compounds (NaCl3) via standard valences + graph realizability.
                                 HONEST: this is a HEURISTIC, not a conservation law -- it would
                                 over-reject genuine hypervalent main-group (ClF3, SF6). Use it as
                                 a sanity rung BELOW the exact atom/charge conservation gate, never
                                 as ground truth.

Wire-in when ready:  from python.scbe.machine_crystal_pne_chem import balance, valence_feasible
Run self-test:       python -m python.scbe.machine_crystal_pne_chem
"""
from __future__ import annotations

from itertools import product as _product

from python.scbe import particle_chem as pc


def balance(skeleton: str):
    """Balance a reaction skeleton by conservation. Returns (balanced_str_or_None, message)."""
    return pc.balance(skeleton)


# standard valences: main group = the single common valence; variable metals = a set
_VALENCE = {
    "H": {1}, "O": {2}, "C": {4}, "N": {3}, "F": {1}, "Cl": {1}, "Br": {1}, "I": {1},
    "Na": {1}, "K": {1}, "Li": {1}, "Ca": {2}, "Mg": {2}, "S": {2}, "P": {3},
    "Fe": {2, 3}, "Mn": {2, 3, 4, 6, 7}, "Cu": {1, 2}, "Zn": {2}, "Al": {3},
}


def valence_feasible(formula: str):
    """(ok, reason). ok iff a connected molecule is graph-realizable under standard valences:
    sum(valence) even, >= 2*(natoms-1), and no atom needs more bonds than all others combined.
    Single atoms/ions are trivially ok; unknown-valence elements are not checked (returns ok)."""
    comp, _charge = pc.parse_formula(formula)
    items = list(comp.items())
    natoms = sum(c for _, c in items)
    if natoms <= 1:
        return True, "single atom"
    opts = []
    for el, _ in items:
        if el not in _VALENCE:
            return True, f"{el} valence unknown (not checked)"
        opts.append(sorted(_VALENCE[el]))
    for combo in _product(*opts):
        endpoints = sum(v * c for v, (_, c) in zip(combo, items))
        if endpoints % 2:
            continue
        if endpoints < 2 * (natoms - 1):
            continue
        if any(2 * v > endpoints for v in combo):
            continue
        return True, "ok"
    return False, "no connected structure under standard valences"


def _selftest() -> int:
    checks = [
        ("balance combustion", balance("C3H8 + O2 -> CO2 + H2O")[0] == "C3H8 + 5 O2 -> 3 CO2 + 4 H2O"),
        ("balance redox", balance("KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2")[0]
         == "2 KMnO4 + 16 HCl -> 2 KCl + 2 MnCl2 + 8 H2O + 5 Cl2"),
        ("valence passes NaCl", valence_feasible("NaCl")[0] is True),
        ("valence passes C3H8", valence_feasible("C3H8")[0] is True),
        ("valence rejects NaCl3", valence_feasible("NaCl3")[0] is False),
    ]
    ok = True
    print("=== machine_crystal_pne_chem self-test ===")
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    print("ported: balance (skeleton -> coefficients) + valence_feasible (structural sanity rung)")
    print("ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
