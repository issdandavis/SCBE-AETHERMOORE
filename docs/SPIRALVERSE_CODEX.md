# Spiralverse Codex

This file now points to the canonical, seed-anchored v1 linguistic sources.

## Canonical Sources

- `docs/specs/SPIRALVERSE_CANONICAL_LINGUISTIC_CODEX_V1.md`
- `docs/specs/spiralverse_canonical_registry.v1.json`

## Canonical Constraints

- Exactly six base tongues: `KO`, `AV`, `RU`, `CA`, `UM`, `DR`
- Frozen harmonic weights and phase angles per tongue
- Kor'aelin 24-letter runic set is canonical
- Kor'aelin 14-particle grammar core is canonical
- Tokenizer invariants: `6 x 256` bijection, deterministic roundtrip, byte-preserving cross-translation

## Implementation Anchor

Runtime alignment is enforced against `six-tongues-cli.py` through tests in:

- `tests/test_spiralverse_canonical_registry.py`

Any future linguistic or protocol additions must preserve v1 base constraints unless a new canonical version is explicitly declared.
