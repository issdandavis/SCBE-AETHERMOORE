# Pre-registration protocols (frozen eval artifacts)

These documents **must be completed and frozen before any held-out data is generated or analyzed**. They exist to prevent post-hoc metric selection, threshold tuning, and example reselection.

| Protocol | Purpose | Status |
|----------|---------|--------|
| [PRE_REGISTRATION_GOVERNANCE_HELD_OUT_EVAL_v1.md](./PRE_REGISTRATION_GOVERNANCE_HELD_OUT_EVAL_v1.md) | SCBE gate false-allow / false-block eval on an independent adversarial set | **DRAFT — fill `[FREEZE: …]` then set FROZEN** |
| [PRE_REGISTRATION_TESLA_REYNOLDS_VALIDATION_v1.md](./PRE_REGISTRATION_TESLA_REYNOLDS_VALIDATION_v1.md) | Reynolds-matched bench + validated CFD for pore diodicity | **DRAFT — fill `[FREEZE: …]` then set FROZEN** |

## Workflow

1. Fill every `[FREEZE: …]` field; commit the protocol with status `DRAFT`.
2. Generate or seal the held-out set / geometry package; record hashes in §2.
3. Change status to `FROZEN`; record `protocol_sha256` and date in the freeze block.
4. Run implementation and analysis **once** against the frozen protocol.
5. Any change to metrics, thresholds, categories, or geometry → **new protocol version** and **new sealed artifact** (new held-out set or new coupon geometry).

## Related (non-binding background)

- Tesla bench/CFD background: `docs/research/tesla_valve_reynolds_bench_cfd_test_plan_2026-06-01.md`
- Kill/pivot table (patent desk): `docs/legal/patent-workbench/CLAIM_FLOOD_LOOKUP_DIRECTIONAL_KINETIC_RECTIFIER_2026-06-01.md`
- Software gate: `src/harmonic/` (14-layer pipeline, geodesic decisions)
