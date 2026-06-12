# Patent Claims → Implementation Status Ledger

**Purpose (the standing goal):** every mechanism the patents reference must
either **work** (real code + a test that exercises it) or have a **documented
follow-up**. Nothing referenced may sit in an undefined state. After this holds,
work shifts to improving the system. This file is the tracker.

- **Filed:** non-provisional **App 19/691,526** (2026-05-28), priority from
  provisional **63/961,403** (2026-01-15). 28 claims.
- **Authoritative sources:** `docs/legal/SCBE_NONPROVISIONAL_WORKING_PACKET_2026-05-28.md`,
  `docs/legal/patent-workbench/CLAIM_MATH_SUPPORT_MATRIX_2026-05-28.md`.
- **Status vocab:** `WORKS` (impl + cited test) · `VERIFIED` (I ran the test this
  session) · `PARTIAL` (impl present, not wired as default / integration unconfirmed)
  · `DEFERRED` (non-production or opt-in; CIP candidate) · `NOT FILED`.

Last updated: 2026-06-10.

---

## A. Working — impl + tests present (Tier A)

| # | Mechanism | Claims | Impl | Status |
|---|---|---|---|---|
| 1 | Hyperbolic Poincaré embedding | 1a, 2 | `packages/kernel/src/hyperbolic.ts` | WORKS |
| 2 | Hyperbolic distance `arccosh(…)` | 2 | `packages/kernel/src/hyperbolic.ts` | WORKS |
| 3 | Harmonic cost `π^(φ·d*)` | 1c, 3 | `src/governance/runtime_gate.py` `_harmonic_cost` | WORKS |
| 4 | φ-weighted centroid drift | 1d, 5 | `runtime_gate.py` `_weighted_centroid_drift` | WORKS |
| 5 | Incremental session centroid | 5 | `runtime_gate.py` `_update_centroid` | WORKS |
| 6 | Six-axis φ-weighted tongues | 4, 26–28 | `runtime_gate.py`, `src/tokenizer/ss1.ts` | WORKS |
| 7 | Fail-to-Noise on denial | 7, 22 | `runtime_gate.py` `_fail_to_noise` | WORKS |
| 8 | Persistent runtime state | 8, 9 | `runtime_gate.py` `save_state`/`load_state` | WORKS |
| 9 | Quarantine lock (non-error) | 10 | `src/agentic/quarantine_lock.py` | WORKS |
| 10 | Ordered cheap-reject pre-filter | 11 | `src/cli/petri_pattern_filter.py`, `slm_router.py` | WORKS |
| 11 | Bijective tamper signal | 15–20 | `src/governance/bijective_tamper.py` | WORKS |
| 12 | Canonical AST fingerprint | 16, 20 | `bijective_tamper.py` | WORKS |
| 13 | Confusable-identifier detect | 17, 26 | `src/governance/identifier_canonicality.py` | WORKS |
| 14 | Bijective token alphabet 16×16 | 26, 28 | `src/tokenizer/ss1.ts` | WORKS |
| 15 | Harmonic freq / phase orthogonality | 27 | `ss1.ts`, `src/crypto/geo_seal.py` | WORKS |
| 16 | Reroute / substitution | 23 | `runtime_gate.py` `_check_reroute` | WORKS |
| 17 | Null-space anomaly (mimicry) | 24 | `runtime_gate.py` `_null_space_anomaly` | WORKS |
| 18 | Spin quantization | (prod) | `runtime_gate.py` `_spin` | WORKS |
| 19 | Intent-spike boosting | (prod) | `runtime_gate.py` `_apply_intent_spike` | WORKS |
| 20 | Fleet juggling scheduler | 25 | `src/fleet/juggling-scheduler.ts` | WORKS |
| 21 | 14-layer pipeline | (embodiment) | `packages/kernel/src/pipeline14.ts` | WORKS |
| 22 | PHDM core metric | (system) | `src/ai_brain/phdm-core.ts` | WORKS |

> Provenance: "WORKS" here = the scout located impl + a cited test file; these were
> **not** re-run this session. To promote a row to VERIFIED, run its test and note it.

---

## B. Needs follow-up — referenced but not yet "works as the claim reads"

| # | Mechanism | Claims | Status | Follow-up |
|---|---|---|---|---|
| F1 | **Sacred Eggs ring-descent auth** | 21, 22 | PARTIAL (auth logic **VERIFIED** — fail-closed, 64 tests green 2026-06-10; but **not wired as the default RuntimeGate path** — only `__init__` re-export + tests call it) | Either integrate ring-descent into the default gate dispatch, **or** narrow the claim wording to "an embodiment" so the filed claim matches a tested-but-optional module. `src/crypto/sacred_eggs.py`. See [[project_sacred_eggs_fail_closed]]. |
| F2 | **PQC receipt** (ML-DSA-65 / ML-KEM-768) | 12 | PARTIAL — libs present (`src/crypto/pqc_liboqs.py`, `geo_seal.py`), compliance test exists, but integration into the **main gate receipt path** is unconfirmed | Confirm/wire PQC signing+KEM into the default decision receipt and add an end-to-end test, **or** keep Claim 12 narrow to the standalone PQC module. |
| F3 | **Aerospace-skin disclosure** | — | NOT FILED (drafted; `prosecution_docket_2026-06-09.md`) | File as a separate provisional (new 12-mo clock) or as a CIP of 19/691,526. |

---

## C. Deferred (DEFERRED — non-production / opt-in; CIP candidates, not gaps)

These are intentionally out of the filed claims; they are tracked so they don't
get mistaken for either "works" or "missing."

| Item | Where | Promote-when |
|---|---|---|
| EMA swarm trust formula | demo/archive only | a production `_council_review` uses it |
| Hopfield energy form | archive; prod uses multi-well | `hamiltonianCFI.ts` feeds the main gate directly |
| Trichromatic governance | `src/governance/trichromatic_governance.py` (`use_…=False`) | made the production default |
| Tree of Escalation v1.1+ | `src/governance/tree_of_escalation.py` (v0.5 observational) | it feeds the decision path |

---

## D. Prosecution / admin follow-ups (legal clock — track, don't code)

- Register USPTO ODP APIs to monitor file-wrapper + office actions — see [[reference_uspto_odp]] (before 2026-06-18).
- File IDS with prior art by **2026-08-28**.
- Confirm micro-entity certification (PTO/SB/15A) on file.
- PCT / foreign decision by **2027-01-15** (provisional priority date + 12 mo).

---

## How to keep this honest

A row is only **VERIFIED** when its test was run and passed in a session and that
is noted. Don't upgrade WORKS→VERIFIED on faith. When a follow-up (B) is closed,
move the row to A with the verifying test named. When code referenced by a claim
is deleted or changed, update the row the same day — a stale ledger is worse than
none, because it reads as "covered" when it isn't.
