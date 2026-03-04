# Claims Map — All Patent Families

This file maps every claim family to its source document, filing status, and next action.

---

## FILED (Protected by Priority Date)

### Family A — Lean Provisional (Jan 11, 2026)
- **Docket**: SCBE-2026-001-LEAN-PROV
- **Claims**: 5 (3 independent + 2 dependent)
- **Stack**: 13-layer (pre-L14)
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part A
- **Known issues**: Physics metaphor language ("event horizon", "gravitational dilation")
- **Formula**: H(d,R) = R^(1+d^2) — OLD formula, superseded by Part B

### Family B — Expanded Provisional (Jan 15, 2026)
- **Docket**: USPTO #63/961,403
- **Claims**: 16 (2 independent + 14 dependent)
- **Stack**: 14-layer
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part B
- **Formula**: H(d,R) = R^(d*^2) — CURRENT formula
- **Status**: FILED but Missing Parts (PTO/SB/15A + $82 needed by April 19)
- **Anchors**: B-1 (method, 9 steps), B-2 (system, 10 modules)

---

## DRAFT — Covered by Jan 15, 2026 Priority Date

### Family C — Attorney-Ready Expansion
- **Claims**: 21 (11 independent + 10 dependent)
- **Source**: `PATENT_DETAILED_DESCRIPTION.md` (repo root)
- **Docket entry**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part C
- **Next action**: Include in non-provisional filing (by Jan 15, 2027)
- **Strongest claims**: C-1 (Hyperbolic Governance Pipeline), C-3 (Harmonic Wall), C-5 (Dual-Lattice PQC)

---

## DRAFT — New Matter (Need New Filing)

### Family D — CIP Amendments (Claims 51-73)
- **Claims**: 23 (8 independent + 15 dependent)
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part D
- **Split**:
  - Claims 51-62: Physics-free rewrites (some covered by Jan 15 date, some new)
  - Claims 63-73: Temporal Intent Trajectory (ALL new matter)
- **Next action**: Include in CIP filing
- **Cost**: ~$400 as part of CIP

### Family E1 — Quasicrystal Lattice Auth (P5)
- **Claims**: 11 (1 independent + 10 dependent)
- **Source**: `docs/patent/PATENT_5_QUASICRYSTAL_AUTH.md`
- **Examiner assessment**: STRONG PASS on 101/102/103
- **Implementation**: `src/symphonic_cipher/pqc/quasicrystal_auth.py`
- **Next action**: CIP or new provisional ($82)
- **Value**: High — zero prior art for quasicrystal in auth

### Family E2 — GeoSeal Dual-Lane KEM
- **Claims**: 5 (1 independent + 4 dependent)
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part E-2
- **Next action**: Include in CIP

### Family E3 — Conlang Acoustic Auth
- **Claims**: 8 (2 independent + 6 dependent)
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part E-3
- **Next action**: Separate provisional ($82)
- **Implementation**: Partial

### Family E4 — Grammar Auth
- **Claims**: 3 (1 independent + 2 dependent)
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part E-4
- **Next action**: Include in E5 filing or separate
- **Implementation**: Partial

### Family E5 — Intent-Modulated Command Auth
- **Claims**: 26 (3 independent + 23 dependent)
- **Source**: `docs/patent/UNIFIED_CLAIMS_DOCKET.md` Part E-5
- **Structure**: Method (1-10) + System (11-18) + CRM (19-26)
- **Next action**: Separate provisional ($82)
- **Implementation**: Partial

### Family P6 — Harmonic Cryptography
- **Claims**: 25 (5 independent + 20 dependent)
- **Source**: `docs/patent/PATENT_6_HARMONIC_CRYPTOGRAPHY.md`
- **Implementation**: `src/crypto/harmonic_crypto.py` (validated)
- **Tests**: `tests/test_harmonic_crypto.py`
- **Estimated value**: $300K-$800K standalone
- **4 inventions**:
  1. Harmonic Ring Rotation Cipher (Claims 1-5)
  2. Circle of Fifths Spiral Key Generator (Claims 6-10)
  3. Voice Leading State Transition Optimizer (Claims 11-15)
  4. Counterpoint Multi-Agent Coordination (Claims 16-20)
  5. Integrated System (Claims 21-25)
- **Next action**: File as standalone provisional ($82) — HIGHEST VALUE new filing

---

## SUPERSEDED (Do Not File)

### Family F — Spiralverse Legacy
- **Claims**: 7
- **Source**: `docs/specs/patent/MASTER_PATENT_DOCUMENT.md`
- **Status**: UNFILED, no priority date, uses old tongue names
- **Action**: Reference only — evolved into Families B-D

---

## Filing Priority (When Budget Allows)

| Priority | Family | Cost | Why |
|----------|--------|------|-----|
| 1 | Fix Missing Parts (B) | $82 | Saves Jan 15 priority date |
| 2 | P6 Harmonic Crypto | $82 | Highest standalone value |
| 3 | E1 Quasicrystal (P5) | $82 | Zero prior art, strongest claims |
| 4 | Non-provisional (B+C) | ~$400 | Converts provisional to real patent |
| 5 | E3+E5 Conlang/Intent | $82+$82 | Additional coverage |
| 6 | CIP (D+E2+other) | ~$400 | New matter under existing app |
