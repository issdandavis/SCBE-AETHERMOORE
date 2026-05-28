# SCBE Non-Provisional Packet Review

Date: 2026-05-28

Application family: U.S. Provisional Application No. 63/961,403, filed January
15, 2026.

Title: System and Method for Hyperbolic Geometry-Based Authorization with
Topological Control-Flow Integrity.

Scope: filing-packet review for internal pro se preparation. This is an
engineering and procedural review, not legal representation.

## Official Filing Constraints Checked

- USPTO utility guidance confirms the non-provisional must be filed within the
  12-month provisional pendency period to claim priority.
- USPTO DOCX guidance confirms that specification, claims, and abstract in new
  utility non-provisional applications should be filed in DOCX to avoid the
  non-DOCX surcharge.
- Patent Center guidance confirms that a single multi-section DOCX can contain
  specification, claims, abstract, and drawings, while drawings can also be
  filed separately.
- USPTO fee schedule confirms the excess-claim structure: independent claims
  over three and total claims over twenty trigger extra fees. The current packet
  has three independent claims and twenty-five total claims, meaning five
  excess total claims.

## Packet Structure Review

Reviewed file:

- `docs/legal/SCBE_NONPROVISIONAL_SPEC_v1.docx`

Local structural extraction found the following section order:

1. Title
2. Cross-Reference to Related Applications
3. Background of the Invention
4. Summary of the Invention
5. Brief Description of the Drawings
6. Detailed Description of Preferred Embodiments
7. Claims
8. Abstract

Local checks:

- Formal claims section appears once.
- Formal claim numbers are sequential: 1 through 25.
- Independent claims: 1, 9, and 15.
- Abstract word count: 117 words.
- Removed from the formal DOCX: old internal claim appendix that was previously
  leaking from the detailed-description source into the body.

## Legal-Risk Language Review

The packet was edited to avoid unsupported absolute language. Removed or
softened:

- "cannot be circumvented"
- "guarantee the system's security properties"
- "impossible cost"
- "practically impenetrable"
- "100% detection rate"
- "indistinguishable" fail-to-noise claims
- the old claim-1 `B^(k*d)` whereby clause

Replacement posture:

- The claims now frame drift cost as a nonlinear increasing function used to
  control execution.
- Fail-to-noise is framed as same-length noise or pseudorandom-looking audit
  output rather than cryptographic indistinguishability.
- Simulated results are marked as fixture-set outcomes rather than universal
  performance claims.

## Formula Consistency Review

The specification now treats the harmonic wall as a family of alternative
embodiments rather than one universal formula:

- `H(d, R) = R^(d^2)`
- `H = 1/(1+d+2*pd)`
- `C = pi^(phi*min(d*, d_max))`

This matches the implementation reality better than forcing every embodiment
to be superexponential or unbounded. Claim 3 recites the variants as
alternatives.

## Hardware / Interface Support

The packet includes implementation hooks for a real computing system rather
than only abstract math:

- one or more processors;
- non-transitory memory;
- persistent runtime state;
- REST API endpoint;
- agent-bus service;
- command-line interface;
- programmatic client library;
- downstream executor verifying signed receipts;
- post-quantum receipt module using ML-DSA-65 and ML-KEM-768;
- durable session-state restore after restart.

This supports the Alice/101 posture by tying the math to configured computer
execution, runtime state, quarantine containment, audit receipts, and tamper
gating.

## Figure Coverage Review

Drawing set:

- FIG. 1: 14-layer pipeline.
- FIG. 2: alternative harmonic cost / safety functions.
- FIG. 3: Poincare ball, centroid, embedded point, hyperbolic distance.
- FIG. 4: six-axis golden-ratio semantic weighting.
- FIG. 5: Sacred Egg five-predicate deferred authorization.
- FIG. 6: cheapest-reject-first pre-filter stack.
- FIG. 7: runtime decision gate.
- FIG. 8: bijective tamper detection.
- FIG. 9: deployment architecture.

Diagram changes made in this review:

- FIG. 2 now shows all three disclosed cost/safety embodiments instead of only
  the old `R^(d^2)` curve.
- FIG. 5 now says failure returns same-length noise or pseudorandom-looking
  audit output instead of cryptographic indistinguishability.
- FIG. 6 now describes the harmonic wall as a nonlinear cost/safety threshold
  instead of only an `R^(d^2)` threshold.
- FIG. 7 now describes deny output as same-length audit noise instead of
  indistinguishable random bytes.

## Claim Support Risk Tiers

- Low risk: claims 1-8, runtime gate, hyperbolic distance, centroid, nonlinear
  cost, semantic weighting, durable state, immune/adversarial memory, and
  fail-to-noise output.
- Medium risk: claims 9-14, deployment surfaces, quarantine containment,
  cheapest-reject-first stack, post-quantum receipts, audit receipt fields.
- Medium-to-high risk: claims 15-20, bijective tamper detection, AST
  fingerprint comparison, confusable identifier checks, NFC stub fallback.
- Higher risk / continuation-style: claims 21-25, especially multi-predicate
  authorization containers and physics-based juggling coordination. These have
  implementation and concept support, but should be checked against the
  provisional text before relying on the January 15, 2026 priority date.

## Remaining Manual Filing Blockers

- Patent Center ADS fields: enter address, ZIP, and phone directly in Patent
  Center; do not store them in repo.
- DOCX validation: upload `docs/legal/SCBE_NONPROVISIONAL_SPEC_v1.docx` to
  Patent Center DOCX Validator or training mode and fix any USPTO-specific
  warnings/errors.
- Fee verification: re-check filing/search/examination and excess-claim fees on
  the USPTO fee schedule on the day of filing.
- Priority support: compare claims 21-25 against the exact filed provisional
  text before filing if preserving the provisional priority date for those
  features matters.

## Local Verification Commands

```powershell
python docs\legal\patent-figures\generate_patent_figures.py
python docs\legal\build_patent_docx.py
node -e "const fs=require('fs'); JSON.parse(fs.readFileSync('docs/legal/patent-workbench/filing_readiness_checklist.json','utf8')); console.log('json ok')"
git diff --check -- docs\PATENT_DETAILED_DESCRIPTION.md docs\legal\build_patent_docx.py docs\legal\PATENT_CLAIMS_EXPANDED_v2.md docs\legal\patent-figures\generate_patent_figures.py docs\legal\patent-workbench\filing_readiness_checklist.md docs\legal\patent-workbench\filing_readiness_checklist.json
```

