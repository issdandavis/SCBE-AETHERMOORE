# Monorepo Split — RESOLVED: Monorepo is canonical, satellites are archived mirrors

> **Decision (2026-06):** SCBE-AETHERMOORE is **one monorepo**, and that monorepo is the
> single source of truth. The 2026-04 split into satellite repos is **reverted in intent**:
> the satellites are kept only as **archived, read-only mirrors** of their 2026-04-13
> snapshot. Do not clone them for current work; do not push to them.

## Why monorepo-canonical

The split ran live from 2026-04 and within two months produced dual-homed code,
contradictory authority docs, and stub READMEs pointing at non-canonical homes — empirical
evidence that N repos cost a solo maintainer more than they return. The clarity the split
was meant to deliver (clean published surfaces) is achievable at **publish boundaries**
(workspace packages with tight per-artifact `files` globs), not **repo boundaries**, at one
repo's maintenance cost and zero code-path risk.

## Divergence check (done before archiving — no work lost)

Verified 2026-06-09 against GitHub commit history + working tree:

| Satellite | Post-import commits? | Action |
|---|---|---|
| scbe-agents | none (import-only, all 2026-04-13) | safe to archive |
| scbe-training-lab | none (import-only) | safe to archive |
| scbe-tongues-toolchain | none (import-only) | safe to archive |
| scbe-experiments | **2 satellite-only files** (`injection_to_bits.py`, `train_injection_classifier.py`) | **ported back into `experiments/` first**, then safe |
| scbe-docs-archive | none (import-only) | safe to archive |

The two scbe-experiments files existed nowhere in the monorepo and were recovered into
`experiments/` before any archive step.

## Satellite repos (now archived mirrors)

- agents/hydra/mcp → https://github.com/issdandavis/scbe-agents
- tools/stasm,stvm → https://github.com/issdandavis/scbe-tongues-toolchain
- experiments/ → https://github.com/issdandavis/scbe-experiments
- training/ → https://github.com/issdandavis/scbe-training-lab
- docs/ (subset) → https://github.com/issdandavis/scbe-docs-archive

## Remaining follow-ups

- Update aethermoore.com copy (the "nine focused repos" framing) to match this decision —
  that copy lives outside this repo and is not auto-fixed by this sweep.
- Deliver product-surface clarity via published-package `files` globs (the real fix the
  split was reaching for).
