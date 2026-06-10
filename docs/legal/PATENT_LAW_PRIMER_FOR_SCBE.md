# Patent Law Primer For SCBE
## SCBE-2026-0001 / U.S. Provisional Application No. 63/961,403

Status: internal pro-se workbench, not legal advice.

This primer turns general patent-law concepts into the specific working rules
for the SCBE non-provisional preparation.

## 1. What A Patent Does

A patent does not give the inventor automatic permission to practice the
invention. It gives the patent owner a right to exclude others from making,
using, selling, offering to sell, or importing the claimed invention.

For SCBE, the practical question is:

> What exact computer-implemented system and method do the claims exclude others
> from copying?

That means the claims matter more than the marketing language. The title,
abstract, drawings, and specification explain the invention, but the claims
define the legal boundary.

## 2. Patent Type

SCBE belongs in the utility-patent lane.

Likely statutory categories:

- process / method;
- machine / system;
- manufacture, in the form of a non-transitory computer-readable medium storing
  executable instructions.

Design and plant patents are not the right fit for the SCBE governance system.

## 3. Core Patentability Gates

### 101: Patent-Eligible Subject Matter

Risk: SCBE uses math, geometry, semantic scoring, and decision rules. If claimed
too abstractly, it can look like a mathematical concept or mental process.

SCBE drafting response:

- claim runtime enforcement, not just scoring;
- recite concrete computer operations;
- show a practical application: controlling execution of agentic actions,
  blocking tool dispatch, entering quarantine, updating gate state, and issuing
  audit receipts.

Good claim direction:

```text
receive action -> encode state -> compute nonlinear drift/cost -> determine
governance state -> control execution of the action
```

Weak claim direction:

```text
analyze intent and decide whether it is safe
```

### 102: Novelty

Risk: pieces of SCBE are known separately:

- embeddings;
- anomaly detection;
- access control;
- policy engines;
- control-flow integrity;
- cryptographic receipts;
- LLM safety filters.

SCBE drafting response:

- focus on the ordered combination;
- distinguish runtime execution control from passive classification;
- log prior art by claim element and by combination.

### 103: Nonobviousness

Risk: an examiner may argue that it would be obvious to combine embeddings,
policy gates, and audit logs for AI security.

SCBE drafting response:

- emphasize the specific nonlinear geometric authorization path;
- emphasize stateful trajectory/drift behavior;
- emphasize semantic weighting axes integrated into runtime enforcement;
- emphasize topological CFI and quarantine/audit effects as part of the same
  gate.

### 112: Written Description

Risk: a claim element is not supported by the filed provisional.

SCBE drafting response:

- every claim element needs a support citation;
- support can come from the filed provisional, drawings, or specification as
  filed;
- current repo code is evidence for technical reality, but it does not
  automatically create 2026-01-15 priority unless the provisional disclosed the
  same feature.

### 112: Enablement

Risk: the application says what the system does but does not teach a skilled
engineer how to make and use it.

SCBE drafting response:

- include data structures;
- include formulas;
- include flow diagrams;
- include example thresholds and decision states;
- include pseudocode or implementation descriptions;
- separate working examples from prophetic/future embodiments.

### 112: Definiteness

Risk: coined terms are unclear.

SCBE drafting response:

- define coined terms in the specification;
- use neutral terms in claims;
- pair project vocabulary with standard engineering language.

Examples:

| Project term | Claim/spec phrasing |
|---|---|
| Sacred Tongues | semantic weighting axes or context channels |
| Harmonic Wall | bounded nonlinear governance score |
| GeoSeal | governance gate and audit receipt mechanism |
| Spiralverse | provenance/origin context, not a required claim term |

## 4. Current SCBE Filing Posture

| Item | Status |
|---|---|
| Provisional application | Filed |
| Application number | 63/961,403 |
| Filing date | 2026-01-15 |
| Title | System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity |
| Non-provisional working deadline | 2027-01-15 |
| Entity posture | Micro entity, verify at filing |

The non-provisional must be filed within the required benefit window to preserve
normal priority to the provisional. The application should identify the
provisional application number in the benefit claim.

## 5. What Can Be Added

### Safe To Add As Explanation

These can usually be added to the non-provisional draft as long as they explain
the already-disclosed invention and do not introduce a new invention:

- clearer definitions;
- better figures;
- pseudocode;
- alternative wording for disclosed mechanisms;
- examples of already-disclosed embodiments;
- claim language supported by the provisional.

### Add With Support Review

These may be claimable if the filed provisional supports them:

- topological control-flow integrity;
- semantic/tongue weighting;
- harmonic-wall cost;
- quarantine/review/deny states;
- audit receipts;
- tamper/canonicality checks;
- persistent runtime gate state.

### Likely Continuation/CIP Candidates If Not In Provisional

These may still be valuable, but should not be assumed to get the provisional
priority date without support:

- narrative-derived governance trajectory;
- Go-board/access-manifold admissibility;
- fleet governance;
- agent-bus workflow harness;
- model self-harness;
- newer long-term symbiotic agent orchestration.

## 6. SCBE Claim Strategy

Default target:

- 3 independent claims;
- up to 20 total claims;
- no multiple dependent claims unless deliberately chosen;
- DOCX filing for specification, claims, and abstract.

Suggested independent claims:

1. Method claim:
   computer-implemented geometric authorization and enforcement.
2. System claim:
   one or more processors and runtime gate components.
3. Computer-readable medium claim:
   instructions for tamper-aware governance and execution control.

Dependent claim buckets:

- semantic weighting axes;
- Poincare/hyperbolic embodiment;
- harmonic-wall score;
- topological CFI;
- quarantine containment;
- bijective/canonicality tamper signal;
- audit receipt / cryptographic envelope;
- CLI/API/agent-bus embodiment;
- persistent gate state.

## 7. Filing Process Checklist

1. Export filed provisional packet and receipt from Patent Center.
2. Map current claim families to filed provisional support.
3. Finish prior-art search log.
4. Draft claims.
5. Draft specification with definitions, examples, and figures.
6. Prepare drawings.
7. Prepare abstract under 150 words.
8. Prepare application data sheet.
9. Prepare inventor oath/declaration.
10. Re-check fees and micro-entity status on filing day.
11. Validate DOCX in Patent Center.
12. File non-provisional and save all receipts.

## 8. Game Model Summary

The field is the law. The ball is a proposed claim element. The pitcher is the
technical invention advocate. The batter is the client-coverage advocate. The
umpire is the examiner. The mathematician checks whether the transform is real.
The scientist/engineer checks whether the system can be made and used.

Each round ends with one call:

```text
PRIMARY | DEPENDENT | REVIEW | CONTINUATION | DROP
```

That call decides whether the feature goes into an independent claim, dependent
claim, support-review queue, continuation/CIP queue, or discard pile.

## 9. Official Reference Set

- USPTO patent basics:
  https://www.uspto.gov/patents/basics/essentials
- USPTO nonprovisional utility filing guide:
  https://www.uspto.gov/patents-getting-started/patent-basics/types-patent-applications/nonprovisional-utility-patent
- MPEP 2106, subject matter eligibility:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2106.htm
- MPEP 2163, written description:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2163_07_a.htm
- MPEP 2164, enablement:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2164_01.htm
- Cornell Legal Information Institute, U.S. patent statutes:
  https://www.law.cornell.edu/uscode/text/35
- WIPO patent overview:
  https://www.wipo.int/patents/en/
