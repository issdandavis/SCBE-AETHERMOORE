"""verify_eml_identities: re-run the load-bearing EML / T-cell math as an executable regression.

Encodes the findings of docs/research/eml_t_verification_findings.md so they carry their own receipts:
the binary EML(x, y) = exp(x) - ln(y), with the constant 1, is a real single-binary-operator basis for the
scientific-calculator elementary functions (Odrzywolek, arXiv:2603.21852). This checks, by execution:

  * the 7 load-bearing identities (doc S3) HOLD;
  * the POPULAR log form `eml(eml(1,x),1)` is WRONG -- it equals `e^e / x`, NOT `log x` (doc S2); the
    paper-correct identity has one more outer wrap: `log x = eml(1, eml(eml(1,x),1))`;
  * the ternary "T-cell" Sheffer claim is REFUTED (doc S4): T(x,x,x)=1 is the trivial diagonal, T(1,.,.) is
    singular (ln 1 = 0), and the depth-1 closure of T cannot place a subtraction at the top level, so it
    cannot reconstruct EML (the outer-subtraction lemma).

Precision: stdlib cmath (double) -- the doc's mpmath run gives ~1e-51, here residuals are ~1e-12, which is
exactly what double precision allows; the qualitative conclusions are identical. HONEST SCOPE: this verifies
the MATH findings only; it does NOT endorse the TENG-memristor / HYDRA / atomic-tokenizer extensions, which
the doc explicitly marks unsupported (they hung on T being sound, and T is not).
"""

from __future__ import annotations

import cmath
import math
from typing import Any, Dict

E = math.e


def eml(x: Any, y: Any) -> complex:
    """The paper's single binary operator: exp(x) - ln(y) (principal log)."""
    return cmath.exp(x) - cmath.log(y)


def t_cell(x: Any, y: Any, z: Any) -> complex:
    """The refuted ternary extension: (e^x / ln x) * (ln z / e^y)."""
    return (cmath.exp(x) / cmath.log(x)) * (cmath.log(z) / cmath.exp(y))


def _res(a: Any, b: Any) -> float:
    return abs(complex(a) - complex(b))


def identities_max_residual() -> float:
    """Max residual over the 7 load-bearing identities (doc S3.1-S3.7). ~0 in exact math; ~1e-12 in double."""
    r = []
    for x in (0.5, -3, 17.25, complex(1.2, 0.7)):  # 3.1  eml(x,1) = exp x
        r.append(_res(eml(x, 1), cmath.exp(x)))
    r.append(_res(eml(1, 1), E))  # 3.2  eml(1,1) = e
    for x, y in ((0.7, -2.4), (complex(1, 0.3), complex(-0.5, 1.2))):  # 3.3  eml(x, exp y) = exp x - y
        r.append(_res(eml(x, cmath.exp(y)), cmath.exp(x) - y))
    for x in (0.3, 1.7, -2.5):  # 3.4  sin
        r.append(_res((eml(1j * x, 1) - eml(-1j * x, 1)) / (2j), cmath.sin(x)))
    for x in (0.3, 1.7, -2.5):  # 3.5  cos
        r.append(_res((eml(1j * x, 1) + eml(-1j * x, 1)) / 2, cmath.cos(x)))
    r.append(abs(-(eml(0, -1).imag) - math.pi))  # 3.6  pi = -Im(eml(0,-1))
    for x in (0.5, 2, 100, 1234.5, complex(1, 1), complex(5, -2)):  # 3.7  log x = eml(1, eml(eml(1,x),1))
        r.append(_res(eml(1, eml(eml(1, x), 1)), cmath.log(x)))
    return max(r)


def popular_log_is_eexp_over_x() -> Dict[float, Dict[str, float]]:
    """Doc S2: eml(eml(1,x),1) is e^e/x, NOT log x. Returns each x's residual vs each candidate."""
    out = {}
    for x in (2.0, 7.3, 0.41):
        lhs = eml(eml(1, x), 1)
        out[x] = {"vs_eexp_over_x": _res(lhs, cmath.exp(E) / x), "vs_log_x": _res(lhs, cmath.log(x))}
    return out


def t_diagonal_is_one() -> float:
    """Doc S4.1: T(x,x,x) = 1 (the trivial diagonal). Returns max residual."""
    return max(_res(t_cell(x, x, x), 1) for x in (2, 3.7, 0.4, 17, complex(1.2, 0.5)))


def t_seed_is_singular() -> bool:
    """Doc S4.2: T(1,.,.) is undefined -- ln 1 = 0, so the operator cannot consume the EML seed 1."""
    try:
        t_cell(1, 2, 3)
        return False
    except ZeroDivisionError:
        return True


def t_depth1_cannot_make_eml(a: float = 2.7, b: float = 5.1) -> float:
    """Doc S4.3 (outer-subtraction lemma): none of the 8 depth-1 T outputs equals eml(a,a) -- T cannot place
    a subtraction at the top level, so a single application cannot reconstruct EML. Returns the MIN residual
    to eml(a,a) (large -> unreachable)."""
    outs = [t_cell(p, q, r) for p in (a, b) for q in (a, b) for r in (a, b)]
    target = eml(a, a)
    return min(_res(o, target) for o in outs)


def verdict() -> Dict[str, Any]:
    pop = popular_log_is_eexp_over_x()
    return {
        "identities_hold": identities_max_residual() < 1e-9,
        "popular_log_is_eexp_over_x": all(v["vs_eexp_over_x"] < 1e-9 < v["vs_log_x"] for v in pop.values()),
        "t_diagonal_is_one": t_diagonal_is_one() < 1e-9,
        "t_seed_singular": t_seed_is_singular(),
        "t_cannot_reconstruct_eml": t_depth1_cannot_make_eml() > 1.0,
        "max_identity_residual": identities_max_residual(),
    }


def main() -> int:
    v = verdict()
    print("EML / T-cell verification (findings -> executable receipts)")
    print(
        "  7 EML identities hold        : %s  (max residual %.2e)" % (v["identities_hold"], v["max_identity_residual"])
    )
    print("  popular log form is e^e/x    : %s  (NOT log x)" % v["popular_log_is_eexp_over_x"])
    print("  T(x,x,x) = 1 (trivial)       : %s" % v["t_diagonal_is_one"])
    print("  T(1,.,.) singular (ln 1 = 0) : %s" % v["t_seed_singular"])
    print("  T cannot reconstruct EML     : %s  (refutes the ternary Sheffer claim)" % v["t_cannot_reconstruct_eml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
