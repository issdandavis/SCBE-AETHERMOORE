# SCBE Non-Provisional Working Packet

Status: inventor/counsel working draft, not legal advice.
Priority target: preserve benefit of U.S. Provisional Application No. 63/961,403, filed January 15, 2026.
Conversion deadline: January 15, 2027.
Entity position: micro entity, to be verified at filing.

## Purpose

This packet is for preparing the utility non-provisional patent application from
the implemented SCBE-AETHERMOORE codebase. It should help counsel quickly see:

- what the invention is,
- what claim families are worth pursuing,
- where the code/spec support lives,
- what should be treated as continuation/CIP material if not fully supported by
  the provisional.

## Current Filing Cost Baseline

As of the USPTO fee schedule last revised May 1, 2026, a micro-entity utility
non-provisional filed electronically in Patent Center has these base USPTO fees:

- Basic utility filing fee: $70
- Utility search fee: $154
- Utility examination fee: $176
- Baseline total: $400

Avoidable surcharges:

- Paper/non-electronic filing fee: $200 micro entity
- Non-DOCX surcharge: $86 micro entity
- Each independent claim over 3: $120 micro entity
- Each claim over 20: $40 micro entity
- Multiple dependent claim fee: $185 micro entity

Practical target: keep the initial application to 3 independent claims and up to
20 total claims unless counsel has a reason to pay for more.

## Existing Application Support

Primary documents already in the repo:

- `docs/PATENT_DETAILED_DESCRIPTION.md` - current detailed description draft.
- `docs/PATENT_CLAIMS_COVERAGE.md` - claim-to-implementation support map.
- `docs/SCBE_PATENT_PORTFOLIO.md` - larger portfolio framing.
- `docs/business/PATENT_FIGURES.txt` - formal figure concepts.

Primary implementation anchors:

- `src/symphonic_cipher/scbe_aethermoore/organic_hyperbolic.py`
- `src/symphonic_cipher/scbe_aethermoore/layers_9_12.py`
- `src/symphonic_cipher/scbe_aethermoore/layer_13.py`
- `src/governance/runtime_gate.py`
- `src/governance/bijective_tamper.py`
- `src/governance/identifier_canonicality.py`
- `src/tokenizer/ss1.ts`
- `packages/kernel/src/hyperbolic.ts`
- `packages/kernel/src/languesMetric.ts`
- `src/agentic/quarantine_lock.py`

## Invention Summary

SCBE is a computer-implemented governance and authorization system for AI,
agentic tooling, and software actions. Instead of relying only on a classifier or
static allow/block list, SCBE transforms an input/action/context into a geometric
state, measures distance from trusted operational regions in hyperbolic space,
applies semantic weights and temporal/coherence signals, and emits a governed
decision such as ALLOW, REVIEW, QUARANTINE, or DENY.

The core protectable mechanism is the combination of:

1. context/action encoding into a bounded hyperbolic manifold,
2. hyperbolic distance or drift measurement from trusted state,
3. harmonic cost scaling that increases with drift,
4. semantic/tongue weighting that affects the cost or route,
5. runtime decision gating that changes system behavior based on the measured
   trajectory,
6. tamper/canonicality checks for code or identifier-level adversarial input.

## Claim Strategy

### Independent Claim 1 - Method: Hyperbolic Governance Gate

Protect the broad method of governing a computational action by:

- receiving an input, proposed tool call, code change, or authorization request;
- generating a context vector from the request;
- embedding that vector into a bounded non-Euclidean manifold, preferably a
  Poincare ball;
- computing hyperbolic distance between the embedded vector and at least one
  trusted center or operational region;
- applying a cost function that increases as distance/drift increases;
- combining the cost with one or more semantic, temporal, or coherence signals;
- generating a governance decision that allows, reviews, quarantines, or denies
  the action.

This is the broadest and most important claim family.

### Independent Claim 2 - System: Runtime Enforcement Architecture

Protect the deployed system:

- processor and memory;
- governance pipeline executable by the processor;
- semantic encoder;
- hyperbolic distance engine;
- harmonic cost/scoring engine;
- decision gate;
- audit/receipt output;
- optional quarantine lock module that restricts execution resources or tools.

This should cover APIs, CLIs, agent buses, and local runtime services.

### Independent Claim 3 - Computer-Readable Medium: Tamper-Aware Governance

Protect the newer code-supported improvement:

