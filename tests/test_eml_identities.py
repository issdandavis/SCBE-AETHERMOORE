"""EML / T-cell math findings as an executable regression (docs/research/eml_t_verification_findings.md).

These re-run the load-bearing math: the 7 EML identities hold, the popular log form is WRONG (= e^e/x, not
log x), and the ternary T extension is refuted on its own three grounds. Verify-by-execution -- the doc's
claims carry their own receipts, and a future edit that breaks the math (or revives the broken T claim) fails.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research" / "eml_simulator" / "verify_eml_identities.py"


def _mod():
    spec = importlib.util.spec_from_file_location("_eml_test", MODULE_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_seven_eml_identities_hold():
    m = _mod()
    assert m.identities_max_residual() < 1e-9  # all 7 hold to double precision


def test_popular_log_form_is_wrong_it_is_eexp_over_x():
    m = _mod()
    pop = m.popular_log_is_eexp_over_x()
    for x, r in pop.items():
        assert r["vs_eexp_over_x"] < 1e-9, x  # eml(eml(1,x),1) == e^e/x
        assert r["vs_log_x"] > 1e-3, x  # and it is NOT log x


def test_paper_correct_log_identity_holds():
    m = _mod()
    import cmath

    for x in (0.5, 2, 100, complex(1, 1)):
        assert abs(m.eml(1, m.eml(m.eml(1, x), 1)) - cmath.log(x)) < 1e-9  # log x = eml(1, eml(eml(1,x),1))


def test_t_diagonal_is_the_trivial_one():
    m = _mod()
    assert m.t_diagonal_is_one() < 1e-9  # T(x,x,x) = 1


def test_t_cannot_consume_the_seed_one():
    m = _mod()
    assert m.t_seed_is_singular() is True  # T(1,.,.) singular: ln 1 = 0


def test_t_cannot_reconstruct_eml_outer_subtraction_lemma():
    m = _mod()
    # none of the 8 depth-1 T outputs comes near eml(a,a) -- T can't place a subtraction at the top level
    assert m.t_depth1_cannot_make_eml() > 1.0


def test_overall_verdict():
    m = _mod()
    v = m.verdict()
    assert v["identities_hold"] and v["popular_log_is_eexp_over_x"]
    assert v["t_diagonal_is_one"] and v["t_seed_singular"] and v["t_cannot_reconstruct_eml"]
