# SCBE-AETHERMOORE — Founding-Docs Flight Manual

**Purpose:** Issac's doctrine — *"anytime we have a problem with our system, review the docs from the founding: find our axioms, our layer guides, our notes, and our extension map, and make sure the ship keeps flying."* This is that map, made addressable. When something looks broken/refuted/stuck, come here first, jump to the governing founding doc, and check design intent before accepting a surface verdict.

**Built:** 2026-07-11 from a full inventory of 30 founding docs across both checkouts (`aws-lambda-simple-web-app-active` = patent workshop; `SCBE-AETHERMOORE` = current founding spine) + the filed provisional in OneDrive + the session's reduction-to-practice code.

**How to use:** (1) Anchors below = the single sources of truth — when docs disagree, these win. (2) The Map = every founding doc by doctrine category. (3) Reduction-to-practice ledger = what's *proven* vs *asserted* (honesty firewall). (4) Dents-to-fix = the live worklist to keep the ship flying.

---

## 0. CANONICAL ANCHORS (true north — these win over any single doc)

| Anchor | Canonical value | Authority |
|--------|-----------------|-----------|
| **Core axiom (never changes)** | Poincaré distance `d_H(u,v) = arccosh(1 + 2‖u−v‖² / ((1−‖u‖²)(1−‖v‖²)))` — all dynamics transform *points*, never the metric | `axiom_grouped/SPECIFICATION.md`, `LAYER_INDEX.md` L5 |
| **Layer-12 harmonic score (CURRENT)** | **Bounded** `H_score(d*,pd) = 1/(1 + d* + 2·pd)` ∈ (0,1], scale 1e6 | `docs/LAYER_INDEX.md`, `ABACUS_ARCHITECTURE.md` (bit-identical in `governanceAbacus.ts`) |
| **Layer-12 (DEPRECATED — do not cite)** | `H = R^(d²)` / `R^((φ·d*)²)` "exponential wall" | Refuted: adversarial-cost bench measured it **linear**, not exponential ([[adversarial-cost-benchmark]]) |
| **Decision tiers (L13)** | ALLOW ≥ .65 · QUARANTINE ≥ .45 · ESCALATE ≥ .25 · DENY < .25 | `ABACUS_ARCHITECTURE.md` |
| **Formula source-of-truth** | `docs/specs/CANONICAL_FORMULA_REGISTRY.md` → `CANONICAL_SYSTEM_STATE.md` → `SCBE_CANONICAL_CONSTANTS.md` | cited as top authority by both LAYER_INDEX copies + full-system map (⚠ not yet inventoried — index next) |
| **Filing** | Provisional **63/961,403** (2026-01-15) → Non-provisional **19/691,526** (2026-05-28), docket **SCBE-2026-0001** | Patent Center; priority date 2026-01-15 carries |
| **Filed title** | "System and Method for Hyperbolic Geometry-Based Authorization with Topological Control-Flow Integrity" | `assemble_patent_spec_docx.py` TITLE const |

---

## 1. AXIOMS & MATH CORE

| Doc | Essence | Status |
|-----|---------|--------|
| `aws-lambda…/SCBE_MATH_SPEC.md` | Equation-only blueprint to reconstruct the whole engine (φ-weighted metric, harmonic wall, spin/coherence, decimal drift, claim-map eqs→claims 1-18) | intact (uses older `R^(1+d²)` form) |
| `aws-lambda…/symphonic_cipher/scbe_aethermoore/axiom_grouped/SPECIFICATION.md` | The 14-layer stack under 5 quantum axioms (Unitarity/Locality/Causality/Symmetry/Composition); Poincaré invariant | Jan-15 provisional snapshot ⚠ inventor typo "Isaac" |
| `SCBE-AETHERMOORE/docs/specs/LAYER_MATH_COMPRESSED.md` | **Most-evolved** one-block-per-layer math ref; adds Cauchy Core + adaptive-κ; 47D complex manifold | current math (2026-04-13) |
| `SCBE-AETHERMOORE/docs/specs/LAYERED_GEOMETRY_SEMANTIC_PACKING_NOTE_2026-04-25.md` | Design note: tokens = invariant outer hull + rotatable inner geometry; octree harmonic links (routing scaffold, *not* semantics) | note, self-limited |
| `aws-lambda…/scbe_aethermoore/UNIFIED_SPECIFICATION.md` | Paradigm overview: "ethics are the geometry"; alt 5-layer stack, concentric trust rings, time-dilation trapdoor | overview (Kyber/Dilithium still HMAC-simulated) |

## 2. LAYER GUIDES & ARCHITECTURE