- instructions that compute a canonical representation of source/input;
- perform encode/decode or normalization comparison;
- produce a bijective tamper or identifier-canonicality signal;
- escalate the runtime decision when the signal indicates encoding-level,
  syntax-level, or confusable-identifier tampering.

Counsel should decide whether this belongs in the same non-provisional if fully
supported by the January 15, 2026 provisional, or whether it should be a
continuation-in-part / separate application.

## Draft Claims

### Claim 1 - Method

1. A computer-implemented method for governing execution of a computational
   action, the method comprising:
   receiving, by one or more processors, a request associated with the
   computational action;
   generating, from the request, a context representation comprising one or more
   semantic, operational, or temporal features;
   transforming the context representation into an embedded point in a bounded
   hyperbolic space;
   computing a hyperbolic distance between the embedded point and at least one
   trusted reference point or trusted reference region in the bounded hyperbolic
   space;
   computing a governance cost from the hyperbolic distance using a nonlinear
   cost function that increases as the hyperbolic distance increases;
   combining the governance cost with at least one additional governance signal
   selected from semantic weighting, temporal drift, spectral coherence, spin
   coherence, identifier canonicality, or bijective tamper detection; and
   emitting a governance decision controlling whether the computational action is
   allowed, reviewed, quarantined, or denied.

2. The method of claim 1, wherein the bounded hyperbolic space comprises a
   Poincare ball and the transforming comprises applying a tanh-normalized
   projection with epsilon clamping to keep the embedded point inside an open
   unit ball.

3. The method of claim 1, wherein the hyperbolic distance is computed using an
   arccosh distance formula over the bounded hyperbolic space.

4. The method of claim 1, wherein the nonlinear cost function comprises a
   harmonic wall function of the form R raised to a power dependent on the
   hyperbolic distance.

5. The method of claim 1, wherein the additional governance signal comprises a
   six-axis semantic weighting system in which each semantic axis has a
   predetermined weight and phase relationship.

6. The method of claim 5, wherein the predetermined weights are based on powers
   of the golden ratio.

7. The method of claim 1, further comprising accumulating state across a
   plurality of requests and increasing or decreasing the governance decision
   severity based on trajectory drift across the plurality of requests.

8. The method of claim 1, wherein a QUARANTINE decision applies a containment
   mode that restricts available tools, execution time, execution permissions, or
   outbound effects of the computational action.

### Claim 9 - System

9. A system for runtime governance of agentic or artificial-intelligence
   actions, the system comprising:
   at least one processor; and
   a non-transitory memory storing instructions that, when executed by the at
   least one processor, cause the system to:
   classify a proposed action into a context representation;
   map the context representation into a hyperbolic geometry representation;
   measure drift of the proposed action relative to a trusted state;
   calculate a harmonic governance cost from the measured drift;
   apply a decision gate to the harmonic governance cost and one or more
   auxiliary signals; and
   route the proposed action according to a decision selected from at least
   allow, review, quarantine, and deny.

10. The system of claim 9, wherein the system is exposed through at least one of
    an application programming interface, command-line interface, agent bus, or
    local runtime service.

11. The system of claim 9, wherein the memory stores a persistent runtime state
    comprising at least a centroid, cumulative cost, query count, trust history,
    or immune memory, and wherein the persistent runtime state is restored after
    process restart.

12. The system of claim 9, wherein the auxiliary signals include a Petri-style
    pattern filter, a non-Latin or tongue coverage gate, a small-language-model
    router, or a deterministic high-risk instruction gate.

13. The system of claim 9, wherein the quarantine route applies a non-error
    containment state that blocks or limits subsequent execution rather than
    treating the action as an ordinary runtime crash.

14. The system of claim 9, wherein the system emits an audit receipt comprising
    at least the decision, score or cost, signal identifiers, and one or more
    decision-relevant metadata fields.

### Claim 15 - Computer-Readable Medium

15. A non-transitory computer-readable medium storing instructions that, when
    executed by one or more processors, cause the one or more processors to:
    receive source text, code, or an identifier-containing input;
    generate a normalized or canonical form of the input;
    compare the input to the normalized or canonical form using a bijective
    encoding, decoding, or retokenization operation;
    compute a tamper signal based on a mismatch, syntax failure, canonicality
    failure, or confusable identifier condition; and
    provide the tamper signal to a governance gate that escalates or blocks a
    proposed computational action.

16. The medium of claim 15, wherein the bijective encoding maps bytes to tokens
    and back to bytes without loss.

