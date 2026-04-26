# Bijective Two-Tongue GCD Evidence

Date: 2026-04-25

Status: local end-to-end coding-system evidence.

Experiment: `experiments/bijective_2tongue_build/run.py`

## Claim

One operation can be represented in two tongue-bound coding surfaces while preserving both transport identity and semantic execution.

Operation:

- Euclid GCD over `gcd(462, 1071)`

Surfaces:

- KO / Python
- RU / Rust

## Local Result

```text
== Bijective round-trip ==
  KO (Python): 137 tokens, first="nav'oa", round_trip_ok=True
  RU (Rust)  : 177 tokens, first="krak'um", round_trip_ok=True

== Cross-tongue (re-key the same bytes through a second tongue) ==
  Python source re-encoded as RU and decoded: identical=True

== Semantic bijection (run both, expect equal output) ==
  Python output: 21
  Rust output  : 21

ALL GREEN: bijection holds at bytes, cross-tongue, and semantic layers (gcd=21).
```

## What It Proves

- Byte-to-token transport is lossless for KO/Python and RU/Rust.
- The same source bytes can be re-keyed through a second tongue and reconstructed identically.
- The Python and Rust implementations produce the same semantic result.
- This is a concrete substrate for the juggling scheduler: one operation, multiple language/tongue forms, separate sub-agent lanes, shared receipt check.

## What It Does Not Prove Yet

- It does not prove all language pairs work.
- It does not prove the model can generate the pair after training.
- It does not prove scheduler behavior until dispatch, watch, receipt, and merge are tested with separate agents.

## Next Eval

Require a trained coding model to:

1. Produce KO/Python GCD.
2. Produce RU/Rust GCD.
3. Preserve byte-bijective transport.
4. Execute both forms or provide exact run commands.
5. State that both outputs must equal `21`.
