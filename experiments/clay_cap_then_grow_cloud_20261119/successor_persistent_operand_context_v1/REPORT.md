# Persistent operand-context successor

## Outcome of the completed run

The private offline CPU run completed, but its preregistered learning gates did
not pass. The recovered result is bound by SHA-256
`b48bb48859bcd7ac9cfc1f717f3f121ea18427bb5c4f1a048b504c24da2b1b79`.
The provider exposed exactly nine files totaling 18,181,194 bytes. Only the
three JSON receipts have been recovered so far; local model replay remains
deferred by the unchanged 3 GiB available-RAM gate.

Both correctly paired and target-shuffled arms reached very low checkpoint
loss, but held-out exact accuracy remained around 1-2%. The candidate lost two
of three matched seeds to the shuffled-label control. Its mean exact-accuracy
advantage was 0.000663, far below the required two-pooled-SD threshold of
0.007076.

The operation split identifies the failure mechanism:

- subtraction held-out results remain in the training result range 0-29 and
  reached 3.44-5.59% exact accuracy;
- addition held-out results are 60-118, outside the training support 0-58, and
  were zero on two seeds;
- multiplication held-out results are 169-576, outside the training support
  0-144, and were zero on every seed.

This is target-support memorization, not arithmetic extrapolation. Exact
counting retention passed, so catastrophic forgetting is not the explanation.

## Smallest mechanism change

The successor does not add more downstream width or retune the optimizer. It
adds one `Linear(6, 192)` projection, 1,344 parameters, that supplies the exact
five-byte record plus decode position to the action carrier at every generated
digit:

```text
context = [opcode/2, x_hi/255, x_lo/255, y_hi/255, y_lo/255, step/7]
carrier_t = frozen_hidden_t + GELU(context_projection(context))
```

The embedding, recurrent core, and counting head remain frozen. The existing
adapter and action head remain trainable. Total trainable parameters are exactly
142,164 for every trained arm.

The new `context_permuted_control` uses the identical architecture and parameter
count but deranges contexts within operation and output-length strata. The
original target-shuffle and zero-update controls remain. The same three seeds,
18,000 updates, optimizer, loss, batching, held-out rows, two-pooled-SD rule,
3-of-3 matched-seed rule, nonzero-per-operation rule, exact retention rule, and
independent replay rule remain in force. The finite-evaluation gate additionally
requires a strictly positive one-sided 95% paired-bootstrap lower bound for
both exact accuracy and operation-stratified macro accuracy.

The experiment is falsified if the candidate fails any gate. No execution or
promotion is authorized by these files.

## Bounded implementation evidence

`run_persistent_operand_context.py` now implements the six-scalar persistent
context, deterministic stratified context derangement, context-aware teacher
forcing, autoregressive reuse at every decode step, exact trainable-module
selection, and frozen-core action loss. Its SHA-256 is
`6693166b30d09ea8f14aa511c2a0e50f19d35aa7e5d08f03731c0960362ba2d4`.

The runner CLI is deliberately smoke-only. It cannot start a cloud campaign.
The smoke loaded no parent or recovered model. It verified all six deterministic
context assignments, a bit-identical matched initialization, a finite synthetic
update, unchanged synthetic frozen tensors, the 1,344/142,164 parameter
accounting, and the three result-support invariants. Its receipt SHA-256 is
`742493e34af62a73727f2d1104df17725da4a341e5beb0fe3463fc091bfc90ee`.

Focused verification: six Pytest tests passed, Ruff passed, Python AST parsing
passed, and `git diff --check` passed. Exact replay of the recovered terminal
models remains deferred by the unchanged 3 GiB available-RAM gate.

An independent review found and repaired a prototype-only evaluation defect:
generation formerly derived the context from the prompt row unconditionally,
which made held-out evaluation of the context-permuted arm impossible. The
evaluation surface now accepts and receipts an explicit independent context
row. The same review added the paired finite-evaluation bootstrap required by
the Clay evidence standard; neither change authorizes a campaign launch.
