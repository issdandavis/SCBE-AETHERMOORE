# Tongue braid + residual null-space note

Status: reproducible engineering result, 2026-08-20. Not peer reviewed.

## Question

Can the six Sacred Tongues provide an integrity check whose failure modes differ from the exact six-axis residual already used by the system?

## Construction

The tongues are ordered `KO, AV, RU, CA, UM, DR` at 60-degree steps. For an opcode displacement vector, the linear residual is evaluated in exact Eisenstein-integer coordinates. With `z = zeta_6`, antipodal axes obey

`z^(j+3) = -z^j`.

Equal non-zero displacements on an antipodal pair therefore cancel in the residual. The tongue cage is different machinery: each tongue is a bijective road that independently parses its rendered opcode and objects when it disagrees with the claim.

## Exhaustive residual result

The committed `tongue_braids.py --selftest` enumerates every non-zero one- and two-tongue displacement over all 64 opcodes.

| Corruption family | Cases | Detected | Uniquely localized | Invisible |
|---|---:|---:|---:|---:|
| One tongue | 378 | 100.00% | 1.59% | 0 |
| Two tongues | 59,535 | 99.68% | 0.02% | 189 |

All 189 invisible cases are the three antipodal pairs shifted together by the same non-zero amount:

- `KO <-> CA`
- `AV <-> UM`
- `RU <-> DR`

The count is exact: three pairs times 63 possible non-zero equal shifts equals 189.

For a single-tongue residual, 186 signatures occur in ambiguous pairs and six are singletons. The six singletons are the `+32` half-turn, one per tongue, because `+32` is its own opposite modulo 64.

## Joined cage check

The same self-test sends a `+7` equal displacement through each of the three residual-blind pairs. The braid cage returns `ABSTAIN` and names both corrupted tongues in all three probes:

- `AV + UM -> tongue_AV, tongue_UM`
- `KO + CA -> tongue_CA, tongue_KO`
- `RU + DR -> tongue_DR, tongue_RU`

This establishes complementary failure structure: the linear residual has an exactly characterized null direction, while the independently parsed tongue roads reject representative points on every named blind pair.

## Claim boundary

- The residual enumeration is exhaustive for the configured 64-opcode, six-tongue, one- and two-corruption model.
- The joined cage check currently covers one representative non-zero shift per antipodal pair. It is not yet an exhaustive 189-case cage measurement.
- This is an integrity and fault-localization result. It is not evidence about the Riemann Hypothesis or an unrestricted error-correcting guarantee.

## Reproduction

Run from the `loom` repository at commit `c9b7a8e`:

```text
python tongue_braids.py --selftest
```

Expected terminal line: `SELFTEST: PASS`.
