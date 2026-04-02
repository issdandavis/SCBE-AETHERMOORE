# Wave Layer Fiber Optics Training Plan

Status: CONCRETE REPO PLAN
Date: April 1, 2026

---

## Decision

The audio layer should be generalized into a broader wave layer.

The higher-order formalization for that move now lives in:

- [UNIVERSAL_PROPAGATION_GRAMMAR.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/UNIVERSAL_PROPAGATION_GRAMMAR.md)

Music and fiber optics are not being treated as the same domain. They are being treated as two domains that expose the same underlying primitives:

- frequency / wavelength
- amplitude / power
- phase
- interference
- coherence / resonance

Fiber optics adds domain-specific structures that the music analogy does not cover directly:

- polarization
- chromatic dispersion
- polarization-mode dispersion
- Kerr nonlinearity
- spatial / modal structure

That means the implementation move is not "teach the model music so it learns optics." The move is "teach the model wave-native representations, then specialize them into domains."

---

## Repo Artifacts Added

- [fiber_optics_multiview_schema.json](C:/Users/issda/SCBE-AETHERMOORE/training-data/schemas/fiber_optics_multiview_schema.json)
- [training-data/fiber_optics/README.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/README.md)
- [fiber_optics_sft_prompt_taxonomy.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/fiber_optics_sft_prompt_taxonomy.md)
- [fiber_optics_qwen_adapter_runbook.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/fiber_optics_qwen_adapter_runbook.md)

These are the concrete starting pieces for a specialist adapter on the existing Qwen/Colab lane.

---

## Training Packet Design

The multiview packet for fiber optics should be:

- `L0`: raw traces or sampled signal summaries
- `L1`: transformed wave features
- `L2`: channel / impairment diagnosis
- `L3`: human explanation and fix

Examples of `L0`:

- OTDR-like traces
- spectra
- BER or Q-factor logs
- link-budget tables

Examples of `L1`:

- attenuation
- chromatic dispersion coefficient
- PMD estimate
- nonlinear phase shift
- phase and FFT summaries
- polarization state

Examples of `L2`:

- chromatic dispersion
- PMD
- attenuation loss
- Kerr nonlinearity
- splice / connector loss

Examples of `L3`:

- explanation of what failed
- recommended first remediation
- uncertainty notes
- escalation guidance when evidence is mixed

---

## Immediate Execution Order

1. Build `100-300` seed records using the new schema.
2. Use the first 100 prompt types in [fiber_optics_sft_prompt_taxonomy.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/fiber_optics_sft_prompt_taxonomy.md) as the corpus skeleton.
3. Fork [finetune_qwen_governance.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/finetune_qwen_governance.ipynb) rather than inventing a new training lane.
4. Train a narrow LoRA adapter on `Qwen/Qwen2.5-0.5B-Instruct`.
5. Hold out `20-30` records for impairment-class separation and remediation quality.
6. Only after SFT stabilizes, add DPO-style correction data from a deterministic optics checker or simulator.

---

## Why This Fits SCBE

This plan matches the repo's existing direction instead of fighting it:

- it uses multiview training rather than prose-only instruction tuning
- it stays adapter-first rather than mutating the general model
- it reuses the current Qwen/Colab fine-tune path
- it naturally extends the wave/harmonic theory into a second measured domain

The right near-term target is a fiber specialist route that can diagnose the canonical impairments from structured multiview packets. If that works, the broader wave layer becomes an implementation surface instead of just a theory note.
