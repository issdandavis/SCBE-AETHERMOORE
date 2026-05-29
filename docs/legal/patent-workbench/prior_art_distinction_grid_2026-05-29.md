# SCBE-2026-0001 — Prior Art Distinction Grid
# App 19/691,526 — Internal prosecution-prep memo, not legal advice.
# Companion to: issued_patent_comparator_set_2026-05-29.md
#                post_filing_legal_backing_2026-05-29.md

## Purpose

Maps each issued comparator to the claim-1/9/15 element set.
Cells: Y = reference teaches this element | P = partial/arguably teaches | N = not taught.
The §103 non-obviousness argument is in the rows where no reference has Y,
and in the column that shows no single combination reaches all Y.

---

## Element Inventory — Claim 1 (Method)

| # | Element label (from claim 1) |
|---|---|
| E1 | Receive request for computational action |
| E2 | Generate context representation (semantic/operational/temporal features) |
| E3 | Transform to Poincaré ball via tanh-normalized projection w/ epsilon clamping |
| E4 | Maintain session centroid updated from prior embedded points within session |
| E5 | Compute hyperbolic distance between embedded point and session centroid |
| E6 | Compute governance cost via nonlinear cost function increasing with hyperbolic distance |
| E7 | Combine governance cost with auxiliary signals (semantic weighting, spectral coherence, etc.) |
| E8 | Adjust severity as function of trajectory drift across prior requests |
| E9 | Emit allow/review/quarantine/deny execution decision |

---

## Distinction Grid — Claim 1 Elements

| Comparator | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 | E9 |
|---|---|---|---|---|---|---|---|---|---|
| **US12340000B2** (Intuit — prompt injection) | Y | P | N | N | N | N | N | N | P |
| **US12229265B1** (HiddenLayer — sidecar) | Y | N | N | N | N | N | N | N | P |
| **US12118471B2** (token trust tagging) | Y | P | N | N | N | N | N | N | P |
| **US11297078B2** (PayPal — ML cyber) | Y | P | N | P | N | N | P | N | P |
| **US11399037B2** (graph/embedding anomaly) | Y | P | N | N | P | N | N | N | P |
| **US11093816B2** (CNN anomaly detection) | Y | P | N | N | N | N | P | N | P |
| **US12413977B2** (access control / bot detect) | Y | P | N | N | N | N | P | N | P |
| **Nickel & Kiela 2017 (Poincaré Embeddings)** | N | N | Y | N | Y | N | N | N | N |

### Reading the grid

- **E3 (Poincaré ball embedding)**: Zero issued comparators teach this. Only prior art
  source is the Nickel/Kiela academic line — which is purely representational (knowledge
  graphs), not governance or execution control. No reference teaches tanh-normalized
  projection with epsilon clamping for request governance.

- **E4 (session centroid updated from prior embedded points)**: Zero comparators teach
  a session-adaptive centroid in hyperbolic space. PayPal (US11297078B2) maintains a
  user behavior model, but it is Euclidean/statistical, not a running centroid in
  hyperbolic space tied to a session.

- **E5 (hyperbolic distance computation)**: Only Nickel/Kiela teach this, and they
  teach it in the context of hierarchical data representation, not adversarial drift
  measurement or governance cost computation.

- **E6 (nonlinear cost function increasing with hyperbolic distance)**: No reference
  teaches this. This is the core inventive step — the specific mathematical relationship
  that produces exponential governance cost scaling as adversarial drift approaches the
  Poincaré ball boundary. Zero coverage in the comparator set.

- **E8 (trajectory drift adjustment across prior requests)**: No reference teaches
  session-level trajectory drift as a severity modifier. The closest is PayPal's user
  behavior model, but that is aggregate statistical profiling, not per-session geometric
  trajectory tracking.

- **E9 (four-tier execution decision)**: All comparators have some form of block/allow,
  but none have the specific four-tier allow/review/quarantine/deny with quarantine as
  a non-error containment state. The quarantine tier — restricting tools without
  terminating the session — is not taught by any comparator.

---

## Element Inventory — Claim 9 (System) Additional Elements

| # | Element label (additional over Claim 1) |
|---|---|
| E10 | Non-transitory memory storing persistent runtime state |
| E11 | Persistent runtime state restored after process restart |
| E12 | Session centroid comprising centroid vector, cumulative cost, and query count |

| Comparator | E10 | E11 | E12 |
|---|---|---|---|
| **US12340000B2** | Y | N | N |
| **US12229265B1** | Y | N | N |
| **US12118471B2** | Y | N | N |
| **US11297078B2** | Y | N | N |
| **US11399037B2** | Y | N | N |
| **US11093816B2** | Y | N | N |
| **US12413977B2** | Y | N | N |

**E11 (restore after restart)** and **E12 (cumulative cost + query count in centroid)**:
Zero coverage. Durable state restoration is a concrete machine behavior that none of the
comparator systems implement for their governance/detection models.

---

## Element Inventory — Claim 15 (CRM / Bijective Tamper)

| # | Element label (from claim 15) |
|---|---|
| F1 | Receive source code or identifier-containing input |
| F2 | Generate re-encoded form via bijective encode→decode round-trip |
| F3 | Compute canonical AST of input and decoded form |
| F4 | Compute tamper signal from AST divergence / parse failure / Unicode failure / confusable-identifier |
| F5 | Provide tamper signal to governance gate that blocks/escalates execution |
| F6 | Tamper signal distinguished from tokenizer reconstruction-quality measure |

