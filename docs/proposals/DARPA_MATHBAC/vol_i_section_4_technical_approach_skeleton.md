# Vol I Section 4 Technical Approach Skeleton

Status: Draft skeleton, 2026-05-31
Proposal: DARPA-PA-26-05 MATHBAC TA1
Scope: Technical Approach body draft, not final submission prose

## 4.0 Technical Approach Overview

SCBE proposes a TA1 mathematical framework for designing, evaluating, and
optimizing agentic communication protocols in a bounded science-discovery
setting. The Phase I instantiation will use NMR spectroscopy as the selected
science subdomain, with two task families:

1. 1H NMR to molecular-structure prediction.
2. Mixture-spectrum deconvolution.

These choices implement Decision Boxes A-D as follows:

| Decision | Selected option | Proposal effect |
|---|---|---|
| A | NMR spectroscopy | Fixes the science subdomain and grounds the worked example. |
| B | ChemBERTa-77M primary SSM + Qwen2.5-Coder-0.5B-Instruct orchestrator | Provides a small science model with accessible chemistry latent space plus a general-purpose orchestration agent. |
| C | Mixtral-8x7B baseline protocol model | Provides the TA1 mixture-of-experts baseline comparison. |
| D | 1H NMR structure prediction + mixture-spectrum deconvolution | Supplies the two Phase I task families and IV&V challenge seed families. |

The technical approach is organized around five mathematical challenges named
by the PA. SCBE treats these as one composed operator problem rather than five
separate features:

```text
T = L14 o L13 o L12 o ... o L1
```

Each layer is a typed transformation over token streams, latent-state traces,
protocol-graph state, and verifier outputs. The central Phase I claim is that
multi-agent communication can be evaluated as a composed operator whose
stability, convergence, and semantic adequacy are measurable from captured
communication streams and accessible latent spaces.

Source anchors:

- `ta1_mathematical_challenges_v1.md`
- `proposer_added_metrics_v1.md`
- `decision_boxes_a_d_prep.md`
- `pa_26_05_compliance_checklist.md`

## 4.1 Agent Operator Model and Reduced-Order Representation

PA challenge addressed: TA1-MC-1, Agents as Operators / Systems.

SCBE will represent each participating agent as a local operator with:

- an input token stream,
- an accessible or partially accessible latent-state trace,
- a reduced-order representation of local response dynamics,
- an output stream that can be checked against task and protocol constraints.

For the NMR instantiation, the agent set will include:

| Agent role | Primary model | Function |
|---|---|---|
| Spectral encoder | ChemBERTa-77M plus spectral feature adapter | Encodes molecular candidates and latent chemical state. |
| Orchestrator | Qwen2.5-Coder-0.5B-Instruct | Schedules tool calls, decomposes task steps, and writes structured protocol messages. |
| Baseline protocol model | Mixtral-8x7B | Supplies the mixture-of-experts comparison protocol. |
| Verifier/oracle components | Deterministic scripts plus metric calculators | Score NMR-fit loss, structural validity, and protocol metrics. |

For 1H NMR to structure prediction, an input spectrum will be transformed into
a candidate-structure search problem. For mixture-spectrum deconvolution, the
same operator formalism will be applied to multiple overlapping sources, making
agent-to-agent communication necessary rather than decorative.

Phase I work products:

- M1: finalize the agent roster, model-access plan, latent-space capture plan,
  and initial ROM specification.
- M3: calibrate low-rank ROMs on the two NMR task families.
- M9: report ROM fidelity against held-out NMR tasks and IV&V challenge cases.

Proposal text to write later:

> We do not claim that the full agent dynamics are linear. We claim that the
> local behavior of each agent can be approximated by a reduced-order operator
> around observed campaign states, and that the approximation error is itself a
> measured deliverable.

Risk and mitigation:

