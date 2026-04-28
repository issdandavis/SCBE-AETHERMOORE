# Partner-Side Soak-Window Written Confirmation — Hoags Inc.

**Sender:** Collin Hoag, President, Hoags Inc.
**Received:** 2026-04-26 (Performer's local mailbox; reply to MATHBAC v1 preview packet sent same week)
**Subject (recovered):** Re: MATHBAC full-proposal v1 preview — partner review
**Status:** Soak-window written confirmation per Closing Note item 6 of `MATHBAC_PREVIEW_TO_COLLIN_2026-04-26.md`.
**Capture mode:** Structured summary recorded by the Performer; verbatim mail body retained in the Performer's mail client (Gmail thread, sender `collinhoag@hoagsandfamily.com`). This file records Sub's written affirmations and outstanding asks for the proposal record.

---

## 1. Greenlit Terms (no further redline expected)

Sub has confirmed acceptance of the following sections as drafted in `MATHBAC_FULL_PROPOSAL_v1_2026-04-26.md` and `from_collin_20260421/teaming_agreement_v2_hoags_hardened.md`:

| Section | Substance | Sub's position |
|---------|-----------|----------------|
| §A.1.1 | Independent stacks; non-exclusive convergent-evidence posture | Accepted |
| §A.1.2 | Roles and independence (Article 2) | Accepted |
| §A.1.3 | Background-IP narrow license (performance-only, non-sublicensable) | Accepted |
| §A.1.4 | Background-IP narrow license (Sub mirror) | Accepted |
| §A.1.5 | Joint Work Boundary (35 USC §116; 17 USC §101) | Accepted |
| §A.1.6 | Decline option and continuity-without-Sub (Article 7.6, 7.7) | Accepted |
| §A.2 | Government rights and data-rights markings — DFARS 252.227-7017 | Accepted |
| Subcontract share | 12% of Phase I budget | Accepted |
| §B.3 | Channel framing (admit/reject decisions; seal-hashes; reproducibility metadata) | Accepted |

The above constitute Sub's *written affirmation* sufficient to support the soak-window step required before MATHBAC full-proposal lock (target submission 2026-06-16).

## 2. Outstanding Asks (must be resolved before revision-2 lock)

Sub has flagged five items for closure before the full proposal is finalized. These are tracked as Performer-side tasks #95, #93, #94, #90, #91 respectively.

### Item 1 — Public-repo due-diligence surface list (Sub-controlled)
Sub asks the Performer to compile and send **separately, NOT in the proposal**, the public-repository surface that a DARPA evaluator might surface in due diligence on Sub's principal. Performer's prior verification (memory: `reference_collin_hoag_dava.md`) confirms `bushyballs/dava-proof` is real and uses "sentient AI consciousness" branding that is a credibility liability. List to be transmitted out-of-band to `collinhoag@hoagsandfamily.com`.

### Item 2 — Sixth surface and disagreement artifact (§5 Item 5.1.6)
Sub asks the Performer to confirm:
- the identity of the sixth communication surface backing the "5-of-6 agreement" claim, and
- which file under `artifacts/mathbac/binary_protocol_harness_with_atomic_v2/` captures the documented disagreement.

**Performer resolution (2026-04-27).** Investigation found that the §5.1.6 evidence pointer was misdirected and the wording of the supporting narrative (and §11.3) overstated the claim relative to the on-disk evidence. Correction landed on 2026-04-27 in `artifacts/mathbac/MATHBAC_FULL_PROPOSAL_v1_2026-04-26.md` (§5.1.6 table row, §5.1.6 discussion paragraph, §11.3 Supplementary claim, §11.3 Status, §11.3 Disclaimer):

1. **What "6 surfaces" actually denotes.** The "6 surfaces" are six logical surfaces formed by grouping the eight named fields of Sub's `phi_beacon` packet (`id, phi, delta, age, auth, next, epoch, emit#`; Annex A Part 2 line 54 of the executed instrument) into the six slots of the Performer's SCBE L1 complex-context tuple: identity, intent, trajectory, timing, signature, commitment / L6 causality.

2. **What the "5 of 6" agreement is.** Five of the six SCBE L1 slots admit a one-to-one field-type-correspondence with a single `phi_beacon` field: `id ↔ identity`, `phi ↔ intent`, `delta ↔ trajectory`, `age ↔ timing`, `auth ↔ signature`. This is a *static type-level* correspondence between the two stacks' packet vocabularies, not a runtime decision-exchange.

3. **Identity of the sixth surface (the documented disagreement).** The sixth SCBE L1 slot — *commitment / L6 causality* — does not have a one-to-one match to a single `phi_beacon` field. It maps polymorphically to the triple (`next, epoch, emit#`), i.e. one-to-many. This polymorphic residue is the documented mismatch.

4. **Authoritative artifact for the disagreement.** The mapping table that records all six surfaces (including the polymorphic sixth) is `docs/proposals/DARPA_MATHBAC/one_pager_v1.md` lines 14–26, backed by Annex A Part 2 line 54 of `from_collin_20260421/teaming_agreement_v2_hoags_hardened.md`. The mismatch lives in the table row whose SCBE-L1 slot is `commitment / L6 causality` and whose `phi_beacon` field is the triple `next / epoch / emit#`. There is **no** disagreement file under `artifacts/mathbac/binary_protocol_harness_with_atomic_v2/` — that harness is a Performer-side observer-stability harness over 365 workbook tasks (3 observers × 3 representation-preserving transforms; `evidence_boundary` in `harness_manifest.json` explicitly disclaims any cross-stack / PSU(1,1) / Möbius equivariance claim) and was an incorrect pointer in the v1 draft.

5. **Scope correction.** §5.1.6 and §11.3 were also tightened to make explicit that the 5-of-6 claim is *static field-type-correspondence*, not runtime *admit/reject decision exchange*. No Phase I falsifier is built on this row; the Phase I load-bearing channel remains CDPTI-Internal (TS↔Python parity, Item 5.1.5). This is consistent with the abstract's framing of the Hoags Rust kernel as "supplementary independent witness" and "corroborating witness only — not required for any Phase I falsifier."

This resolution is offered for Sub's review. If Sub is content with the field-type-correspondence framing as restated above and the corrected evidence pointer, the Performer treats Item 2 as closed pending Sub's countersign of revision-2.

### Item 3 — Annex A Part 2 finalization
Sub asks the Performer to add to Annex A Part 2 of `teaming_agreement_v2_hoags_hardened.md`:
- the kernel UDP `net_probe` / phi-push channel, and
- the convergence-harness items backing CDPTI-External (§5.1.6, §11.3).

Sub explicitly excludes:
- `voice_grammar`
- `lang_dictionary`

**Performer resolution (2026-04-27).** Two new rows landed in `from_collin_20260421/teaming_agreement_v2_hoags_hardened.md` Annex A Part 2 (now 9 rows total), inserted after the `8-slot sentence grammar system` row and before Part 3:

1. **`net_probe` UDP / phi-push channel** — DAVA kernel-side UDP telemetry surface distinct from the serial `[PHI_BEACON]` row; packet format carrying phi-tier, epoch, beacon ID, rolling-hash auth token, emit sequence; sealed-trace-compatible payload format. Asserted as Sub Background IP under DFARS 252.227-7014(a)(15) / 252.227-7013(a)(14). Row text *excludes any reference to* `voice_grammar` *or* `lang_dictionary`.

2. **CDPTI-External convergence-harness items (Sub-side)** — DAVA-side artifacts backing §5.1.6 / §11.3 static field-type-correspondence between the 8-field `phi_beacon` packet (`id, phi, delta, age, auth, next, epoch, emit#`) and the 6-slot SCBE L1 complex-context tuple. Covers: emission state machine, field semantics and invariants (epoch/emit# monotonicity, rolling-hash auth, `next` schedule-pointer), sealed-trace measurement scaffolding, and Sub-side documentation fixing which `phi_beacon` fields type-correspond to which SCBE L1 slot. Row text explicitly disclaims runtime decision-exchange and any claim on Performer-side artifacts. Asserted under same Restricted/Limited Rights basis as DAVA kernel. Row text *explicitly excludes* `voice_grammar` *and* `lang_dictionary`.

Final row text is in the source file and is returned to Sub for review and countersign. If Sub is content with the wording, Performer treats Item 3 as closed pending Sub's countersign of revision-2.

### Item 4 — Soak-window written confirmation
This file is the Performer's record of that confirmation; satisfied by capture of Sub's reply and the affirmations in §1 above.

### Item 5 — §A.4.4 good-faith Phase II sentence
Sub asks the Performer to add one sentence to §A.4.4 expressing the Parties' intent to negotiate Phase II teaming on substantially the same terms, framed as a non-binding signal of continuity. **Performer landed this edit on 2026-04-27** in `MATHBAC_FULL_PROPOSAL_v1_2026-04-26.md` §A.4.4.

## 3. Sub's Stated Turnaround

Sub will turn redlines around within 24 hours once revision-2 of the full proposal is pushed for final review. Performer should not lock revision-2 without confirming Items 1, 2, and 3 back to Sub.

## 4. References

- `artifacts/mathbac/MATHBAC_FULL_PROPOSAL_v1_2026-04-26.md` (proposal under soak)
- `artifacts/mathbac/MATHBAC_PREVIEW_TO_COLLIN_2026-04-26.md` (Closing Note item 6, defining "partner-side written confirmation")
- `docs/proposals/DARPA_MATHBAC/from_collin_20260421/teaming_agreement_v2_hoags_hardened.md` (instrument under soak)
- `docs/proposals/DARPA_MATHBAC/from_collin_20260421/DAVA_IP_ASSERTION_v2.md` (Sub's IP assertion under DFARS 252.227-7017)
