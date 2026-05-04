# GeoShell Paired-Agent Adapter HOLD - 2026-05-04

## Decision

Status: HOLD.

The GeoShell paired-agent adapter is not promotion-ready. The retry training run passed the inline constrained gate, but the independent adapter smoke regressed from 2/4 to 1/4. Promotion must be based on the independent smoke gate, not only the training job's inline gate.

## Evidence

### Training Retry

- Training job: `69f8a0fc9d85bec4d76f2198`
- Job URL: `https://huggingface.co/jobs/issdandavis/69f8a0fc9d85bec4d76f2198`
- Train rows used: `210`
- Eval rows used: `28`
- Global step: `120`
- Training loss: `0.9348946556448936`
- Inline gate: `4/4`
- Adapter push: `true`

Dataset uploads:

- Train commit: `95df7a8405db4f9f9fb412a875cd739a218c9b76`
- Holdout commit: `ae1c88b67eadbe8e5c9a4f585ed34c0c7c536222`

### Independent Smoke Comparison

| Case | First smoke `69f89eb798a8d679adfb8ef5` | Retry smoke `69f8a39798a8d679adfb8f09` | Direction | Shared failure mode |
| --- | --- | --- | --- | --- |
| `builder_navigator_packet` | FAIL: missing `verification` | FAIL: missing `verification`, `tests` | Worse | Emits role-ish packet text, but does not preserve verification/test contract. |
| `ca_abs_add_pair_route` | PASS | FAIL: missing `Builder`, `Navigator`, `0x00`, `deterministic` | Regressed | Loses exact role/fact scaffolding under free generation. |
| `geoshell_event_shape` | PASS | PASS | Stable | Basic event row shape appears learned. |
| `tokenizer_alignment_packet` | FAIL: missing later tongue markers and forbidden `secret` | FAIL: forbidden `secret` only | Partly improved but still blocked | Full Sacred Tongues names improved, but credential-like field language remains unsafe. |

Final independent smoke result after retry: `1/4`.

## Diagnosis

More supervised fine-tuning rows improved the constrained training gate while making free generation worse on packet shape. The model appears to be learning local schema fragments and prompt-adjacent words, but not the full promotion contract.

The biggest gap is not data volume. It is output discipline:

- The inline gate uses a forced `required-items:` scaffold, which makes compliance easier than natural free generation.
- Builder/Navigator examples are still not strong enough to force exact role casing plus verification/test fields.
- `secret_query` style negatives need to be represented as rejected behavior, not merely absent from positive examples.
- The adapter needs either a constrained response template, a deterministic postprocessor, or preference training with the actual bad smoke outputs as rejected samples.

## Next Training Move

Do not add broad positive rows blindly.

Recommended next iteration:

1. Freeze the current smoke canaries unchanged.
2. Build a failure-pack dataset from the two independent smoke jobs.
3. Add contrastive records:
   - chosen: concise valid packet with exact required markers.
   - rejected: actual bad generations that omit `verification`, omit `tests`, lowercase role names, omit `0x00`, omit `deterministic`, or include `secret_query`.
4. Train with a preference objective if available, or convert the pairs into strict repair SFT rows.
5. Re-run the independent adapter smoke and require `4/4` before promotion.

## Promotion Gate

Promotion condition:

- Inline training gate: `4/4`
- Independent adapter smoke: `4/4`
- No forbidden credential-like markers in any canary response
- Stable pass on retry with the same canary set

Until those are true, the adapter remains HOLD.