| Risk | Mitigation |
|---|---|
| ChemBERTa latent traces do not encode enough NMR-relevant information. | Add explicit spectral descriptors as adapter inputs while keeping the model fixed. |
| Qwen orchestrator dominates the chemistry model. | Require protocol messages to expose which model produced each step and score MEE/ACV by source role. |
| ROM fidelity is weak early in Phase I. | Treat low fidelity as a measured M3 failure mode and refine rank by spectral-gap thresholding. |

## 4.2 Protocol Graph and Hamiltonian Multi-Well Network

PA challenge addressed: TA1-MC-2, Communication Protocols in Operator Networks.

SCBE will model the campaign as a time-windowed protocol graph:

```text
G_t = (V, E_t)
```

where vertices are agents, tools, verifier components, or task-state stores, and
edges are communication events. Each edge will carry:

- source and target role,
- message type,
- declared task dependency,
- latency and token cost,
- verifier artifact references,
- latent-delta summaries when available.

The NMR task families exercise two graph regimes:

| Task family | Protocol regime |
|---|---|
| 1H NMR to structure prediction | Mostly single-source inversion with verifier feedback. |
| Mixture-spectrum deconvolution | Coupled-agent inference with competing hypotheses and reconciliation. |

SCBE will compute graph and spectral readouts over this protocol graph,
including algebraic connectivity, cascade detection, recurrence detection, and
phase-transition markers. This is a Phase I instrumentation commitment, not a
claim that all protocol-graph tools already ship in the current repository.

Phase I work products:

- M3: protocol-graph schema and synthetic graph tests.
- M6: CDPTI integration over captured campaign logs.
- M13: side-by-side protocol-graph comparison against the Mixtral baseline.

Proposal text to write later:

> A protocol is superior only if it improves task performance while preserving
> graph-level structure: no hidden state jumps, no unrecorded verifier bypass,
> no dependency cycles disguised as progress.

Risk and mitigation:

| Risk | Mitigation |
|---|---|
| Protocol graph instrumentation is not complete at kickoff. | Declare M3 graph instrumentation as an explicit work-package with schema and tests. |
| Mixture deconvolution creates dense graphs that are hard to interpret. | Use PIS and CDPTI summaries to compress graph behavior into IV&V-readable metrics. |
| Baseline model emits fewer explicit protocol events. | Wrap all baseline calls in the same event logger so hidden simplicity is not rewarded. |

## 4.3 Performance Prediction via Harmonic-Wall Scoring and Lyapunov Certification

PA challenge addressed: TA1-MC-3, Performance Prediction.

SCBE will predict campaign performance using a cost vector and a stability
score. The cost vector will include:

```text
c_t = (tokens_t, wall_clock_t, verifier_cost_t, retry_cost_t, compliance_cost_t)
```

For NMR, the task-specific outcome quantities will include:

- spectrum-to-prediction loss,
- molecular validity,
- candidate-rank accuracy,
- mixture-component recovery,
- structural ambiguity flags,
- verifier agreement.

The harmonic-wall score will be used as the canonical Phase I scalar for
distance-to-stable-protocol behavior:

```text
H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)
```

where `d_H` is the hyperbolic distance term and `pd` is predictive density.
Vol I will state that this is the committed L12 boundary form; legacy variants
remain codebase history or specialized extensions, not proposal claims.

The Lyapunov-style convergence statement remains intentionally empirical:

```text
V(t) = -log H(t)
V(t + 1) <= (1 - eta) V(t) + b
```

SCBE will measure `eta` and `b` per task family during Phase I rather than
claiming universal constants in the proposal.

Phase I work products:

- M3: initial `eta`, `b`, and threshold calibration on proposer task data.
- M6: IV&V-ready performance-prediction curves.
- M13: living-metric comparison to the baseline protocol.

Proposal text to write later:

> The proposal does not ask DARPA to accept a hand-tuned success metric. It
> commits to a bounded score, reports the constants needed for falsification,
> and gives IV&V the captured traces needed to recompute the score.

Risk and mitigation:

