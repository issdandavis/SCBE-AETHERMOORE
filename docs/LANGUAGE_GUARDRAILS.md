# Language Guardrails

**Document ID**: SCBE-LANG-2026-02-18
**Scope**: All project documentation, patent text, README, marketing copy
**Status**: ACTIVE -- Applies to all docs in this repo

---

## Purpose

Prevent hype, unsupported claims, and promotional language from entering patent filings, technical documentation, or public-facing materials. Every statement must be traceable to evidence or clearly marked as speculative.

---

## The Three Registers

### 1. Patent Register (PATENT_DETAILED_DESCRIPTION.md, claims text)

**Rules**:
- Every claim must map to a row in [CLAIMS_EVIDENCE_LEDGER.md](CLAIMS_EVIDENCE_LEDGER.md)
- Use "configured to" and "comprising" per USPTO convention
- State what the system DOES, not what it COULD do
- Quantitative claims require experiment ID and AUC/metric
- No superlatives ("best", "unbreakable", "revolutionary")
- No future tense ("will achieve", "is expected to")

**Allowed**: "The system achieves 0.9942 AUC across six attack types (Experiment 4)."
**Forbidden**: "The system is virtually unbreakable." / "This will revolutionize AI safety."

### 2. Technical Register (CLAUDE.md, SPEC.md, architecture docs, code comments)

**Rules**:
- State what code does, not what it aspires to
- Distinguish CODE_EXISTS_UNTESTED from PROVEN
- Reference specific files and line numbers when describing behavior
- Use present tense for implemented features, conditional for planned
- No marketing language in technical docs

**Allowed**: "Layer 12 computes H(d,R) = R^(d^2). Production uses the bounded variant 1/(1+d+2*pd)."
**Forbidden**: "Our groundbreaking harmonic wall provides military-grade security."

### 3. Experimental Register (CLAIMS_AUDIT_V4.md, experiment logs)

**Rules**:
- State pass criterion BEFORE running experiment
- Report exact numbers (AUC to 4 decimal places)
- Report failures and disproven claims with equal prominence
- No cherry-picking: report all conditions, not just favorable ones
- Include trial count, seed, and pipeline version

**Allowed**: "GeoSeal v2: AUC = 0.543. Swarm dynamics destroy discriminative signal."
**Forbidden**: "GeoSeal shows promising early results." (when AUC = 0.543)

---

## Forbidden Phrases

These phrases are banned from all registers:

| Phrase | Why | Replace With |
|--------|-----|-------------|
| "unbreakable" | No system is; patent-toxic | "achieves N-bit security at distance d_crit = X" |
| "revolutionary" | Promotional; no technical meaning | [describe what it does] |
| "military-grade" | Meaningless marketing term | "NIST Level 3 (ML-KEM-768 + ML-DSA-65)" |
| "quantum-proof" | Nothing is proven quantum-proof | "post-quantum: based on MLWE + MSIS (NIST FIPS 203/204)" |
| "unhackable" | Invites contradiction | "100% detection rate across N tested attack types" |
| "AI-powered" (as differentiator) | Everything is; adds no information | [describe the specific mechanism] |
| "patent-pending" (in technical docs) | Legal status, not technical property | Move to README/index only |
| "will be" / "is expected to" | Future tense = unproven | "is" (if proven) or "requires validation" (if not) |
| "state-of-the-art" | Requires comparative benchmark you may not have | "achieves AUC = X on benchmark Y" or omit |
| "novel" (without citation) | Must cite what it's novel relative to | "novel relative to [prior art]: [specific distinction]" |
| "impossible to circumvent" | Mathematically false for any finite system | "cost scales as R^(d^2), requiring d_crit = 9.42 for 128-bit security" |
| "zero-day proof" | Not a real security property | [describe specific attack classes tested] |

---

## Status Label Rules

When describing a feature's readiness, use exactly one of these labels:

| Label | Meaning | Allowed Claims |
|-------|---------|---------------|
| **PROVEN** | Experiment exists with AUC >= 0.95 or 100% gate accuracy | "The system detects X with AUC = Y" |
| **PROVEN_PARTIAL** | Proven under restricted conditions | "Under synthetic conditions, the system achieves..." |
| **CODE_EXISTS_UNTESTED** | Code runs, no comparative experiment | "The implementation computes X. Comparative validation pending." |
| **THEORETICAL_ONLY** | Math is correct, no code | "The mathematical framework defines X. Implementation pending." |
| **DISPROVEN** | Experiment contradicts claim | "Experiment N shows X does not hold: [data]" |
| **REFRAMED** | Original claim disproven, new framing works | "Originally claimed as X; reframed as Y based on [data]" |

**Rule**: The label must match the row in CLAIMS_EVIDENCE_LEDGER.md. If you describe a feature and there's no ledger row, add one first.

---

## Citation Format

When referencing experimental evidence:

```
(Exp N: AUC = X.XXXX, N trials, pipeline = [synthetic|real])
```

When referencing prior art distinction:

```
Novel relative to [Author, Year]: [1-sentence distinction]
```

When referencing code:

```
See [filename]:[line_range] or [module_name]
```

---

## Review Checklist

Before merging any documentation change:

- [ ] No forbidden phrases present
- [ ] Every quantitative claim has an experiment ID
- [ ] STATUS labels match CLAIMS_EVIDENCE_LEDGER.md
- [ ] No future-tense promises for unvalidated features
- [ ] Disproven claims are reported, not hidden
- [ ] Patent text uses USPTO register conventions
- [ ] "Novel" claims cite what they're novel relative to

---

*These guardrails apply to all human and AI-generated text in this repository.*
*Violations should be flagged in PR review.*
