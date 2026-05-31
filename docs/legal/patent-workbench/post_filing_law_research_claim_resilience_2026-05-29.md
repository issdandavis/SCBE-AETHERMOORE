# SCBE Post-Filing Law Research and Claim Resilience Map

Status: internal prosecution-prep research memo, not legal advice.

Filed application: 19/691,526  
Docket: SCBE-2026-0001  
Confirmation: 1177  
Purpose: explain what likely happens next and how the filed claim families may hold up under the legal standards an examiner is likely to apply.

## Practical Process From Here

The filing is now in prosecution. The normal path is:

1. USPTO intake and formalities review.
2. Application is docketed to an art unit and examiner.
3. Examiner searches prior art and reviews claims.
4. Examiner issues either:
   - a restriction/election requirement;
   - a non-final Office Action;
   - a notice of allowability;
   - or a formal notice requiring correction.
5. Applicant responds to every rejection, objection, and requirement.
6. Examiner either allows, reopens with another non-final action, or makes a final rejection.
7. After final, options may include amendment, request for continued examination (RCE), appeal, continuation, or abandonment.

USPTO states that an Office Action requires a properly signed written response for prosecution to continue, and that the reply must address each rejection and objection. USPTO also states that most replies must be received within six months, but Office Actions usually set a shorter two- or three-month period before extension fees apply.

Source:

- USPTO, Responding to Office Actions: https://www.uspto.gov/patents/maintain/responding-office-actions

## Main Legal Standards That Matter

### Section 101 - Patent-Eligible Subject Matter

The likely software/AI attack is that the claims are "just math" or an abstract idea on a generic computer. MPEP 2106 says a claim that recites a mathematical concept is not automatically ineligible. The key question is whether the claim as a whole integrates the judicial exception into a practical application.

SCBE defense frame:

- Do not argue that hyperbolic distance itself is patentable.
- Argue that the claimed machine uses the distance in a practical runtime control pipeline.
- Emphasize that the result changes machine behavior: allow, review, quarantine, reroute, deny, receipt, fail-to-noise, or tamper flag.
- Emphasize persisted runtime state, session centroid, execution interfaces, and audit artifacts.

Best claims under 101:

- Claims 1 and 9, because they are runtime governance/execution-control claims.
- Claims 10-11, because quarantine and ordered pre-filtering are operational machine behavior.
- Claims 15-20, because bijective tamper and AST/canonicality checks are concrete computer-security mechanisms.

More exposed claims under 101:

- Claims 3, 4, 27, and 28 if described as formulas, harmonics, or token math without the surrounding execution-control role.
- Claims 21 and 25 if described with metaphorical names rather than technical authorization-container and trajectory-scheduler language.

Source:

- MPEP 2106, Patent Subject Matter Eligibility: https://www.uspto.gov/web/offices/pac/mpep/s2106.html

### Section 102 - Novelty

Novelty asks whether a single prior-art reference teaches every element of a claim. The current internal prior-art work has not found one reference that combines:

1. proposed action represented as machine state;
2. bounded hyperbolic/Poincare state;
3. session centroid or trajectory reference;
4. nonlinear drift-to-cost calculation;
5. execution routing to allow/review/quarantine/reroute/deny;
6. tamper/audit/receipt behavior.

Current posture:

- Claim 1 is strongest if all elements stay together as an ordered runtime control process.
- A reference on hyperbolic embeddings alone should not defeat the whole claim unless it also teaches the governance/execution routing combination.
- A reference on LLM guardrails alone should not defeat the whole claim unless it also teaches the bounded geometric drift system.

Risk:

- The examiner does not need to find "SCBE" by name. A close access-control or anomaly-detection reference can still be used for individual elements.

### Section 103 - Obviousness

This is probably the hardest practical fight. MPEP 2141 frames obviousness around the claimed invention and prior art as a whole, and a hypothetical person of ordinary skill who is not an automaton and may combine references.

Likely examiner combinations:

- hyperbolic embeddings + anomaly detection;
- access-control policy engine + runtime guardrail;
- prompt-injection firewall + quarantine/deny response;
- Unicode/canonicalization security checks + code-analysis gate;
- signed audit receipt + existing cryptographic receipt systems.

SCBE defense frame:

- The invention is not one component. It is the ordered runtime composition.
- The prior art may teach representation, filtering, or auditing separately, but the claimed combination uses geometric drift as an execution-control signal with durable state.
- Benchmark evidence can help show why the combination is not an arbitrary aggregation.

Best technical evidence to build:

- Raw model baseline.
- Regex/Petri only.
- KO/tongue coverage gate only.
- RuntimeGate overlays only.
- Full SCBE route.
- Metrics: false allow, false block, latency, model calls avoided, tamper detections, quarantine/reroute decisions, receipt completeness.

Source:

- MPEP 2141, Obviousness Guidelines: https://www.uspto.gov/web/offices/pac/mpep/s2141.html

### Section 112(a) - Written Description, Enablement, Best Mode

MPEP 2161 separates written description, enablement, and best mode. MPEP 2163 asks whether the specification shows possession of the invention as claimed at the filing date. MPEP 2164 asks whether the specification teaches how to make and use the claimed invention.

SCBE strength:

- The core runtime gate is supported by formulas, state objects, code anchors, and implementation notes.
- Claims 1-11, 15-20, 24, 26, and 27 have the cleanest support path.

SCBE risk:

- Broad dependent claims that span optional or newer subsystems need careful support mapping.
- Claims 12, 21-23, 25, and 28 should be treated as useful embodiments, not the center of the case.
- If an examiner says a term is too broad or unsupported, the response should cite exact paragraphs, figures, and implementation examples. If needed, amend the term into narrower technical language.

