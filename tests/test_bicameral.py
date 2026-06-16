"""Bicameral cognition — logic vs intuition hemispheres, reconciled."""
import random

import pytest

from python.scbe import bicameral as B
from python.scbe import polyglot as P


def _exec(prog):
    ns = {}
    exec(compile(P.emit(prog, "python", safe=True), "p.py", "exec"), ns)  # noqa: S102
    return ns["tongue_fn"](2.0, 3.0, 4.0)


@pytest.mark.parametrize("seed", range(30))
def test_logic_hemisphere_matches_the_real_python_face(seed):
    rng = random.Random(seed)
    ops = sorted(P.SCALAR_OPS)
    # build a stack-valid program so it doesn't underflow
    prog, depth = [], 3
    for _ in range(rng.randint(1, 10)):
        if depth >= 2 and rng.random() < 0.6:
            prog.append(rng.choice([o for o in ops if o in B.EXACT and B.EXACT[o][0] == 2])); depth -= 1
        else:
            prog.append(rng.choice([o for o in ops if B.EXACT[o][0] == 1]))
        depth = max(depth, 1)
    bytes_ = P.program_bytes(*prog)
    try:
        expected = _exec(bytes_)
    except Exception:
        pytest.skip("python face raised on this program")
    assert abs(B.logic(bytes_) - expected) < 1e-9          # exact hemisphere == real face


def test_linear_program_is_intuitive():
    t = B.think(P.program_bytes("add", "mul", "inc"))
    assert t["relation"] == "exact match"
    assert t["confidence"] == 1.0 and t["nonlinear_ops"] == []


def test_sqrt_diverges_and_localizes():
    t = B.think(P.program_bytes("add", "sqrt", "mul"))
    assert "sqrt" in t["nonlinear_ops"]
    assert t["relation"] in ("close", "diverged", "sign flip")
    assert "sqrt" in t["interpretation"]


def test_pow_is_fudged_to_multiply():
    # stack is [2,3,4]; pow uses top two (a=3,b=4): logic 3**4=81, intuition 3*4=12
    prog = P.program_bytes("pow")
    assert B.logic(prog) == 81.0
    guess, nl = B.intuition(prog)
    assert guess == 12.0 and "pow" in nl


def test_incomplete_program_reconciles_to_incomplete():
    t = B.think(P.program_bytes("add", "add", "add"))   # underflows the 3-deep stack
    assert t["relation"] == "incomplete" and t["confidence"] == 0.0


def test_render_has_both_hemispheres():
    out = B.render(P.program_bytes("add", "sqrt"))
    assert "logic" in out and "intuition" in out and "relation" in out and "->" in out
