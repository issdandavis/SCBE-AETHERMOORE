# Full-system refusal precedence — 2026-09-09

This follow-up closes the legacy-wrapper bypass left open in
`PATENT_ENGINEERING_REPAIRS_20260909.md`. It does not supersede that report's
other open issues or change the original component-test receipt.

Both `src/symphonic_cipher/scbe_aethermoore/full_system.py` and
`symphonic_cipher/scbe_aethermoore/full_system.py` could replace a Layer 13
refusal with ALLOW. First-use requests skipped the layer decision entirely.
Later requests could have high/critical risk softened when coherence was high.
HEIGHTENED mode could also return QUARANTINE before considering multiple
violations which would have caused DENY in NORMAL mode.

## Resulting behavior

| Layer 13 result | Minimum final restriction |
|---|---|
| ALLOW | Continue checking; other failures can still refuse |
| REVIEW | QUARANTINE |
| DENY | DENY |
| SNAP | SNAP |

The rule applies to NORMAL, HEIGHTENED, LEARNING and LOCKDOWN, with or without
an established reference. LOCKDOWN refuses access. Topology failure and
excessive manifold divergence cause SNAP; causality failure causes DENY.
Invalid/nonfinite numeric evidence and contradictory risk classifications
cannot create an ALLOW. Existing supplemental entropy/coherence checks can
make the result stricter. The obsolete high-coherence softening code is gone.

Only a final ALLOW installs or replaces the reference. Refused observations
still produce metrics and audit entries; they do not become an approved
baseline. This is important for bootstrap: the first request has no automatic
right to define what subsequent requests should be compared against.

## Audit change

The existing HMAC chain now authenticates a canonical JSON record with schema
`scbe.full-system-decision.v2`, identity, intent, timestamp, Layer 13 decision
and final decision. The record is created after decision composition. This
allows, for example, a pipeline ALLOW followed by LOCKDOWN DENY to be recorded
faithfully. The HMAC algorithm, key handling and nonce generation are unchanged.

An existing chain of opaque legacy entries can continue with the new records.
Tests verify mixed-chain integrity and detect alteration of the final decision.
This is not a signed tool capability: resource/context scope, expiry, replay
protection and the execution boundary still require separate implementation.

## Evidence

New regressions first ran against the preserved pre-edit wrappers: 118 failed
and 24 passed. After repair and six additional escalation/chain cases, all
148 regressions passed. The tests import both source trees by distinct package
identities and verify the loaded file paths, avoiding an accidental double
test of one implementation.

| Final focused run | Passed |
|---|---:|
| Both wrappers: decision precedence, invalid evidence, state admission, audit | 148 |
| Primary full-system and fourteen-layer suites | 71 |
| Legacy full-system and fourteen-layer suites | 71 |
| Total passing executions | 290 |

The direct decision controls use real bounded L12-to-L13 calculations that
produce ALLOW, REVIEW, DENY and SNAP. Public-method state tests inject those
outcomes at the pipeline boundary while exercising the remaining wrapper.
They prove composition and state handling, not detector accuracy. A separate
unpatched public-pipeline test verifies refusal precedence on actual outputs.
Positive controls require an ALLOW path and approved-reference updates; an
implementation that refuses every request would fail these tests.

Four old tests per source tree assumed arbitrary first requests must ALLOW.
Those tests now require layer-decision precedence, accurate counters and audit
integrity. A convenience-function regression requires refusal in LOCKDOWN.
No layer threshold was relaxed to retain old permissive behavior.

The broader `npm run test:all` check was also attempted under a 180-second
owned-process bound with two Vitest workers and GPU visibility disabled. Its
TypeScript stage finished with 214 passing files, 6737 passing tests and 20
skips, but one file could not be collected: `tests/hydra-terminal-browse.test.ts`
imports the absent
`external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs`.
The missing external module is outside this patch. Because the script uses
`npm test && npm run test:python`, the repository-wide Python stage did not run.
The focused Python suites above did run and pass. The first broad attempt had
uncaptured nested-shell output; the second explicitly forwarded the handles
and produced the diagnostic logs. Neither is a clean full-repository pass.

Exact commands, logs, original source bytes, inventory and the task-only patch
are under `artifacts/wrapper_denial_repair_20260909/`. Tests used CPU only with
two numerical-library threads. No dependency or training-data change was made.

## Remaining limits and next work

Ordinary demo inputs can now be rejected where the old wrapper silently
allowed them. The full pipeline still needs an explicitly authorized baseline
and measured calibration on allowed and forbidden actions. The wrapper passes
constant trajectory/signature scores and computes a context hash that it does
not use in authorization. Those are not authenticated action evidence.

Before connecting this demonstration wrapper to privileged execution, bind the
principal, requested resource/action and capability lifetime to an enforced
tool boundary; test replay, tampering, state poisoning and restart behavior.
The broader patent review's container, instrumented CFI and calibration work
remains open. Neither the 290 tests nor the geometry simulations establish a
complete security product, cryptographic improvement or patent coverage.

Clay's sentence experiment is separate. Its existing supervisor and worker
were observed live during this repair, with the recovered arm complete and
the next arm training. No SCBE wrapper source is part of that run's 40 pins.
