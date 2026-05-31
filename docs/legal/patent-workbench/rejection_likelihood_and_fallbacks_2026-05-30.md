# Rejection Likelihood and Fallbacks - SCBE-2026-0001

Status: internal prosecution-prep memo, not legal advice.

Application: `19/691,526`  
Docket: `SCBE-2026-0001`  
Filed: `2026-05-28`

## Bottom Line

Expect at least one Office Action with rejections or objections. That is normal
for a software/AI/security utility application and should not be treated as
failure. The practical plan is to have fallbacks ready before the first action:

1. defend eligibility as a concrete computer-security/runtime-control
   improvement;
2. narrow claims around the strongest implemented machine pipeline;
3. separate broad/product/lore improvements into continuation or CIP candidates;
4. use benchmarks as supporting evidence, not as claim language;
5. preserve appeal/RCE as later options if amendment and argument do not close
   the case.

## Likelihood Assessment

This is qualitative. A precise probability cannot be responsibly assigned before
the application is docketed to an art unit and examiner.

| Issue | Likelihood | Why it is likely | Primary fallback |
|---|---|---|---|
| 35 USC 101 subject matter eligibility | High | Claims involve software, math, semantic weighting, and AI/runtime governance. USPTO guidance says software is not automatically abstract, but abstract-idea analysis is central for computer-implemented inventions. | Frame as a specific improvement to computer/security execution control, not a generic "do it on a computer" rule. |
| 35 USC 103 obviousness | High | Examiners commonly combine prior art references for software/security systems. Hyperbolic embeddings, authorization, anomaly scoring, and agent governance each have nearby art. | Argue the full ordered combination and amend toward concrete implementation couplings that the art does not teach together. |
| 35 USC 112 clarity / written description | Medium-high | SCBE terms are coined, claims are broad, and the spec includes many layers. Examiner may ask for clearer antecedent basis, support, or enablement. | Use definitions, claim-support matrix, figure mapping, and dependent-claim fallback amendments. |
| Restriction/election | Medium | The application includes governance gates, tokenization/tamper, semantic weighting, quarantine, and benchmark/evidence material. | Elect the core runtime-gate/security invention; reserve tokenizer/Polly/Longform/GeoSeed for continuation/CIP. |
| Formality / OPAP notice | Low-medium | Filed packet and payment evidence exist, but formal receipt must still be checked. | Respond exactly to the notice and calendar the deadline. |
| Immediate allowance | Low | Broad first filing in software/security usually requires at least one negotiation cycle. | Treat first action as information: learn examiner's theory and adapt. |

## Expected Process

1. Formal filing receipt / application record.
   Check Patent Center for the formal Filing Receipt and verify title, inventor,
   priority claim, entity status, and foreign filing license status.

2. OPAP/formality review.
   USPTO may issue a notice if an application is missing or deficient in a way
   that requires correction. A notice should state the issue, correction period,
   and any fees.

3. First Office Action on the merits.
   The examiner can issue a restriction requirement, non-final rejection, final
   rejection later in prosecution, or notice of allowability. USPTO says Office
   Action replies must address each rejection/objection and most replies have a
   six-month statutory outer limit, usually with a shorter two- or three-month
   no-extension-fee period.

4. Response cycle.
   The normal first response is argument plus claim amendments. If final
   rejection arrives later, fallback paths include amendment after final, RCE, or
   appeal if claims have been twice rejected/finally rejected.

## Fallback Stack

### Fallback A - 101 Eligibility

Use this if the examiner says the claims are an abstract idea, math, mental
process, or generic computer implementation.

Response direction:

- Emphasize a concrete runtime-control pipeline that changes execution state:
  ALLOW / QUARANTINE / DENY / REROUTE or analogous control output.
- Tie geometry and semantic weighting to a specific security/governance
  technical problem: safe tool execution under drift, tamper, or policy risk.
- Use the filed figures and pseudocode to show a configured machine process.
- Avoid arguing that "AI", "math", or "geometry" alone makes it patentable.

Amendment direction:

- Add limitations requiring measured request context, trusted centroid/reference
  state, hyperbolic distance, nonlinear cost, threshold comparison, and
  execution-state control.
- Move softer "meaning" or "consciousness" language out of claims and into
  background/story only, if present.

### Fallback B - 103 Obviousness

Use this if the examiner combines hyperbolic embeddings, access control,
anomaly detection, prompt governance, or security-policy references.

