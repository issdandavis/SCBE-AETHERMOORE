# SCBE-2026-0001 — Prosecution Docket & Next Steps

Generated: 2026-06-09. **Not legal advice** — verify every date against Patent
Center, the MPEP, and the current USPTO fee schedule. Pro se (37 CFR 1.29(a)
micro entity). Inventor: Issac Daniel Davis.

## Current state (as of 2026-06-09)

| Field | Value |
| --- | --- |
| Non-provisional | **19/691,526**, filed **2026-05-28**, utility under 35 USC 111(a) |
| Title (per filing receipt) | System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity |
| Provisional (priority) | **63/961,403**, filed **2026-01-15** |
| Confirmation no. | 1177 · Patent Center doc 76776451 · docket SCBE-2026-0001 |
| Entity | MICRO (37 CFR 1.29(a); paid micro rates, total $720) |
| Status | "Application Filed" (code 20). No examiner / art unit assigned. Zero office actions. |
| Public ODP API | **404 — not indexed until publication (~2027-07).** Track via Patent Center until then. |

Priority date for all clocks below = **2026-01-15** (provisional).

## Dated docket

| When | Item | Why it matters |
| --- | --- | --- |
| **Now** | Pull the **official Filing Receipt** from Patent Center (the 2026-05-28 doc on file is the *acknowledgement*, not the filing receipt). Verify: (a) domestic-benefit claim to 63/961,403 is listed, (b) MICRO entity recorded, (c) inventor name + title correct. | A missing/garbled priority claim is cheap to fix now (Corrected ADS), expensive after the window. The benefit claim is what gives the 2026-01-15 date. |
| **Now** | Confirm the **micro-entity certification (PTO/SB/15A)** posted. | Micro rates were paid; paying micro without the cert on file is a fixable but real defect. |
| **~2026-08-28** | File an **IDS (Information Disclosure Statement)** with known material prior art from `prior_art_search_log.md`. | 3-month safe-harbor from NP filing → no fee, no certification. After it, IDS needs a fee/cert. Duty of disclosure (37 CFR 1.56) runs the whole pendency. |
| **2027-01-15** | **Decide foreign / PCT strategy** (12 months from provisional). File PCT and/or direct nationals if international rights wanted. | Hard bar — miss it and most foreign rights are lost. Most consequential strategic call. Decide by ~Nov 2026. |
| **2027-05-15** | Domestic priority-claim deadline (later of 4 mo from NP filing or 16 mo from provisional, 37 CFR 1.78). | Should already be satisfied at filing; this is the backstop. Verify via the filing receipt above. |
| **~2027-07-15** | **18-month publication.** Auto-publishes unless a non-publication request was filed at filing. | Non-pub request is only valid if you waive foreign filing — almost certainly NOT what you want, so expect publication. After publication the public ODP monitor starts working. |
| **~2027–2028** | First **Office Action** (typical pendency 12–24 mo). | Respond within the set period (usually 3 mo, extendable to 6 with fees). Identify 101/102/103/112; amend narrowly; argue from claim language + spec support. |

## Decisions pending (no hard deadline, but real)

- **Aerospace-skin provisional** — drafted, not filed. If you want that subject
  matter protected, either file it as its own provisional (starts a fresh
  12-month clock) or fold it into a **CIP** of 19/691,526. Note: the working
  packet already flagged `bijective_tamper` / `identifier_canonicality` as
  possible new-matter vs the 2026-01-15 provisional → CIP candidates.
- **Micro-entity maintenance** — if gross income or institutional affiliation
  changes, you must notify USPTO of loss of micro-entitlement before/with the
  next fee.

## Tooling note

- `scripts/system/uspto_prosecution_monitor.py --app 19691526` returns 404 until
  publication (public API = published apps only). The seeded baseline is a manual
  placeholder, not a real fetch. **Action:** rely on Patent Center for status
  now; the monitor becomes useful from ~2027-07. (Optionally, the script could be
  extended to the authenticated Patent Center / Private-PAIR-equivalent endpoint
  if one is available to applicants for unpublished apps.)
- The seed JSON carries a stale title ("Cryptographic Intent Containment…"); the
  **filing receipt title is authoritative**.

## Do-this-week shortlist

1. Patent Center → download the official Filing Receipt → verify priority claim +
   micro cert + inventor/title. Save it to `04_FILED_RECEIPTS/`.
2. Begin assembling the **IDS** (deadline 2026-08-28) from the prior-art log.
3. Put **2027-01-15 (PCT/foreign)** on the calendar as the big strategic decision.
