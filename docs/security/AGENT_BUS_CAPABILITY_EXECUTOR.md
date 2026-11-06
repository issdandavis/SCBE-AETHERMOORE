# Agent Bus capability executor

The security architecture now treats model output as an untrusted proposal. A
model may describe a command, but only trusted host code can authorize and run
it.

```text
model proposal
  -> typed GeoSeal plan
  -> policy + topology evaluation
  -> signed topological evidence bound to that exact plan
  -> one-use capability
  -> replay reservation + signed authorization receipt
  -> isolated executor
  -> signed result receipt
```

This is the executable form of the rose analogy used for the project: the
security topology is the root and thorns; agent behavior is the bloom. The
topology can influence authorization, while deterministic host controls remain
responsible for enforcing the result.

## Implemented boundary

`packages/agent-bus/src/secure-execution.ts` provides:

- HMAC-SHA256 capabilities with issuer, subject, audience, key ID, nonce,
  not-before, expiry, one-use limit, exact plan and argument hashes, workspace,
  access mode, isolation kind, tool class, permission mode, and resource limits;
- topological evidence that binds the plan to evaluator and risk-receipt hashes
  plus bit-spine, trit-array, STISTA, and MultiSign representation hashes;
- exact `ALLOW` enforcement. `QUARANTINE`, `ESCALATE`, `DENY`, `REVIEW`, and
  `SNAP` evidence cannot issue an execution capability;
- a durable replay store and a signed, hash-chained three-record journal for
  `AUTHORIZED`, `RESERVED`, and `RESULT` events;
- a shell-free command parser and an isolated-executor interface with no host
  fallback inside this module;
- a Docker executor with no network, dropped capabilities, no-new-privileges,
  non-root execution, read-only root filesystem, bounded memory/CPU/PIDs/output,
  noexec temporary storage, and a path-bounded workspace mount.

`packages/agent-bus/src/pipeline.ts` adds `executePipelinePlan`. Trusted callers
can pass `secureExecution` after GeoSeal compilation and policy checks. The
result carries the capability and receipt paths with the normal Agent Bus
record.

## Security interpretation

The neural or geometric system supplies evidence; it does not become the sole
security boundary. The signed capability converts that evidence into a narrow,
auditable authority. This prevents an attractive latent-space score from
silently granting broader operating-system power than the reviewed plan.

Control state must live outside the agent-writable workspace. A capability is
rejected if it is stale, outlives its topology evidence, binds another plan,
uses altered arguments, has already been reserved, or expects a different
subject, audience, workspace, or isolation provider.

## Current gaps

- The trusted adapter that computes topological evidence from the live
  14-layer/ChoiceScript/neural probes is not wired to the capability issuer yet.
  Tests use explicit evidence fixtures.
- The existing Agent Bus still supports its compatibility host runner when a
  caller omits `secureExecution`. Production policy must require the secure
  branch for tools that change external state.
- The canonical kernel `pipeline14.ts` currently emits three decisions
  (`ALLOW`, `QUARANTINE`, `DENY`), while ChoiceScript and energy-governance
  surfaces also expose `ESCALATE`. One canonical policy enum and transition
  table are still needed.
- ChoiceScript conditions inspect bounded workflow data such as `_last_result`.
  Neural hidden-state probes exist separately and are not yet automatic inputs
  to ChoiceScript.
- HMAC key custody, rotation, remote sandbox attestation, and deployment-level
  denial of direct host execution need an operational profile.

## Validation

The full Agent Bus suite passes 744 tests across 30 files. Focused tests cover
capability tampering, replay, expiry, non-ALLOW topology, stale/mismatched
evidence, signed receipts, Docker hardening, isolation failure, pipeline
integration, and the control-state boundary.

ChoiceScript no longer uses Python `eval`. Its bounded AST interpreter permits
data-only expressions and rejects object traversal, imports, lambdas,
comprehensions, and arbitrary method calls. Its focused suite passes 27 tests,
including exclusive routing for all four project policy outcomes.
