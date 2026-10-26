# Agent hooks, capability windows, and model-layer evidence

This implementation joins two different observation surfaces without treating
them as the same security boundary:

1. `scripts/system/scbe_hook_router.py` receives agent lifecycle and tool-call
   events before or after an external action.
2. Clay's `layer_hook_bus.py` observes selected PyTorch modules inside a model
   forward or backward pass.

The outer hook can deny a proposed tool call when the host waits for its
pre-commit decision. The model-layer hook is always observational. It can
measure a computation, but it cannot prove that a tool was authorized or stop
an execution path that bypasses the hook.

## Tool-call path

```text
native tool call
  -> AgentHook-compatible envelope
  -> native and normalized action fields
  -> fixed destructive/exfiltration checks
  -> capability class and permission profile
  -> optional session/time/explicit capability gate
  -> dH, phase, and 14-layer route telemetry
  -> allow or deny
  -> hash-linked local receipt
```

The native `tool_name` and `tool_input` remain in the event. Derived fields are
added as policy hints rather than rewriting the original call. This follows the
AgentHook v0.2 draft's native-plus-normalized event model.

The capability names are the existing names from
`src/coding_spine/agent_tool_bridge.py`:

| Availability | Capabilities | Admission requirement |
|---|---|---|
| Universal | `read`, `system_ghost_terminal_audit` | Existing static policy |
| Session bounded | `write_workspace`, `execute_tests` | Session ID and an allowing permission profile, or explicit authorization |
| Time bounded | `network_or_cloud`, `system_ghost_terminal_cleanup` | Matching capability lease active at event time, plus profile or explicit authorization |
| Explicit only | `secrets_or_credentials`, `destructive_filesystem` | Named explicit authorization; secrets remain denied by default and the destructive classifier still takes precedence |

Capability-window enforcement is opt-in with
`scbe_context.enforce_capability_window`. This preserves existing hook behavior
while integrations are migrated. An active time lease contains `not_before`,
`expires_at`, and a `capabilities` list. A lease for one capability never opens
another.

## The tool-call axis

For a declared capability `c`, its six-tongue profile is expanded across the 14
SCBE stages and weighted by powers of the golden ratio. The resulting vector is
normalized to a unit tool axis:

```text
a_c[l] = phi^tongue(l) * profile_c[tongue(l)]
axis_c = a_c / ||a_c||
```

If a caller provides a 14-element layer state `s`, derivative `ds`, and positive
step `dt`, the hook measures whether the predicted state moves toward the
positive ray of that capability:

```text
s_next = s + dt * ds
convergence = distance_to_axis(s) - distance_to_axis(s_next)
```

Positive convergence means the supplied trajectory moved closer to the axis.
It is evidence about a route, not permission to take the route. The route score
is a bounded ranking signal:

```text
cost = d_H(position, trusted_center)
     + 2 * abs(phase_deviation)
     + predicted_axis_distance / sqrt(14)

route_score = 1 / (1 + cost)
```

Bad or missing geometric inputs cannot grant access. Points on or outside the
Poincare-ball boundary are recorded as telemetry errors. Exact capability,
permission, session, lease, and explicit-authorization checks remain the
admission basis.

## Evidence and privacy boundary

The runtime receipt log is append-only and hash-linked with a sequence number,
previous-event hash, and event hash. This detects later edits, deletion in the
middle, and reordering when the complete log is available. It is not a digital
signature, external timestamp, hardware attestation, or protection against a
process that bypasses the publisher.

Clay layer events contain tensor shape, dtype, device, finite fraction, mean,
standard deviation, RMS, L2 norm, maximum absolute value, zero fraction, and a
summary hash. They never record raw activations, gradients, prompts, targets,
or token IDs. Even summaries can reveal operational information, so layer logs
still require access and retention controls.

## Threat model

| Threat | Control in this slice | Remaining limit |
|---|---|---|
| Prompt or tool-output injection requests a dangerous action | Pre-tool static rules and capability gate | An unhooked tool path is unseen |
| Replay of a cloud or cleanup permission | UTC interval and exact capability match | Host-supplied context is not yet a signed capability token |
| Geometry is forged to make a call look trustworthy | Geometry is explicitly telemetry-only | Bad telemetry can still mis-rank eligible routes |
| Receipt edited after execution | SHA-256 chain and verifier | An attacker controlling the writer and all copies can replace the full chain |
| Layer observer changes model output | Hooks return `None`; equality regression test | Third-party hooks can be mutating and need separate review |
| Activation logging leaks prompts or memorized text | Bounded aggregate summaries only | Aggregates are not anonymous and need restricted storage |
| Poisoned training data or model weights alter behavior | Checkpoint hashes, lineage, matched controls, held-out tests | Hashes prove identity, not model quality or safety |
| Parallel tasks interfere through shared weights | Isolated route can prevent inactive-expert gradients | Shared normalization/readout parameters still allow collateral movement |

The categories follow NIST AI 100-2's lifecycle framing for poisoning, evasion,
privacy, attacker capabilities, and mitigations.

## Research and interface basis

- [AgentHook v0.2 draft specification](https://github.com/agentic-thinking/agenthook/blob/main/SPEC.md)
- [AgentHook envelope schema](https://github.com/agentic-thinking/agenthook/blob/main/envelope.schema.json)
- [PyTorch `nn.Module` hooks](https://docs.pytorch.org/docs/stable/generated/torch.nn.Module.html)
- [NIST AI 100-2 E2025 adversarial machine-learning taxonomy](https://doi.org/10.6028/NIST.AI.100-2e2025)
- [Progressive Neural Networks](https://arxiv.org/abs/1606.04671)
- [Cross-Stitch Networks](https://openaccess.thecvf.com/content_cvpr_2016/papers/Misra_Cross-Stitch_Networks_for_CVPR_2016_paper.pdf)
- [Parameter-Efficient Transfer Learning for NLP](https://proceedings.mlr.press/v97/houlsby19a.html)
- [Switch Transformers](https://www.jmlr.org/papers/v23/21-0998.html)
- [PCGrad](https://papers.neurips.cc/paper_files/paper/2020/file/3fe78a8acf5fda99de95303940a2420c-Paper.pdf)

The AgentHook specification is pre-1.0 and expected to change. The publisher
manifest therefore declares self-attestation and claims no upstream
conformance level.
