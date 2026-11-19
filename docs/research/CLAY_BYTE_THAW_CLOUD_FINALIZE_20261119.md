# Clay Byte-Embedding Thaw Cloud Finalize — Terminal Negative

Date: 2026-11-19  
Authority: measurement only; no training, execution, merge, promotion, deletion, or local-lineage mutation

## Outcome

The recovery campaign stopped fail-closed. A private Hugging Face CPU Job had
492.689 GiB free, passed the unchanged 25 GiB gate, hash-verified the exact
packet and runner, and reused all nine completed horses without optimizer work.
The exact aggregate completed with `producer_gate = NOT_MET`. The original
hash-bound independent verifier then returned
`FAIL_INDEPENDENT_INFERENCE_REPLAY` with 11 errors, so no atomic success receipt
was promoted or copied into the active local lineage.

This is a substantive negative measurement, not another capacity failure:

- parameter count matched;
- counting and base-parent behavior were preserved;
- thawed byte rows changed;
- none of the three preregistered comparisons cleared both the 2x pooled-SD
  effect gate and the paired finite-uncertainty gate.

The active campaign remains unchanged: root `RESULT.json` is absent, root status
is still `RUNNING`, and all 18 horse files (nine `MODEL.pt`, nine `RESULT.json`)
still match the packet by size and SHA-256.

## Exact private inputs

- Private dataset: `issdandavis/clay-byte-thaw-finalize-20261119`
- Final stage commit: `51ddc086989a234823c24583c4614e84fb438eea`
- Packet: 36,184,119 bytes,
  `5af43e7e138e3c1109fb40689fb2bb3400384610342bae8aebac636266723686`
- Descriptor:
  `471647529905de1afcc84e6f4a89814fe730f9929baf80170bea8df95767b241`
- Recovery runner:
  `359b56fa6776a7f7e171b1f5ee4f674c2d76eb2a2bed4de69c92434b3b23126f`
- Final HF wrapper:
  `b94b2c01084c6437eaec4e2dc629d709a38e0ea88d5f31cb974ce5b66a9d111c`
- Original campaign runner:
  `41ae605fe8a72df2bc24c6a55a43eb30a7a93e324838dd3b731cf1f8b5a4d956`
- Original independent verifier:
  `9b3bc0310e1d011d68a87f2bc3101a9bddc0dd7121822e38809f1f7d24585de8`
- Source commit: `12dde4d50fcbc700bc88bc6706c7473476104691`

Provider readback matched all four staged files. The dataset stayed private.

## Provider jobs

| Job | Purpose | Gate / terminal state |
|---|---|---|
| `6afee0114fdc5ab3c55981a1` | capacity probe | completed; 510.522 GiB free |
| `6afee16f4fdc5ab3c55983be` | import-closure probe | gate passed at 341.187 GiB; stopped before campaign on missing NumPy |
| `6afee20cefaf5e14f4b13052` | corrected import-closure probe | gate passed at 480.356 GiB; stopped before aggregate on missing scikit-learn |
| `6afee34f4fdc5ab3c55986e5` | final bounded finalize/replay | gate passed at 492.689 GiB; aggregate `NOT_MET`; independent replay `FAIL` |

The last job's provider log is 5,577 bytes with SHA-256
`f322513941af74521d2f393b7a22c52371aa8c4c8bb960328e46a42e16c5fca7`.
The Hugging Face Jobs API exposes the `cpu-basic` flavor but no spend amount;
therefore spend is recorded as **not reported**, not as zero.

## Aggregate result

Primary `byte_thaw_multiview` mean accuracy was `0.2106666667`; mean macro-F1
was `0.2106008566`.

| Control | Accuracy delta / 2x pooled SD | Macro-F1 delta / 2x pooled SD | Paired W/L/T, p | Gate |
|---|---:|---:|---:|---|
| frozen adapter multiview | `+0.006222 / 0.045493` | `+0.007404 / 0.047177` | `726/698/3076`, `p=0.474314` | fail |
| byte-thaw shuffled | `+0.005111 / 0.033630` | `+0.005016 / 0.033878` | `729/706/3065`, `p=0.561417` | fail |
| byte-thaw static | `-0.006889 / 0.031963` | `-0.007221 / 0.032174` | `726/757/3017`, `p=0.435976` | fail |

The exact producer aggregate was recomputed locally from the nine immutable
horse JSON receipts only (no inference and no writes) and matched the provider's
`NOT_MET` classification.

## Why the verifier reported 15 models, not nine

There is no enumeration bug. The campaign owns three thaw arms over three seeds:
`3 x 3 = 9` completed horse models. The independent verifier deliberately adds
two imported baseline controls over those same three seeds:
`2 x 3 = 6`. Its expected receipt count is therefore `9 + 6 = 15`.

The replay failure is separate from the producer gate. One of its 11 errors is
deterministically explained from preserved bindings: the baseline replay receipt
is pinned to frozen-replay builder
`4df7bc99505d778217dabece3aaec85fe30ce6b3783b15309a91689f86ed3997`,
while the exact source commit used here contains
`34214da66c2bbcd002a05f22dfcfdde4d963093dfc0d5129f81a7ed844223e5c`.
The verifier therefore emits `baseline independent replay verifier binding is
stale`.

The job used `--summary-only`, and the wrapper correctly stopped before uploading
its ephemeral failed result, so the other ten error strings were not preserved.
This report does not guess their categories. The negative aggregate remains valid
because it was completed before replay and independently reconstructed from the
immutable result records.

## No-training proof

The provider copied the nine completed horse directories first. In the exact
campaign source, `train_arm` checks for `RESULT.json`, verifies `MODEL.pt` against
its recorded hash, and immediately returns before model creation, optimizer
construction, or updates. All nine result files existed. No checkpoint files
were included in the packet, no optimizer update was observed, and the local
horse hashes remain byte-identical.

## Evidence

- Machine receipt:
  `artifacts/research/clay_byte_thaw_hf_finalize_20261119/TERMINAL_NEGATIVE_RECEIPT.json`
- Provider stage/readback:
  `artifacts/research/clay_byte_thaw_hf_finalize_20261119/HF_STAGE_RECEIPT_V3.json`
- Sanitized job receipts and exact provider logs:
  `artifacts/research/clay_byte_thaw_hf_finalize_20261119/terminal/`
- Lightning fail-closed receipt:
  `artifacts/research/clay_byte_thaw_lightning_finalize_20261119/LIGHTNING_RECOVERY_RECEIPT.json`

No further provider retry is authorized for this campaign. The correct next
scientific action is to treat byte-thaw as a negative result under the
preregistered gate, not to mutate the gate or promote the models.
