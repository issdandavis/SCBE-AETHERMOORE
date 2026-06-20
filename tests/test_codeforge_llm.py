"""The LLM build executor: an AI proposes a Loom program, the machine verifies it.

Uses fake `ask` functions (no live model) so the AI-proposes / machine-verifies
loop is fully testable — including a wrong program and a looping program both
being caught rather than shipped.
"""

from python.codeforge import forge, make_llm_build_executor

GOOD_ADDER = """```loom
L: dec r1 D
   inc r3
   jmp L
D: dec r2 E
   inc r3
   jmp D
E: out r3
   halt
```"""

# off by one: an extra `inc r3` before out -> outputs r1 + r2 + 1
WRONG_ADDER = """```loom
L: dec r1 D
   inc r3
   jmp L
D: dec r2 E
   inc r3
   jmp D
E: inc r3
   out r3
   halt
```"""

LOOPING = "```loom\nspin: jmp spin\n```"  # never halts, never outputs

GARBAGE = "I'm sorry, I can't write that program."


def _ask(reply):
    return lambda prompt: reply


def test_llm_good_program_ships():
    cat = forge("add 3 and 4", build=make_llm_build_executor(_ask(GOOD_ADDER)))
    assert cat.ok is True
    assert cat.result["verified"] is True and cat.result["behavioral_ok"] is True
    assert cat.result["source"]["python"]  # the verified program is woven into languages


def test_llm_wrong_program_is_blocked_at_verify():
    cat = forge("add 3 and 4", build=make_llm_build_executor(_ask(WRONG_ADDER)))
    assert cat.ok is False
    verify = next(r for r in cat.receipts if r.phase == "verify")
    assert verify.status == "blocked"  # the gate caught the off-by-one
    assert all(r.phase != "deliver" for r in cat.receipts)  # stopped before delivery — nothing shipped


def test_llm_looping_program_is_caught_not_hung():
    # the reference is bounded + loop-detecting, so this returns (it does not hang)
    cat = forge("add 3 and 4", build=make_llm_build_executor(_ask(LOOPING)))
    assert cat.ok is False
    verify = next(r for r in cat.receipts if r.phase == "verify")
    assert verify.status == "blocked"


def test_llm_garbage_drifts_at_build():
    cat = forge("add 3 and 4", build=make_llm_build_executor(_ask(GARBAGE)))
    assert cat.ok is False
    assert cat.receipts[1].phase == "build" and cat.receipts[1].status == "drift"


def test_default_build_still_deterministic():
    # passing no executor keeps the deterministic synthesizer (regression guard)
    cat = forge("add 3 and 4")
    assert cat.ok is True and cat.result["op"] == "add"
