"""stepwise: a guided step machine where a misstep rewinds (with a warning + rebuilt context) instead
of failing, and exact computations are offloaded to deterministic `calc` steps (never the model).

These tests prove the two mechanics: the model is called only for choices (calc steps run in code),
and a rejected value rewinds to before the misstep and retries with the ran-steps context + warning,
recovering when the next answer is right and stopping honestly when it never is.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.stepwise import (  # noqa: E402
    always_proposer,
    number_label_task,
    run_stepwise,
    scripted_proposer,
)


def test_calc_steps_run_in_code_not_the_model():
    # number_label has two calc steps (r3, r5) + one choice; only the choice should call the model
    r = run_stepwise(number_label_task(6), scripted_proposer(["Fizz"]))
    assert r["completed"] is True
    assert r["answer"] == "Fizz"
    assert r["model_calls"] == 1  # the modulo was done by calc, not asked of the model
    assert r["state"]["r3"] == 0 and r["state"]["r5"] == 1  # exact, never hallucinated


def test_a_misstep_rewinds_and_recovers():
    # 'Buzz' is wrong for 6 (r5 != 0); the machine rewinds, warns, and accepts the corrected 'Fizz'
    r = run_stepwise(number_label_task(6), scripted_proposer(["Buzz", "Fizz"]))
    assert r["completed"] is True and r["answer"] == "Fizz"
    assert r["rewinds"] == 1
    statuses = [t["status"] for t in r["trace"] if t["source"] == "model"]
    assert statuses == ["misstep", "ok"]  # bad value dropped, never committed


def test_exhausted_rewinds_stops_honestly_at_the_step():
    # a model that always mis-steps does not corrupt the answer -- it stops at its ceiling
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2)
    assert r["completed"] is False
    assert r["stuck_at"] == "label"
    assert r["rewinds"] == 3  # max_rewinds=2 -> a third misstep ends it


def test_rewind_context_carries_the_ran_steps_and_a_warning():
    seen = []

    def capturing(ctx, options):
        seen.append(ctx)
        return "Buzz" if len(seen) == 1 else "Fizz"  # misstep first, then correct

    r = run_stepwise(number_label_task(6), capturing)
    assert r["completed"] is True and r["rewinds"] == 1
    # the retry context rebuilds where we are from the steps that ran, plus the misstep warning
    assert "r3=0" in seen[1] and "r5=1" in seen[1]
    assert "[!]" in seen[1]


def test_offloaded_modulo_makes_the_correct_label_pass_for_any_i():
    # because r3/r5 are exact, a correct label choice always verifies -- across the rule's branches
    for i, label in [(3, "Fizz"), (5, "Buzz"), (15, "FizzBuzz"), (7, "7")]:
        r = run_stepwise(number_label_task(i), scripted_proposer([label]))
        assert r["completed"] is True and r["answer"] == label
