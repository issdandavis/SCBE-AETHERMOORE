# Patent Tracker - SCBE-2026-0001

Status: active post-filing prosecution tracking.

This is the top-level tracker for the filed SCBE utility application. It points
to the detailed docket and evidence files, and it separates completed filing
facts from future monitoring tasks.

## Case Summary

| Field | Value |
|---|---|
| Internal docket | SCBE-2026-0001 |
| Active application | 19/691,526 |
| Compact application number | 19691526 |
| Application type | Utility - Nonprovisional Application under 35 USC 111(a) |
| Filing/payment timestamp | 2026-05-28 10:54:51 PM ET |
| Confirmation number | 1177 |
| Patent Center number | 76776451 |
| First named inventor | Issac Daniel Davis |
| Priority provisional | 63/961,403, filed 2026-01-15 |
| Current local status | Filed and paid; formal filing receipt / next USPTO notice pending |

## Evidence Index

| Evidence | Path |
|---|---|
| Post-filing docket | `docs/legal/patent-workbench/post_filing_docket_2026-05-30.md` |
| Application status record | `docs/legal/patent-workbench/application_status.md` |
| Readiness / docket checklist | `docs/legal/patent-workbench/filing_readiness_checklist.md` |
| Payment receipt | `docs/legal/filing-packet-scbe-2026-0001/04_FILED_RECEIPTS/USPTO_ELECTRONIC_PAYMENT_RECEIPT_APP_19-691526_2026-05-28.pdf` |
| Filing receipt snapshot | `docs/legal/filing-packet-scbe-2026-0001/04_FILED_RECEIPTS/FILING_RECEIPT_SNAPSHOT_APP_19-691526.md` |
| Filed spec | `docs/legal/filing-packet-scbe-2026-0001/01_SUBMIT_THESE_TO_PATENT_CENTER/SCBE_NONPROVISIONAL_SPEC_v1.docx` |
| Filed drawings | `docs/legal/filing-packet-scbe-2026-0001/01_SUBMIT_THESE_TO_PATENT_CENTER/drawings_pdf_letter/` |
| Signed forms | `docs/legal/filing-packet-scbe-2026-0001/03_SIGNATURE_FORMS_REVIEW/` |
| Prior-art log | `docs/legal/patent-workbench/prior_art_search_log.md` |
| Claim support scan | `docs/legal/patent-workbench/claim_support_scan.md` |
| Rejection likelihood / fallbacks | `docs/legal/patent-workbench/rejection_likelihood_and_fallbacks_2026-05-30.md` |
| Value position evidence | `docs/legal/patent-workbench/value_position_evidence_2026-05-30.md` |

## Active Tracker

| ID | Status | Target / Date | Task | Evidence / Notes |
|---|---|---:|---|---|
| PT-001 | done | 2026-05-28 | File non-provisional and pay fees | Local receipt snapshot and payment receipt saved. |
| PT-002 | open | ASAP | Save formal filing receipt from Patent Center | Compare title, inventor, entity status, priority claim, and correspondence data. |
| PT-003 | open | ASAP / recurring | Check for OPAP or other formality notice | If a notice posts, calendar the exact due date from the notice. |
| PT-004 | open | 2026-08-28 review | IDS review window | MPEP 609.04(b): IDS is considered without fee/statement if filed within three months of filing or before first Office Action on the merits, whichever is later. |
| PT-005 | open | Before any foreign/PCT action | Foreign filing license check | Confirm status from formal filing receipt / Patent Center before any non-US filing. |
| PT-006 | open | 2027-01-15 strategy deadline | Foreign/PCT priority strategy review | Calendar as a priority-claim planning deadline from provisional filing date; verify with official guidance before action. |
| PT-007 | in_progress | Ongoing | Office Action response bench | Build 101, 102, 103, and 112 response shells from filed claims/spec only. |
| PT-008 | in_progress | Ongoing | Continuation/CIP candidate log | Track post-2026-05-28 Longform Bridge, Polly Pad, GeoSeed, and agent-bus improvements separately. |
| PT-009 | open | On formal filing receipt | Publication expectation check | If no non-publication request was filed, record expected publication timing from official receipt/status. |
| PT-010 | open | On first substantive USPTO action | Deadline calculator | Record mailing date, shortened statutory period, extension windows, and final statutory deadline. |
| PT-011 | done | 2026-05-30 | Rejection likelihood and fallback memo | See `rejection_likelihood_and_fallbacks_2026-05-30.md`. |
| PT-012 | done | 2026-05-30 | Value/evidence memo | Public-safe wording for "this is worth something" without saying issued/patented. |

## Monitoring Commands

```powershell
# Local workbench health
npm run patent:status

# Local email check for USPTO / patent messages
python scripts/system/daily_patent_check.py --check-email

# USPTO monitor when API key is configured
python scripts/system/uspto_prosecution_monitor.py --app 19691526
```

## Working Rules

- Patent Center is the source of truth for official status.
- Do not store Patent Center credentials, private address copies, card details,
  or unrelated personal records in the repo.
- Treat post-filing inventions as continuation/CIP candidates unless the filed
  specification already supports them.
- Do not make public claims stronger than the evidence: say "filed", "pending",
  "local evidence preserved", or "waiting for USPTO notice."
- When a USPTO notice arrives, update this tracker before drafting any response.

## Official Sources

- USPTO Patent Center status guidance:
  https://www.uspto.gov/patents/apply/checking-application-status/check-filing-status-your-patent-application
- USPTO OPAP missing/incomplete application notices:
  https://www.uspto.gov/patents/apply/when-patent-applications-are-incomplete-or-missing-information
- MPEP 609.04(b) IDS timing:
  https://www.uspto.gov/web/offices/pac/mpep/documents/0600_609_04_b.htm
