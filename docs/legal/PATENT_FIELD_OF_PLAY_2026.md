# Patent Field Of Play
## SCBE-2026-0001 / U.S. Provisional Application No. 63/961,403
## System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity

Status: internal pro-se workbench, not legal advice.
Prepared: 2026-05-28.

## Current Submission

| Field | Current record |
|---|---|
| Application number | 63/961,403 |
| Compact application number | 63961403 |
| Filing date | 2026-01-15 |
| Current status | Application Dispatched from Preexam, Not Yet Docketed |
| First named inventor | Issac Daniel Davis |
| Docket | SCBE-2026-0001 |
| Title | System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity |

Current procedural position: provisional application is filed. The working task
is to prepare a non-provisional utility application that claims benefit of the
provisional while preserving as much SCBE system scope as the filed disclosure
and current evidence can support.

## Official Field Lines

These are the out-of-bounds lines for the drafting game:

1. A non-provisional utility application claiming benefit of a provisional
   normally must be filed not later than 12 months after the provisional filing
   date. For SCBE-2026-0001, the working deadline is 2027-01-15.
2. The non-provisional must include a specification with description, at least
   one claim, drawings when necessary, inventor oath/declaration, and required
   fees.
3. The specification, claims, and abstract should be filed in DOCX to avoid the
   non-DOCX surcharge for non-provisional utility filings.
4. The benefit claim should specifically identify the provisional application.
5. New matter cannot be added to the filed disclosure by amendment. Features not
   supported by the provisional may still be valuable, but they need careful
   treatment as later-filed/continuation/CIP candidates instead of being assumed
   to get the 2026-01-15 priority date.
6. Claims must avoid being only an abstract idea, math formula, policy rule, or
   mental process. The practical application is runtime enforcement: controlling
   execution, quarantine, denial, audit receipt, state update, and tool dispatch.
7. The specification must describe the invention so a skilled engineer can make
   and use the claimed system. Each broad claim needs enough implementation
   detail, examples, and fallback embodiments.

## Baseball Field Model

The patent drafting problem can be modeled like a game field.

### Field

The field is the legal-procedural boundary:

- home plate: the filed provisional application;
- first base: official USPTO requirements and forms;
- second base: written-description and enablement support;
- third base: eligibility, novelty, and non-obviousness arguments;
- home run: a non-provisional claim set that is broad, supported, enabled, and
  tied to concrete runtime enforcement.

### Foul Lines

The foul lines are:

- unsupported new matter;
- abstract claims that only recite math or policy;
- overclaiming unimplemented future ideas;
- vague coined terms without standard technical definitions;
- unsupported guarantees such as "unhackable" or "always prevents attacks";
- claims that omit the execution-control step and therefore look like analysis
  only.

### Ball

The ball is one proposed claim element or invention variable per round.

Examples:

- hyperbolic distance;
- semantic weighting axes;
- harmonic wall;
- topological control-flow integrity;
- quarantine lock;
- bijective tamper signal;
- runtime gate persistence;
- agent-bus workflow control;
- narrative-derived governance trajectory.

Each pitch defines the ball:

```text
B_i = {
  element,
  support_source,
  technical_function,
  legal_risk,
  fallback_scope,
  priority_status
}
```

### Pitcher

The pitcher is the invention-side advocate. The pitcher tries to throw a clean,
technically accurate claim element:

```text
Pitch(B_i) = describe(element, structure, operation, support)
```

The pitch must include:

- what the component does;
- what data it receives;
- what transform it performs;
- what state or output it changes;
- where it is supported in the provisional, code, figure, or spec draft.

### Batter

The batter is the client-side advocate. The batter tries to hit the claim
element as broadly as possible without going foul:

```text
Hit(B_i) = broaden(element) subject to support and enforceability
```

The batter asks:

- can this cover CLI, API, agent bus, workflow, and model tool-use variants;
- can exact constants be generalized;
- can "Sacred Tongues" become "semantic weighting axes";
- can Poincare ball become "bounded nonlinear geometric domain";
- can one implementation become a family of embodiments.

### Umpire

The umpire is the examiner/legal skeptic. The umpire calls:

- strike: unsupported, indefinite, obvious, or abstract;
- ball: too narrow or not worth a claim;
- fair: supported and technically concrete;
- foul: valuable but outside the provisional support boundary;
- review: support uncertain; needs provisional text check.

### Announcer

The announcer explains the round in plain language. The announcer has no legal
authority and does not decide the call. Its job is to keep the drafting game
readable:

- name the ball under review;
- describe the pitch and hit;
- explain why the umpire called fair, foul, review, or strike;
- state the next workbench action.

### Crowd

The crowd is a panel of small models used for cheap outside reactions. The crowd
members are not legal authority and are not treated as experts. They are useful
because many small, noisy opinions can expose:

- confusing wording;
- overbroad claim language;
- naive-reader misunderstandings;
- possible design-arounds;
- places where coined terms need standard definitions.

The crowd can be called as often as needed, but its output is advisory only. A
crowd vote cannot override the filed provisional, official sources, the support
matrix, or the umpire's rulebook.

### Scoreboard

Each claim element gets scored:

| Score | Meaning |
|---|---|
| Fair / primary | Use in independent or strong dependent claim. |
| Fair / dependent | Use as dependent claim or embodiment. |
| Review | Needs filed provisional support check. |
| Foul / continuation | Valuable, but likely later continuation/CIP material. |
| Strike | Drop or rewrite. |

## Mathematical Form Of The Game

Let:

```text
L = legal constraints
S = filed provisional support
C = current code/spec support
R = prior art risk
E = eligibility risk
M = market/client value
```

