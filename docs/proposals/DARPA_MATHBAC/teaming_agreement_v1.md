# Teaming Agreement — MATHBAC TA1 Proposal

**Solicitation:** DARPA-SN-26-59 (MATHBAC), Technical Area 1
**Date:** 2026-04-20
**Status:** Draft v1 for Collin's review. Not signed. Not binding until executed.

---

## Parties

- **Prime:** Issac D. Davis, sole proprietor
  SAM UEI **J4NXHM6N5F59** · CAGE **1EXD5** (active 2026-04-13)
  Email: issdandavis7795@gmail.com · Phone: (360) 808-0876

- **Subcontractor:** Hoags Inc., a Washington corporation, represented by Collin Hoag, President
  CAGE **15XV5**
  Email: collinhoag@hoagsandfamily.com · Phone: (458) 239-3215

## 1. Purpose

The Parties agree to team, with Issac D. Davis as Prime and Hoags Inc. as sole Subcontractor, for the purpose of preparing, submitting, and (if awarded) executing a Phase I proposal in response to DARPA-SN-26-59 MATHBAC TA1.

## 2. Exclusivity

For the period of this agreement, each Party agrees not to join any other team submitting to DARPA-SN-26-59 TA1 without the written consent of the other Party. Either Party remains free to pursue unrelated solicitations or unrelated technical areas within DARPA-SN-26-59 (e.g., TA2) independently.

## 3. Cost split (opening position)

- **65% Prime / 35% Subcontractor** of the awarded Phase I dollar value, inclusive of labor, travel, materials, and indirect rates.
- This split is an opening position for the final proposal budget. Both Parties may adjust in writing before the cost proposal is submitted, based on scope refinement.
- The Subcontractor's share is disbursed against invoices for delivered work packages (defined in Section 5).

## 4. Roles

- **Prime (Issac D. Davis)** is responsible for:
  - Proposal authorship and submission (technical narrative, cost volume, compliance).
  - Primary point of contact with the DARPA Program Manager.
  - Cost-proposal signatory and contract signatory.
  - Technical lead on SCBE-AETHERMOORE deliverables: 14-layer pipeline, Poincaré-ball observer, hyperbolic L8 bootstrap against `tier_code`, Möbius-equivariance proof, open-vocabulary regime test.
  - Administrative burden: SAM.gov maintenance, audit-ready artifact retention, DCAA-style timekeeping.

- **Subcontractor (Hoags Inc.)** is responsible for:
  - Technical lead on DAVA deliverables: bare-metal Rust kernel, `phi_beacon` emissions, trace CSV generation, tier_code labeling, 100-trace scale-up capacity.
  - Live QEMU capture capability for the phi-telemetry substrate bridge (Deliverable #4).
  - Co-authorship of jointly-owned scientific output (joint memo, paper, deliverable reports).

## 5. Work packages & deliverables

The Parties jointly commit to the Phase I deliverables articulated in `docs/proposals/DARPA_MATHBAC/joint_memo_v1.md`, namely:

1. 100-trace scale-up of the sealed-blind protocol with open-vocabulary regimes. (Sub lead)
2. Algorithmic realm-layout derivation (SDP-promoted k-means++ with minimum-separation constraints). (Prime lead)
3. Bootstrap confidence intervals on KL capacity and 24/24 accuracy, **including the `tier_code`-vs-real-hyperbolic-L8 bootstrap reconciliation for the v2 §3.4 discrepancy**. (Prime lead, using Sub's `proof_strategies.py` for parity.)
4. Live QEMU capture of DAVA `phi_beacon` emissions ingested by SCBE L1 in real time. (Sub lead for emitter; Prime lead for ingestion.)
5. Formal statement and proof attempt of a Poincaré-curvature-based channel-capacity upper bound. (Joint.)

Detailed scoping of each work package into the cost proposal is an outcome of Phase I award notification, not of this teaming agreement.

## 6. Intellectual Property

Intellectual property is governed by the companion document `docs/proposals/DARPA_MATHBAC/ip_carveout_v1.md`, which both Parties execute concurrent with this teaming agreement.

## 7. Proposal deadlines

- **Abstract submission:** 2026-04-30.
- **Full proposal (if DARPA invites):** within the BAA-specified window (typically 8-12 weeks after abstract feedback).
- Both Parties agree to meet or beat any deadline the Prime sets at least 72 hours before the DARPA deadline, to allow submission-checklist review.

## 8. Representations

- Each Party represents it is legally authorized to enter this agreement.
- Each Party represents the Pre-existing IP identified in the companion carveout document is owned or lawfully licensed by it, and its contribution to the team does not infringe any third party's rights.
- Each Party represents it has no present commitments to a competing TA1 team.

## 9. Confidentiality

- Non-public technical material shared between the Parties in support of this proposal (including DAVA source, SCBE internal specs, unpublished bootstraps) is confidential.
- Confidential material may not be disclosed to third parties except as required by the DARPA submission process, or by law, without the owning Party's written consent.
- Confidentiality survives termination of this agreement for five (5) years.

## 10. Term & termination

- Effective on the latest signature date below.
- Terminates on the earlier of: (a) a final "not selected" notification from DARPA on the Phase I abstract or full proposal, (b) execution of the DARPA Phase I contract (at which point this teaming agreement is superseded by a formal subcontract), or (c) 30 days after written notice of termination by either Party.
- Sections 6 (IP), 9 (Confidentiality), and any accrued financial obligations survive termination.

## 11. Governing law

Washington State.

## 12. Entire agreement

This document, together with the IP Carveout referenced in Section 6, is the entire agreement of the Parties with respect to the MATHBAC TA1 teaming. Amendments require writing signed by both Parties.

---

## Signatures

**Issac D. Davis**, sole proprietor

Signature: _______________________________________  Date: __________________


**Collin Hoag**, President, Hoags Inc.

Signature: _______________________________________  Date: __________________
