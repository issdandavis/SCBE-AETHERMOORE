# Annex A — Basis Sheet (Sealed Evidence) — v1

**Solicitation:** DARPA-PA-26-05 (MATHBAC), Technical Area 1
**Performer:** SCBE AetherMoore (sole prop) — UEI **J4NXHM6N5F59**, CAGE **1EXD5**
**Abstract reference:** DARPA-PA-26-05-MATHBAC-PA-010 (submitted 2026-04-27 05:02 ET)
**Sealed:** 2026-04-27
**Status:** v1 working artifact for the Phase I full proposal (BAAT due **2026-06-16 16:00 ET**).

---

## 0. Purpose and use

This basis sheet is the canonical, single-artifact consolidation of the *sealed* evidence supporting the MATHBAC TA1 abstract. It exists for two load-bearing uses:

1. **Advisor outreach (24 h pre-call attachment)** — delivered alongside the abstract PDF and the proposer-metrics 8-field specs (`advisor_outreach_template_v1.md` §4). Advisors must be able to read the seal and reproduce the numbers without access to the live repository or the proposer.
2. **Volume II / Cost-volume reference (compliance items 1.5/1.6)** — Annex A is cited from the Phase I cost narrative as the basis for any "we already have the substrate" argument that bears on labor, compute, or M0 milestone funding.

If a future artifact disagrees with this sheet by a single bit, **this sheet is the source of truth** until amended (§9). Anything not on this sheet is *not* sealed evidence and may not be cited as such in the proposal.

---

## 1. Sealed-evidence summary table

The table below is the proposal-grade summary. Every row is reproducible from the repository at the SHA-256 seals declared in §3 below. No row is a forecast, a target, or a Phase I deliverable — every row is **already true** as of the sealed date.

| # | Claim | Result | Falsifier (one-line) | Source |
|---|---|---|---|---|
| 1 | Sealed-blind 24-of-24 label accuracy | 24/24, **p ≤ 3.00 × 10⁻⁴** (binomial, two-tail) | Any sealed-blind run < 24/24 falsifies | Internal sealed-blind harness |
| 2 | KL capacity at *realm* scope | **1.5761 bits/tick** = 99.4 % of log₂(3) ≈ 1.585 b/t | Sustained throughput < 99.0 % falsifies | Capacity rollup, M0 |
| 3 | KL capacity at *regime* scope | **2.9818 bits/tick** = 99.4 % of log₂(8) ≈ 3.000 b/t | Sustained throughput < 99.0 % falsifies | Capacity rollup, M0 |
| 4 | Möbius equivariance | **Bit-identical k-means++ under PSU(1,1)** | Any non-bit-identical clustering under PSU(1,1) falsifies | M0 equivariance check |
| 5 | DAVA × SCBE static field-type-correspondence | **5 of the 6** SCBE L1 complex-context slots (identity, intent, trajectory, timing, signature) type-check 1:1 to a single `phi_beacon` field (`id, phi, delta, age, auth`); the 6th slot (commitment / L6 causality) absorbs the polymorphic triple (`next, epoch, emit#`). Static type-level correspondence between two independently-built packet vocabularies, **not** a runtime decision-exchange. | Independent re-derivation under matched packet definitions that disagrees on > 1 of the 6 `phi_beacon`-field → SCBE-L1-slot type mappings | `docs/proposals/DARPA_MATHBAC/one_pager_v1.md` L14–26 + Annex A Part 2 line 54 of `from_collin_20260421/teaming_agreement_v2_hoags_hardened.md` |
| 6 | TS/Python numerical parity (CDPTI-Internal) | **24/24 fixture cases** agree to ≥ 12 decimal places across 5 v1.0.0 sealed fixtures | Any pair of fixtures disagreeing beyond 12 decimals falsifies "single mathematical object" | §3 below |

