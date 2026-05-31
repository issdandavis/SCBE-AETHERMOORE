# MATHBAC Price / Cost Analysis Research

**Date**: 2026-05-31  
**Proposal path**: SCBE Prime Lead + Hoags Supporting Sub  
**Status**: Working research basis for Attachment E and Attachment F. Not final until copied into the official DARPA templates.  

## Recommendation

Use a lean, credible Phase I proposed price of:

**Recommended BAAT proposed cost: `$839,000`**

This is well below the MATHBAC Phase I cap of `$2,000,000`, but still large enough to support 16 months of real labor, required travel, commercial GPU compute, IV&V artifact preparation, and a bounded Hoags subcontract.

## Price Zones

| Zone | Total price | When to use | Risk |
| --- | ---: | --- | --- |
| Lean minimum | `$690,000` | If we strip compute, travel, and Hoags to bare minimum. | May look under-scoped for a 16-month DARPA TA1 effort. |
| Recommended | `$839,000` | Best current balance: serious, efficient, not bloated. | Requires disciplined scope control and Hoags staying bounded. |
| Upper credible | `$1,120,000` | If official templates require more travel, security, accounting support, or larger subcontract. | Still below cap, but less aligned with user's low-cost posture. |
| Do not use unless forced | `$1,400,000+` | Old draft posture with larger sub share and heavier compute. | Looks padded for the current SCBE-led/tag-along-sub structure. |

## Recommended Cost Build

| Cost element | Basis | Amount |
| --- | --- | ---: |
| Prime direct labor | 3,520 hours across PI/technical lead, benchmark engineering, IV&V/reporting, and project/admin functions. | `$360,960` |
| Hoags supporting subcontract | Bounded DAVA/IP/telemetry support only; not a 35% co-lead share. | `$120,000` |
| Compute | Intermittent HF/GPU endpoint use, local model runs, storage, dataset staging, and benchmark reruns. | `$72,000` |
| Travel | Three required 3-day meetings: two DC-area, one SF Bay-area; primarily Issac, with limited sub travel only if needed. | `$18,000` |
| Other direct costs | Data, storage, secure backup, publication/artifact prep, accounting/compliance support, software services. | `$54,000` |
| Provisional G&A / indirect | 30% applied to prime base excluding subcontract: labor + compute + travel + ODC. | `$151,488` |
| Subtotal cost | Before fee. | `$776,448` |
| Fixed fee | 8% of subtotal cost, conservative for low-capital R&D. | `$62,116` |
| **Recommended total** | Rounded for BAAT / cost workbook. | **`$839,000`** |

## Prime Direct Labor Detail

| Labor category | Hours | Rate | Extended |
| --- | ---: | ---: | ---: |
| Prime PI / Technical Lead | 1,536 | `$115/hr` | `$176,640` |
| Research Software / Benchmark Engineering | 1,024 | `$105/hr` | `$107,520` |
| Data / IV&V / Reporting | 640 | `$85/hr` | `$54,400` |
| Project Admin / Compliance | 320 | `$70/hr` | `$22,400` |
| **Prime direct labor total** | **3,520** |  | **`$360,960`** |

These are direct labor planning rates. They are below several 2026 GSA IT schedule ceiling rates for comparable categories, which makes them defensible as efficient small-business rates.

## Hoags Supporting Subcontract Detail

| Sub task | Amount | Notes |
| --- | ---: | --- |
| SUB-1: DAVA background-IP / Annex A Part 2 support | `$25,000` | Needed if Hoags is listed in BAAT. |
| SUB-2: DAVA trace-generation / sealed-protocol context | `$30,000` | Only if artifact paths/hashes are verified. |
| SUB-3: phi_beacon field/spec support | `$20,000` | Exclude unresolved 5-of-6 claim unless closed. |
| SUB-4: net_probe / phi-push context | `$20,000` | Optional support; not load-bearing. |
| SUB-5: Sub review, reporting, milestone support | `$25,000` | Final language approval and milestone support. |
| **Hoags subcontract total** | **`$120,000`** | 14.3% of recommended total. |

This keeps Collin as tag-along support. It replaces the old 35% split with a scope-based supporting-sub value.

## Compute Basis

Hugging Face dedicated endpoint pricing supports using commercial GPU compute as an intermittent direct cost rather than a large owned-infrastructure line. Current examples include:

