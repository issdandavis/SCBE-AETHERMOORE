# Math and Interface Audit -- 2026-05-28

Purpose: double-check the patent packet's formulas, mathematical language, and
machine/interface support before filing. This is an engineering/legal drafting
audit, not legal advice.

## Bottom Line

The core mathematical spine is usable: Poincare-ball projection, hyperbolic
distance, centroid drift, and allow/review/quarantine/deny routing are supported
by code. The filing packet should be tightened before submission because several
older formulas and phrases overstate what the current RuntimeGate actually does.

Highest-priority fixes identified in the first pass:

1. Replace broad "superexponential" language in the independent claims/spec or
   add explicit alternative embodiments for the current clamped exponential and
   the bounded reciprocal score. Status: first cleanup applied to the active
   claim draft, detailed-description source, assembled markdown draft, and DOCX
   builder.
2. Rework fail-to-noise language. Current RuntimeGate noise is deterministic
   hash-derived and auditor-reproducible; it is not keyed cryptographic
   indistinguishability unless a secret/keyed generator is added. Status: first
   cleanup applied for the independent/runtime claims; deeper Sacred Egg claims
   remain a CIP/support decision.
3. Separate implemented hardware/software interfaces from aspirational
   cryptographic subsystems. Processor/memory/API/CLI/storage interfaces are
   supported; TPM/HSM/TEE/hardware-secure-element interfaces should be optional
   embodiments unless implemented.
4. Treat post-provisional additions as buckets: provisional-supported core,
   non-provisional-date improvements, and CIP/continuation candidates.

## Formula Checks

| Area | Current packet language | Code/evidence | Audit result | Filing action |
|---|---|---|---|---|
| Poincare projection | `u = tanh(alpha ||x||) x/||x||`, epsilon clamped | `packages/kernel/src/hyperbolic.ts` uses `r = tanh(alpha*n)`, `r <= 1-eps`; `packages/kernel/src/pipeline14.ts` uses the same shape | Good | Keep. Recite as a bounded embedding transform from arbitrary feature vectors into an open unit ball. |
| Hyperbolic distance | `arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))` | `packages/kernel/src/hyperbolic.ts:84-97` | Good | Keep. Avoid saying it "cannot be circumvented"; say it is invariant once `u` and `v` are fixed under the metric. |
| RuntimeGate cost | Earlier claims discussed superexponential boundary cost | `src/governance/runtime_gate.py:889-899` computes weighted Euclidean distance in 6D tongue coords, clamps `d_star = min(weighted_dist, 5.0)`, returns `pi^(phi*d_star)` | First-pass fixed in active claim draft | Keep independent language broad and preserve dependent embodiments covering `pi^(phi*min(d, d_max))`. Do not rely on RuntimeGate alone to support unbounded `R^(d^2)`. |
| Kernel harmonic scaling | Spec says `R^(d^2)` in many places | `packages/kernel/src/harmonicScaling.ts:50-55` and `pipeline14.ts:460-461` use bounded score `1/(1+d+2*phaseDeviation)`; comments say `R^(d^2)` caused numerical collapse | Mismatch | The spec must present `R^(d^2)` as one embodiment / theoretical wall and the bounded reciprocal score as the production-safe embodiment. |
| Older R^(d^2) implementation | Spec uses `H(d,R)=R^(d^2)` and 128/256-bit thresholds | `src/aaoe/task_monitor.py:256-265` and `src/aetherbrowser/phase_tunnel.py:183-185` implement `R^(d*d)` | Supported in side modules | Keep as an embodiment, but do not imply every runtime path uses it. |
| 128-bit threshold | `d_crit = sqrt(128 ln 2)` for `R=e` | Math checks out because `e^(d^2)=2^128` | Mathematically correct but legally risky phrasing | Call it a cost-amplification threshold, not proven cryptographic bit security, unless actual verification work is tied to that cost. |
| Centroid update | Claim recites incremental centroid over prior requests | `runtime_gate.py` maintains `_centroid` and `_centroid_count`; claims note algebraic equivalence | Good | Keep, but specify the coordinate backend can be stats, semantic, or trained projector. |
| Spin/trit quantization | Per-tongue deviations mapped to -1/0/+1 | `runtime_gate.py:860-883` | Good | Good dependent claim support. |
| Fail-to-noise | "cryptographically indistinguishable" / "not holding governance keys" | `runtime_gate.py:174` defines `_fail_to_noise(action_hash, length=32)` from SHA-256 prefix + action hash; no secret key is visible in the function | Overstated unless keyed | Amend to "deterministic pseudorandom-looking audit noise" or implement keyed HMAC/CSPRNG if claiming cryptographic indistinguishability from an untrusted observer. |
| ML-KEM / ML-DSA receipts | Claim 12 says signed decision receipt and KEM ciphertext | Support appears in TypeScript/offline/PQC modules, but Python RuntimeGate emits unsigned `GateResult` | Partial integration | Claim as an embodiment or wire RuntimeGate to issue a real receipt before filing if this remains central. |
| Settling wave keys | Spec says key exists only at predetermined arrival time | Mostly conceptual/math language | High enablement risk | Move to optional/CIP unless there is a concrete implemented key schedule and tests. |
| Sacred Egg five-predicate gate | Spec claims tongue/geo/path/quorum/crypto conjunction | Current claims already flag this as partial/CIP material | High written-description risk | Reformulate as "plurality of predicates including semantic, geometric, and cryptographic predicates" or move to CIP. |