| Risk | Mitigation |
|---|---|
| Harmonic-wall constants do not transfer cleanly between the two NMR task families. | Report task-family-specific calibration and use transfer gap as an adaptability metric. |
| Spectrum ambiguity causes correct multiple answers. | Score structural equivalence classes and ambiguity flags, not only exact-match labels. |
| Baseline comparison over-focuses on end-state accuracy. | Pair outcome metrics with MEE, ACV, CDPTI, and PIS trace metrics. |

## 4.4 Protocol Optimization as a Constrained MDP over Tier Actions

PA challenge addressed: TA1-MC-4, Protocol Optimization.

SCBE will treat protocol design as a constrained optimization problem:

```text
minimize   E[sum_t c_t]
subject to task_success >= tau
           ACV >= ACV_min
           oracle_confidence >= gamma
```

The discrete action space is the governance tier:

```text
A = {ALLOW, QUARANTINE, ESCALATE, DENY}
```

Continuous controls include temperature, retry budget, verifier budget, model
selection, and allowed tool depth. The NMR tasks give concrete success
functions:

| Task family | Success function |
|---|---|
| 1H NMR to structure prediction | Correct structure or correct equivalence class within top-k candidates. |
| Mixture-spectrum deconvolution | Correct component count and component identities within calibrated tolerance. |

The Phase I optimization loop will compare:

1. handcrafted baseline protocol,
2. Mixtral baseline protocol,
3. SCBE-governed protocol with metric feedback,
4. ablated SCBE protocol without selected metrics.

Phase I work products:

- M1: baseline protocol definition.
- M6: optimization objective and first ablation table.
- M13: side-by-side IV&V rubric comparison with mathematical explanation.

Proposal text to write later:

> The governance tier is not a compliance wrapper after the fact; it is the
> discrete action layer of the protocol optimizer.

Risk and mitigation:

| Risk | Mitigation |
|---|---|
| Optimization improves speed but reduces trace quality. | ACV and MEE are hard side constraints, not optional dashboards. |
| Model-selection policy overfits proposer data. | Hold out IV&V-style challenge families and report adaptability gap. |
| Mixtral baseline has higher raw task accuracy. | Evaluate whether SCBE improves trace quality, stability, and explainability even when raw accuracy is close. |

## 4.5 Oracle Construction via Spectral, Information, and Verifier Triplet

PA challenge addressed: TA1-MC-5, Construction of an Oracle.

SCBE will define semantic-understanding confirmation as a triplet:

```text
Oracle pass iff:
  I(X_i; X_j) >= I_min
  coherence(X_i, X_j) >= gamma_min
  MEE(message) >= MEE_min
```

For NMR, the oracle will be grounded in:

- spectral fit between proposed structure and observed 1H NMR signal,
- consistency of molecular descriptors and chemistry constraints,
- evidence emitted by the agent chain,
- verifier agreement across deterministic checks.

The oracle is falsifiable: ablating mutual-information, spectral-coherence, or
verifier-evidence checks must reduce measured performance on held-out
confirmed/unconfirmed communication acts.

Phase I work products:

- M3: initial `(I_min, gamma_min, MEE_min)` calibration.
- M6: ablation report showing oracle component necessity.
- M14: oracle packaged inside the computational design tool.

Proposal text to write later:

> A message is not counted as understood merely because a downstream agent
> continued the conversation. It is counted as understood only when information
> transfer, spectral alignment, and verifier evidence jointly pass threshold.

Risk and mitigation:

| Risk | Mitigation |
|---|---|
| Mutual-information estimates are noisy on short campaigns. | Use sliding windows and report confidence intervals. |
| NMR spectra contain ambiguous mappings. | Treat ambiguity as a first-class oracle output rather than a failure to hide. |
| Verifier artifacts are sparse early in the campaign. | Use MEE density as a protocol-design pressure and milestone metric. |

## 4.6 Metrics and IV&V Interface

SCBE will report the required TA1 rubric metrics:

- percent success-rate improvement,
- speedup,
- adaptability/generalizability.

