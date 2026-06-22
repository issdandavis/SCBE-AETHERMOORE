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

1. `known_logic_injection`: if a deterministic answer/process exists, inject that packet first.
2. `model_echo_or_fallback`: the model may repeat/apply the packet; if it cannot, use the deterministic answer directly.
3. `model_patch`: only ask the coding model to invent a patch when no known process covers the task.
4. `visible_tests`: patch must pass the shown or public tests.
5. `abstaining_verifier`: patch is compared against a trusted reference or contract on generated inputs beyond visible tests.
6. `repair_loop`: failures feed back into the model with concrete execution output.
7. `archive_retrieval`: search prior verified fixes and pitfall traces for a structurally similar pattern.
8. `strong_solver`: escalate to a larger model, deterministic synthesizer, or human review.
9. `verified_or_escalated`: record a receipt; never mark an unverified patch as fixed.

This makes the model a proposer, not the authority. The verifier is the authority.

## Known Logic Injection

If the system already knows the answer, the model should not be asked to reason it out. The known
answer/process is wrapped as a `KnownLogicPacket`:

```text
task -> deterministic tool/process -> known answer -> model echo/apply -> verifier -> keep echo or fallback
```

Examples:

- `sieve_primes(n)`: compute prime membership exactly, then inject "prime" or "composite".
- `chart_lookup(key)`: read the chart cell exactly, then inject that value.
- `if_then(condition)`: run a bounded branch rule, then inject the chosen branch.
- code reference/contract: inject a known-good implementation or transform and verify the model's patch against it.

This is not a prompt tweak like "use better logic." It is correct information injection: the model is
treated as a parrot/adapter over a deterministic source. If the model cannot repeat or apply the packet,
`python.helm.known_logic_injection.inject_or_fallback` returns the deterministic answer directly with
`false_success_count == 0`.

Local diagnostic evidence from MBPP failures matched this design: on 20 prior single-shot failures,
reference-answer injection made the 1.5B model reproduce correct logic on 14/20; inject-or-fallback reached
19/20 because the reference was the authority.

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
- `python.helm.known_logic_injection`: deterministic answer/process packets with model echo or fallback.
- Recovery-loop evidence: `197/300` single-shot vs `203/300` with repair, `+6 net`, McNemar exact `p=0.0312`.

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
