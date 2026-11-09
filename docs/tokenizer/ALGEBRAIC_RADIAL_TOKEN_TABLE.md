# Algebraic Radial Token Table

Status: mechanics prototype only. It makes no model-quality, comprehension, or speed claim.

## Construction

The table exists before text enters it. For `N` cells, `S` sectors, and even dimension `D`, cell `i` has sector `s`, local ordinal `n`, radius

`r_i = sqrt((n + 1/2) / (N/S))`

and phase

`theta_i = golden_angle * (n + 1) + 2*pi*s/S + theta_seed (mod 2*pi)`.

For harmonic pair `p = 0..D/2-1`, its coordinates are

`x_i[2p:2p+2] = r_i/(p+1) * [cos((p+1)theta_i), sin((p+1)theta_i)]`.

That is the algebraic table: one compact seed and formula reconstruct every cell. Tokens do not name or place the cells.

### The zero-dimensional origin

The compact `seed` is the useful 0-dimensional object here: one scalar with no spatial axes. The construction lifts that scalar into a phase and then into `D` coordinates. A scalar zero is therefore allowed as an origin, but it is not confused with relation evidence. Downstream relations separately record:

- trit `-1`, `0`, or `+1` when measured;
- `POSITIVE_LIMIT` or `NEGATIVE_LIMIT` when a measured value approaches zero from a signed side;
- `NEUTRAL` for a measured balanced zero;
- `ABSENT` or `UNMEASURED` when no numeric zero is justified.

## Stable hyperspace movement

Each sector receives a bounded angle `a_s = atan(lambda_s)`. The same chain of Givens rotations is applied to every cell in that sector. Since each Givens matrix is orthogonal,

`||R_s x_i|| = ||x_i||`

and, for cells in the same sector,

`||R_s x_i - R_s x_j|| = ||x_i - x_j||`.

This is the concrete version of pulling a vector to an extreme parameter while keeping its stable internal ratios: even enormous finite `lambda_s` values approach a finite quarter-turn rather than overflowing.

## Weight-based token occupancy

A canonical token identity is hashed into a bounded numeric carrier. Explicit typed weights can be added before normalization. A token occupies the cell with the largest alignment

`A(t,c) = <unit(hash(t) + gain*w_t), x_c>`.

Ties are retained in the receipt. Surface spelling does not derive the geometry. Canonical byte/span identity from `prime_token_catalog.py` can be used as `canonical_id`; atomic, speech, source, or other measured views can be supplied as explicit weights without pretending those deterministic views are independent observations.

## Sector relay sieve

For source `i`, target `j`, and depth `d`, the measured radial relation is

`g_ij^d(lambda) = q_ij * exp(-beta ||x_i(lambda)-x_j(lambda)||^2) * cos((d+1)(theta_j-theta_i))`.

The sign and strength are stored separately:

- `tau_ij = sign_epsilon(g_ij) in {-1,0,+1}`
- `m_ij = |g_ij|`

Two bounded sieves run per source and depth:

- the top `k_local` measured relations inside the source sector preserve the stable internal structure;
- the top `k_portal` measured relations outside the source sector become cross-sector portal relays.

Their combined magnitudes are normalized. Sector rotations leave local distances and local phase differences invariant, while changing cross-sector distances and phases. Movement can therefore re-rank portal relays without destroying the sector's internal table.

`ABSENT`, `UNMEASURED`, and measured neutral zero are different states. A measured zero may additionally carry `NEUTRAL`, `POSITIVE_LIMIT`, or `NEGATIVE_LIMIT` metadata. Missing evidence never silently becomes a zero-valued observation.

## Required experiment controls

Before this mechanism can be called useful, it must beat both the no-intervention baseline and a size-matched control over multiple seeds. The preregistered comparison should include:

1. identity/no-movement table;
2. fixed lexical or byte baseline;
3. size-matched random radial geometry;
4. shuffled token-to-weight binding;
5. equal-width non-radial projection;
6. family/view ablations;
7. source-disjoint and sector/direction-disjoint holdouts.

Stop on non-finite values, unreproducible receipts, source leakage, unrecorded ties, missingness collapse, or a result smaller than twice the pooled standard deviation.

## Hardware mapping

The mechanics are chosen to fit ordinary hardware rather than require a new optical device:

- cell coordinates and token carriers are fixed-width contiguous vectors;
- Givens movement is a sequence of fused multiply-add rotations;
- relation signs fit signed two-bit/trit metadata while magnitudes remain separately quantized;
- local and portal neighbors form CSR/COO-style sparse edge lists;
- each `(sector, depth)` flash can be dispatched as an independent CPU SIMD, GPU warp/block, or accelerator tile;
- canonical receipts and tie lists remain on the control plane, not in the hot multiply path.

The current Python implementation prioritizes exactness and auditability. A later kernel may pack trits and quantize magnitudes only after parity tests prove it reproduces the reference outputs. Alignment to 32/64-wide hardware is an implementation optimization, not a mathematical claim that every attention head owns a physical 64-bit lane.
