# Patent Style Sheet 2026

Status: internal drafting aid. Not legal advice.

## Purpose

Keep SCBE patent drafts technically accurate, readable, and free of spelling or
terminology drift.

## Preferred Neutral Terms

Use these in claims and formal specification text:

| Avoid in claims | Prefer in claims |
|---|---|
| Sacred Tongues | semantic axes, semantic weighting axes, language-domain axes |
| Harmonic Wall | nonlinear governance cost function, harmonic cost function |
| GeoSeal | governance gate, authorization seal, decision receipt |
| Spiralverse | training corpus, origin corpus, semantic provenance record |
| military-grade | high-assurance, hardened, governed, audited |
| impossible | computationally infeasible, prevented under stated conditions |
| AI soul / identity | runtime state, persistent governance state, trajectory state |
| time dilation | delay, containment interval, quarantine timeout, execution throttling |

Coined terms may remain in definitions, examples, and embodiments when paired
with a neutral technical definition.

## Capitalization

- SCBE-AETHERMOORE
- SCBE
- GeoSeal
- Sacred Tongues
- Harmonic Wall
- Poincare ball
- Poincare embedding
- hyperbolic distance
- harmonic cost
- bijective tamper signal
- identifier canonicality
- quarantine lock
- RuntimeGate when referring to the code class
- runtime gate when referring to the general mechanism

## Spelling Normalization

| Common rough input | Patent draft form |
|---|---|
| qaurtine, quartine | quarantine |
| mechinism | mechanism |
| governece, govnerce | governance |
| toknizer | tokenizer |
| bijective toknizer | bijective tokenizer |
| hexa | hexadecimal |
| binary to hexa | binary-to-hexadecimal |
| agentic harnes | agentic harness |
| cli | CLI |
| llm | LLM |
| ai | AI |
| powershell | PowerShell |

## Formula Style

Use one notation per mechanism:

- Hyperbolic distance: `d_H`
- Harmonic cost: `H(d, R)`
- Drift-adjusted or effective distance: `d*` or `d_eff`, but do not mix them in
  the same section.
- Poincare point: `u`
- Trusted center/reference: `v`, `mu`, or "trusted reference point"; pick one
  per draft.

## Claim Language Rules

- Start broad, then narrow in dependent claims.
- Prefer "comprising" over "consisting of" unless counsel says otherwise.
- Avoid claiming only the exact 14-layer sequence if the broader invention is a
  governed hyperbolic distance/cost gate.
- Avoid locking independent claims to the names KO, AV, RU, CA, UM, and DR.
- Use "at least one" where multiple implementation choices exist.
- Use "selected from" for optional signal groups.
- Use "one or more processors" and "non-transitory computer-readable medium" for
  standard software claim forms.

## Red Flag Phrases

Remove or qualify these before attorney handoff:

- mathematically impossible
- physically impossible
- military-grade
- unhackable
- guarantees safety
- cannot be bypassed
- proves alignment
- post-quantum secure unless tied to a real primitive and implementation scope
- production certified

Safer replacements:

- "increases cost under the stated metric"
- "reduces attack success under the tested conditions"
- "routes to quarantine or denial under configured thresholds"
- "uses post-quantum primitives in some embodiments"
- "provides an auditable governance decision"

## Draft Review Checklist

- Every important coined term has a neutral definition.
- Every claim element is supported by a spec paragraph.
- Every figure is referenced in the specification.
- Every formula matches the code/support map.
- Claims do not depend on marketing names.
- Newer features are flagged if priority support is uncertain.
- Micro-entity cost discipline is preserved unless counsel approves otherwise.