For a proposed claim element `x`, define:

```text
Support(x) = f(S, C)
Risk(x) = g(R, E, ambiguity)
Value(x) = h(M, coverage, design-around resistance)
```

The drafting objective:

```text
maximize Coverage(x)
subject to:
  Support(x) >= support_threshold
  Enablement(x) >= enablement_threshold
  Eligibility(x) >= eligibility_threshold
  Ambiguity(x) <= ambiguity_threshold
```

Operationally:

```text
Claimable(x) =
  PRIMARY      if support is strong and practical application is concrete
  DEPENDENT    if support is present but scope should be narrowed
  REVIEW       if support must be checked against the filed provisional
  CONTINUATION if valuable but likely outside the provisional support
  DROP         if unsupported or not technically meaningful
```

## Current Scope We Can Work In

### Strongest Core Scope

These are the best candidates for the main non-provisional:

1. Geometric authorization gate:
   - encode action/context;
   - embed/project into nonlinear or hyperbolic domain;
   - compute distance/drift from trusted state;
   - compute governance cost;
   - enforce runtime decision.

2. Runtime execution control:
   - allow, review, quarantine, deny;
   - prevent tool dispatch on blocked decisions;
   - update session/reference state;
   - generate audit receipt.

3. Semantic weighting:
   - use multiple semantic axes/context channels;
   - modify cost or route using the axes;
   - define project names as embodiments, not claim dependencies.

4. Topological control-flow integrity:
   - verify admissible state transitions;
   - reject or quarantine invalid route transitions;
   - tie CFI to runtime execution, not just static code analysis.

5. Tamper/canonicality:
   - detect non-canonical/bijective/identifier anomalies;
   - combine tamper signal with governance decision.

### Good Dependent Claim Scope

- harmonic-wall bounded score;
- Poincare ball embodiment;
- six-dimensional semantic vector embodiment;
- golden-ratio weighting embodiment;
- quarantine containment state;
- deterministic audit receipt;
- cryptographic receipt envelope;
- persistent runtime-gate state;
- CLI/API/agent-bus embodiments.

### Review Before Claiming As Priority-Supported

- narrative-derived reference trajectory;
- multi-tier Go-board/access-manifold admissibility;
- fleet governance;
- n8n-style workflow harness;
- self-harness inside a model;
- long-term cross-agent symbiotic harness;
- newer quarantine token-drain mechanism if not in the provisional.

These may be good continuation/CIP material if the filed provisional does not
clearly describe them.

## Fair-Play Round Protocol

Use this for each feature:

1. Pitcher defines the feature technically.
2. Batter broadens the feature into claim language.
3. Examiner skeptic attacks 101, 102, 103, and 112.
4. Scientist/engineer checks code/spec support.
5. Mathematician checks whether the formula is exact, bounded, and meaningful.
6. Drafting judge assigns:
   - PRIMARY,
   - DEPENDENT,
   - REVIEW,
   - CONTINUATION,
   - DROP.
7. Announcer summarizes the call in plain language.
8. Optional crowd panel gives short advisory reactions.
9. Workbench records evidence and next action.

## First Round Balls

| Ball | Starting call | Why |
|---|---|---|
| Hyperbolic governance gate | PRIMARY | Core title and implementation anchor. |
| Topological CFI | PRIMARY/DEPENDENT review | Title-level feature; support must be mapped tightly. |
| Semantic weighting axes | DEPENDENT | Strong but should use neutral terms. |
| Harmonic wall | DEPENDENT | Strong mathematical embodiment, avoid over-narrowing independent claim. |
| Quarantine lock | DEPENDENT/REVIEW | Useful enforcement state; verify provisional support. |
| Bijective tamper | DEPENDENT/REVIEW | Valuable, but support must be checked against provisional. |
| Agent bus workflow harness | CONTINUATION/REVIEW | Likely newer implementation surface. |
| Narrative governance function | CONTINUATION/REVIEW | Good concept; priority depends on filed narrative/event support. |
| Fleet systems | CONTINUATION | Likely broad future system, not first priority claim unless disclosed. |

## Next Legal-Procedure Steps

1. Export Patent Center documents into
   `docs/legal/patent-workbench/uploads/`.
2. Verify exact provisional contents against the current claim families.
3. Complete the claim-support matrix with line/figure/code evidence.
4. Build formal figure list:
   - system architecture;
   - geometric authorization flow;
   - topological CFI state transition;
   - quarantine/audit receipt flow;
   - semantic weighting vector.
5. Keep the non-provisional under the base fee target where possible:
   - 3 independent claims;
   - up to 20 total claims;
   - no multiple dependent claims unless deliberately chosen.
6. File specification, claims, and abstract in DOCX through Patent Center.
7. Include inventor declaration/oath and fee payment.
8. Re-check official USPTO fees and Patent Center upload validation on filing
   day.

## Official Sources Checked

- USPTO nonprovisional utility filing guide:
  https://www.uspto.gov/patents-getting-started/patent-basics/types-patent-applications/nonprovisional-utility-patent
- MPEP 211.01(a), claiming benefit of provisional application:
  https://www.uspto.gov/web/offices/pac/mpep/s211.html
- USPTO benefit-claim notice:
  https://www.uspto.gov/patents/laws/patent-related-notices/benefit-claims-prior-applications-under-35-usc
- MPEP 2106, subject matter eligibility:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2106.htm
- MPEP 2163, written description:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2163_07_a.htm
- MPEP 2164, enablement:
  https://www.uspto.gov/web/offices/pac/mpep/documents/2100_2164_01.htm
