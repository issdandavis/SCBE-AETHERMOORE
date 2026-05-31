# SCBE Nonprovisional Post-Filing Checklist

Status: filed and paid.

This checklist starts after the Patent Center electronic acknowledgement receipt.
It is not legal advice; it is an operational control sheet for the pro se filing.

## Filed Application

- Application number: 19/691,526
- Attorney docket number: SCBE-2026-0001
- Confirmation number: 1177
- Patent Center number: 76776451
- Filed/payment receipt time: 2026-05-28 10:54:51 PM Z ET
- Fees paid: $720.00
- Provisional priority claimed: 63/961,403, filed January 15, 2026
- Local acknowledgement receipt: `docs/legal/filing-packet-scbe-2026-0001/04_FILED_RECEIPTS/USPTO_ELECTRONIC_PAYMENT_RECEIPT_APP_19-691526_2026-05-28.pdf`

## What To Do Now

1. Save the formal Filing Receipt when Patent Center posts it.
   - Expected source: Patent Center application record / IFW.
   - USPTO notes that new documents may not display immediately after filing.

2. Confirm the filing receipt details.
   - Title exactly matches the intended title.
   - Inventor name and correspondence address are correct.
   - Micro-entity status is reflected.
   - Provisional benefit claim to 63/961,403 is present.
   - Foreign filing license status is noted before any non-US/PCT action.

3. Establish monitoring.
   - Manual: search Patent Center by application number `19/691,526`.
   - Automated: set `USPTO_ODP_API_KEY`, then run:
     `python scripts/system/uspto_prosecution_monitor.py --app 19691526`
   - Daily local reminder:
     `python scripts/system/daily_patent_check.py --check-email`

4. Build an Office Action response bench before any Office Action arrives.
   - Prepare response shells for section 101, 102, 103, and 112.
   - Keep claim chart support for independent claims 1, 9, and 15 easy to access.
   - Keep benchmark/evidence packet separate from the filed spec; use it for argument support, not as filed matter.

5. Avoid new-matter confusion.
   - New technical improvements after filing should go into a continuation/CIP candidate log, not silently into the filed case.
   - Do not describe post-filing improvements as already present in this application unless the filed spec actually supports them.

## Expected USPTO Events

- Electronic acknowledgement receipt: already saved.
- Formal filing receipt: should issue in due course if filing-date requirements are satisfied.
- Pre-exam/formality notices: possible; respond by the stated deadline if any issue appears.
- First Office Action: common in software/AI cases; response must address every rejection/objection.

## Response Deadline Rule Of Thumb

USPTO guidance states that most Office Action replies have a statutory six-month outer limit, while the Office Action usually sets a shorter period, commonly two or three months, for reply without extension fees. Calendar both dates immediately when any Office Action arrives.

## Official Sources Checked

- USPTO, Check the filing status of your patent application: https://www.uspto.gov/patents/apply/checking-application-status/check-filing-status-your-patent-application
- USPTO, Responding to Office Actions: https://www.uspto.gov/patents/maintain/responding-office-actions
- MPEP 503, Application Number and Filing Receipt: https://www.uspto.gov/web/offices/pac/mpep/s503.html

## Not Needed Today

- Do not file extra papers just because the application was submitted.
- Do not file an IDS unless a material known reference needs disclosure.
- Do not amend claims unless a USPTO notice or strategic reason requires it.
- Do not start PCT/foreign filing without checking budget, foreign filing license, and deadline strategy.
