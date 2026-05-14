# SCBE Multi-Abacus Architecture

**Status:** v0 — first abacus (`governanceAbacus`) shipped 2026-05-13. Remaining
abacuses parked under "Roadmap" below until a concrete consumer asks for one.

**One-line idea:** an *abacus* is a deterministic, BigInt-only mechanical
implementation of a closed mathematical surface inside SCBE. Same inputs map
to the same beads on the same rods, on every platform, forever — no float
drift, no platform-dependent rounding, no NaN class.

The word "abacus" is the contract:

- inputs quantize to integer **bead positions on rods**;
- every step is an integer add / subtract / multiply / divide;
- the same arithmetic operations a human could perform on a Roman counting
  board, an Egyptian counting board, a Chinese suanpan, a Japanese soroban,
  or a Russian schoty;
- the output rod can be read back as either an exact rational
  (`num/den`) or a fixed-precision decimal string.

This is intentionally narrow. Abacuses are **not** general numerical kernels.
They are the small set of scoring / decision surfaces where SCBE governance
needs cross-platform bit-identity for audit, replay, and dispute resolution.

## Why a "multi-abacus" pattern instead of one big one

A single monolithic BigInt computation kernel would couple every governance
surface into one rod layout. That is the wrong shape for SCBE, because
different surfaces have different inputs, different ranges, and different
threshold contracts. The historical precedent is exactly this — counting
boards specialized by trade:

| Historical abacus    | Shape it was optimized for                          | SCBE analogue                                           |
| -------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| Roman counting board | base-10 with `V`/`L`/`D` half-bead shortcuts        | tier-threshold abacuses (few discrete decision bands)   |
| Egyptian rope/board  | unit-fraction decomposition                         | phi-weighted tongue scoring (Σ wᵢ·xᵢ in exact rationals)|
| Chinese suanpan      | 2/5 beads — natural for hex/decimal both            | composite scoring with mixed-base bead lifts            |
| Japanese soroban     | 1/4 beads — minimum-bead representation             | minimal-state per-event abacus (one rod per dimension)  |
| Russian schoty       | inclined wires, 10 beads/rod, 4-bead delimiter      | breathing-state rolling-window abacus                   |

Each SCBE abacus picks the historical layout whose bead semantics most
closely match the math it is asked to mechanize. Calling them all "the SCBE
abacus" would lose this. Calling them all separate, with one contract
(BigInt, no float, exact rational or fixed-decimal output) keeps the
audit story clean.

## Shipped: `governanceAbacus`

- **File:** `src/harmonic/governanceAbacus.ts`
- **Public API:** `scbe-aethermoore/harmonic` → `runGovernanceAbacus`, `formatAbacusBoard`, `TIER_THRESHOLDS`
- **CLI:** `scbe abacus run --d-h <v> --pd <v> [--json]`
- **Layout:** Roman-style discrete-threshold board — four rods (`d_h`,
  `phase_dev`, `denominator`, `score`), each quantized at `scale = 1e6`.
- **Formula:** `H(d_h, pd) = 1 / (1 + d_h + 2·pd)` (canonical L12, matches
  `harmonicScale` in `src/harmonic/harmonicScaling.ts`).
- **Tier rod (L13):**
  - `H ≥ 0.65` → ALLOW
  - `H ≥ 0.45` → QUARANTINE
  - `H ≥ 0.25` → ESCALATE
  - `H <  0.25` → DENY
- **Balanced-ternary collapse:** `+1` ALLOW, `0` QUARANTINE/ESCALATE, `-1` DENY.
- **Parity:** smoke at `scripts/harmonic/abacus_smoke.cjs` confirms 7/7
  sample inputs match `harmonicScale` within `1e-6`, tier-identical.
- **Phi-free.** Phi-weighted tongue scoring is a *separate* abacus (see
  Roadmap). Mixing the two was the bug we cleaned up before this first ship.

## Roadmap (parked — implement on demand only)

These are sketches, not commitments. Each one ships only when a real consumer
inside the repo asks for cross-platform bit-identity for that surface.

### `tongueWeightAbacus` (Egyptian unit-fraction layout)

- **Purpose:** mechanical Σᵢ wᵢ·xᵢ over the six Sacred Tongues with phi-scaled
  weights `KO=1, AV=φ, RU=φ², CA=φ³, UM=φ⁴, DR=φ⁵`.
