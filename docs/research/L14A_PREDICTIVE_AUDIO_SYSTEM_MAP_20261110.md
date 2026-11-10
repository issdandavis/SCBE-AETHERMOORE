# Layer-14A predictive audio probe system map

Status: preregistered local experiment; no model or tokenizer promotion.

```text
three private teacher WAV files
  -> fixed 0.5 s RMS windows (16 kHz mono PCM)
  -> bounded Layer-14A SpectralObservation records
  -> causal PredictiveSensoryTritRouter state through time t
  -> 12-value typed feature packet
  -> equal-parameter 12 -> 3 linear probe
  -> next-window direction target at t+1
  -> held-video evaluator + matched controls
  -> immutable horse checkpoint/ledger/result
  -> separately implemented inference replay
```

## Reused authorities

| Node | Path | Role and status |
|---|---|---|
| typed L09/L14 observation | `src/symphonic_cipher/scbe_aethermoore/layer_contracts.py` | distinguishes observed, measured silence, missing, and too-short input |
| predictive dual-trit router | `src/symphonic_cipher/scbe_aethermoore/ai_brain/predictive_sensory_trits.py` | causal prediction, residual, adaptation, omission, precision, and route score |
| source manifest | `C:/dev/clay-training-runs/teacher-loop-videos-20261109/dataset/teacher_video_corpus.json` | three private teacher-video sources; SHA-256 `4d88f440dd0ef1a4faba6ba8d6d0449326789bbe32be4d1b2c3d633df442f053` |
| audio files | `C:/dev/clay-training-runs/teacher-loop-videos-20261109/audio/*.wav` | mono 16-bit PCM at 16 kHz; automatic transcripts are not targets |

## New bounded nodes

| Node | Input / output | Invariant |
|---|---|---|
| audio packet builder | one source waveform -> `[rows, 12]` float32 | row t uses observations only through t; target uses t+1 |
| probe campaign | 3 held-source folds x 8 arms x 5 seeds | every arm has exactly 39 trainable parameters |
| resumable horse | two alternating checkpoint slots plus hash-checked latest pointer | completed horses are immutable and skipped |
| evaluator | per-example prediction ledger and aggregate cross entropy / balanced accuracy | one source is absent from training in every fold |

## Arms and downstream risks

- `predictive_trits`: declared candidate.
- `raw_lags`: tests whether ordinary current/previous/delta values explain the result.
- `raw_current`: tests whether temporal state is unnecessary.
- `no_adaptation`: removes adaptation while retaining expectation state.
- `no_omission`: removes omission semantics.
- `shuffled_binding`: one-to-one row permutation preserves feature marginals while breaking time binding.
- `random_features`: equal-width deterministic random packet.
- `zero_features`: no-input baseline.

No Clay parent checkpoint is loaded. Existing weights, tokenizer tables, E187-E198 artifacts, and prime-token catalog are read-only. A positive probe result would establish only source-disjoint predictive-audio sidecar information; it would not authorize Layer-13 integration, model merge, partial unfreeze, or catalog scoring.

## Build gate

- Capability: test whether typed prediction/adaptation/omission state predicts the next audio-energy direction beyond ordinary lags and matched controls.
- New downstream problem: the target is future-derived, so the implementation must prove that features at t cannot depend on samples after t.
- Success: candidate clears every arm in every held source by the preregistered uncertainty and paired-prediction gates.
- Compute: local GTX 1660 Ti, less than 0.25 GiB expected VRAM, less than 0.25 GiB artifacts, and a 25 GiB launch / 5 GiB runtime disk gate.
- Save root: `C:/dev/clay-training-runs/l14a-predictive-audio-20261110/full-v1`; rollback is selecting no probe.
- Stop: non-finite features/loss, source overlap, hash drift, future-perturbation failure, checkpoint mismatch, disk-gate failure, or any control-gate failure.

Pre-build inventory: `C:/dev/clay-training-runs/l14a-predictive-audio-20261110/PREBUILD_SYSTEM_INVENTORY.json`, SHA-256 `780773030c78fe3526ac43002eb2e99effbbe363ada9cce3bd4842b7e156a4ff`.

