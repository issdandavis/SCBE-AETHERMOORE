# Binary Lambda Calculus Time-Placement Lane

## Purpose

Binary and hex are still the ground transport views:

- binary exposes bit positions, masks, flags, parity, carry, endianness, and error-correction structure;
- hex compresses the same byte substrate into readable nibbles for dumps, hashes, packets, and opcodes.

Binary Lambda Calculus adds a third lane: computation grammar over time. It does not replace binary or hex. It annotates how spans of bits act as binders, branches, and references inside a lambda term.

## Source Basis

John Tromp's Binary Lambda Calculus encodes lambda terms in de Bruijn notation:

- abstraction: `00`;
- application: `01`;
- variable index `n`: `1` repeated `n` times followed by `0`.

This matches the "time placement" gap in the SCBE coding system: the same bit substrate can be read as bytes, nibbles, or executable structure depending on grammar position.

## Integration Rule

Use this lane only for bounded transport, tests, and training records:

- keep binary/hex as byte-level evidence;
- keep BLC as structural computation evidence;
- require round-trip decode before using a BLC record as training material;
- do not treat BLC output as a security signature or cryptographic primitive.

## Repo Surfaces

- Implementation: `src/crypto/binary_lambda.py`
- Tests: `tests/crypto/test_binary_lambda.py`
- SFT builder: `scripts/build_blc_time_placement_sft.py`
- SFT output: `training-data/sft/blc_time_placement_v1.sft.jsonl`
- Manifest: `training-data/sft/blc_time_placement_v1_manifest.json`

## Example

Identity function:

```text
de Bruijn: (lambda 1)
BLC bits: 0010
placement: 00 = binder, 10 = nearest reference
```

Application of identity to identity:

```text
de Bruijn: ((lambda 1) (lambda 1))
BLC bits: 0100100010
byte-padded binary: 01001000 10000000
hex: 48.80
```

The padded binary and hex are transport views. The BLC placement map is the computation view.