- **Why Egyptian:** phi can only be approximated; the cleanest exact-rational
  representation is a convergent of the continued fraction (Fibonacci
  ratios). The Egyptian layout — sums of distinct unit fractions — is the
  natural mental model for "phi as a sum of bead shortcuts".
- **Inputs:** six per-tongue activations `xᵢ ∈ ℝ⁺`, plus the phi convergent
  to use (default `(F_{n+1}/F_n)` for some `n` — e.g. `(89/55)` gives 4-decimal
  parity with float phi).
- **Output:** exact rational composite score + bead board with one rod per
  tongue + a "phi register" rod.

### `breathingAbacus` (schoty rolling-window layout)

- **Purpose:** mechanize the L6 breathing transform — rolling-window
  modulation of a scalar series.
- **Why schoty:** schoty has a fixed bead delimiter (4-bead group) that
  naturally encodes a window edge. The window slides; old beads roll off
  one end while new ones roll on the other.
- **Inputs:** input series, window length, decay coefficient (rational).
- **Output:** windowed bead state + scalar output rod.

### `triadicAbacus` (three-board soroban layout)

- **Purpose:** mechanize the L11 triadic temporal distance — three accumulators
  at different time horizons (immediate, medium, long).
- **Why soroban:** soroban's minimum-bead representation is ideal when you
  need three independent registers that all feed one final decision rod.
- **Inputs:** intent samples + three horizon lengths.
- **Output:** three accumulator rods + composite triadic distance rod.

### `composeAbacus` (suanpan composite layout)

- **Purpose:** composition rule — given outputs from multiple per-layer
  abacuses, produce the pipeline-level decision under the L1/L14 composition
  axiom.
- **Why suanpan:** the 2/5 layout naturally encodes both binary (gate
  pass/fail) and decimal (numeric score) on the same rod, which matches the
  shape of "score + tier" outputs from upstream abacuses.

## Contract that every abacus must obey

A module is only an "abacus" in this architecture if it satisfies all of:

1. **Pure functions only.** No I/O, no global mutation, no `Date.now`.
2. **BigInt or fixed-int only.** No `Number` arithmetic on hot paths.
   `Number` is allowed only for quantizing user-facing inputs and for
   rendering output strings.
3. **Exact rational output available.** Even when a fixed-decimal display is
   the primary surface, the API must also expose `{ num: bigint, den: bigint }`
   so consumers can audit without rounding loss.
4. **Configurable scale.** A `scale: bigint` parameter (default conservative,
   e.g. `1_000_000n`) controls quantization resolution. Same scale on every
   platform ⇒ bit-identical bead positions.
5. **Bead board renderer.** A `formatAbacusBoard(run): string` companion
   prints the rod state in a fixed human-readable format. Useful for audit
   logs and disputes ("here is exactly the bead layout the system computed
   when it denied your event").
6. **Cross-language parity test.** Once a TypeScript abacus exists, a
   matching Python smoke must verify the same inputs yield the same beads.
   (Python `decimal.Decimal` at the same scale is the reference.)
7. **No phi unless the abacus is the phi abacus.** Each abacus mechanizes
   exactly one surface. Cross-surface arithmetic happens in `composeAbacus`,
   not inside per-layer abacuses.

## What this gives the project

- **Auditability.** A denied event can be replayed mechanically: rebuild the
  bead board from the inputs, read back the same tier. No "the model
  produced 0.4499999 vs 0.4500001 on different hardware" disputes.
- **Reproducibility claim.** "Bit-identical L12+L13 scoring across Node,
  Python, browsers, and CI runners" is now a concrete property you can
  link to from sales and proposal copy, backed by a 70-line file and a
  passing smoke.
- **A clean wedge.** Each abacus is small, isolated, and shippable on its
  own. The roadmap is "park until a consumer asks," not "build them all."

## See also

- `src/harmonic/governanceAbacus.ts` — first implementation.
- `src/harmonic/harmonicScaling.ts` — the canonical float `harmonicScale`
  this abacus tracks bit-for-bit.
- `src/harmonic/balancedTernary.ts` — the tri-state primitive used for the
  `trit` collapse.
- `scripts/harmonic/abacus_smoke.cjs` — parity check.
