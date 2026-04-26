# Photonic Accelerator Lane

## Scope

This lane models photonic neural processing units as specialized accelerator providers, not general-purpose replacements for CPU or GPU execution.

The current implementation is provider-neutral and simulated:

- Code: `src/tokenizer/accelerator_routing.py`
- Tests: `tests/tokenizer/test_accelerator_routing.py`

No named vendor is hardcoded. Real hardware can later replace the simulator behind the same packet shape.

## Task Packet

The first scoring version uses explicit workload features:

- `matmul_fraction`
- `nonlinear_op_fraction`
- `precision_required_bits`
- `input_is_optical_signal`
- `branching_density`
- `memory_access_density`
- `latency_budget_ms`
- `energy_budget_j`
- `fallback`

The provider profile is also explicit:

- `precision_native_bits`
- `matmul_throughput_score`
- `nonlinear_supported_score`
- `optical_input_native`
- `branching_supported_score`
- `memory_access_score`
- `energy_efficiency_score`
- `latency_score`

Until measured hardware data exists, `accelerator_fit_score` is a hand-tuned heuristic. It must not be described as learned or hardware-validated.

## 14-Layer Impact

Only some layers materially change when a photonic accelerator lane is added:

| Layer | Impact |
|---|---|
| L1 Complex Context | Add accelerator task context and resource budget fields. |
| L2 Realification | Convert task/context state to real-valued packet features. |
| L3 Weighted Transform | Apply hardware-aware weighting over energy, latency, precision, branch, and memory pressure. |
| L8 Multi-Well Realms | Add a `photonic_low_precision_nonlinear` route well. |
| L9 Spectral Coherence | Strong fit for optical front ends, signal processing, LiDAR, imaging, fiber telemetry, and spectral preprocessing. |
| L11 Triadic Temporal Distance | Compare task timing and resource trajectory against predicted accelerator cost. |
| L13 Decision & Risk | Emit route decisions: `PHOTONIC_NPU`, `PHOTONIC_NPU_WITH_VERIFY`, `GPU`, `CPU`, `HOLD`, or fallback. |
| L14 Audio/Observability Axis | Emit route ID, fit score, predicted latency, predicted energy, precision loss, and failure modes. |

Other layers may carry the result but do not need photonic-specific logic yet. This prevents forcing every new technology into all 14 layers just because the pipeline has 14 layers.

## Failure Modes

The simulator reports:

- `precision_mismatch`
- `branching_density_high`
- `memory_access_high`
- `latency_budget_exceeded`
- `energy_budget_exceeded`

These are routing signals, not proof of real hardware behavior.

## Build Direction

Next useful extensions:

1. Add a CLI wrapper that accepts a task packet JSON and emits an accelerator route decision.
2. Feed route decisions into Stage 6 resource-decay records.
3. Add measured provider profiles if real Q.ANT, HHI-style optical preprocessing, or other photonic hardware access becomes available.
