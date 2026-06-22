# System Coding 100% Success Blueprint

The target is not "the model says it fixed the code." The target is:

```text
every code-fix task exits in a proven state:
  VERIFIED_FIX  - candidate is execution-equivalent to the reference/contract beyond visible tests
  ESCALATE      - system cannot prove a fix, so it refuses to ship and asks for a stronger oracle

false success must stay 0.
```

For system coding, 100% is therefore two numbers:

- `code_fix_success_rate`: tasks that reach `VERIFIED_FIX`
- `operational_closure_rate`: tasks that reach `VERIFIED_FIX` or `ESCALATE`

The hard invariant is:

```text
false_success_count == 0
```

If a task cannot be verified, it is not a failure of honesty. It is an escalation slot. The system only
fails when it ships an unverified or wrong patch as success.

## Fix Ladder

Each task moves through the same ladder:

1. `model_patch`: the coding model proposes a patch.
2. `visible_tests`: patch must pass the shown or public tests.
3. `abstaining_verifier`: patch is compared against a trusted reference or contract on generated inputs beyond visible tests.
4. `repair_loop`: failures feed back into the model with concrete execution output.
5. `archive_retrieval`: search prior verified fixes and pitfall traces for a structurally similar pattern.
6. `strong_solver`: escalate to a larger model, deterministic synthesizer, or human review.
7. `verified_or_escalated`: record a receipt; never mark an unverified patch as fixed.

This makes the model a proposer, not the authority. The verifier is the authority.

## Roles

- `framer`: extracts function name, contract, visible tests, hidden/shadow test shape, and blast radius.
- `patcher`: generates the smallest candidate patch.
- `runner`: executes visible tests in isolation.
- `verifier`: runs behavior checks beyond visible tests using `python.helm.abstaining_verifier`.
- `repairer`: converts failures into a new patch attempt.
- `retriever`: pulls known pitfall/fix traces and reusable repair motifs.
- `escalator`: stops local automation when proof is not available.

## Metrics

Track all of these per run:

```text
attempted
verified_fix
escalated
rejected_candidates
abstained_candidates
false_success
code_fix_success_rate = verified_fix / attempted
operational_closure_rate = (verified_fix + escalated) / attempted
```

Do not hide `escalated`. Escalation is what prevents fake success.

## Current Evidence

The current code-fix substrate already has the correct load-bearing primitives:

- `python.helm.abstaining_verifier.differential`: trust/reject/abstain by execution beyond visible tests.
- `python.helm.verify_cli`: CI-facing wrapper with exit codes `0 trust`, `1 reject`, `2 abstain`, `3 usage error`.
- Recovery-loop evidence: `113/180` single-shot vs `120/180` with repair, `+7 net`, McNemar exact `p=0.0654`.

That means the next target is not blind fine-tuning. It is improving `verified_fix` while keeping
`false_success` at zero.

## Definition of Done

A system-coding run is product-ready only when:

```text
false_success_count == 0
operational_closure_rate == 1.0
code_fix_success_rate is reported honestly
all escalations include the missing oracle/reason
```

The path to true 100% code fixes is to shrink `escalated` by adding better references, shadow tests,
retrieval, deterministic repair transforms, and stronger solvers. The path is not lowering the verifier.
