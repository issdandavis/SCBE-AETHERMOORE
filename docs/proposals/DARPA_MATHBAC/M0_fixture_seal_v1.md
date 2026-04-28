# MATHBAC M0 Fixture Seal — v1

**Solicitation:** DARPA-PA-26-05 (MATHBAC)
**Abstract reference:** DARPA-PA-26-05-MATHBAC-PA-010 (submitted 2026-04-27 05:02 ET)
**Sealed:** 2026-04-27
**Authority:** Issac D. Davis (sole performer, sole prop UEI J4NXHM6N5F59)

## Purpose

This file records the cryptographic seal for the CDPTI-Internal fixture set referenced in `proposer_metrics_specs_v1.md` §3.3. The seal is the load-bearing artifact that lets a third party (DARPA, the teaming partner, or any future auditor) verify that the fixtures used at evaluation time are bit-identical to the fixtures committed at M0.

If any fixture in this list changes by a single byte, its SHA-256 will change. Any change to a sealed fixture without a matching update to this file is a self-evident audit failure.

## Sealed fixtures

All paths relative to repository root. All fixtures version 1.0.0.

| Fixture | Size (bytes) | SHA-256 |
|---|---:|---|
| `tests/interop/polyglot_vectors/poincare_distance.v1.json` | 805 | `39be23f6f2793d819f66a62a950a1cd1b1989edb0d761a670be67f8e89685258` |
| `tests/interop/polyglot_vectors/mobius_addition.v1.json` | 1058 | `2bcbafcf5ef032184e4289ddbb9fd627c5215d97f87fb6e8704966d61d95fbe9` |
| `tests/interop/polyglot_vectors/exponential_map.v1.json` | 1111 | `8c7f65ffd0cd2623cde0631fe3cf045db0a663dac0235b44c4b6ba45562b8de1` |
| `tests/interop/polyglot_vectors/logarithmic_map.v1.json` | 1141 | `48ef1c19f775f199a86f2bc50082ed844dbdcd2415612d04afe5d466a00b8779` |
| `tests/interop/polyglot_vectors/harmonic_wall.v1.json` | 1122 | `2b780eefeb1b204c281326f7b68a95b14173b94e86ee689ac61f3cc5f3a7d54a` |

## Verification

To re-derive these seals locally:

```bash
cd <repo-root>
python -c "
import hashlib
from pathlib import Path
for fx in [
    'poincare_distance.v1.json',
    'mobius_addition.v1.json',
    'exponential_map.v1.json',
    'logarithmic_map.v1.json',
    'harmonic_wall.v1.json',
]:
    p = Path('tests/interop/polyglot_vectors') / fx
    raw = p.read_bytes()
    print(f'{fx}\t{len(raw)}\t{hashlib.sha256(raw).hexdigest()}')
"
```

The output must match the table above byte-for-byte. Any mismatch is a fail-closed condition: CDPTI-Internal cannot be evaluated against an unsealed or rebuilt fixture set.

## Coverage at M0

| Layer | Operation | Cases | Tested? |
|---|---|---:|---|
| L4 | Exponential map `exp_p(v)` | 5 | ✓ |
| L4 (inv) | Logarithmic map `log_p(q)` (round-trip cross-validated) | 5 | ✓ |
| L5 | Hyperbolic distance `d_H` | 5 | ✓ |
| L7 | Möbius addition `u ⊕ v` | 5 | ✓ |
| L12 | Harmonic wall `H(d, pd) = 1/(1+φ·d_H+2·pd)` | 5 | ✓ |
| **Total** | | **25** | |

Layers L1–L3, L6, L8–L11, L13–L14 are not yet sealed at M0; they expand across Phase I (M1–M3) per the §3.3 fixture-set growth plan.

## Runners (committed and CI-exercised)

- **TypeScript (vitest):** `tests/cross-language/polyglot-hyperbolic-ops.test.ts` and `tests/cross-language/polyglot-poincare-vectors.test.ts`. Tolerance `toBeCloseTo(_, 12)`. All 24 fixture-driven assertions PASS as of 2026-04-27.
- **Python (pytest):** `tests/interop/test_polyglot_hyperbolic_ops.py` and `tests/interop/test_polyglot_poincare_vectors.py`. Tolerance `pytest.approx(_, abs=1e-12)`. All 7 fixture-driven assertions PASS as of 2026-04-27.

## Amendment policy

Adding a new fixture to the M0 set or relaxing the 12-decimal threshold for an existing case requires a numbered amendment to this file (`M0_fixture_seal_v1.md` → `_v2.md`, `_v3.md`, ...) with rationale. The amendment must cite the offending fixture and the specific reason the threshold cannot hold. Removing a fixture without an amendment is a falsifier-event for CDPTI-Internal.

## Provenance

Generated 2026-04-27 by reading each fixture file as raw bytes (no JSON re-serialization) and computing SHA-256 with Python 3 stdlib `hashlib`. The seal does not depend on JSON formatter, line-ending convention, or trailing-whitespace handling — bit-for-bit equivalence is the criterion.
