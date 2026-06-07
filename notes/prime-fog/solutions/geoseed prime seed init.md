---
tags: [prime-fog, geoseed, m6, constructor, density-floor]
updated_at: 2026-06-05
---

# GeoSeed Prime Seed Init

Status: constructive handoff from prime-fog closure into GeoSeed/M6.

This implements the "scaled prime seed" as an initializer, not a predictor:

```text
smooth address tower -> guaranteed bracket -> primorial wheel lanes
```

Code:

```text
src/geoseed/prime_seed_init.py
```

Docs:

```text
docs/research/geoseed_prime_anchor_seed_init.md
```

## Contract

For a prime index `n`, the seed returns:

- smooth address estimate for `p_n`
- proven candidate window bounds by default (`mode="proven"`)
- explicit `coverage_contract`
- wall radius as distance from the smooth center to the selected window edge
- candidate window bounds
- M6 shell mapping from `KO..DR` to mod layers `2,3,5,7,11,13`
- final primorial modulus `30030`
- allowed residue lane count `phi(30030)=5760`

The output is the deterministic candidate field. It never claims to choose the
prime inside that field.

Default contract:

```text
mode="proven" -> p_n is guaranteed inside [lower_bound, upper_bound]
```

The proof contract uses unconditional Dusart / Rosser-Schoenfeld prime-index
bounds. It does not assume RH.

Legacy narrow mode:

```text
mode="tight" -> sigma*sqrt(x)/log(x) scale window, not guaranteed
```

Example at `n=10000`:

| Mode | Window | Width | Wheel candidates | Contract |
| --- | ---: | ---: | ---: | --- |
| proven | `[104306, 114307]` | 10001 | ~1918 | guaranteed |
| tight | `[103944, 104840]` | 896 | ~172 | not guaranteed |

## Why This Is Allowed

The second-lane search is closed. This does not reopen it.

This is the constructive face of the same result:

```text
frozen/density floor -> guaranteed field initializer
```

Any future claim that this seed selects primes must pass a new null gate first.
