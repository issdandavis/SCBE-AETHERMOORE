"""Exact reaction balancer — atom + charge conservation via rational nullspace.

The chemistry stack already *decomposes* a single compound (RDKit) but never
*balances* a multi-species reaction. This module fills that gap: given reactant
and product formulas it finds the smallest positive integer coefficients that
conserve every element and total charge, with ZERO model calls (the balance is
the exact-rational nullspace of the composition matrix — the same move as the
Mason backward solver), and emits a ``ReactionStatePacket`` receipt.

Stdlib-only (``fractions``), so it runs anywhere the reaction CLI runs. It is a
conservation/identity engine, not a thermodynamic-feasibility or kinetics claim;
those defer to real engines (Cantera, NASA CEA) at the middle layer.

Formula syntax: nested groups ``Ca(OH)2`` / ``[Fe(CN)6]``, hydrate dots
``CuSO4.5H2O``, and charge as ``SO4^2-`` / ``(2-)`` / a bare trailing ``+``/``-``
(= +/-1). Subscripts are counts; charge must be explicit (caret/paren/bare sign)
to stay unambiguous (``O2-`` = 2 oxygens, charge -1; write ``Ca^2+`` not ``Ca2+``).
"""

from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction
from math import gcd
from typing import List, Sequence, Tuple

from .reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    ReactionStatePacket,
    build_reaction_state_packet,
)


class BalanceError(ValueError):
    """Raised when a reaction cannot be uniquely balanced as written."""


# --------------------------------------------------------------------------- #
# Formula parsing
# --------------------------------------------------------------------------- #


def parse_formula(formula: str) -> Tuple[Counter, int]:
    """Parse a chemical formula into ``(element_counts, charge)`` (exact ints)."""
    body, charge = _split_charge(formula.strip())
    counts: Counter = Counter()
    for part in re.split(r"[.·]", body):
        if not part:
            continue
        mult = 1
        m = re.match(r"^(\d+)", part)
        if m:
            mult = int(m.group(1))
            part = part[m.end() :]
        for el, n in _parse_group(part).items():
            counts[el] += n * mult
    return counts, charge


def _split_charge(formula: str) -> Tuple[str, int]:
    m = re.search(r"\^(\d*)([+-])$", formula)  # ^2+, ^-, ^3-
    if m:
        mag = int(m.group(1)) if m.group(1) else 1
        return formula[: m.start()], mag if m.group(2) == "+" else -mag
    m = re.search(r"\((\d*)([+-])\)$", formula)  # (2-), (3+)
    if m:
        mag = int(m.group(1)) if m.group(1) else 1
        return formula[: m.start()], mag if m.group(2) == "+" else -mag
    m = re.search(r"([+-])$", formula)  # bare trailing sign => +/-1
    if m:
        return formula[: m.start()], 1 if m.group(1) == "+" else -1
    return formula, 0


def _parse_group(s: str) -> Counter:
    counts: Counter = Counter()
    stack: List[Counter] = [counts]
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "([":
            stack.append(Counter())
            i += 1
        elif c in ")]":
            i += 1
            m = re.match(r"\d+", s[i:])
            mult = int(m.group()) if m else 1
            if m:
                i += m.end()
            grp = stack.pop()
            for el, k in grp.items():
                stack[-1][el] += k * mult
        else:
            m = re.match(r"([A-Z][a-z]{0,2})(\d*)", s[i:])
            if not m:
                raise BalanceError(f"cannot parse formula fragment: {s[i:]!r}")
            el = m.group(1)
            k = int(m.group(2)) if m.group(2) else 1
            stack[-1][el] += k
            i += m.end()
    if len(stack) != 1:
        raise BalanceError(f"unbalanced parentheses in {s!r}")
    return counts


# --------------------------------------------------------------------------- #
# Balancing
# --------------------------------------------------------------------------- #


def is_conserved(
    reactants: Sequence[Tuple[int, str]],
    products: Sequence[Tuple[int, str]],
) -> Tuple[bool, dict]:
    """Return ``(ok, deltas)`` for a coefficiented reaction (atoms + charge)."""
    left: Counter = Counter()
    right: Counter = Counter()
    lq = rq = 0
    for coeff, f in reactants:
        comp, q = parse_formula(f)
        for el, k in comp.items():
            left[el] += coeff * k
        lq += coeff * q
    for coeff, f in products:
        comp, q = parse_formula(f)
        for el, k in comp.items():
            right[el] += coeff * k
        rq += coeff * q
    deltas = {el: right[el] - left[el] for el in set(left) | set(right) if right[el] - left[el] != 0}
    if lq != rq:
        deltas["charge"] = rq - lq
    return (not deltas), deltas