17. The medium of claim 15, wherein the canonical form includes Unicode
    normalization.

18. The medium of claim 15, wherein the governance gate denies the proposed
    computational action when the tamper signal exceeds a deny threshold.

19. The medium of claim 15, wherein the governance gate quarantines the proposed
    computational action when the tamper signal exceeds a quarantine threshold
    but does not exceed a deny threshold.

20. The medium of claim 15, wherein the tamper signal is recorded in an audit
    trail or decision receipt.

## Claim Support Map

| Claim family | Main support | Notes |
|---|---|---|
| Hyperbolic embedding and distance | `docs/PATENT_DETAILED_DESCRIPTION.md`; `organic_hyperbolic.py`; `packages/kernel/src/hyperbolic.ts` | Strongest priority-support candidate. |
| Harmonic wall cost | `docs/PATENT_DETAILED_DESCRIPTION.md`; `layer_13.py`; `layers_9_12.py`; `agent/types.ts` | Keep formula language broad enough to avoid locking into one constant. |
| Sacred Tongues / semantic weights | `docs/PATENT_DETAILED_DESCRIPTION.md`; `src/tokenizer/ss1.ts`; `packages/kernel/src/languesMetric.ts` | Claim as semantic weighting/routing, not lore. |
| Runtime gate | `src/governance/runtime_gate.py`; `api/`; `packages/agent-bus/` | Good system-claim bridge to product. |
| Quarantine lock | `src/agentic/quarantine_lock.py`; `tests/agentic/test_quarantine_lock.py` | Useful dependent claims. |
| Bijective tamper / canonicality | `src/governance/bijective_tamper.py`; `src/governance/identifier_canonicality.py`; runtime gate integration | May be new matter if not in provisional. Counsel should check. |

## Benchmark Evidence

The patent workbench now includes a deterministic benchmark for the
Resonant Thought Lattice / ringed retrieval-verifier controller:

- Command: `npm run patent:benchmark`
- Script: `scripts/legal/resonant_thought_lattice_benchmark.py`
- Report: `docs/legal/patent-workbench/benchmarks/resonant_thought_lattice_benchmark.md`
- JSON: `docs/legal/patent-workbench/benchmarks/resonant_thought_lattice_benchmark.json`

Current fixture result:

| Control | Mean score |
|---|---:|
| Single-pass lexical baseline | 0.6150 |
| Ringed retrieval-verifier controller | 0.9163 |

The eight-case fixture improved in 7 of 8 cases with 0 regressions. This is
deterministic controller evidence, not live LLM evidence. Safe patent-facing
language: in a fixed patent-workbench fixture, the ringed controller improved
evidence coverage and anti-pattern avoidance over a single-pass baseline under
the stated rubric.

## Figure Set To Prepare

Use `docs/business/PATENT_FIGURES.txt` as the starting point. Minimum useful
non-provisional figures:

1. Fourteen-layer pipeline block diagram.
2. Hyperbolic embedding and distance diagram in the Poincare ball.
3. Harmonic wall cost curve.
4. Semantic/tongue weighting axes and phase/weight relationship.
5. Runtime decision gate: allow/review/quarantine/deny.
6. Bijective tamper/canonicality detection flow.
7. Agent-bus/API/CLI deployment architecture.
8. Quarantine lock containment flow.

## Attorney Review Questions

1. Which drafted claims are fully supported by the January 15, 2026 provisional?
2. Should bijective tamper/canonicality be included here, filed as a CIP, or
   split into a second application?
3. Should the independent claims use "hyperbolic space" broadly or "Poincare
   ball" narrowly with broader dependent variants?
4. Should "Sacred Tongues" appear in claims, or should claims use neutral terms
   like "six-axis semantic weighting system" and keep the named vocabulary in
   the specification?
5. Should the non-provisional include both AI governance and general access
   control embodiments, or should those be separated for restriction-risk
   control?
6. Is the initial claim set kept at or below 3 independent / 20 total claims to
   preserve the micro-entity baseline fee?

## Immediate Next Steps

1. Export the current provisional as filed, including drawings and receipt.
2. Have counsel compare this packet against the filed provisional for written
   description support.
3. Freeze a canonical figure list and convert the top figures into formal patent
   drawings.
4. Convert `docs/PATENT_DETAILED_DESCRIPTION.md` into DOCX-format
   specification sections.
5. Decide whether to file only the supported core now and reserve newer
   improvements for continuation/CIP.
