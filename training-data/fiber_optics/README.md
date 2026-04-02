# Fiber Optics Wave-Layer Starter Corpus

This folder is the repo-local landing zone for a specialist fiber-optics adapter that uses the SCBE multiview idea in a wave-native domain.

## Goal

Train a small Qwen adapter to diagnose and explain fiber-optics impairments from four linked views:

- `L0` raw traces or sampled signal summaries
- `L1` transformed wave features
- `L2` channel / impairment diagnosis
- `L3` human explanation and fix recommendation

This treats fiber optics as a second instance of the broader SCBE wave layer, alongside music-harmonic reasoning.

## Canonical Impairments

- `chromatic_dispersion`
- `polarization_mode_dispersion`
- `attenuation_loss`
- `kerr_nonlinearity`
- `splice_or_connector_loss`
- `amplifier_noise`

## Files In This Starter Pack

- [fiber_optics_multiview_schema.json](C:/Users/issda/SCBE-AETHERMOORE/training-data/schemas/fiber_optics_multiview_schema.json) - specialized JSON schema for multiview optics records.
- [fiber_optics_sft_prompt_taxonomy.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/fiber_optics_sft_prompt_taxonomy.md) - first 100 prompt types for SFT construction.
- [fiber_optics_qwen_adapter_runbook.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/fiber_optics_qwen_adapter_runbook.md) - exact repo path for the first Colab/Qwen training lane.

## Recommended Corpus Sources

- public optics tutorials
- standards summaries and vendor troubleshooting notes
- optics textbooks and paper excerpts you can legally summarize
- simulator outputs and synthetic traces you generate locally
- BER / Q-factor / link-budget tables converted into instruction-response form

## Record Strategy

Keep prose-only examples separate from multiview examples. The specialist adapter should learn the same impairment from multiple representations, not just from explanatory text.

Recommended split:

- `40%` prose and concept explanation
- `35%` multiview diagnosis records (`L0-L3`)
- `15%` calculations and link-budget tasks
- `10%` remediation comparison and counterfactual tasks

## First Execution Target

Do not create a brand-new notebook first. Fork the existing Qwen governance lane in [finetune_qwen_governance.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/finetune_qwen_governance.ipynb), swap in the fiber-optics dataset config, and keep the run adapter-sized until the schema and prompt mix stabilize.
