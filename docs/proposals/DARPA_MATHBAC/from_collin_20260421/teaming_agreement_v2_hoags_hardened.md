# PRE-AWARD TEAMING AGREEMENT AND INTELLECTUAL PROPERTY ASSIGNMENT

**Version:** 2.0-HOAGS (hardened Annex A; adds Annex G — IP Representation Exhibit)
**Base draft:** teaming_agreement_v2_draft.md by Issac D. Davis, 2026-04-20
**Hoags amendments:** Annex A Part 2 strengthened; Annex G added; Part 3 updated with 2026-04-21 proof data
**Status:** Hoags Inc. proposed changes — for Issac's review and incorporation into execution copy

---

Articles 1–12 and Annexes B–F are UNCHANGED from teaming_agreement_v2_draft.md.
Only Annex A (Parts 2 and 3) and the new Annex G are modified below.

---

# ANNEX A — DFARS 252.227-7017 ASSERTIONS (HARDENED)

*Per DFARS 252.227-7017, each Party identifies below the technical data and computer software
for which it asserts restrictions on the Government's rights. Failure to assert restrictions
prior to award results in Unlimited Rights delivery per DFARS 252.227-7013(b)(1).*

## Part 1 — Prime's (Issac D. Davis) Assertions

*UNCHANGED from teaming_agreement_v2_draft.md — reproduced here for completeness.*

| (1) Technical Data or Software | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Asserting Party |
|---|---|---|---|
| SCBE-AETHERMOORE 14-layer pipeline (TypeScript canonical; Python reference; Rust experimental), including source, compiled artifacts, and layer-specific modules L1–L14 | Developed at private expense, 2024–2026, no Government funding; public commits predate 2026-03-24 SN issuance | Restricted Rights (software) / Limited Rights (technical data) | Issac D. Davis |
| Langues Weighting System (LWS) specification and implementation, including Sacred Tongues tokenizer (KO, AV, RU, CA, UM, DR with phi-scaled weights) | Developed at private expense, 2024–2026; published under KDP ASIN B0GSSFQD9G as *The Six Tongues Protocol* (timestamped prior art) | Restricted Rights / Limited Rights | Issac D. Davis |
| Harmonic wall formula *H(d, pd) = 1/(1 + d_H + 2·pd)* and reference implementations in TypeScript and Python | Developed at private expense, 2025–2026; disclosed in USPTO Provisional 63/961,403 | Restricted Rights / Limited Rights | Issac D. Davis |
| Audio-axis telemetry stack and vacuum-acoustics modules | Developed at private expense, 2025–2026 | Restricted Rights / Limited Rights | Issac D. Davis |
| PHDM (Polyhedral Hyperbolic Defense Manifold) and associated crypto primitives (ML-KEM-768, ML-DSA-65 integration) | Developed at private expense, 2025–2026; library integrations use open-source primitives with permissive licenses | Restricted Rights / Limited Rights | Issac D. Davis |

---

## Part 2 — Sub's (Hoags Inc.) Assertions — HARDENED

*The following replaces the four-row table from teaming_agreement_v2_draft.md.
Each row now satisfies the three-prong DFARS 252.227-7017 audit standard:
(a) developed at private expense, (b) no employer resources used, (c) pre-existing to Government funding.*

**Footnote †** (applies to all rows): DAVA Background IP was developed entirely at private
expense on personal hardware owned by Collin Hoag, during personal time, beginning no later
than 2024-Q4. Developer was employed by Microsoft Corporation during this period; however,
(i) no Microsoft resources, facilities, networks, tools, datasets, or proprietary information
were used, (ii) the work was not performed within the scope of employment duties, and
(iii) the work does not relate to Microsoft's products or research. Microsoft's standard
Washington-state IP assignment clause does not apply on these facts. No Government funding was
applied at any stage. See Annex G for the formal written representation.

