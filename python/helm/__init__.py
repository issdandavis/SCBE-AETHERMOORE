"""Helm — the operator loop: approval is a procedure, not a person.

Each step carries **approval criteria**. If the criteria are met, the step is
approved and runs — that's it. The AI runs the whole loop on its own; a human
encodes the criteria once.

    from python.helm import Step, run_objective, render, upstream, flag, human

    steps = [
        Step("build",  "build",  build_fn),                                  # no criteria -> just runs
        Step("verify", "verify", verify_fn),
        Step("deploy", "deploy", ship_fn, criteria=(                          # ships ONLY when:
            upstream("verify", "ok", True),                                   #   verify said ok
            flag("within_budget"),                                           #   budget switch on
        )),
        Step("charge", "spend",  bill_fn, criteria=(human("approved_spend"),)),  # genuine human gate
    ]
    run = run_objective("ship the tool", steps, context={"within_budget": True})
    run.fully_autonomous     # True iff every step's criteria were met and it ran
    print(render(run))

Criteria builders: ``upstream(step, key, equals)`` (an earlier step's result),
``flag(key)`` / ``human(key)`` (a context switch), ``met(name, fn)`` (any predicate).
Steps and criteria are pluggable callables — codeforge, the gate, and tools drop in.
"""

from .machine import (
    Action,
    Check,
    Criterion,
    OperatorRun,
    Receipt,
    Step,
    flag,
    human,
    met,
    render,
    run_objective,
    upstream,
)

__all__ = [
    "Step",
    "Criterion",
    "Action",
    "Check",
    "Receipt",
    "OperatorRun",
    "run_objective",
    "render",
    "met",
    "flag",
    "human",
    "upstream",
]
