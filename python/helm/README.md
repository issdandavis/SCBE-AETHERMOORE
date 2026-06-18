# Helm — the operator loop (criteria-based approval)

**Approval is a procedure, not a person.** An objective comes in; for each step the AI checks the step's **approval criteria** — and **if the criteria are met, the step is approved and runs. That's it.** No human clicking a queue: the AI runs the whole loop on its own, and a human's job is to *encode the criteria once*.

Standalone (stdlib only). Steps and criteria are pluggable callables, so **codeforge** (build+verify), the **governance gate**, and shell/tools drop straight in.

## The model
- A step with **no criteria** is unconditional — it just runs (fine for low-stakes work).
- A **risky step** (deploy, spend, …) carries criteria that must **all** pass — e.g. *"the build verified" + "tests passed" + "within budget."* Met → it ships, autonomously, no human in the loop.
- A **genuinely human-gated** action is simply a criterion that checks a human-provided signal (`human("approved_spend")`) — so human approval is *expressible*, not the default.

## Use
```python
from python.helm import Step, run_objective, render, upstream, flag, human

steps = [
    Step("build",  "build",  build_fn),                                  # no criteria -> runs
    Step("deploy", "deploy", ship_fn, criteria=(
        upstream("build", "verified", True),                             # only if the build verified
        flag("within_budget"),                                          # and the budget switch is on
    )),
    Step("charge", "spend",  bill_fn, criteria=(human("approved_spend"),)),  # a real money gate
]
run = run_objective("ship the tool", steps, context={"within_budget": True})
run.fully_autonomous     # True iff every step's criteria were met and it ran
print(render(run))
```

Live, with the real codeforge as the build step:
```
helm · 'add 3 and 4' · 2 approved, 1 denied
  ✓ build (build)
  ✓ deploy (deploy)                       # auto-approved: build.verified == True
  ✗ charge (spend)  ← criteria not met: human:approved_spend
```

## Criteria builders
- `upstream(step, key, equals)` — an earlier step's result satisfies a value (e.g. `verified == True`).
- `flag(key)` / `human(key)` — a switch in the run context (set upstream, or by a person for the rare true gate).
- `met(name, fn)` — any predicate of `(objective, context, step)`.

## Properties
- **Procedure, not a person:** a step runs iff its criteria pass; denied steps record exactly which criterion failed.
- **Fail-safe:** a criterion that errors counts as *not met* (denied, not run).
- **Auditable + deterministic:** every step is receipted into a tamper-evident chain; same objective + steps + context → same `chain_digest`.
- **Resilient:** an approved step whose action raises is recorded `failed`; the loop continues.
- **Re-runnable:** re-run with an updated `context` (or after upstream results change) and previously-denied steps clear their criteria — the loop, driven by the rules.
