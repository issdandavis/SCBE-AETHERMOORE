# Phase Control Modulation Matrices

This is a small experimental lane for comparing:

- periodic six-tongue phase control
- aperiodic six-tongue phase control

It is intentionally separate from production governance paths.

## Why this exists

The repo already has:

- canonical six-tongue phase offsets
- quasicrystal / phason language
- n8n and AetherBrowse workflow hooks

What it did not have was a small inspectable artifact that answers:

1. what does a repeating phase-control matrix look like?
2. what does a phi-driven aperiodic variant look like?
3. how could either be serialized into a workflow payload?

## Files

- [phase_control.py](C:/Users/issda/SCBE-AETHERMOORE/src/experimental/phase_control.py)
- [phase_control_modulation_experiment.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/phase_control_modulation_experiment.py)
- [test_phase_control_modulation_experiment.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_phase_control_modulation_experiment.py)

## Run

```powershell
python scripts/phase_control_modulation_experiment.py --steps 12 --period 6
```

Default output:

- `artifacts/experiments/phase_control_modulation_report.json`

## Current model

- `periodic`
  - uses the canonical six-tongue ring with a rational repeat window
  - useful when you want stable scheduled behavior

- `aperiodic`
  - uses phi-driven irrational progression plus per-node quasi offsets
  - useful when you want structure without short-cycle repetition

## n8n fit

The output already contains a compact `n8n_payload_hint` block. That means the next step can be a workflow node that chooses:

- `mode = periodic`
- `mode = aperiodic`

and passes the selected step/matrix/modulation payload to AetherBrowse, a coordinator, or a later control surface.
