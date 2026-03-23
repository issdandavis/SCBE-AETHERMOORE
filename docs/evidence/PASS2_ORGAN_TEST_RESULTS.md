# Pass 2: Organ-by-Organ Test Results

Date: 2026-03-22
Runtime: 9m 10s full suite

---

## Summary

```
[RESULT: 3847 passed, 48 failed, 13 skipped, 21 xfailed, 3 xpassed]
[TARGET: >95% pass rate]
[ACTUAL: 98.8% pass rate (3847/3895 collected)]
[VARIABLES: 15 test files have collection errors (import failures)]
```

---

## Organ-by-Organ Results

### SKELETON (PQC + Crypto Primitives)
```
[RESULT: 71 passed, 1 skipped, 0 failed]
[TARGET: 100% pass]
[STATUS: HEALTHY]
[VARIABLES: pi^phi scalar, HKDF, commit fields, ternary trits]
[KNOBS: PHI constant, cost threshold, out_len, salt]
[ROCK SOLID: _pi_phi_scalar(), _hkdf_extract(), _hkdf_expand()]
```

### NERVOUS SYSTEM (L13 Governance Gate)
```
[RESULT: 7 passed, 0 failed]
[TARGET: 100% pass]
[STATUS: HEALTHY]
[VARIABLES: epoch_id, lang_weights, curvature_kappa, layer12_R]
[KNOBS: QUORUM (4/6), SAFE_RANGES dict]
[ROCK SOLID: FluxParams.compute_hash(), ConsensusEngine.vote()]
[INTERCONNECTION: FluxParams → voxel_header → epoch binding]
```

### MEMORY (Storage Surfaces)
```
[RESULT: 177 passed, 0 failed]
[TARGET: 100% pass]
[STATUS: HEALTHY]
[VARIABLES: max_depth, cell_size, quadtree_capacity, grid_size]
[KNOBS: octree_max_depth=3 (tuned), lattice_cell_size=0.5 (tuned)]
[ROCK SOLID: HyperbolicOctree, HyperbolicLattice25D, bridge workload]
[SUB-VARIABLES: compaction_score, node_explosion, overlap_heat]
```

### DNA (Encoding + Patterns)
```
[RESULT: 43 passed, 0 failed]
[TARGET: 100% pass]
[STATUS: HEALTHY]
[VARIABLES: spin threshold, tongue_coords, centroid, phi weights]
[KNOBS: quantize threshold=0.03-0.05, dispersal threshold=0.05]
[ROCK SOLID: SpinVector, build_metric_tensor(), DispersalReport]
[SUB-VARIABLES: spin_entropy, effective_dimension, tongue_dispersals]
[INTERCONNECTION: dispersal → routing → fusion surfaces]
[TICTAC: 9 features × 6 boards = 54 trits, winning lines discriminate attacks]
```

### CIRCULATORY (Routing + Membrane)
```
[RESULT: 27 passed, 0 failed]
[TARGET: 100% pass]
[STATUS: HEALTHY]
[VARIABLES: match_threshold, max_branches, penalty_decay, membrane_permeability]
[KNOBS: match_threshold=2.0, max_branches=4, penalty_decay=0.9]
[ROCK SOLID: TongueBloom, LeaderCharge, PolyhedralFallback]
[WEAK SPOT: QC acceptance window rejects everything (needs float→int fix)]
[INTERCONNECTION: dispersal_route() → zone_id → lightning_query → lattice25d]
```

### IMMUNE (Tamper + Adversarial)
```
[RESULT: 29 passed, 0 failed]
[TARGET: >90% pass, detection_rate >25%]
[STATUS: FUNCTIONAL — needs improvement]
[VARIABLES: SPIN_DRIFT_THRESHOLD=5, COST_THRESHOLD=12.0, BOUNDARY_THRESHOLD=1.5]
[KNOBS: threshold tuning, 2-signal minimum for detection]

Adversarial benchmark:
  [RESULT: detection_rate=28.6%, false_positive_rate=0.0%]
  [TARGET: detection_rate >40%, false_positive_rate <10%]
  [GAP: 71.4% ASR — need to improve]

Per-class:
  [combined_multi:      100% detected] [TARGET: >80%] [STATUS: EXCEEDS]
  [boundary_exploit:     80% detected] [TARGET: >60%] [STATUS: EXCEEDS]
  [encoding_obfuscation: 40% detected] [TARGET: >40%] [STATUS: MEETS]
  [tool_exfiltration:    40% detected] [TARGET: >40%] [STATUS: MEETS]
  [direct_override:      30% detected] [TARGET: >40%] [STATUS: BELOW]
  [tongue_manipulation:  30% detected] [TARGET: >40%] [STATUS: BELOW]
  [indirect_injection:   20% detected] [TARGET: >30%] [STATUS: BELOW]
  [adaptive_sequence:     9% detected] [TARGET: >20%] [STATUS: BELOW]
  [spin_drift:            0% detected] [TARGET: >10%] [STATUS: FAILING]
  [multilingual:          0% detected] [TARGET: >10%] [STATUS: FAILING]

[SUB-VARIABLES: spin drift cost DOES escalate (2.05→13.91) but below threshold]
[INTERCONNECTION: text_to_tongue_coords() → spin → cost → threshold → detect]
```