def balance(reactants: Sequence[str], products: Sequence[str]) -> List[int]:
    """Smallest positive integer coefficients conserving all atoms + charge.

    Zero model calls: the exact-rational nullspace of the composition matrix.
    Raises ``BalanceError`` if there is no unique positive balance as written.
    """
    species = list(reactants) + list(products)
    if len(species) < 2:
        raise BalanceError("need at least one reactant and one product")
    signs = [1] * len(reactants) + [-1] * len(products)
    comps = [parse_formula(f) for f in species]
    elements = sorted({el for comp, _ in comps for el in comp})
    rows: List[List[Fraction]] = []
    for el in elements:
        rows.append([Fraction(sign * comp.get(el, 0)) for (comp, _), sign in zip(comps, signs)])
    rows.append([Fraction(sign * q) for (_, q), sign in zip(comps, signs)])  # charge row
    null = _rational_nullspace(rows, len(species))
    if len(null) != 1:
        raise BalanceError(f"reaction has no unique balance (nullity={len(null)})")
    vec = null[0]
    lcm = 1
    for v in vec:
        lcm = lcm * v.denominator // gcd(lcm, v.denominator)
    ints = [int(v * lcm) for v in vec]
    g = 0
    for v in ints:
        g = gcd(g, abs(v))
    if g:
        ints = [v // g for v in ints]
    if all(v <= 0 for v in ints):
        ints = [-v for v in ints]
    if not all(v > 0 for v in ints):
        raise BalanceError(f"no positive balance with the given sides: {ints}")
    return ints


def _rational_nullspace(matrix: List[List[Fraction]], ncols: int) -> List[List[Fraction]]:
    M = [row[:] for row in matrix]
    nrows = len(M)
    pivots: List[int] = []
    r = 0
    for c in range(ncols):
        piv = next((rr for rr in range(r, nrows) if M[rr][c] != 0), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = M[r][c]
        M[r] = [x / inv for x in M[r]]
        for rr in range(nrows):
            if rr != r and M[rr][c] != 0:
                factor = M[rr][c]
                M[rr] = [a - factor * b for a, b in zip(M[rr], M[r])]
        pivots.append(c)
        r += 1
        if r == nrows:
            break
    free = [c for c in range(ncols) if c not in pivots]
    basis: List[List[Fraction]] = []
    for fc in free:
        vec = [Fraction(0)] * ncols
        vec[fc] = Fraction(1)
        for pr, pc in enumerate(pivots):
            vec[pc] = -M[pr][fc]
        basis.append(vec)
    return basis


def format_equation(coeffs: Sequence[int], reactants: Sequence[str], products: Sequence[str]) -> str:
    nr = len(reactants)

    def side(cs: Sequence[int], fs: Sequence[str]) -> str:
        return " + ".join((f if c == 1 else f"{c} {f}") for c, f in zip(cs, fs))

    return f"{side(coeffs[:nr], reactants)} -> {side(coeffs[nr:], products)}"


def balance_reaction_packet(reactants: Sequence[str], products: Sequence[str]) -> ReactionStatePacket:
    """Balance a reaction and wrap the result in a hash-signed ReactionStatePacket."""
    coeffs = balance(reactants, products)
    nr = len(reactants)
    equation = format_equation(coeffs, reactants, products)
    ok, deltas = is_conserved(list(zip(coeffs[:nr], reactants)), list(zip(coeffs[nr:], products)))
    return build_reaction_state_packet(
        domain="chem",
        step=1,
        bounded_operation="balance_reaction",
        source=ReactionEndpoint(
            identity=" + ".join(reactants),
            representation="reactant_formulas",
            language="chem",
            tongue="KO",
        ),
        target=ReactionEndpoint(
            identity=" + ".join(products),
            representation="product_formulas",
            language="chem",
            tongue="DR",
            metadata={"equation": equation, "coefficients": list(coeffs)},
        ),
        semantic_engravings=[
            f"balanced: {equation}",
            f"coefficients: {list(coeffs)}",
            "atom + charge conservation by exact rational nullspace",
        ],
        loss_notes=[] if ok else [f"not conserved: {deltas}"],
        recalculation=ReactionRecalculation(scientific_checks_ok=ok, identity_ok=ok),
        identity_preserved=ok,
        claim_boundary=[
            "exact atom + charge conservation (stoichiometry) only",
            "not a thermodynamic-feasibility, equilibrium, or kinetics claim",
        ],
    )