| Doc | Essence | Status |
|-----|---------|--------|
| `SCBE-AETHERMOORE/docs/LAYER_INDEX.md` | **Canonical** 14-layer index → math/file/test/axiom per layer; L12 = bounded score | intact (current truth) |
| `SCBE-AETHERMOORE/docs/specs/LAYER_INDEX.md` | Diverged twin — still carries the **deprecated** `R^((φd*)²)` wall | ⚠ stale — reconcile to docs/ copy |
| `SCBE-AETHERMOORE/docs/ABACUS_ARCHITECTURE.md` | BigInt-only "abacus" contract → cross-platform bit-identical scoring; `governanceAbacus.ts` shipped 2026-05-13 | intact (best current-truth anchor with docs/LAYER_INDEX) |
| `SCBE-AETHERMOORE/docs/specs/MASTER_ARCHITECTURE_CONTRACT_21D_M4_SQUAD.md` | Deploy contract: 21D state layout, frozen core vs shadow extensions, 5 promotion gates | intact |
| `SCBE-AETHERMOORE/docs/specs/MECHANICAL_LAYER_TANGENTIAL_TREE.md` | Design note: 3rd "mechanical" layer (compiler/mapmaker); bijective reality matrix | note (explicitly non-scientific) |

## 3. EXTENSION MAP / SYSTEM MAPS

| Doc | Essence | Status |
|-----|---------|--------|
| `SCBE-AETHERMOORE/docs/SCBE_FULL_SYSTEM_MAP.md` | Repo authority chain + code zones + key paths (2026-06-14) | intact (newest map) |
| `SCBE-AETHERMOORE/docs/PLATFORM_MAP.md` | Ecosystem sorted into 6 layers, each tagged Production/Beta/Experimental/Conceptual | intact |
| `SCBE-AETHERMOORE/docs/REPO_SURFACE_MAP.md` | Solo-builder "which lane to open first"; 4 real lanes + quarantine list | 2026-04-21 |
| `SCBE-AETHERMOORE/docs/ops/GEOSEAL_SOURCE_MAP_2026-04-30.md` | Provenance trail for GeoSeal (canonical = 17,774-byte Notion export) | ⚠ Notion copies not hydrated (cloud provider exited) |
| `SCBE-AETHERMOORE/docs/specs/PYRAMID_CONSTELLATION_MANIFOLD_MAP.md` | Experimental: 6-tongue compass → depth/perception pyramid star-lattice in the ball | experimental |
| `SCBE-AETHERMOORE/docs/CANONICAL_SYSTEM_STATE.md` | Declares canonical vs legacy vs experimental; fixes runtime formula + status language | 2026-04-08 (carries canonical L12) |
| `SCBE-AETHERMOORE/docs/PRODUCTIZATION_ROADMAP.md` | Honest extractable-products inventory + 90-day GTM (governance wedge) | grounded 2026-06 |

## 4. CLAIMS — PROVISIONAL DRAFTS (workshop; not the filed non-prov text)

| Doc | Essence | Status |
|-----|---------|--------|
| `aws-lambda…/PATENT_CLAIMS_FINAL.md` | 21 claims around "variable drift δ" graduated access; each mapped to a passing test | pre-filing draft |
| `aws-lambda…/PATENT_CLAIMS_COVERAGE.md` | Claim→code crosswalk, 21/21 @100%; **its Poincaré + Topological-CFI framing matches the filed title** | reduction-to-practice evidence |
| `aws-lambda…/USPTO_PROVISIONAL_SWARM.md` | Revised provisional (v4.1) + swarm claims 22-30 + per-claim skeptical rebuttal | draft |
| `aws-lambda…/symphonic_cipher/scbe_aethermoore/PATENT_SPECIFICATION.md` | Separate "Context-Bound…Fail-to-Noise" invention thread, claims 1-62 | ⚠ different invention thread under same brand |

## 5. CLAIMS — NON-PROVISIONAL (filed 19/691,526) & TLCFI CODE

