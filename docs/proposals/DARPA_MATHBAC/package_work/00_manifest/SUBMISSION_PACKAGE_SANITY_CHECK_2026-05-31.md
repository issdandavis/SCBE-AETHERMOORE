# MATHBAC Submission Package Sanity Check - 2026-05-31

Purpose: hard-gate the BAAT zip before staging. This file is package-control guidance only and must not be uploaded as an attachment.

## Current Decision

Do not generate the final BAAT zip yet.

Reason: required final attachments are still missing or draft-only. Attachment D is stronger after the Spera / Lyapunov / CDPTI / BMRB-PDB pass, but the package is not submission-ready.

## Required BAAT Root Files

| Root file | Current source | Current status |
| --- | --- | --- |
| `Attachment_C_Proposal_Summary_Slide.pdf` | `03_attachment_c_summary_slide/ATTACHMENT_C_SUMMARY_SLIDE_DRAFT.md` | reviewed draft source; final PDF missing |
| `Attachment_D_Volume_I_Technical_Management.pdf` | `04_attachment_d_vol_i_technical_management/ATTACHMENT_D_VOL_I_DRAFT.md` | draft source only |
| `Attachment_E_Volume_II_Price.pdf` | `05_attachment_e_vol_ii_price/PRICE_COST_ANALYSIS_RESEARCH_2026-05-31.md` | draft source only |
| `Attachment_F_Streamlined_Cost_Buildup.xlsx` | `06_attachment_f_cost_workbook/*.csv` | draft source only |
| `Attachment_G_Model_OT_for_Research.pdf` | `07_attachment_g_model_ot/Attachment_G_SCBE_FILLED.docx`; `07_attachment_g_model_ot/Attachment_G_Model_OT_for_Research_DRAFT.pdf` | filled draft present; TIN/manual review/final PDF missing |
| `Attachment_H_Task_Description_Document.pdf` | `08_attachment_h_tdd/ATTACHMENT_H_TDD_DRAFT_2026-05-31.md` | draft source only |
| `Attachment_I_OT_Reps_and_Certs.pdf` | `09_attachment_i_reps_certs/Attachment_I_SCBE_FILLED.docx`; `09_attachment_i_reps_certs/Attachment_I_OT_Reps_and_Certs_DRAFT.pdf` | filled draft present; signature/date/final PDF missing; no TIN field |
| `Attachment_X_Proposal_Overview_and_Proposed_Metrics.pdf` | `../../proposer_added_metrics_v1.md` | draft source only |
| `Common_Disclosure_Form_Issac_Davis.pdf` | `11_disclosure_forms/DISCLOSURE_REQUIREMENTS_INVENTORY_2026-05-31.md` | inventory only; official form/final PDF missing |
| `Current_and_Pending_Support_Issac_Davis.pdf` | `11_disclosure_forms/DISCLOSURE_REQUIREMENTS_INVENTORY_2026-05-31.md` | inventory only; official form/final PDF missing |

## Exclusion Rules

Keep these out of the BAAT zip unless a later written decision explicitly changes the gate:

- `docs/ops/SCBE_API_TUNNEL_AGENT_HANDOFF_2026-05-31.md`
- `docs/ops/RESEARCH_VAULT_AGENT_HARNESS_BUS_CLI_INTEGRATION_PLAN.md`
- `12_ip_and_data_rights/collin_public_repo_due_diligence_2026-05-31.md`
- `12_ip_and_data_rights/collin_item2_surface_status_2026-05-31.md`
- all `SOURCE_MAP.md` files
- all package `README.md` files
- `00_manifest/FULL_DOCUMENT_CONSISTENCY_REVIEW_2026-05-31.md`
- `00_manifest/USER_ONLY_ACTIONS_TO_FINALIZE_2026-05-31.md`
- `11_disclosure_forms/DISCLOSURE_REQUIREMENTS_INVENTORY_2026-05-31.md`
- cost research notes that are not final Attachment E/F
- public repo diligence notes
- unresolved 5-of-6 / 6th-surface claims
- private-key, API-key, OAuth, mail, tunnel, or local runtime notes

## Language Gates

Final staged files must not contain:

- `guaranteed award`
- `DARPA owns this`
- `DARPA-owned`
- Hoags or Collin as lead PI, co-PI, co-lead, prime, or proposal authority
- DAVA as the center of gravity
- unresolved `[SIXTH_SURFACE_NAME]` placeholders
- claims that internal implementation is funded, obligated, or delivered before award

Allowed Hoags framing:

> Hoags Inc. is a bounded supporting subcontractor for DAVA-related background-IP assertions and optional corroborating telemetry context. SCBE-AETHERMOORE remains the prime, lead performer, and owner of the Phase I mathematical framework, protocol-design, benchmark, management, and reporting deliverables.

## Sanity Scan Commands

Run against draft sources now:

```powershell
rg -n "guaranteed award|DARPA owns|DARPA-owned|lead PI|co-PI|co PI|co-lead|\\[SIXTH_SURFACE_NAME\\]|Bearer|BEGIN [A-Z ]*PRIVATE KEY|api[_ -]?key\\s*[:=]|password\\s*[:=]|token\\s*[:=]" docs\proposals\DARPA_MATHBAC\package_work -g "*.md" -g "*.csv"
```

Run against the final staging folder before zip:

```powershell
rg -n "guaranteed award|DARPA owns|DARPA-owned|lead PI|co-PI|co PI|co-lead|\\[SIXTH_SURFACE_NAME\\]|Bearer|BEGIN [A-Z ]*PRIVATE KEY|api[_ -]?key\\s*[:=]|password\\s*[:=]|token\\s*[:=]" docs\proposals\DARPA_MATHBAC\package_work\99_final_zip_staging
```

The second scan must be clean or explicitly explained before the zip is created.

## Staging Gate

Only copy files into `99_final_zip_staging/` after:

1. Every required final filename exists in the correct final format.
2. Attachment E, Attachment F, and BAAT cost fields agree exactly.
3. Attachment D/H language keeps Hoags as supporting sub only.
4. Annex A / data-rights language has no unresolved placeholders.
5. The final staging folder passes the language/secret scan.
6. The staging folder contains only root-level BAAT upload files.