| Comparator | F1 | F2 | F3 | F4 | F5 | F6 |
|---|---|---|---|---|---|---|
| **US12340000B2** (prompt injection) | N | N | N | N | P | N |
| **US12118471B2** (token trust tagging) | P | N | N | N | P | N |
| Any known tokenizer quality paper | N | N | N | N | N | — |

**F2 (bijective encode→decode round-trip as tamper detector)**: No issued patent or
known prior art teaches using the bijective property of a tokenizer as a tamper signal
source. The specifically claimed behavior — encoding source code, decoding it, computing
canonical ASTs of both, and comparing — is not taught by any comparator.

**F3 (canonical AST comparison)**: No comparator uses AST comparison for security
purposes. Code analysis tools (e.g., static analyzers) use ASTs, but not as a
round-trip tamper signal in a governance gate.

**F4 (four tamper signal classes)**: Syntax-divergence, structural-divergence,
NFC-normalization divergence, and confusable-identifier — this four-class taxonomy is
not present in any comparator or known prior art combination.

**F6 (distinct from reconstruction-quality measure)**: The claim itself is written to
distinguish from tokenizer evaluation literature (BLEU scores, reconstruction loss,
perplexity). No examiner can cite tokenizer quality papers as anticipating this
because the claim explicitly excludes that category.

---

## §103 Combination Analysis — What the Examiner Would Need

### To reject Claim 1 under §103:

The examiner would need at minimum:

- **Ref A**: A system that embeds action representations for governance purposes
  (closest: US11399037B2, but it is Euclidean/graph, not Poincaré ball)
- **Ref B**: Poincaré ball embedding (Nickel/Kiela, but purely representational)
- **Ref C**: Session state that persists centroid data (not present in any comparator)
- **Motivation**: Why a skilled person would combine graph anomaly detection (Ref A)
  with knowledge-graph hyperbolic embeddings (Ref B) and arrive at a session-centroid
  governance cost function with execution routing

**The combination fails because:**

1. Ref A + Ref B teaches representation, not governance. The examiner must explain
   why a skilled person reading both references would produce a session-adaptive
   centroid in hyperbolic space that generates a nonlinear cost driving execution
   decisions. This motivation does not exist in either reference.

2. E6 (nonlinear cost increasing with hyperbolic distance) is in zero references.
   It is the core claim element — no combination produces it.

3. E8 (trajectory drift as severity modifier) is in zero references. Adding E8
   requires a third reference with no clear motivation to combine.

4. E11 (restore after restart) and E12 (centroid vector + cumulative cost + query
   count) require a fourth reference. No known four-reference combination reaches
   all elements of claim 9.

### To reject Claim 15 under §103:

The examiner would need:

- **Ref A**: A system that uses tokenizer round-trips for some purpose
- **Ref B**: AST-based code analysis
- **Ref C**: A governance gate that changes execution based on code properties
- **Motivation**: Why a skilled person would combine tokenizer round-trip analysis
  (used for quality evaluation in NLP) with AST comparison (used in static analysis)
  to produce a security tamper signal that gates execution

**The combination fails because:**

1. Tokenizer round-trips in NLP literature are reconstruction-quality measures,
   not security signals. The claimed use (bijective property as tamper detector) is
   the opposite of the purpose in prior art.

2. F6 explicitly distinguishes the claim from the reconstruction-quality use of
   tokenizers. An examiner citing NLP reconstruction papers to reject claim 15 would
   be citing the exact prior art the claim is written to distinguish — that argument
   is circular.

3. No reference combines AST canonical comparison with a governance gate. Static
   analysis tools output warnings, not execution routing decisions.

---

## §101 Use of Comparators — Response Template Language

If the examiner issues a §101 rejection, these comparators can be cited in response:

> "The USPTO has allowed similar AI/security pipeline claims where the claim recites
> a concrete computer architecture processing a specific input through a computed
> signal to produce a machine behavior change. See, e.g., US12340000B2 (prompt injection
> detection), US12229265B1 (AI sidecar guardrail), US11297078B2 (ML cybersecurity
> mitigation). These patents confirm that AI safety and security pipeline claims are
> patent-eligible when framed as concrete execution-routing systems rather than abstract
> principles. Applicant's claims are distinguishable from those patents in specificity,
> not in kind — and are similarly rooted in a concrete computer architecture that
> changes execution behavior based on computed signals."

Note: citing these patents does not establish allowability. It establishes that the
examiner's own Art Unit has allowed structurally similar claims and must apply
consistent reasoning.

---

## Strongest Distinction Sentence (for any OA response)

> "None of the cited references, alone or in combination, teaches or suggests the
> ordered SCBE combination of: (1) transforming a proposed computational action into
> a bounded Poincaré ball embedding via tanh-normalized projection; (2) measuring
> hyperbolic distance from a session-adaptive centroid that persists and is restored
> across process restarts; (3) computing a nonlinear governance cost that increases
> with measured hyperbolic drift; and (4) routing execution to an allow, review,
> quarantine, or deny decision. The absence of elements (2) and (3) from the entire
> prior art record is dispositive."

---

*Prepared 2026-05-29. Internal only. Not legal advice.*
