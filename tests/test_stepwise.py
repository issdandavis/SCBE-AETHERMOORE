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
    Step,
    Task,
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
    # a model that always mis-steps does not corrupt the answer -- it stops at its ceiling.
    # allow_offload=False isolates the pure rewind-exhaustion path (the oracle rescue is tested separately).
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2, allow_offload=False)
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


# --- auto-offload: when the model exhausts its rewinds, a deterministic oracle rescues the step ---


def test_auto_offload_rescues_a_step_the_model_never_gets():
    # a hopeless model (always 'Buzz', wrong for 6) burns its rewinds; the oracle supplies 'Fizz'
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2, allow_offload=True)
    assert r["completed"] is True
    assert r["answer"] == "Fizz"  # the rule, not the model, produced it
    assert r["offloaded"] == ["label"]
    assert r["trace"][-1]["source"] == "offload"  # the final value came from the tool, recorded as such


def test_allow_offload_false_preserves_the_un_rescued_baseline():
    # the same hopeless model, offload disabled -> still stops honestly (this is the measured baseline)
    r = run_stepwise(number_label_task(6), always_proposer("Buzz"), max_rewinds=2, allow_offload=False)
    assert r["completed"] is False
    assert r["stuck_at"] == "label"
    assert r["offloaded"] == []


def test_offload_only_fires_on_failure_not_when_the_model_succeeds():
    # a model that gets it first try never invokes the oracle -- offload is a fallback, not a shortcut
    r = run_stepwise(number_label_task(6), scripted_proposer(["Fizz"]), allow_offload=True)
    assert r["completed"] is True and r["answer"] == "Fizz"
    assert r["offloaded"] == []  # the tool stayed holstered; the model did the work


def _buggy_oracle_task():
    # one choice step: model can't pick the secret, and the oracle is WRONG (returns 'b', check wants 'a')
    return Task(
        name="buggy_oracle",
        goal="pick the secret value",
        steps=[
            Step(
                "pick",
                "pick",
                options=lambda st: ["a", "b"],
                check=lambda st, v: v == "a",
                oracle=lambda st: "b",  # a buggy tool: returns a value that fails the check
            )
        ],
    )


def test_a_buggy_oracle_never_ships_a_wrong_answer():
    # the oracle's value is itself checked; a wrong oracle falls through to stuck, it does NOT commit
    r = run_stepwise(_buggy_oracle_task(), always_proposer("b"), max_rewinds=1, allow_offload=True)
    assert r["completed"] is False  # would have been True if we trusted the oracle blindly
    assert r["stuck_at"] == "pick"
    assert r["offloaded"] == []
    assert "pick" not in r["state"]  # the bad oracle value was never written into state


def _check_less_oracle_task(oracle_value):
    # a step with an oracle but NO check: the only gate is legality (the value must be in options)
    return Task(
        name="check_less",
        goal="pick a legal value; no correctness predicate, just the walls",
        steps=[Step("pick", "pick", options=lambda st: ["a", "b"], oracle=lambda st: oracle_value)],
    )


def test_check_less_oracle_returning_an_illegal_value_falls_through_to_stuck():
    # the bug the review caught: a check-less oracle must NOT bypass the legality wall the model obeys.
    # oracle returns 'z' (not in options) -> it is rejected, never committed, step stops honestly.
    r = run_stepwise(_check_less_oracle_task("z"), always_proposer("z"), max_rewinds=1, allow_offload=True)
    assert r["completed"] is False
    assert r["stuck_at"] == "pick"
    assert r["offloaded"] == []
    assert "pick" not in r["state"]  # the illegal oracle value was never written into state


def test_check_less_oracle_returning_a_legal_value_is_committed():
    # the legitimate use: a check-less oracle that returns an in-options value rescues the step
    r = run_stepwise(_check_less_oracle_task("a"), always_proposer("z"), max_rewinds=1, allow_offload=True)
    assert r["completed"] is True
    assert r["answer"] == "a"
    assert r["offloaded"] == ["pick"]


def _no_oracle_task():
    # a genuine judgement the code can't do: a choice step with NO oracle registered
    return Task(
        name="no_oracle",
        goal="make a judgement only a model can",
        steps=[Step("judge", "judge", options=lambda st: ["x", "y"], check=lambda st, v: v == "x")],
    )


def test_a_step_with_no_oracle_still_stops_honestly():
    # the honest boundary: no tool can supply this, so even with offload on, a hopeless model stops
    r = run_stepwise(_no_oracle_task(), always_proposer("y"), max_rewinds=1, allow_offload=True)
    assert r["completed"] is False
    assert r["stuck_at"] == "judge"
    assert r["offloaded"] == []