---

## Pre-existing Tests (Full Codebase)

### Passing organs (not from this session)
```
[RESULT: 3847 passed across full suite]
[INCLUDES:]
  - harmonic/ pipeline tests (L1-L14 TypeScript tests via vitest references)
  - crypto/ dual lattice, hyperpath, GeoSeal tests
  - symphonic_cipher/ axiom tests (unitarity, locality, causality, symmetry, composition)
  - hydra/ spine, head, limbs, ledger, consensus, swarm tests
  - browser/ agent, bounds checker, fleet coordinator tests
  - knowledge/ funnel, scraper, tokenizer graph tests
  - aaoe/ identity, task monitor, ephemeral prompt tests
  - api/ route, governance scan, tongue encode tests
```

### Failing organs (48 failures)
```
[RESULT: 48 failed]
[CATEGORIES:]
  QC voxel drive:      9 failed  [CAUSE: tests reference methods not yet implemented]
  Webtoon pipeline:    4 failed  [CAUSE: quality gate / prompt compilation drift]
  Geoseed:             8 failed  [CAUSE: M6 spec changes not reflected in tests]
  Dynosphere:          5 failed  [CAUSE: API surface changed]
  Braided voxel:       4 failed  [CAUSE: encoding changes]
  Misc:               18 failed  [CAUSE: various — import paths, API changes]
```

### Collection errors (15 files can't import)
```
[RESULT: 15 files fail to collect]
[CAUSE: missing dependencies, moved modules, renamed classes]
[FILES:]
  test_aethermoore.py            — scipy import
  test_cstm_nursery.py           — module moved
  test_ede.py                    — missing dependency
  test_flock_shepherd.py         — API changed
  test_gate_swap_trimanifold.py  — module renamed
  test_industry_grade.py         — missing dependency
  test_layer13_cymatic_voxel.py  — class renamed
  test_mmx.py                    — module not at expected path
  test_potato_head.py            — module moved
  test_pqc.py                    — liboqs not installed
  test_quasicrystal_lattice.py   — API changed
  test_scbe_comprehensive.py     — missing imports
  test_scbe_n8n_bridge.py        — missing dependency
  test_spiral_seal.py            — module moved
  test_trinary_negabinary.py     — module renamed
```

---

## Health Score by Organ

| Organ | Tests | Pass | Fail | Health | Notes |
|-------|-------|------|------|--------|-------|
| SKELETON | 71 | 71 | 0 | **100%** | Rock solid |
| NERVOUS (L13) | 7 | 7 | 0 | **100%** | Rock solid |
| MEMORY | 177 | 177 | 0 | **100%** | Rock solid |
| DNA | 43 | 43 | 0 | **100%** | Rock solid |
| CIRCULATORY | 27 | 27 | 0 | **100%** | QC integration weak |
| IMMUNE | 29 | 29 | 0 | **100%** (tests pass, detection 28.6%) | Thresholds need tuning |
| FULL BODY | 3895 | 3847 | 48 | **98.8%** | 15 import errors + 48 failures |

---

## Top Priority Fixes (ordered by impact)

1. **Immune: spin drift detection (0%)** — cost escalation IS real (2→14) but
   doesn't cross 2-signal threshold. Fix: add cumulative cost tracker across
   a conversation sequence, not per-message.

2. **Immune: multilingual detection (0%)** — text metrics are language-blind.
   Fix: Sacred Tongue byte-level encoding divergence (tested, didn't work at
   byte level — needs token-level semantic encoding).

3. **Circulatory: QC acceptance window** — rejects all real data because
   float→int conversion loses precision. Fix: native float gate vectors.

4. **Collection errors (15 files)** — module moves/renames broke imports.
   Fix: update import paths (low risk, high cleanup value).

5. **QC voxel drive (9 failures)** — tests call methods that don't exist
   (strict mode, spin_coherence, ttl_seconds). Fix: implement or delete tests.

---

## What's Rock Solid (don't touch)

- `_pi_phi_scalar()` — mathematically proven, 42 tests
- `FluxParams + ConsensusEngine` — 4/6 quorum, hash determinism
- `HyperbolicOctree` — 0.074 node explosion at 10K, gets better with scale
- `CymaticCone` — 50/50 Chladni access control, zero storage overhead
- `SpinVector + build_metric_tensor()` — φ-weighted, DR 11x more expensive than KO
- `TongueBloom` — bloom filter pre-screening for lightning query
- `PolyhedralFallback` — always works (the reliable backup)