| Doc | Essence | Status |
|-----|---------|--------|
| `SCBE-AETHERMOORE/scripts/legal/assemble_patent_spec_docx.py` | Assembler that stitches the filed non-prov spec (title exact-match); pulls `PATENT_CLAIMS_EXPANDED_v2.md` + detailed-desc + abstract | ⚠ **its 3 source files do not exist on disk / in git** |
| `SCBE-AETHERMOORE/src/symphonic_cipher/topological_cfi.py` | TLCFI reference impl: CFG → Hamiltonicity (Dirac/Ore) → dimensional lift → principal curve → O(1) deviation | ⚠ latent run bug (see Dents #5) |
| `SCBE-AETHERMOORE/scripts/patent_benchmark.py` | Berkheimer-style §101 evidence bench; names app 19/691,526 / docket SCBE-2026-0001 | intact |
| `aws-lambda…/USPTO_PATENT_APPLICATION.md` | Formal app draft — but titled "Post-Quantum…Security Envelope" (**title diverges from filed**) | superseded precursor |

## 6. CODE EMBODIMENTS (reduction-to-practice)

| Doc | Pillar | Status |
|-----|--------|--------|
| `C:\dev\loom\opcode_router.py` | Pillar-1 hyperbolic authorization — behaviour+Poincaré separates twins from synonyms at **4.5× margin** | ✅ **VERIFIED** (this session) |
| `SCBE-AETHERMOORE/src/symphonic_cipher/topological_cfi.py` | Pillar-2 topological CFI | ⚠ simulated on toy CFGs + run bug |
| `SCBE-AETHERMOORE/docs/ABACUS_ARCHITECTURE.md` → `governanceAbacus.ts` | Bit-identical L12/L13 scoring (audit/replay) | shipped 2026-05-13 |

## 7. FILING PLAYBOOK / PORTFOLIO

| Doc | Essence |
|-----|---------|
| `aws-lambda…/PATENT_FILING_MASTER.md` | Pre-filing consolidation playbook (2026-01-11 "READY TO FILE"); provisional→non-prov→PCT roadmap; source Google-Doc/Notion/PR links |
| `aws-lambda…/SCBE_PATENT_PORTFOLIO.md` | 3-patent family view (hyperbolic gov / topological CFI / dynamic resilience), 62+ claims, moat tables |
| **Filed provisional (ground truth)** | `C:\Users\issda\OneDrive\Downloads\Copy of SCBE-AETHERMOORE USPTO Patent Application - CLEAN.pdf` + source `OneDrive\SCBE_Archives\SCBE-AETHERMOORE-provisional-patent.md` |

---

## REDUCTION-TO-PRACTICE LEDGER (honesty firewall — proven vs asserted)

| Pillar | Claimed | Actual status |
|--------|---------|---------------|
| **P1 — Hyperbolic authorization (PBHG)** | adaptive Poincaré trust gating | ✅ **PROVEN in code** (`opcode_router.py`, behaviour+Poincaré, 4.5× twin/synonym margin) |
| **P2 — Topological CFI (TLCFI)** | "90%+ ROP/JOP detection @ <0.5% overhead vs 70%/10-20%" | ⚠ **simulated on toy CFGs only**; real-binary detector is the open build; module has a run bug |
| **P3 — Lyapunov stability** | "globally asymptotically stable" | ⚠ **proof *sketch* only** — unproven |
| PQC (ML-KEM-768 / ML-DSA-65) | post-quantum binding | ⚠ **HMAC-simulated placeholders** in current code (per UNIFIED status table) |

---

## DENTS TO FIX (the "keep the ship flying" worklist)

1. **Formula drift — pin ONE canonical wall.** `R^(1+d²)` vs `R^(d²)` vs `R^((φd*)²)` vs bounded `1/(1+d*+2pd)` all live in founding docs. Canonical = **bounded**; `R^(d²)` family is **deprecated** (measured linear). Add a one-line "canonical L12 = bounded; R^(d²) retired" banner to each math doc.
2. **Reconcile the LAYER_INDEX twins.** `docs/specs/LAYER_INDEX.md` still teaches the deprecated wall; overwrite it with (or delete in favor of) `docs/LAYER_INDEX.md`.
3. **De-dup SCBE_SYSTEM_OVERVIEW.md** (byte-identical in `docs/` and `docs/specs/`); both still teach the refuted "exponential/vertical wall" — **highest overclaim risk if quoted in a pitch.** Pick one home; add the honesty caveat.
4. **Title divergence.** Formal app drafts are titled "Post-Quantum…Security Envelope"; the *filed* title is "Hyperbolic Geometry-Based Authorization with Topological CFI." The matching framing lives only in the coverage/portfolio docs. Align narrative to the filed title.
5. **`topological_cfi.py` run bug.** `class CFGEdge` has bare annotations (no `@dataclass`/`__init__`) yet `create_sample_cfg()` calls `CFGEdge(src,tgt,etype)` → `TypeError`; `HyperbolicPoint` has a doubled `@dataclass`. Fix before citing it as a runnable embodiment.
6. **Inventor typo:** `axiom_grouped/SPECIFICATION.md` says "Isaac Davis" — should be **ISSAC**.
7. **GeoSeal canonical text at risk:** the 17,774-byte Notion export (the canonical GeoSeal source) failed to hydrate from OneDrive. Pull the Dropbox parallel copy into the repo so it stops living only in the cloud.

---

## THE ONE REAL GAP

The **non-provisional's formal expanded claims** (19/691,526, filed 2026-05-28) exist **only** as Patent Center **PDF submission #76776451** (or the Google Doc). The assembler's three source files (`PATENT_CLAIMS_EXPANDED_v2.md`, `PATENT_DETAILED_DESCRIPTION.md`, `PATENT_ABSTRACT_v1.md`) were never committed and are gone from disk, git history (4 branches + 6 sibling repos checked), and training corpora. To work the *filed* claims, download that PDF.

## NEXT TO INDEX (to complete the manual)
`docs/specs/CANONICAL_FORMULA_REGISTRY.md` · `docs/specs/SCBE_CANONICAL_CONSTANTS.md` · `docs/specs/CANONICAL_SYSTEM_STATE.md` · the GeoSeal Notion export (Dropbox copy).
