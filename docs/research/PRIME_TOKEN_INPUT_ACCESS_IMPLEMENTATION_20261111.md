# Prime-token frozen input-access implementation — 2026-11-11

Status: `MECHANICS_TESTED_MATERIAL_TRAINING_NOT_RELEASED`

This implementation closes the code-mechanics prerequisites in the frozen
prime-token input-access preregistration. It does not close any data, source,
E92, seed, or human-release gate.

## Implemented boundary

- `python/scbe/prime_token_input_access.py` builds sealed, processor-owned
  packets for the canonical six-view candidate and four equal-width controls.
  The views remain correlated descriptions of one occurrence. The wrapper
  replaces owned hidden positions before block 0 and zeros the owned raw and
  route lanes so placeholder bytes cannot leak through another path.
- `python/scbe/prime_token_training.py` trains only the low-rank reader. It
  checks the parent hash after every step and persists adapter, optimizer,
  sampler, Python, NumPy, CPU RNG, and CUDA RNG state in alternating atomic
  checkpoint slots.
- `scripts/tokenizer/run_prime_token_input_access.py` requires both a completely
  passing release audit and a separate, audit-hash-bound human authorization
  before importing a material runtime factory. Each `(arm, seed)` receives a
  dedicated lineage. Tool dispatch, promotion, and partial unfreezing remain
  disabled.
- `python/scbe/prime_token_independent_replay.py` reconstructs packet features
  without calling the producer builder, verifies the checkpoint pointer and
  parent lineage, ignores producer metric aggregates, and recomputes
  per-position predictions.
- `scripts/tokenizer/replay_prime_token_input_access.py` exposes that path for a
  separately supplied held-out runtime and fails when a producer ledger differs
  from replay.

## Tested invariants

The focused implementation suite proves:

1. deterministic packet seals and mutation detection;
2. equal feature width and reader parameter count across learned arms;
3. lexical-only auxiliary zeroing and one-to-one shuffled bindings;
4. independent reconstruction equality for all five learned packet modes;
5. bit-identical delegation when no packet is present;
6. owned placeholder insensitivity and unowned-token sensitivity;
7. no influence from a future owned record on earlier logits in the compatible
   causal test core;
8. reader update with a bit-identical frozen parent;
9. split save/load/next-step equality with uninterrupted training;
10. fail-closed material admission and checkpoint/ledger tamper detection.

Command:

```text
python -m pytest tests/tokenizer/test_prime_token_input_access.py \
  tests/tokenizer/test_prime_token_training_release.py \
  tests/tokenizer/test_algebraic_radial_token_table.py -q
```

Result: `26 passed` on Python 3.12.10 after Black and Ruff. This is mechanics
evidence only. No catalog row was labelled, no source session was opened, no
parent or descendant weight was modified, and no material trainer was started.

## Remaining release blockers

The current release remains `WAITING_FOR_RELEASE_REQUIREMENTS`. In particular,
it still needs the prospective query minimum and closed source sessions, the
source-disjoint assignment and source-family gate, completed E92 plus independent
verification, three declared fresh seeds, and explicit human material release.
Passing those gates would authorize only a reviewed training launch, never
promotion, serving, tool dispatch, or partial unfreezing.
