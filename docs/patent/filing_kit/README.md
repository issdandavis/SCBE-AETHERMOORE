# Patent Filing Kit — SCBE-AETHERMOORE

**Inventor**: Issac Davis
**Primary Application**: USPTO #63/961,403
**Priority Date**: January 15, 2026

---

## Kit Structure

```
filing_kit/
├── README.md                    ← YOU ARE HERE
├── 01-urgent/                   ← DO THIS FIRST ($82 + 2 forms)
│   ├── FILING_WALKTHROUGH.md    ← Step-by-step USPTO walkthrough
│   ├── PTO_SB_15A_MICRO_ENTITY_CERT.md  ← Micro entity form (fill + sign)
│   └── PTO_SB_16_COVER_SHEET.md         ← Cover sheet form (fill + sign)
├── 02-claims/                   ← All claim families, organized
│   ├── CLAIMS_MAP.md            ← Master map: what's filed, what's drafted
│   ├── filed_A_lean_provisional.md      ← 5 claims (FILED Jan 11)
│   ├── filed_B_expanded_provisional.md  ← 16 claims (FILED Jan 15)
│   ├── draft_C_attorney_ready.md        ← 21 claims (ready for non-provisional)
│   ├── draft_D_cip_amendments.md        ← 23 claims (physics-free rewrites)
│   ├── draft_E1_quasicrystal.md         ← 11 claims (new matter)
│   ├── draft_E2_geoseal.md              ← 5 claims (new matter)
│   ├── draft_E3_conlang_acoustic.md     ← 8 claims (new matter)
│   ├── draft_E4_grammar_auth.md         ← 3 claims (new matter)
│   ├── draft_E5_intent_modulated.md     ← 26 claims (new matter)
│   └── draft_P6_harmonic_crypto.md      ← 25 claims (new matter, $300-800K value)
├── 03-technical/                ← Supporting specifications
│   └── (symlinked from docs/patent/ and repo root)
├── 04-evidence/                 ← Test results, implementation proof
│   └── (generated from test runs)
└── 05-prior-art/                ← Prior art analysis
    └── (symlinked from docs/patent/)
```

---

## Deadlines

| # | Deadline | Action | Cost | Status |
|---|----------|--------|------|--------|
| 1 | **April 19, 2026** | File Missing Parts (PTO/SB/15A + fee) | **$82** | PENDING |
| 2 | Jan 15, 2027 | File non-provisional or lose priority date | ~$400 | FUTURE |
| 3 | Ongoing | File new provisionals for new matter | $82 each | OPTIONAL |

---

## Filing Priority Order

### IMMEDIATE (when you have $82)
1. Open `01-urgent/FILING_WALKTHROUGH.md`
2. Download + fill PTO/SB/15A from `01-urgent/PTO_SB_15A_MICRO_ENTITY_CERT.md`
3. Download + fill PTO/SB/16 from `01-urgent/PTO_SB_16_COVER_SHEET.md`
4. Go to patentcenter.uspto.gov → upload → pay $82
5. Save receipt

### NEXT 3 MONTHS (free — just prep work)
1. Review `02-claims/CLAIMS_MAP.md` — understand what you have
2. Decide: CIP vs. multiple provisionals (see strategy section below)
3. Run test suites and save output to `04-evidence/`
4. Optionally: get attorney review ($2-5K) for the non-provisional

### BY DECEMBER 2026
1. Finalize non-provisional application
2. Include Parts B + C claims (37 claims covered by Jan 15 priority date)
3. File before January 15, 2027

---

## Claim Inventory Summary

| Family | Claims | Status | Priority Date | New Matter? |
|--------|--------|--------|---------------|-------------|
| A (Lean Provisional) | 5 | FILED | Jan 11, 2026 | No |
| B (Expanded Provisional) | 16 | FILED | Jan 15, 2026 | No |
| C (Attorney-Ready) | 21 | DRAFT | Covered by Jan 15 | No |
| D (CIP Amendments) | 23 | DRAFT | Mixed | Partial |
| E1 (Quasicrystal) | 11 | DRAFT | None | YES |
| E2 (GeoSeal) | 5 | DRAFT | None | YES |
| E3 (Conlang Acoustic) | 8 | DRAFT | None | YES |
| E4 (Grammar Auth) | 3 | DRAFT | None | YES |
| E5 (Intent-Modulated) | 26 | DRAFT | None | YES |
| P6 (Harmonic Crypto) | 25 | DRAFT | None | YES |
| **TOTAL** | **~143** | | | |

**Filed**: 21 claims
**Draft (covered by existing priority)**: 21 claims
**Draft (new matter, needs new filing)**: ~101 claims

---

## Filing Strategy Options

### Option A: Minimum Viable (Recommended for budget)
1. Fix missing parts → $82
2. File non-provisional with B+C claims (37 claims) → ~$400
3. File P6 Harmonic Crypto as separate provisional → $82
4. **Total: $564** to protect your strongest IP

### Option B: Maximum Coverage
1. Fix missing parts → $82
2. File CIP with D+E1+E2 claims → ~$400
3. File P6 separately → $82
4. File E3 (Conlang) separately → $82
5. File E5 (Intent-Modulated) separately → $82
6. Non-provisional for original claims → ~$400
7. **Total: ~$1,128**

### Option C: Conservative
1. Fix missing parts → $82
2. Non-provisional with B+C only → ~$400
3. Everything else waits for budget
4. **Total: $482**

---

## Source Documents (DO NOT EDIT — reference only)

| Document | Location | Role |
|----------|----------|------|
| UNIFIED_CLAIMS_DOCKET.md | docs/patent/ | Master source of truth |
| PATENT_ACTION_PLAN.md | docs/patent/ | Strategy + code fixes |
| CIP_TECHNICAL_SPECIFICATION.md | docs/patent/ | CIP tech spec |
| CLAIMS_INVENTORY.md | docs/patent/ | Full CIP claim inventory |
| PRIOR_ART_ANALYSIS.md | docs/patent/ | 7-domain prior art risk |
| PATENT_DETAILED_DESCRIPTION.md | repo root | Attorney-ready claims source |
| PATENT_6_HARMONIC_CRYPTOGRAPHY.md | docs/patent/ | P6 claims (25) |
| PATENT_5_QUASICRYSTAL_AUTH.md | docs/patent/ | P5 claims (11) |

---

## Product Idea: Patent Readiness Automation

> "Charge $5, save people $400 in attorney prep fees"

The filing kit structure above is productizable:
- Auto-fill PTO/SB/15A from user profile
- Auto-fill PTO/SB/16 from application data
- Deadline tracking with reminders
- Claim organization + family mapping
- Evidence collection from test suites
- Step-by-step walkthrough generation

This maps directly to the Patent Intelligence Pipeline (Phase 2: Submission Helper).
See: `docs/patent/` notes on USPTO APIs + `memory/MEMORY.md` Patent Intelligence section.
