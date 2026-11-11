# Prime-token material runtime boundary — 2026-11-11

Status: `RUNTIME_MECHANICS_TESTED_MATERIAL_DATA_NOT_IMPORTED`

## What changed

`python/scbe/prime_token_material_runtime.py` is the concrete runtime factory
for the already preregistered frozen-input horse race. It reuses the recovered
14-layer `FullSystemLM` checkpoint and source rather than introducing another
parent loader. Both files are hash checked before import or deserialization.

The factory accepts only a hash-bound runtime configuration and a prepared case
manifest containing the exact `train`, `validation`, `final_test`, `ordinary`,
and `retention` lanes. It rejects record-ID or source-family overlap across the
three learning/evidence splits. Every train row becomes a bounded
`PrimeTrainingExample`; every held row is retained separately for the producer
evaluator and independent replay.

The evaluator receipt is a real JSON artifact, not a free-form hash. It exactly
binds the allowed output vocabulary, relationship classes, function classes,
and the rule `full-vocabulary-argmax_then_exact_and_class_equivalence`.
Relationship and function scores therefore cannot be redefined after results
exist.

## Measures beyond accuracy

Each held output reports:

- exact token accuracy;
- relationship-class agreement;
- function-class agreement;
- bounded-output probability margin;
- bounded-output entropy.

The run also reports ordinary-input false activation, frozen-parent retention,
throughput, peak memory, and checkpoint bytes. The runner now adds a direct
reader-connectivity receipt containing the effective feature-to-hidden matrix
norm, mean absolute strength, spectral norm, stable rank, nonzero fraction, and
one connection norm for each of the six catalog views. These diagnostics show
whether the reader was used and where its capacity concentrated; they do not
authorize promotion by themselves.

## Baseline correction

The checkpoint-free `no_intervention` replay previously reconstructed and
passed a prime packet through the wrapper. That was not a valid unchanged-parent
baseline because processor-owned positions can change even when no adapter
checkpoint exists. Producer evaluation and independent replay now explicitly
omit the packet for `no_intervention`. Every replay case records
`prime_packet_used`, and evidence aggregation rejects a baseline that used one
or a learned arm that did not.

## Authority boundary

This runtime module has no command-line launch path and is imported only after
the existing runner clears both the machine release audit and the separately
hash-bound human authorization. It does not grant training, unfreezing,
promotion, serving, merge, or tool-dispatch authority. No material record or
model weight was loaded while implementing or testing it.

## Verification

```text
python -m pytest tests/tokenizer/test_prime_token_input_access.py \
  tests/tokenizer/test_prime_token_training_release.py \
  tests/tokenizer/test_algebraic_radial_token_table.py \
  tests/tokenizer/test_prime_token_input_access_evidence.py \
  tests/tokenizer/test_prime_token_material_runtime.py -q
```

Result: `37 passed` on Python 3.12.10, plus Black, Ruff, and Flake8 for the new
runtime and tests. This is implementation evidence only.
