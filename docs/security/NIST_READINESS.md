# SCBE security engineering self-assessment

Assessment date: 2026-09-18. Scope: the reviewed SCBE source, selected runtime
contracts and repository delivery controls. This is a **partial self-assessment**,
not an attestation of organization-wide compliance, a NIST certification, or a
FIPS validation. No readiness percentage is assigned.

The baseline is the final [NIST SSDF 1.1, SP 800-218](https://csrc.nist.gov/pubs/sp/800/218/final).
SSDF 1.2 was an initial public draft at review time, not the assessment baseline.
A deployment should maintain a current/target profile following
[NIST CSF 2.0 Organizational Profiles, SP 1301](https://csrc.nist.gov/pubs/sp/1301/final).
[NIST explains its independent laboratory validation process here](https://www.nist.gov/standardsgov/compliance-faqs-nist-it-security-validation-program).

## Evidence boundary

The reviewed entry points are:

- `src/symphonic_cipher/topological_cfi.py` and the legacy root copy;
  `packages/kernel/src/hamiltonianCFI.ts`, re-exported by `src/harmonic`.
- Both `scbe_aethermoore/layers/fourteen_layer_pipeline.py` and `full_system.py`
  copies, including the causality wrapper around breathing.
- `src/governance/runtime_gate.py`, its persistence and final reference admission.
- Both `scbe_aethermoore/pqc/pqc_core.py` compatibility wrappers and their mock
  boundary. The separate `src/crypto/pqc_liboqs.py` backend remains a distinct path.
- `formal/lean`: 47 kernel-checked mathematical statements. Their assumptions
  and implementation correspondence limits are documented separately.

No review of this scope proves that every API, tool, worker, exported package,
deployed service or control-flow instrumentation point reaches these guards.
Repository permissions were inspected through GitHub's authenticated API, not
inferred from workflow names. The owner remains the organizational risk owner;
this document does not sign an attestation on the owner's behalf.

## Repairs and regression evidence

| Contract | Implementation and evidence |
|---|---|
| Only declared directed edges authorize a transition | Frozen policy snapshots in Python and TypeScript CFI; exhaustive small-graph and reversed-edge tests in `tests/test_patent_security_regressions.py` and `tests/harmonic/hamiltonianCFI.security.test.ts` |
| Missing policy and malformed identifiers cannot authorize | Explicit readiness, integer/domain checks, invalid-reinitialization revocation, and latched TS traversal failure |
| Later checks cannot soften a prior refusal | Full-system composition preserves REVIEW/DENY/SNAP across modes and cold starts; `tests/governance/test_full_system_decision_precedence.py` |
| Rejected inputs cannot train the trusted reference | RuntimeGate commits the centroid, trust and trichromatic reference only after its final result; versioned persistence discards legacy untrusted references; `tests/governance/test_patent_decision_repairs.py` |
| Scores have declared domains and direction | Invalid measurements fail closed; bounded safety is distinguished from increasing harmonic cost. Geometry does not add cryptographic security bits |
| Breathing does not collapse the state | Positive radial transform, explicit inverse and Jacobian; invalid or saturated boundary values are rejected. Tests compare derivatives with independent finite differences |
| Mock cryptography cannot activate silently | Legacy wrappers require two explicit test settings for mock operations; removing them revokes the mock path, including verification. `tests/security/test_breathing_and_backend_contracts.py` |
| Audit describes the final decision | Full-system HMAC payload v2 includes both L13 and composed decisions. This is an integrity property for that payload, not proof of durable logging |

The baseline regression run reproduced 197 failures across 224 new checks before
porting the existing repairs. After those repairs the same 224 checks passed.
The expanded local validation passed 482 Python tests and 105 TypeScript tests.
The implementation correspondence audit passed all seven groups (12,641 finite
checks). Lean rebuilt 47 theorems, audited their dependencies, and rejected three
false fixtures. These counts describe different kinds of evidence and are not
added together into a security score.
The [validation receipt](evidence/validation-20260918.json) records the source
commit and hashes; [the correspondence receipt](evidence/runtime-contracts-20260918.json)
records each group. Subsequent changes must be assessed against their own commits.
Tests of insecure mocks establish protocol mechanics only. Native backend smoke
tests require an actual library, exact ML-KEM-768/ML-DSA-65 algorithm availability,
round trips and rejection of altered signature messages.

### Reproduce the focused checks

Use the repository's existing development dependencies. Run without production
credentials. The boundary tests explicitly unset mock opt-ins to test defaults.

```sh
SCBE_FORCE_SKIP_LIBOQS=1 python -m pytest -o addopts='' \
  tests/test_patent_security_regressions.py \
  tests/governance/test_patent_decision_repairs.py \
  tests/governance/test_full_system_decision_precedence.py \
  tests/security/test_breathing_and_backend_contracts.py -q
npx vitest run tests/harmonic/hamiltonianCFI.security.test.ts \
  tests/harmonic/breathing.security.test.ts tests/harmonic/hyperbolic.test.ts
python formal/lean/audit_implementation.py --repo . --output /new/path/runtime-audit.json
```

For Lean, follow `formal/lean/README.md`. The proof audit rejects unfinished
proofs/custom axioms and checks three deliberately false statements fail to
compile. It proves the specified mathematical contracts, not the deployed system.
The new Python regressions are included in `scripts/system/run_core_python_checks.py`
so normal PR checks exercise them. TS regressions run through the existing suite.

## SSDF practice inventory

Status is for the **whole practice**: an implemented code check does not close an
organizational control. “Partial” means evidence exists but the listed work remains.

| Practice | Current evidence | Status and next evidence needed |
|---|---|---|
| PO.1 Requirements | Explicit contracts, threat boundaries, this assessment | Partial: approve a deployment-specific requirements and threat model |
| PO.2 Roles | Maintainer and private reporting contact in `SECURITY.md` | Partial: name release reviewer, incident backup and risk acceptance owner |
| PO.3 Toolchain | Pinned Lean/mathlib; CI build, formatting and security workflows | Partial: inventory and pin remaining build actions/tools; restrict build credentials |
| PO.4 Security criteria | Required GitHub checks plus the added contract regressions | Partial: require real-backend checks for the actual release and track exceptions |
| PO.5 Environments | Isolated review worktree; read-only workflow permissions where inspected | Partial: verify production/dev separation, runner access and secrets lifecycle |
| PS.1 Source protection | PR ruleset, no force-push/deletion, required CI | Partial: independent approval is not required; administrative bypass remains possible |
| PS.2 Release integrity | Source hashes and proof receipts | Partial: attach signed provenance and verified package digests to a specific release |
| PS.3 Release archives | Version control and CI artifacts | Partial: demonstrate retained immutable release bundle and rollback recovery |
| PW.1 Design | Trust boundaries, decision order, mock restrictions | Partial: complete capability scope/replay and entry-point coverage analysis |
| PW.2 Design review | Counterexamples and source-to-test mapping | Partial: independent reviewer and deployment-specific threat review |
| PW.4 Reuse | Lockfiles; dependency updates #2855 and #2856 merged; Soup Sieve patched to 2.9 | Partial: release SBOM, license inventory and triaged dependency audit findings |
| PW.5 Coding | Domain checks, explicit state transitions, security regression cases | Partial: extend these checks to remaining service/runtime paths |
| PW.6 Build configuration | Package-boundary checks and pinned proof environment | Partial: attest actual release compiler, flags and reproducibility |
| PW.7 Code analysis | Existing CodeQL, secret scan, Bandit; focused diff review | Partial: resolve release-specific scan findings and review all exposed entry points |
| PW.8 Executable testing | Python/TS regressions, native crypto lane, negative proof fixtures | Partial: targeted fuzzing, concurrency, load, replay and fault-injection coverage |
| PW.9 Defaults | Fail-closed changed interfaces and explicit mock opt-ins | Partial: replace/guard automatic calibration; prove secure deployed configuration |
| RV.1 Discovery | Private reporting contact; scheduled scans | Partial: verified intake, inventory ownership and monitoring coverage |
| RV.2 Remediation | Reproduced defects and focused repairs; dependency PRs merged | Partial: release/advisory process, response drill and remediation tracking |
| RV.3 Root causes | Tests distinguish geometry, safety, authority and crypto strength | Partial: systematic recurrence review across duplicated/experimental surfaces |

On September 18, `main` required six CI checks. This repair set changed
`required_status_checks.strict` from false to true, retaining the same checks:
PRs must be tested against the current base. Neither an independent human review
requirement nor a new paid service was enabled. Readiness must not be inferred
from green checks that omit a component.

## Release blockers and next work

1. **Deployment authorization coverage.** Trace principal, resource, operation,
   context, expiry and replay state from each ingress to execution. Freeze and
   authenticate policy inputs. A valid graph edge is not a tool permission.
2. **Enrollment and persistence.** RuntimeGate's first five requests can be
   automatically admitted for calibration. Restrict enrollment to trusted inputs
   before treating that heuristic as an enforcing security boundary. Protect
   snapshots with access controls and authenticated, atomic persistence; test
   concurrent requests and crash recovery. Current JSON validation is not a MAC.
3. **Crypto release identity.** Record actual algorithms, backend versions,
   operating environment and cryptographic module boundary. Disable both mock
   override families. Known-answer/interoperability and negative tests must run
   on the shipped backend. No certificate was verified for this deployment.
4. **Release supply chain.** Generate an SBOM and provenance for the final artifact,
   resolve or explicitly accept audit findings, and archive the resulting bundle.
   Existing npm/pip audit workflow findings are advisory, not blocking gates.
   The two open Dependabot alerts inspected during this pass were both Soup Sieve
   regex denial-of-service issues in the example lockfile; its 2.9 update addresses
   the reported vulnerable version. Repository alert closure is checked after merge.
5. **Operations.** Verify durable audit export, monitoring, least privilege, key
   rotation, backup restore, incident response and vulnerability disclosure drills.
   Source fixes alone do not establish these controls.

FIPS 140-3 validation is a separate program. Check the exact module and conditions
in the [CMVP validated-module directory](https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules).
Using a named NIST algorithm, a test library or a geometric authorization layer
does not establish module validation or increase the underlying cipher's strength.

## Breathing as a constrained deformation

For the Python profile, `b(t)=exp(log(1+a)*sin(omega*t))`, with `0 <= a <= 1.5`.
It follows that `1/(1+a) <= b <= 1+a`; the default stays between 0.4 and 2.5.
With `r=||u||`, let `f(r)=tanh(b*atanh(r))`. The radial derivative is
`b*(1-f(r)^2)/(1-r^2)` and tangential sensitivity is `f(r)/r`; both approach `b`
at the origin. The inverse replaces `b` by `1/b` at the same time.

These are measurable constraints for the user's structural “ribs” analogy.
They do not grant permissions, prove general robustness, or preserve hyperbolic
distances. Conditioning can deteriorate near the boundary. Floating-point
saturation is rejected rather than represented as a reversible operation.
The TS rendering/math profile uses `exp(A*sin(omega*t))`, with its existing
amplitude clamp `[0,0.1]`. These profiles have distinct declared parameters.

The separate `src/scbe_14layer_reference.py` clamped-factor profile and other
experimental transforms remain outside this derivative guarantee. Changes to
the breathing schedule require recalibration of downstream empirical thresholds.
