# Persistent operand-context private CPU release packet

This directory stages the reviewed successor from prototype commit
d864f35d085a148a8e6f3171fd1ad9f0888b6bf4 and repair commit
57519aa385b22330d249da724b52b265216c96e9. It has not been saved,
uploaded, or run on Kaggle. EXECUTION_ADMISSION.json is NOT_CONSUMED and
deliberately has execution_authorized=false; the default runner path therefore
fails before capacity checks, dataset access, or model loading.

The packet retains the proven cap-then-grow experiment: seeds 20261134,
20261135, and 20261136; 18,000 updates; Adam at 0.002; batch 128; checkpoints
every 500 updates; frozen embedding, recurrent core, and counting head. The
candidate, explicit context-permuted control, and target-shuffle control each
train exactly 142,164 parameters from bit-identical initialization. A
parameter-matched zero-update arm is evaluated and saved as well.

The repaired explicit context source is used during both teacher forcing and
every autoregressive held-out step. The release adds a separate replay program
that independently rebuilds arithmetic rows and the context derangement,
reloads all 12 saved models, replays every held-out prediction and counting
score, and verifies hashes. The final decision still requires the original
three-seed/two-pooled-SD/3-of-3 gates, nonzero operation and out-of-support
checks, exact retention/frozen identity, plus a 4,096-draw paired bootstrap
whose one-sided 95% lower bounds are strictly positive. Promotion is always
NONE.

Local evidence is mechanics-only: Python compilation and Ruff passed; 16 tests
passed; the bounded synthetic smoke passed without loading a parent; and the
default execution path failed closed. Local model replay remains blocked by
1.18 GB free RAM against the unchanged 3 GiB gate, and no models were
downloaded.

Read-only Kaggle inspection showed CLI 2.2.5, current access to the existing
private input, 21.43 GPU hours and 19.99 TPU hours remaining. This packet is
CPU-only, so planned accelerator consumption is zero. The earlier in-Kaggle
preflight found /tmp above the unchanged 25 GiB floor; that observation is not
treated as fresh for a future launch. The runner remeasures the same floor
before extraction or parent loading.

The actual future upload surface is the clean packet/ directory. A later
authorized launcher must update the admission, rebuild and verify the manifest,
record the provider version, and consume the admission locally. Ordinary
kaggle kernels push is not part of this preparation.