SCBE will also report four proposer-added metrics from Attachment X:

| Metric | Role in Section 4 |
|---|---|
| MEE | Measures checkable mathematical evidence emitted during the protocol. |
| ACV | Measures structural compliance with unitarity, locality, causality, symmetry, and composition. |
| CDPTI | Measures phase transitions in communication dynamics. |
| PIS | Provides a fixed-dimensional protocol identity signature for cataloging and comparison. |

All four metrics are computed from data the proposal already commits to
capture: communication streams, event logs, verifier artifacts, and accessible
latent traces. IV&V receives the captured traces, scoring scripts, and output
artifacts needed to reproduce each metric.

## 4.7 Technical Work Packages

| Work package | Months | Output |
|---|---:|---|
| WP1: NMR task-family harness | M1-M3 | Two task families, data schema, baseline protocol, success functions. |
| WP2: Latent capture and ROM | M1-M6 | Model-access plan, ROM calibration, fidelity report. |
| WP3: Protocol graph instrumentation | M1-M6 | `G_t` schema, spectral readouts, cascade and recurrence detectors. |
| WP4: Metric calculators | M3-M9 | MEE, ACV, CDPTI, PIS scoring package. |
| WP5: Optimization loop | M6-M13 | constrained-MDP protocol optimizer and ablation table. |
| WP6: Computational design tool | M9-M14 | packaged executable toolchain for IV&V testing. |
| WP7: Protocol catalog and final theory packet | M13-M16 | catalog entries, final framework report, Phase II handoff. |

## 4.8 Milestone Alignment

| Milestone | Section 4 technical evidence |
|---|---|
| M1 | Subdomain, models, baseline protocol, latent-space plan, first rubric analysis. |
| M3 | Initial successes/failures, metric calibration, protocol-graph schema, ROM draft. |
| M6 | Framework demonstration with IV&V-ready captured communication and latent data. |
| M9 | Software-suite report, ROM outputs, IV&V challenge progress. |
| M13 | Side-by-side baseline comparison with mathematical explanation. |
| M14 | Computational design tool demonstration and test results. |
| M16 | Final theory, implementations, catalog, and Phase II plan. |

## 4.9 Generalization Beyond NMR

NMR is the Phase I proving ground, not the boundary of the mathematics. The
operator, protocol-graph, optimization, and oracle framework is designed to
generalize to:

- cheminformatics and reaction prediction,
- materials discovery,
- theorem-proving or symbolic science domains,
- code/security auditing domains where protocol trace quality is central.

The proposal should be explicit that cross-domain generalization is claimed at
the protocol-structure level, while task-specific scoring functions must be
recalibrated per subdomain.

## 4.10 Drafting Gaps Before Final Vol I Integration

Open drafting gaps:

1. Add exact baseline datasets and data-license language for the two NMR task
   families.
2. Fill numerical baseline-performance table for current methods.
3. Insert compute assumptions for ChemBERTa, Qwen, and Mixtral runs.
4. Decide whether NMR spectra are represented as raw arrays, feature vectors,
   text summaries, or all three for IV&V.
5. Add Attachment X cross-references for all four proposer-added metrics.
6. Add exact Phase II reward-design paragraph.
7. Add citations in final proposal style after the Volume I template is known.

Do not finalize Vol I Section 4 until these gaps are closed or explicitly
marked as Phase I calibration items.

## 4.11 Source Map

| Source file | Used for |
|---|---|
| `decision_boxes_a_d_prep.md` | A-D recommended decisions and deferral rule. |
| `pa_26_05_compliance_checklist.md` | Mandatory TA1 clauses, milestones, IV&V interface, and proposal gaps. |
| `ta1_mathematical_challenges_v1.md` | MC-1 through MC-5 technical mapping and honest implementation-status boundaries. |
| `proposer_added_metrics_v1.md` | MEE, ACV, CDPTI, PIS definitions and PA six-field metric requirements. |