- T4 around `$0.50/hr`
- L4 around `$0.70-$0.80/hr`
- A10G around `$1.00/hr`
- L40S around `$1.80/hr`
- A100 around `$2.50-$3.60/hr`
- 8x A100 up to about `$20-$28.80/hr`

The recommended `$72,000` compute line is intentionally conservative. It covers:

- repeated benchmark reruns,
- ChemBERTa/Qwen/Mixtral latent extraction,
- endpoint staging,
- storage and transfer,
- burst capacity for IV&V-style challenge problems,
- failed-run buffer.

It does not assume sustained 24/7 frontier-model hosting.

## Travel Basis

The solicitation requires budgeting for three 3-day meetings over 16 months: two in the DC area and one in the San Francisco Bay area. The working travel line is:

| Trip | Planning amount |
| --- | ---: |
| DC meeting 1 | `$4,500` |
| DC meeting 2 | `$4,500` |
| SF Bay meeting | `$3,500` |
| Limited sub/contingency | `$5,500` |
| **Travel total** | **`$18,000`** |

This assumes GSA per diem-based lodging/M&IE, commercial airfare from the Pacific Northwest, ground transportation, and small contingency. Final Attachment E/F should use the official GSA lookup for the actual travel month.

## Indirect / G&A Basis

Use a provisional G&A/indirect rate of **30%** applied to the prime base excluding subcontract. This is a working proposal rate, not a DCAA-approved rate. The Attachment E narrative should say:

> SCBE proposes a 30% provisional G&A/indirect rate applied to prime direct labor and prime non-subcontract direct costs, subject to negotiation and final rate treatment under the award instrument. Subcontract costs are treated as pass-through and are not marked up by Prime.

This is consistent with the DCAA concept that provisional billing rates approximate final year-end rates until final indirect rates are settled.

## Fixed Fee / Profit Basis

Use **8% fixed fee** on subtotal cost. This is lower than the old 10% draft, aligns with the user's not-expensive posture, and remains reasonable for R&D risk.

## Milestone Payment Draft

Attachment F requires fixed payable milestones. Use the required MATHBAC milestones and spread dollars by work intensity:

| Month | Milestone | Payment |
| ---: | --- | ---: |
| M1 | Kickoff, theory/model/baseline plan, personnel assignment | `$84,000` |
| M3 | Initial successes/failures + initial math framework | `$109,000` |
| M6 | PI meeting + framework description + IV&V data pipeline demo | `$151,000` |
| M9 | Initial software-suite report + ROMs + challenge progress | `$151,000` |
| M13 | PI meeting + side-by-side baseline comparison + protocol set | `$151,000` |
| M14 | Computational design tool demo + IV&V test results | `$84,000` |
| M16 | Final report + catalog + Phase II plan | `$109,000` |
| **Total** |  | **`$839,000`** |

## Attachment E Narrative Stub

> The proposed Phase I price is `$839,000` for a 16-month TA1 effort. The price is based on a lean SCBE-prime execution model with Hoags Inc. included as a bounded supporting subcontractor. Labor is the principal cost driver because the work is mathematics, software, benchmark, and IV&V artifact production rather than capital equipment procurement. Compute is budgeted as intermittent commercial GPU endpoint use and local-model evaluation rather than persistent frontier-model hosting. Travel covers the three required PI meetings. Subcontract cost is separately identified and limited to DAVA-related background-IP, telemetry, and corroborating support tasks. The proposed fee is 8%, and the provisional G&A/indirect rate is 30% on the prime non-subcontract base, subject to negotiation.

## Final Checks Before BAAT

- BAAT proposed cost must be exactly `$839,000` if this build is used.
- Attachment E total must equal Attachment F workbook total.
- Hoags subcontract must appear as a separate line.
- Prime must not mark up Hoags pass-through subcontract cost.
- If Collin does not approve final sub language, remove or reduce the subcontract line before final upload.
- If official DARPA templates force different fee/indirect treatment, update this file and the workbook together.

## Source Basis

- MATHBAC local compliance checklist: Phase I cap, meeting/travel requirement, and milestone schedule.
- Hugging Face Inference Endpoints pricing: commercial GPU hourly rates and endpoint cost formula.
- GSA per diem page/API documentation: official CONUS travel rate source and lookup method.
- GSA MAS IT schedule example: comparable ceiling labor rates for software engineering, data science, systems engineering, technical writing, and project management.
- DCAA provisional billing rate guide: provisional indirect rates as interim approximations before final indirect-rate settlement.

