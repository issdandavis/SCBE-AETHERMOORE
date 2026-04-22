# MATHBAC Submission Readiness - 2026-04-20

## Colin 5:43 PM packet

Source email:
- From: `collinhoag@hoagsandfamily.com`
- Date: `2026-04-20 17:43:23 -0700`
- Subject: `MATHBAC TA1 - Signed teaming docs + strategy5.py [2026-04-20]`

Staged attachments:
- `artifacts/proton_mail/2026-04-20_collin_1743/teaming_agreement_v1_signed.pdf`
- `artifacts/proton_mail/2026-04-20_collin_1743/ip_carveout_v1_signed.pdf`
- `artifacts/proton_mail/2026-04-20_collin_1743/MATHBAC_ABSTRACT_DRAFT.pdf`
- `artifacts/proton_mail/2026-04-20_collin_1743/strategy5_for_issac.py`

## Official identifier split

Use these consistently:
- `DARPA-SN-26-59` = MATHBAC Proposers Day special notice
- `DARPA-PA-26-05` = MATHBAC program announcement / proposal opportunity

Implication:
- Proposers Day docs, playbooks, event notes, and registration references can keep `DARPA-SN-26-59`
- Proposal-facing abstract and submission-facing materials should use `DARPA-PA-26-05`

## Checked items

- Colin's email says Hoags accepted the draft terms with one correction: Hoags Inc. is Oregon, not Washington.
- The attached abstract already shows `MATHBAC Abstract - DARPA-PA-26-05`.
- The repo's teaming and IP docs currently cite `DARPA-SN-26-59`, which is acceptable for Proposers Day / teaming context but should not be blindly reused as the proposal solicitation identifier.
- Colin's `strategy5_for_issac.py` baseline reproduces on the staged blind set:
  - `D_KL = 0.029375` nats
  - `Channel capacity = 1.9576 bits/tick`
  - `Ceiling = log2(4) = 2.0000 bits`
  - `% of ceiling = 97.9%`
  - `Agreement rate = 81.7%`
- Strategy result written to `artifacts/tmp/DARPA_MATHBAC/evidence/strategy5_result.json`.

## Immediate next actions

1. Treat the attached abstract as the proposal-facing header baseline and keep `DARPA-PA-26-05` there.
2. Keep the teaming agreement and Proposers Day materials on the `DARPA-SN-26-59` track unless a final proposal package version is created from them.
3. Run `artifacts/proton_mail/2026-04-20_collin_1743/strategy5_for_issac.py` against the committed segmentation bundle to confirm the Euclidean baseline before swapping in real `d_H`.
4. Patch any outward-facing technical packet or abstract text that still leaks stronger-than-supported claims before shipping.
5. If a final submission packet is assembled, add a one-line note distinguishing `SN` versus `PA` so the identifiers do not get mixed again.
