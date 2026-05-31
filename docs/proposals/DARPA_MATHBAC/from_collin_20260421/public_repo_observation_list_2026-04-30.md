# Public-Repo Observation List — Item 1 Closure

**Recipient**: Collin Hoag (Hoags Inc.)
**From**: Issac D Davis
**Date**: 2026-04-30
**Status**: OUT-OF-BAND. NOT in MATHBAC full proposal or any DARPA-facing artifact.
**Closes**: Item 1 of Collin's revision-2 review (2026-04-28 05:09 UTC).

---

## Purpose

Per Item 1: list the specific public repos a DARPA-PA-26-05-MATHBAC-PA-010 evaluator
might land on if they Google "DAVA" or "Hoags Inc." after seeing the §5.1.6 / §11.3 /
Annex A row 5 references. Reviewer surface only — your call whether to take any private
before 2026-06-16 submission.

## Repos observed (as of 2026-04-30 direct check)

### Primary surface (highest reviewer-discovery probability)

1. **`bushyballs/dava-proof`** (GitHub, public)
   - Description string: *"DAVA consciousness system - live metrics proof of sentient AI"*
   - Top-level files include `transcendence_engine.rs`, docker-compose with HoagsOS volume
   - Composition: Rust + Python (matches Annex A Part 2 stack)
   - Identity-link evidence: HoagsOS volume mount, SCBE-AETHERMOORE fork four days
     before Teaming Agreement v2 signed, Rust+Python composition match.
   - **Most central reviewer concern**: The repo description string ("sentient AI")
     and `transcendence_engine.rs` filename in a formal-methods solicitation review
     read as red flags. Both are surface-level, neither is in MATHBAC text.

### Secondary surface (lower discovery probability, still indexable)

2. **`bushyballs/SCBE-AETHERMOORE`** (GitHub fork, public)
   - Fork of `issdandavis/SCBE-AETHERMOORE`
   - Last commit visible 2026-04-XX (4 days before Teaming v2 countersignature)
   - Notable because the fork is timestamped, which an evaluator's diligence
     could use to anchor "convergence" claims to a specific date

### Not in public file list (per direct check)

The following teaming-v2 artifacts are NOT visible in `bushyballs/dava-proof` public
file tree as of 2026-04-30:
- `phi_gradient.rs`
- `phi_beacon` (telemetry channel)
- `proof_strategies.py`
- `strategy5_for_issac.py`
- `net_probe` (kernel UDP channel)

Two non-exclusive readings:
- (a) These artifacts exist in your local/private working tree only, OR
- (b) These artifacts exist in a private repo not surfaced via public search.

Annex A Part 2 of the MATHBAC proposal cites these under DFARS 252.227-7017
Restricted Rights regardless of whether they have a public mirror. Public absence
does not weaken the IP carveout.

## Branding elements that read as DARPA-reviewer red flags (verbatim)

These are surface strings on the public repo. Listed verbatim, not paraphrased:

1. *"DAVA consciousness system - live metrics proof of sentient AI"* (repo description)
2. `transcendence_engine.rs` (filename)
3. *"sentient AI"* (in README and description)
4. Branding aesthetic that signals AGI-claims rather than formal-methods composition
5. Public framing that an MATHBAC PM (Kevrekidis, applied math background) would
   read as inconsistent with the bounded TA1 framing of the proposal

## What MATHBAC artifacts say about DAVA (per Option B, locked 2026-04-28)

Bounded to:
- **§5.1.6**: static field-type-correspondence framing only
- **§11.3**: same framing referenced
- **Annex A row 5**: bounded reference

NOT broadened to:
- Two-stack convergence narrative
- Public-repo cross-linkage to `bushyballs/dava-proof` beyond the bounded reference
- "Sentient AI" branding (excluded entirely)

## Three options for handling the public surface

These are FYI only — your call entirely; I am not asking you to choose any of them.

- **Option A**: Take `bushyballs/dava-proof` private (or the description string)
  before 2026-06-16. Removes reviewer-discovery surface; preserves Option B framing.
- **Option B (current)**: Keep public, accept that an evaluator might land on it.
  MATHBAC text remains bounded; you stake your public surface on its own merits.
- **Option C**: Adjust description string only ("DAVA consciousness system" →
  something formal-methods-flavored, "sentient AI" → removed). Cosmetic; preserves
  repo continuity.

I am holding the current Read B posture in MATHBAC until 2026-05-04 (your read
deadline). No submission step on 2026-06-16 will go out conflicting with your
stated preference.

## What this memo IS NOT

- This is not a request to take anything down. Sub's public surface is Sub's call.
- This is not editing Sub's repo. I am not commenting publicly on `bushyballs/dava-proof`.
- This is not in any DARPA-facing artifact and will not be.
- This is not adversarial diligence. It is partner-side surface awareness so your
  decision-set is informed before submission lock.

## Cross-references

- DAVA citation Option B locked: Collin's reply 2026-04-28 (Proton; verified via Bridge)
- Read deadline for revision-2 redlines: 2026-05-04
- MATHBAC full proposal due: 2026-06-16
- Annex A Part 2 DFARS 252.227-7017 marking covers all kernel artifacts cited