Sources:

- MPEP 2161, Section 112(a) requirements: https://www.uspto.gov/web/offices/pac/mpep/s2161.html
- MPEP 2163, Written Description: https://www.uspto.gov/web/offices/pac/mpep/s2163.html
- MPEP 2164, Enablement: https://www.uspto.gov/web/offices/pac/mpep/s2164.html

### Section 112(b) - Definiteness

MPEP 2173 focuses on whether the public can understand claim boundaries. The filing should avoid relying on coined names when technical language can do the job.

Translate during prosecution:

- Sacred Tongues -> semantic weighting axes / disjoint token vocabularies.
- Sacred Egg -> N-predicate authorization container.
- Fleet juggling -> trajectory-based multi-agent scheduler.
- Harmonic wall -> nonlinear drift-to-cost function.
- Fail-to-noise -> deterministic hash-derived denial output.

Risk terms:

- "harmonic" without formula.
- "Sacred" names without definition.
- "physics-based" if not tied to concrete trajectory variables.
- "domain-specific entropy" if not tied to disjoint token vocabularies or routing paths.

Source:

- MPEP 2173, Claim Definiteness: https://www.uspto.gov/web/offices/pac/mpep/s2173.html

## Claim Family Standing

### Strong Core

Claims 1-2:

- Best posture: bounded hyperbolic drift used as a runtime execution-control signal.
- Main attack: abstract math or known hyperbolic embeddings.
- Response posture: the claim changes execution state, not just representation.

Claims 5, 8, 9:

- Best posture: durable session centroid and runtime state continuity.
- Main attack: ordinary state persistence.
- Response posture: persistence carries the geometric reference state used for later governance.

Claims 10-11:

- Best posture: quarantine containment and ordered cheap-to-expensive gates.
- Main attack: known guardrails/firewalls.
- Response posture: these are combined with geometric runtime governance and measurable model-call reduction.

Claims 15-20:

- Best posture: concrete code-security tamper detection through bijective/canonical round trip and AST/identifier checks.
- Main attack: known Unicode/canonicalization/security linting.
- Response posture: the tamper signal participates in the governance decision for proposed computational action.

Claim 24:

- Best posture: null-space anomaly detection in the RuntimeGate path.
- Main attack: ordinary anomaly detection.
- Response posture: it detects suspicious under-deviation as a governance-cost modifier.

Claims 26-27:

- Best posture: disjoint serialized token alphabets and phase/axis separation as implementation details.
- Main attack: tokenization and phase math are known.
- Response posture: they are not standalone; they feed the runtime governance/token-origin mechanism.

### Useful But Review-Sensitive

Claim 3:

- Keep as species of nonlinear cost, not as an assertion every formula is live everywhere.

Claim 12:

- PQC primitives are standardized, so novelty cannot rest on ML-KEM/ML-DSA themselves.
- Better: receipt embodiment for audit/provenance in the governance pipeline.

Claims 21-22:

- Argue as N-predicate authorization container and deterministic denial behavior.
- Avoid making "Sacred Egg" the legal term of art.

Claim 23:

- Argue as routing to a safer path/review/quarantine/lower-risk execution route.
- Watch for support if examiner asks whether it was fully described as filed.

Claim 25:

- Argue as trajectory-based multi-agent task scheduling.
- Avoid loose sports/physics metaphors in formal response.

Claim 28:

- Argue as structurally distinct token sequences/routing paths.
- Avoid claiming statistical independence unless measured and supported.

## ODP / Citation Data Research Lane

The USPTO Data Set API endpoint the user identified:

- `GET /api/v1/patent/oa/enriched_cited_reference_metadata/v3/fields`
- `POST /api/v1/patent/oa/enriched_cited_reference_metadata/v3/records`

Potential use:

- mine Office Action citation metadata for references examiners cite against similar software/AI/security claims;
- search cited-reference patterns around hyperbolic embeddings, authorization, anomaly detection, prompt injection, tamper detection, and Unicode/canonicalization;
- build a "likely examiner citation" table before the first Office Action.

Current local test:

- A direct unauthenticated request to the fields endpoint returned HTTP 403 Forbidden.
- Treat this as an access/API-key lane, not a filing defect.

## Recommended Preparation Before First Office Action

1. Build a one-page Section 101 response shell.
   - Title: "The claims integrate mathematical calculations into practical runtime execution control."
   - Include: execution-routing diagram, persisted state, quarantine/deny/reroute outputs, audit receipt.

2. Build a prior-art comparison table.
   - Rows: hyperbolic embeddings, access control, LLM guardrails, anomaly detection, code tamper detection, cryptographic receipts.
   - Columns: what reference teaches, what it lacks, which claim element is different.

3. Build a benchmark evidence packet.
   - Do not claim it proves patentability.
   - Use it to show real technical effect: fewer false allows, reduced model calls, earlier detection, deterministic audit output.

4. Build a glossary for prosecution.
   - Use examiner-safe terms instead of SCBE-internal names.

5. Keep continuation ideas separate.
   - Holographic overlay/magnified drift view.
   - Mechanical/analog AI extensions.
   - Ancient algebra/tokenizer template expansions.
   - Any invented-after-filing additions.

## Bottom Line

The application will likely receive at least one Office Action because software/AI/security claims are routinely challenged under 101, 103, and 112. That does not mean the filing is weak. The defensible center is strong if kept grounded in concrete runtime governance: persisted geometric state, measured drift, nonlinear cost, execution routing, tamper checks, and audit artifacts.

The prosecution strategy should be: defend the independent runtime-control claims first, use dependent claims as fallback embodiments, and avoid letting coined SCBE language become the legal battlefield.
