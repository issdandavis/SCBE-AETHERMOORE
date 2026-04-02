# Fiber Optics Qwen Adapter Runbook

This is the concrete training path for a first fiber-optics specialist adapter on the current SCBE Qwen lane.

## Use This Existing Notebook

Primary base:

- [finetune_qwen_governance.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/finetune_qwen_governance.ipynb)

Fallback / broader LoRA lane:

- [scbe_finetune_colab.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/scbe_finetune_colab.ipynb)

Do not start with a new notebook. Fork the governance notebook first because it already targets `Qwen/Qwen2.5-0.5B-Instruct`, uses Colab-friendly 4-bit LoRA, and is aligned with the repo's current small-model path.

## Phase 1: Dataset Assembly

1. Create a new local dataset lane under `training-data/fiber_optics/`.
2. Normalize source material into the multiview schema in [fiber_optics_multiview_schema.json](C:/Users/issda/SCBE-AETHERMOORE/training-data/schemas/fiber_optics_multiview_schema.json).
3. Start with `100-300` records, not thousands.
4. Keep all four views when available:
   - `L0` raw trace summary
   - `L1` derived wave features
   - `L2` diagnosis
   - `L3` explanation / fix

## Phase 2: Chat Formatting

Adapt the current governance notebook formatter so the user turn includes the multiview packet, for example:

```text
<|im_start|>system
You are a fiber-optics diagnostic specialist. Use raw traces, wave features, and impairment evidence to diagnose the link and recommend the safest first remediation step.
<|im_end|>
<|im_start|>user
[fiber-optics-dispersion-analysis]
L0: ...
L1: ...
L2 candidate evidence: ...
Question: Identify the dominant impairment and explain the first action.
<|im_end|>
<|im_start|>assistant
...
<|im_end|>
```

## Phase 3: First Adapter Run

Use the existing notebook defaults as the starting point:

- base model: `Qwen/Qwen2.5-0.5B-Instruct`
- 4-bit quantization on Colab T4
- LoRA only, no full-model tuning
- 3 epochs max for the first pass
- target output repo: a new specialist adapter, not the main governance model

Suggested first adapter name:

- `issdandavis/scbe-qwen-fiber-optics-0.5b-lora`

## Phase 4: Evaluation

Hold out `20-30` records covering all major impairments.

Minimum eval slices:

- chromatic dispersion recognition
- PMD recognition
- attenuation vs splice-loss separation
- Kerr nonlinearity diagnosis
- remediation recommendation quality
- uncertainty / escalation behavior on mixed cases

## Phase 5: Governance Loop Follow-Up

Once the first adapter is stable, add deterministic feedback:

1. model proposes diagnosis and remediation
2. rule-based optics checker or simulator validates the proposal
3. rejected / corrected / accepted triples become DPO-style data

That is the optics analog of the coding governance loop already present in this repo.

## Why This Path

This keeps the work aligned with existing repo infrastructure:

- same Qwen family already in use
- same Colab/T4 lane already documented
- same SFT-first workflow already working
- a specialist adapter instead of a risky global behavior change

The right first milestone is not "fiber-optics AGI." It is a narrow adapter that reliably separates `chromatic_dispersion`, `PMD`, `attenuation_loss`, and `kerr_nonlinearity` from multiview packets.