Response direction:

- Do not argue each part in isolation. Argue the ordered coupling:
  semantic weighting + hyperbolic drift + nonlinear cost + runtime gate output +
  audit/quarantine behavior.
- Distinguish flat vector access-control art from Poincare/hyperbolic
  distance-to-centroid governance if the references do not teach the same
  geometry/control coupling.
- Use benchmark evidence only as secondary support for technical effect, not as
  a substitute for claim limitations.

Amendment direction:

- Narrow toward the strongest implemented features in `runtime_gate.py`,
  bijective tamper/canonicality modules, quarantine lock, and agent-bus
  governance receipts.
- Add dependent claims around specific fail-to-noise/quarantine/reroute behavior
  instead of trying to win every broad claim first.

### Fallback C - 112 Written Description / Enablement / Clarity

Use this if the examiner says coined terms are unclear or the spec does not
support the full scope.

Response direction:

- Point to the filed definitions, figures, pseudocode, and claim-support matrix.
- Translate coined terms into neutral machine terms:
  semantic weighting axes, runtime gate, audit receipt, containment state,
  canonical identifier, tamper signal.
- If an element is only supported by post-filing code, do not force it into this
  case. Move it to the continuation/CIP log.

Amendment direction:

- Replace brand/lore labels with structural terms.
- Add antecedent basis and explicit data-flow steps.
- Preserve broad concept in one claim family only if the spec supports it.

### Fallback D - Restriction / Election

Use this if the examiner says the claims cover multiple inventions.

Likely groups:

- Core runtime/hyperbolic governance gate.
- Bijective tamper and identifier canonicality.
- Semantic/tokenizer/tongue weighting.
- Quarantine/agent containment.
- Later Longform/Polly/GeoSeed/operator tooling.

Preferred election:

- Elect the core runtime/hyperbolic governance gate first because it is the
  strongest anchor tying math to machine control and security execution.

Reserve:

- Tokenizer, Polly Pad, Longform Bridge, GeoSeed orbital model, and station/agent
  tooling for continuation/CIP candidates if the examiner splits inventions.

### Fallback E - Final Rejection

If the case reaches final rejection:

- Interview/amend if the examiner identifies allowable subject matter.
- File RCE if useful amendments/evidence remain.
- Appeal to PTAB only when the legal/factual issue is clean enough to justify
  the cost and delay.
- Consider continuation before abandonment or issuance if broader claim coverage
  is still strategically valuable.

## Practical Prep Work To Do Now

- Build a 101 response shell tied to the filed claims and MPEP 2106.
- Build a 103 distinction chart keyed to the prior-art log.
- Build a 112 definitions/support chart replacing coined terms with neutral
  machine terms.
- Create a continuation/CIP candidate log for post-filing features:
  Longform Bridge, Polly Pad, GeoSeed orbital model, browser/rubix adapter,
  pathfinding systems, and station/keeper/operator layers.
- Keep benchmark evidence in a separate prosecution-support packet.

## Source Notes

- USPTO MPEP 2106: software is not automatically ineligible, but eligibility
  analysis under abstract-idea guidance is central for computer-implemented
  inventions.
- USPTO MPEP 2141/2144: obviousness analysis can rely on prior art plus
  articulated reasoning; conclusory reasoning should be challenged.
- USPTO Office Action guidance: replies must address each rejection/objection;
  most replies have a six-month statutory outer limit and a shorter no-fee reply
  period.
- USPTO PTAB appeal guidance: appeal becomes available after a claim has been
  twice rejected or finally rejected.
- USPTO FY budget assumptions are not application-specific, but they show the
  Office models aggregate allowance around roughly 60 percent in recent budget
  assumptions; this should not be treated as the odds for this case.

## Official Sources

- MPEP 2106, Patent Subject Matter Eligibility:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2106.htm
- MPEP 2141, Obviousness:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2141_01.htm
- MPEP 2144, Supporting a 103 Rejection:
  https://www.uspto.gov/web/offices/pac/mpep/s2144.html
- USPTO, Responding to Office Actions:
  https://www.uspto.gov/patents/maintain/responding-office-actions
- USPTO, Appeals:
  https://www.uspto.gov/patents-application-process/patent-trial-and-appeal-board/appeals
- USPTO FY 2024 Congressional Submission, Appendix V allowance assumptions:
  https://www.uspto.gov/sites/default/files/documents/fy24pbr.pdf