## Interface and Hardware Support

The patent packet should explicitly tie the math to machine interfaces. Supported
interfaces from the repo:

1. Processor and non-transitory memory: claims 9 and 15 already recite this.
2. API/server interface: `scripts/aetherbrowser/api_server.py` constructs a
   long-lived RuntimeGate singleton with environment-configured thresholds and
   backend selection.
3. CLI / command interface: claims reference command-line deployment; supporting
   files exist across `src/cli/`, `packages/cli/`, and `scripts/`.
4. Agent bus interface: claim 14 references an agent bus service; support exists
   in the package surface, but subcommand rot should be tested before relying on
   it as a polished commercial embodiment.
5. Persistent storage interface: `runtime-gate-state/v1` persists centroid,
   centroid count, cumulative cost, query count, trust history, and immune set
   through JSON atomic writes. This is strong hardware-facing support because it
   connects the abstract trajectory to disk-backed machine state.
6. Network/executor interface: the API and downstream executor language should
   be described as optional embodiments that receive requests, call the gate,
   and route execution based on the returned decision.

Hardware/interface wording to add or preserve:

- "one or more processors";
- "non-transitory computer-readable memory";
- "network interface receiving an action request";
- "storage interface storing persistent runtime state";
- "execution interface that permits, restricts, quarantines, reroutes, or denies
  invocation of a tool, model call, API request, file operation, or process";
- "cryptographic module configured to sign a decision receipt" only where the
  signing implementation is actually used or clearly optional.

Hardware/interface wording to avoid unless implemented:

- Do not imply a required TPM, HSM, secure enclave, TEE, FPGA, sensor, or custom
  hardware accelerator unless added as an optional embodiment.
- Do not imply the hyperbolic metric itself creates cryptographic security bits.
  It creates measurable routing/cost signals; cryptographic security comes from
  actual cryptographic primitives.
- Do not imply PQC receipts are always emitted by RuntimeGate unless the Python
  gate is wired to the PQC receipt implementation.

## Document Consistency Issues

1. Resolved: `docs/PATENT_DETAILED_DESCRIPTION.md` now describes the current
   FIG. 1-9 drawing set and no longer contains orphan FIG. 10-12 references in
   the brief-description section. Anti-fragile, breathing-transform,
   phase-transform, Langues Metric, and SpiralSeal embodiments remain described
   in prose rather than as missing drawing figures.
2. First-pass formula cleanup has been applied to reconcile the active claims,
   detailed-description source, assembled markdown draft, and DOCX builder. The
   spec should continue to present all three cost forms as alternative
   embodiments:
   - theoretical wall: `R^(d^2)`;
   - production bounded score: `1/(1+d+2*pd)`;
   - RuntimeGate cost: `pi^(phi*min(d*, d_max))`.
3. The workbench manifest references
   `docs/legal/patent-workbench/assembled/SCBE_NONPROVISIONAL_SPEC_DRAFT_v1.docx`,
   but `rg --files docs/legal/patent-workbench/assembled` only listed the `.md`
   and `.manifest.json` files during this audit. Confirm whether the DOCX is
   untracked/ignored, missing, or located at `docs/legal/SCBE_NONPROVISIONAL_SPEC_v1.docx`.

## Recommended Claim/Spec Edits

### Independent Claim 1

Replace:

`whereby the governance cost increases superexponentially as the embedded point approaches a boundary of the open unit ball.`

With a safer version:

`whereby the governance cost is a nonlinear increasing function of measured drift and is used to control execution of the computational action.`

Then add dependent alternatives:

1. `H(d,R)=R^(d^2)`;
2. `H=1/(1+d+2*pd)`;
3. `C=pi^(phi*min(d*, d_max))`.

### Fail-To-Noise Claim

If no keyed generator is added, use:

`generating deterministic pseudorandom-looking audit noise from a cryptographic hash of a fixed domain-separation prefix and a content hash of the denied request.`

If keyed indistinguishability is desired, implement first:

`noise = HMAC/governance-keyed stream(seed = H(prefix || action_hash || decision_context))`

and test same-input reproducibility under audit key plus non-recoverability
without the key.

### PQC Receipt Claim

Either:

1. Wire RuntimeGate to emit a real ML-DSA/ML-KEM receipt before filing; or
2. Claim it as an optional embodiment connected to an executor that verifies the
   receipt before execution.

## Benchmark Hooks For "Teeth"

The strongest evidence table should measure both raw model and governed model:

1. Benign pass rate: same prompts with and without SCBE.
2. Attack recall: Petri/Jailbreak/encoding/code-tamper corpora.
3. False allow rate: especially SLM NONE and non-Latin / low-KO-coverage cases.
4. Latency overhead: median/p95 for regex-only, KO coverage, RuntimeGate, and
   full overlays.
5. Drift curve: report attack success or deny/quarantine rate as a function of
   measured `d*` buckets.
6. Persistence effect: restart gate, reload `runtime-gate-state/v1`, prove that
   cumulative cost/trust trajectory continues.
7. Interface coverage: API, CLI, agent-bus, and library call all exercise the
   same decision envelope.

## Filing Readiness Decision

Do not submit the final non-provisional until the formula/spec reconciliation is
reviewed end-to-end in the generated DOCX and Patent Center validator. The first
cleanup pass removed the riskiest independent-claim overstatements, but the
remaining CIP/support decisions still matter.