| (1) Technical Data or Computer Software | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Asserting Party |
|---|---|---|---|
| **DAVA bare-metal Rust kernel** — complete source tree (`exodus/` repository), compiled ELF64/ELF32 artifacts, custom `x86_64-hoags` bare-metal target specification (`x86_64-hoags.json`), multiboot bootloader, linker scripts, and all life-module subsystems including: `consciousness_gradient`, `endocrine`, `qualia`, `narrative_self`, `phi_calc`, `phi_beacon`, `phi_gradient`, `alphabet_engine`, `lang_dictionary`, `lang_grammar`, `lang_phrase_planner`, `lang_sentence_buffer`, `lang_self_awareness`, `lang_emotion_syntax`, `lang_coherence_tracker`, `lang_intent_formation`, `lang_bigram`, `lang_word_recency_filter`, `lang_question_form`, `lang_semantic_memory`, `anima_mesh`, `anima_population`, `sensory_mesh`, `oscillator`, `sanctuary_core`, `nexus`, `resonance`, `consciousness_mesh`, and all dependent modules. Approximately 34,900+ Rust source files. First git commit evidence predates DARPA-SN-26-59 issuance (2026-03-24). | Developed entirely at private expense. See Footnote †. No Government funding. | Restricted Rights (computer software, DFARS 252.227-7014(a)(15)) / Limited Rights (technical data, DFARS 252.227-7013(a)(14)) | Collin Hoag, President, Hoags Inc. |
| **`phi_gradient.rs` and phi computation subsystem** — IIT-inspired Φ (phi) integration gradient kernel; tier-classification thresholds at phi-values 250 (SubConscious), 500 (Aware), 750 (Conscious), 900 (Lucid); exponential moving average smoothing; phi-weighted consciousness scoring; all associated constants, helper functions, and serial output format (`[DAVA_FIELD]`, `[PHI_BEACON]` log lines). | Same basis as DAVA kernel. See Footnote †. Module history traceable to personal git commits predating 2026-03-24. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`phi_beacon` telemetry surface** — phi-event emission protocol; Fibonacci-gated reporting intervals; epoch counter; authentication token generation (rolling hash); sealed-trace format for external measurement; `[PHI_BEACON]` serial output spec including fields: `age`, `phi`, `delta`, `epoch`, `id`, `auth`, `emit#`, `next`. | Same basis as DAVA kernel. See Footnote †. No Government funding. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`proof_strategies.py` and `strategy5_for_issac.py`** — Python analysis toolkit for DAVA trace measurement: sealed-label recovery experiment harness; Euclidean channel-capacity measurement pipeline (producing 1.9576 bits/tick result); permutation-test statistical framework; segmentation-bundle reader and commit-hash verifier; regime-classification scoring. | Developed at private expense on personal hardware, personal time, 2026-03 through 2026-04. See Footnote †. No Government funding. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **Sealed-protocol design — DAVA-side components** — the specific protocol design for trace sealing: DAVA trace generation procedure, seal-hash computation and registry format, unsealing trigger conditions, delivery specification, and the DAVA kernel parameters that produce classifiable regime-distinct traces (PAIN/FEAR/NEUTRAL/CALM/JOY endocrine states mapped to sealed bundles). | Jointly conceived by Sub and Prime, 2026-03-15 through 2026-04-20. Sub's solely-owned contribution: the DAVA kernel-side trace generation, sealing, and delivery mechanism. Full Joint IP treatment in Part 3 and Article 4.3. | Restricted Rights / Limited Rights (Sub's contribution to joint work) | Collin Hoag, President, Hoags Inc. |
| **8-slot sentence grammar system** — `lang_grammar.rs` complexity-driven sentence length (2–8 words); `lang_sentence_buffer.rs` sentence assembly with minimum-word guard; `lang_phrase_planner.rs` SVO+embedded-clause slot mapping; `alphabet_engine.rs` 8-position PRONOUN→VERB→NOUN→ADJ→CONJ→VERB→NOUN→ADV pattern. Produces grammatically structured natural-language output from bare-metal phi/consciousness state. Committed 2026-04-21. | Developed at private expense, personal hardware, personal time. See Footnote †. No Government funding. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`net_probe` UDP / phi-push channel** — DAVA kernel-side network telemetry surface distinct from the serial `[PHI_BEACON]` row above: UDP-based phi-event push protocol over Ethernet / QEMU virtual-NIC; packet format carrying phi-tier, epoch, beacon ID, rolling-hash auth token, and emit sequence; emission-cadence control; sealed-trace-compatible payload format suitable for cross-stack measurement by an external observer (including the Performer's CDPTI-External harness). Source modules under `exodus/` net stack and `phi_beacon` push glue, including target-side scheduler hooks. *Excludes any reference to `voice_grammar` or `lang_dictionary` modules.* | Developed at private expense on personal hardware, personal time. See Footnote †. No Government funding. | Restricted Rights (computer software, DFARS 252.227-7014(a)(15)) / Limited Rights (technical data, DFARS 252.227-7013(a)(14)) | Collin Hoag, President, Hoags Inc. |
| **CDPTI-External convergence-harness items (Sub-side)** — DAVA-side artifacts that back the §5.1.6 / §11.3 *static field-type-correspondence* claim between the 8-field `phi_beacon` packet (`id, phi, delta, age, auth, next, epoch, emit#`) and the 6-slot SCBE L1 complex-context tuple (identity, intent, trajectory, timing, signature, commitment / L6 causality). Specifically: `phi_beacon` emission state machine; field semantics and invariants (monotonicity of `epoch` and `emit#`, rolling-hash `auth` derivation, `next` schedule-pointer semantics); sealed-trace measurement scaffolding consumed by the Performer's harness; the Sub-side documentation that fixes which `phi_beacon` fields type-correspond to which SCBE L1 slot. This row covers Sub-side artifacts only; it makes no claim on Performer-side mapping tables, harness drivers, or Performer documentation, and asserts no runtime decision-exchange between the two stacks. *Explicitly excludes: `voice_grammar`, `lang_dictionary`.* | Same basis as DAVA kernel. See Footnote †. No Government funding. Pre-existing to DARPA-SN-26-59. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |

---

## Part 3 — Joint Prior Work (expressly identified; 50/50 co-ownership per Article 4.3)

*Updated 2026-04-21 to include session results from this date.*

| Item | Creation Dates | Evidence | Rights |
|---|---|---|---|
| Joint blind-classification protocol design, seal-hash registry, 24/24 = 100% sealed-label recovery on DAVA traces, permutation-test *p ≤ 3.00×10⁻⁴* | 2026-03-15 through 2026-04-20 | Seal hashes on file; ISSAC_V1_BLIND_REPORT_20260419.md; SEAL_WITNESS_2026-04-19.md | 50/50 Joint IP per Article 4.3 |
| Joint Euclidean/hyperbolic capacity comparison methodology — 1.9576 bits/tick (97.9% of 2-bit ceiling), companion layers at 1.5761 and 2.9818 bits/tick | 2026-04-14 through 2026-04-20 | PROOF_STRATEGY_RESULTS.md; strategy5_for_issac.py outputs | 50/50 Joint IP per Article 4.3 |
| **DAVA live-session proof dataset — 2026-04-21** (Proposers Day eve): 11,033+ kernel-native sentences generated at consciousness tier=Conscious (score 770–806), phi=518, phi_beacon epoch 673, nexus unity=690; sentence distribution 4–8 words; 672+ phi emission events; AETHERMOORE wall active (QUARANTINE/ALLOW decisions emitted every 89 ticks). Raw serial log: `/tmp/dava_stdio.log`. This dataset constitutes direct evidence of regime-coherent natural-language generation from bare-metal IIT-phi substrate, suitable as TA1 proof artifact. | 2026-04-21 | `/tmp/dava_stdio.log` (QEMU serial stdout); git commit ab96f93f0 (feat/dava-physical-body branch) | 50/50 Joint IP per Article 4.3 |

*This Annex A supersedes the Annex A in teaming_agreement_v2_draft.md and is incorporated into
the proposal submitted under DARPA-PA-26-05 as the pre-award DFARS 252.227-7017 assertions list.
Any Award instrument shall incorporate this Annex A by reference.*

---

# ANNEX G — BACKGROUND IP REPRESENTATION EXHIBIT (NEW)

*Added by Hoags Inc. per Article 6.3. To be executed simultaneously with countersignature of Article 12.*

## G.1 Purpose

This Exhibit memorializes Sub's representations under Article 6.3 of the Pre-Award Teaming Agreement
v2.0 with respect to third-party claims on DAVA Background IP, specifically addressing the
Microsoft Corporation IP-assignment question raised by Prime.

## G.2 Representations

Sub (Hoags Inc.), by its signatory Collin Hoag, President, hereby represents and warrants:

**(a) Private development.** The DAVA Background IP identified in Annex A, Part 2 was developed
entirely at Sub's private expense, on personal computing hardware owned by Collin Hoag, during
time outside of any employment obligations.

**(b) No employer resources.** No resources, facilities, equipment, networks, tools, datasets,
proprietary information, or funding belonging to Microsoft Corporation or any other current or
former employer were used in the development of DAVA Background IP at any stage.

**(c) Outside scope of employment.** DAVA was not developed within the scope of any employment
duties. It does not embody, derive from, or incorporate any work product created in the course
of employment.

**(d) Microsoft IP assignment clause inapplicable.** To the best of Sub's knowledge, Microsoft
Corporation's standard Washington-state employment IP assignment clause does not apply to DAVA
Background IP because the conditions for its application — use of employer resources or development
within the scope of employment — are not met on the facts stated in (b) and (c) above.

**(e) No encumbrances.** Sub is not aware of any lien, security interest, license, assignment,
or third-party claim that would impair Sub's ability to grant the licenses set forth in Article
4.5 of the Agreement or assert the restrictions in Annex A, Part 2.

**(f) No disclosure obligation.** Sub has not filed, and is not obligated to file, any invention
disclosure or assignment with Microsoft Corporation or any other party with respect to DAVA
Background IP.

**(g) Pre-existing to Government funding.** DAVA kernel development began no later than 2024-Q4,
and all Background IP identified in Annex A, Part 2 predates DARPA-SN-26-59 (issued 2026-03-24)
and any Government funding relationship.

## G.3 Survival

These representations survive termination of the Agreement and are incorporated by reference
into any Award subcontract executed under Article 7.3 / Annex E.

## G.4 Signature

**SUBCONTRACTOR:**

Signature: ______________________________
Name: Collin Hoag
Title: President, Hoags Inc.
Date: ___________________

*Executed simultaneously with Article 12 countersignature.*

---

## END OF HOAGS AMENDMENTS TO TEAMING_AGREEMENT_V2