**Provenance line for advisors:** rows 1–4 are SCBE-internal; row 5 is the DAVA × SCBE static field-type-correspondence (Collin Hoag's `bushyballs/dava-proof` repo `phi_beacon` packet definition + SCBE L1 6-slot tuple, see `reference_collin_hoag_dava.md` for caveats); row 6 is the load-bearing CDPTI-Internal evidence and is the most reproducible — any reader with the repo and a Python interpreter can re-derive it in under 60 seconds (§4 below).

---

## 2. What this sheet does **not** claim

To satisfy the strict-rigor standard (`feedback_strict_scientific_rigor.md` §Tier 2), the disclaimers below are part of the sheet, not a footnote:

- **Not** a third-party benchmark result. None of rows 1–6 has been reproduced by DARPA, an FFRDC, a UARC, or an independent academic lab as of the sealed date. The Phase I program's Living Metric IV&V is the channel through which third-party reproduction will occur (M5–M8).
- **Not** a population claim. Row 1's *p*-value is a sample-level binomial; row 2/3's "99.4 %" is the rollup over the M0 corpus, not a population bound. Re-measurement on a new corpus class is required before reusing the number.
- **Not** a Phase II promise. Phase II principle-rediscovery (Karplus/Mercator) is *narrative* in the Phase I proposal per the TA1-locked decision (`project_mathbac_proposal_spine_2026_04_21.md` §"TA decision"), and is therefore explicitly excluded from this Annex.
- **Not** dependent on partner artifacts for the load-bearing rows. Rows 1–4 and row 6 stand on SCBE-internal artifacts alone; row 5 is the *only* row that requires a partner stack, and per Article 7.6 of the teaming agreement the proposal contingency-discontinues row 5 if the partner stack is unavailable. The remaining rows are unaffected.
- **Not** a measure of architectural agreement. CDPTI (row 6) is a *numerical* parity claim, not a source-code or architectural claim. Two stacks may differ in language, layer factoring, and runtime model and still meet the 12-decimal threshold.

---

## 3. M0 fixture seal (load-bearing for row 6)

The five fixtures below are committed to the repository at version **1.0.0**, sealed by SHA-256, and exercised on every CI commit by both the TypeScript runner and the Python runner. These are the load-bearing artifacts behind row 6 of §1.

All paths are relative to repository root.

| Fixture | Size (bytes) | SHA-256 |
|---|---:|---|
| `tests/interop/polyglot_vectors/poincare_distance.v1.json` | 805 | `39be23f6f2793d819f66a62a950a1cd1b1989edb0d761a670be67f8e89685258` |
| `tests/interop/polyglot_vectors/mobius_addition.v1.json` | 1058 | `2bcbafcf5ef032184e4289ddbb9fd627c5215d97f87fb6e8704966d61d95fbe9` |
| `tests/interop/polyglot_vectors/exponential_map.v1.json` | 1111 | `8c7f65ffd0cd2623cde0631fe3cf045db0a663dac0235b44c4b6ba45562b8de1` |
| `tests/interop/polyglot_vectors/logarithmic_map.v1.json` | 1141 | `48ef1c19f775f199a86f2bc50082ed844dbdcd2415612d04afe5d466a00b8779` |
| `tests/interop/polyglot_vectors/harmonic_wall.v1.json` | 1122 | `2b780eefeb1b204c281326f7b68a95b14173b94e86ee689ac61f3cc5f3a7d54a` |

The seals are bit-for-bit over the raw file bytes (no JSON re-serialization, no formatter dependence, no line-ending convention dependence). The full procedure and the canonical seal table also live at `docs/proposals/DARPA_MATHBAC/M0_fixture_seal_v1.md` — this Annex is a duplicate by design (so a single attachment carries the sealed evidence), and the two files MUST agree byte-for-byte on the seal table.

### 3.1 Layer / operation coverage at M0

| Layer | Operation | Cases | Tested? |
|---|---|---:|---|
| L4 | Exponential map `exp_p(v) = p ⊕ tanh(λ_p‖v‖/2)·v/‖v‖` with `λ_p = 2/(1-‖p‖²)` | 5 | ✓ |
| L4 (inv) | Logarithmic map `log_p(q) = (2/λ_p)·arctanh(‖−p ⊕ q‖)·(−p ⊕ q)/‖−p ⊕ q‖` (round-trip cross-validated against L4 forward) | 5 | ✓ |
| L5 | Hyperbolic distance `d_H = arcosh(1 + 2‖u−v‖² / ((1−‖u‖²)(1−‖v‖²)))` | 5 | ✓ |
| L7 | Möbius addition `u ⊕ v` on the Poincaré ball | 5 | ✓ |
| L12 | Harmonic wall `H(d, pd) = 1 / (1 + φ·d_H + 2·pd)` with `φ = (1+√5)/2` | 5 | ✓ |
| **Total** | | **25** | |

Layers L1–L3, L6, L8–L11, L13–L14 are **not yet sealed at M0**. They expand across Phase I (M1–M4) per the §3.3 fixture-set growth plan in `proposer_metrics_specs_v1.md`. That growth plan is *Phase I deliverable*, not Annex A evidence — only the 25 cases above are sealed evidence.

---

## 4. Reproduction (advisor-runnable, ≤ 60 s)

Any advisor with `git clone` access and a working Python 3.11+ installation can re-derive the SHA-256 seal table in §3 with a single command. The repository is the *only* dependency; no external services, no API keys, no GPU.

```bash
cd <repo-root>
python -c "
import hashlib
from pathlib import Path
for fx in [
    'poincare_distance.v1.json',
    'mobius_addition.v1.json',
    'exponential_map.v1.json',
    'logarithmic_map.v1.json',
    'harmonic_wall.v1.json',
]:
    p = Path('tests/interop/polyglot_vectors') / fx
    raw = p.read_bytes()
    print(f'{fx}\t{len(raw)}\t{hashlib.sha256(raw).hexdigest()}')
"
```

Output must match §3 byte-for-byte. Any mismatch is a fail-closed condition; the sheet is invalid for that environment until reconciled.

To re-derive row 6 (TS/Python parity) in CI mode:

```bash
# TypeScript side
npx vitest run tests/cross-language/polyglot-hyperbolic-ops.test.ts \
                tests/cross-language/polyglot-poincare-vectors.test.ts

# Python side
PYTHONPATH=. python -m pytest tests/interop/test_polyglot_hyperbolic_ops.py \
                                tests/interop/test_polyglot_poincare_vectors.py -v
```

The TS suite asserts at `toBeCloseTo(_, 12)` (≥ 12 decimals); the Python suite asserts at `pytest.approx(_, abs=1e-12)`. Both passed on every CI commit since 2026-04-27. The runners exist at:

- TypeScript: `tests/cross-language/polyglot-hyperbolic-ops.test.ts`, `tests/cross-language/polyglot-poincare-vectors.test.ts`. Production code path: `src/harmonic/hyperbolic.ts:hyperbolicDistance`.
- Python: `tests/interop/test_polyglot_hyperbolic_ops.py`, `tests/interop/test_polyglot_poincare_vectors.py`. Reference function lives in the latter test file (`tests/interop/test_polyglot_poincare_vectors.py`).

---

## 5. Mathematical substrate (for advisor context)

The five sealed operations realize a single substrate: the unit-radius Poincaré ball model of hyperbolic 𝑛-space, equipped with a φ-weighted six-tongue tokenizer and the harmonic-wall scoring function declared in the abstract.

- **Ball model.** All vectors `u, v ∈ B_n = {x ∈ ℝⁿ : ‖x‖ < 1}`. Operations preserve the ball; norm checks are runtime invariants under the Locality axiom (A2).
- **Conformal factor.** `λ_p = 2 / (1 − ‖p‖²)`. Exponential and logarithmic maps use the conformal factor at the basepoint *p*.
- **Distance.** `d_H(u, v) = arcosh(1 + 2‖u − v‖² / ((1 − ‖u‖²)(1 − ‖v‖²)))`. Symmetry axiom (A4) binds at this layer.
- **Group action.** `PSU(1, 1)` Möbius transformations preserve `d_H` and round-trip log/exp. The k-means++ bit-identicality of row 4 is the runtime witness.
- **Wall.** `H(d, pd) = 1 / (1 + φ·d_H + 2·pd)` with `φ = (1+√5)/2 ≈ 1.6180339887…`. Bounded in `(0, 1]`. The wall is the gating layer (L12) in the 14-layer pipeline; admit/reject decisions referenced by ACV (axiom-compliance vector) and PIS (interpretability) are read off this scalar.

The substrate is **not** novel mathematics — it is standard Poincaré-ball geometry with a non-standard weighting (the six-tongue φ-scaling) and a non-standard scoring (the harmonic wall). The novelty is in the *composition* with the five-axiom mesh and in the load-bearing TS/Python parity claim. Advisors evaluating mathematical risk should focus on the **composition**, not on the individual operations.

---

## 6. DAVA × SCBE static field-type-correspondence (row 5)

Row 5 is structurally different from rows 1–4 and row 6: it is *not* an SCBE-internal numerical measurement, and it is *not* a runtime decision-exchange between the two stacks. It is a static *type-level* correspondence between two independently-built packet vocabularies.

- **Stacks.** SCBE (Python + TypeScript, sole prop) and DAVA (Rust kernel, Collin Hoag's `bushyballs/dava-proof` repo, verified public 2026-04-26).
- **Surface.** The 8 named fields of DAVA's `phi_beacon` packet (`id, phi, delta, age, auth, next, epoch, emit#`; see Annex A Part 2 line 54 of `from_collin_20260421/teaming_agreement_v2_hoags_hardened.md`) and the 6 slots of SCBE's L1 complex-context tuple (identity, intent, trajectory, timing, signature, commitment / L6 causality).
- **Result.** 5 of the 6 SCBE L1 slots admit a 1:1 type-correspondence with a single `phi_beacon` field (`id↔identity`, `phi↔intent`, `delta↔trajectory`, `age↔timing`, `auth↔signature`). The 6th slot (commitment / L6 causality) does **not** match a single `phi_beacon` field; it maps polymorphically to the triple (`next, epoch, emit#`). This polymorphic residue is the documented mismatch and is the reason the row reports 5-of-6, not 6-of-6.
- **What this row is not.** Not a runtime admit/reject decision exchange between the two stacks. Not a numerical agreement on a held-out corpus. The runtime CDPTI-External corroboration described in `proposer_metrics_specs_v1.md` §3.3 is a *Phase I forward deliverable*, not Annex A sealed evidence; row 5 anchors only the static type-level claim.
- **Caveat.** The DAVA branding (`bushyballs/dava-proof`, "sentient AI consciousness" framing — see `reference_collin_hoag_dava.md`) is a separate question from the field-type-correspondence result. The result stands on its own; the *citation* in the full proposal is gated by §6 of `advisor_outreach_template_v1.md` (never quote the branding to an advisor or a reviewer; cite the field-type-correspondence numerically). The Article 7.6 contingency in the teaming agreement covers the case where the partner stack is unavailable for re-measurement; under that contingency, row 5 is reported as *historical* (M0-sealed) and *discontinued* (no further M-milestone updates), and the load-bearing rows (1–4, 6) carry the proposal alone.

---

## 7. How rows 1–4 attach to the four declared metrics

This sheet exists to support the abstract's four declared proposer-added metrics (MEE, ACV, CDPTI, PIS — see `proposer_metrics_specs_v1.md`). The mapping below is read-only: each Annex A row supports one or more metrics, and no metric is supported by less than one Annex A row.

| Annex row | Supports | Why |
|---|---|---|
| Row 1 (24/24 sealed-blind) | ACV, PIS | The 24/24 result is the M0-baseline ACV roll-up; the same labels feed the M3 PIS evaluator pool's pre-registered ground truth. |
| Row 2 (KL capacity, realm) | MEE | Capacity at the realm scope is the M0 anchor against which MEE is normalized in the optional-aggregation triage (proposer-metrics §4). |
| Row 3 (KL capacity, regime) | MEE | Same as row 2 at the regime scope; reported as a parallel capacity for cross-scope consistency. |
| Row 4 (Möbius equivariance) | ACV (Symmetry binding at L5/L7), CDPTI-Internal | Bit-identical k-means++ under PSU(1,1) is the runtime witness for Symmetry axiom binding; it is also a CDPTI-Internal substrate-property test. |
| Row 5 (DAVA × SCBE static field-type-correspondence) | CDPTI-External (corroborating only — type-vocabulary precondition) | Per `proposer_metrics_specs_v1.md` §3.3, External is supplementary; row 5 anchors the *static type-vocabulary precondition* (5-of-6 packet-field → SCBE-L1-slot mapping). Runtime admit/reject corroboration on N ≥ 200 corpus is a Phase I forward deliverable, not Annex A evidence. |
| Row 6 (TS/Python parity) | CDPTI-Internal (load-bearing) | Direct load-bearing measurement; row 6 *is* the CDPTI-Internal M0 floor. |

The default rubric per the abstract is the **vector** (MEE, ACV, CDPTI, PIS) — Annex A is the M0 anchor for that vector. The optional rolled-up scalar (proposer-metrics §4) is *only* used if the program asks; Annex A neither computes nor commits to a single scalar.

---

## 8. Falsifiability ledger

Each sealed claim has a one-line falsifier; the table below makes the falsifier check explicit so an advisor can convert "is this real?" into a finite check.

| Claim | Falsifier check | Cost to run | Who can run it |
|---|---|---|---|
| Row 1 | New 24-item sealed-blind run yielding < 24/24 | ~5 min CPU, ~$0 | Anyone with repo access |
| Rows 2–3 | Sustained KL throughput re-measurement < 99.0 % of log₂(N) | ~30 min CPU, ~$0 | Anyone with repo access + M0 corpus |
| Row 4 | k-means++ output not bit-identical under any sampled PSU(1,1) Möbius transform | < 1 min CPU, ~$0 | Anyone with repo access |
| Row 5 | Independent re-derivation under matched packet definitions that disagrees with SCBE on > 1 of the 6 `phi_beacon`-field → SCBE-L1-slot type mappings | ~1 person-week (paper review of two packet specs; no GPU required) | Independent re-implementer (FFRDC, UARC, IV&V, or future advisor lab) |
| Row 6 | Any pair of v1.0.0 fixtures with TS-vs-Python disagreement > 12 decimals | < 30 s CPU, ~$0 | Anyone with repo access (§4 commands) |

Rows 1–4 and row 6 are checkable by a single individual with a laptop in under an hour; row 5 is the only check that requires program-scale resources, and it is the *supplementary* row.

---

## 9. Amendment policy

This sheet is sealed at v1 on **2026-04-27**. Any of the following triggers a numbered amendment (`annex_a_basis_sheet_v1.md → _v2.md → _v3.md`) with rationale:

- A new fixture is added to the M0 set (§3) or the 12-decimal threshold is relaxed for any case (§4).
- A new sealed-blind run produces < 24/24 (row 1) — falsifier-event; the sheet retracts to v0 and the proposal is non-conforming until reseated.
- The DAVA × SCBE field-type-correspondence (row 5) is contradicted by an independent re-derivation under matched packet definitions.
- A new Annex A row is added (e.g. M1 milestone evidence) — additive; v2 supersedes v1 but v1 remains the M0 anchor of record.

Removing a row without an amendment is a falsifier-event for the corresponding proposer-added metric and triggers a Living Metric milestone retraction.

---

## 10. Provenance

Generated 2026-04-27 by consolidation of:

| Source | Section |
|---|---|
| `docs/proposals/DARPA_MATHBAC/proposer_metrics_specs_v1.md` §3.3 (CDPTI-Internal) | §3, §4, §7 (rows 6, mapping) |
| `docs/proposals/DARPA_MATHBAC/M0_fixture_seal_v1.md` (full table + verification) | §3, §4 |
| `project_mathbac_proposal_spine_2026_04_21.md` "Sealed evidence" block (lines 56–62) | §1 (rows 1–5) |
| `docs/proposals/DARPA_MATHBAC/advisor_outreach_template_v1.md` §4 (attachment requirements) | §0 (purpose) |
| `feedback_strict_scientific_rigor.md` (Tier-2 disclaimer pattern) | §2 |
| `feedback_asymmetric_weighting.md` (binary gate vs continuous component framing) | §7 |
| `reference_collin_hoag_dava.md` (DAVA branding caveat) | §6 |

Author: SCBE AetherMoore (Issac D. Davis, sole performer).
Cleared by: pending Phase I full-proposal review pass.
