# Universal Propagation Grammar

Status: draft v0.1  
Date: 2026-04-01  
Scope: cross-domain wave/information schema for SCBE systems

---

## Purpose

SCBE already has real harmonic, phase, resonance, and governance machinery. What it does not yet have is one formal schema that explains how those ideas transfer across domains without collapsing into metaphor.

The Universal Propagation Grammar (UPG) is that schema.

It treats audio, fiber optics, LLM training, and governance loops as different instantiations of the same deeper structure:

- a carrier holds a pattern
- an excitation injects change
- the pattern propagates through constraints
- distortions reshape it
- coupling and resonance alter its growth
- damping reduces clarity or usable energy
- reconstruction tries to recover the source pattern
- adaptation retunes the system after feedback

The grammar is only valid if it cashes out into measurable predictions in each domain.

---

## Core Terms

### 1. Carrier

The substrate that holds and transports the signal.

Examples:

- audio: air, cavity, diaphragm, digital waveform channel
- fiber optics: fiber core, waveguide mode, optical channel
- LLM training: token stream, activation manifold, parameter space
- governance loop: task queue, patch proposal, execution environment, audit substrate

### 2. Excitation

The event or force that injects motion, structure, or update into the carrier.

Examples:

- audio: pluck, breath, strike, speaker impulse
- fiber optics: laser launch, modulation, amplifier stage
- LLM training: gradient update, prompt, reward signal, preference pair
- governance loop: proposed patch, test trigger, gate evaluation

### 3. Pattern

The structured content being transported.

Examples:

- audio: note, chord, spectral envelope, temporal contour
- fiber optics: encoded pulse train, constellation geometry, BER/Q trajectory
- LLM training: task structure, behavior prior, preference ordering
- governance loop: intended system change, remediation plan, trust state transition

### 4. Propagation

The rule by which the pattern moves through the carrier.

Examples:

- audio: wave travel, reflection, standing-wave buildup
- fiber optics: modal transmission, dispersion, attenuation
- LLM training: forward pass, backpropagation, optimizer trajectory
- governance loop: propose -> evaluate -> reject/accept -> retry

### 5. Distortion

Any transformation that bends, delays, corrupts, or re-weights the pattern relative to the source.

Examples:

- audio: phase smear, clipping, room coloration
- fiber optics: chromatic dispersion, PMD, Kerr nonlinearity, splice loss
- LLM training: spectral bias, reward misspecification, overfitting, distribution shift
- governance loop: stale context, unsafe patching, architecture drift, false confidence

### 6. Coupling

The mechanism by which one subsystem changes another.

Examples:

- audio: sympathetic resonance, cavity loading
- fiber optics: cross-phase modulation, amplifier-chain interactions
- LLM training: SFT affecting DPO headroom, one view improving another
- governance loop: test failures reshaping future proposals, trust state altering permissible actions

### 7. Resonance

Constructive alignment between pattern and carrier or between two coupled systems.

Examples:

- audio: harmonics reinforcing the fundamental
- fiber optics: coherent signal recovery under channel alignment
- LLM training: multi-view agreement, useful feature reuse, strong gradient alignment
- governance loop: candidate patch aligns with tests, architecture, and policy simultaneously

### 8. Damping

Loss of usable energy, clarity, or recoverability over time.

Examples:

- audio: decay, absorption, noise floor
- fiber optics: attenuation, amplifier noise penalties
- LLM training: gradient washout, catastrophic forgetting, low-signal supervision
- governance loop: retry fatigue, context rot, overlong loops with diminishing improvements

### 9. Reconstruction

The act of recovering the original pattern, or the best usable estimate of it, from a degraded observation.

Examples:

- audio: denoising, source separation, room compensation
- fiber optics: equalization, dispersion compensation, impairment diagnosis
- LLM training: inferring latent task structure from examples
- governance loop: deriving the true bug and correct patch from failing outputs

### 10. Adaptation

The retuning step that changes the system after feedback.

Examples:

- audio: tuning an instrument, changing embouchure
- fiber optics: power adjustment, compensation, channel reconfiguration
- LLM training: fine-tuning, curriculum shift, preference optimization
- governance loop: rewrite after rejection, threshold tuning, policy hardening

---

## Structural Invariants

The grammar asserts these invariants across domains:

1. A pattern cannot propagate without a carrier.
2. Every carrier imposes a transfer function.
3. Every propagation path creates distortions, even if they are small.
4. Coupling can amplify or destabilize propagation depending on alignment.
5. Resonance increases useful signal only when the underlying structure is compatible.
6. Damping is unavoidable; the only question is where it appears and how it is measured.
7. Reconstruction quality is bounded by observable evidence and carrier distortion.
8. Adaptation is only meaningful if feedback changes future propagation.

If a supposed mapping violates these invariants, it is not a real UPG instantiation.

---

## Minimal Formalization

Let:

- `C` = carrier state
- `E` = excitation
- `P` = intended pattern
- `T(C)` = carrier transfer function
- `D` = distortion field
- `K` = coupling term
- `R` = resonance gain
- `L` = damping / loss term
- `P_hat` = reconstructed pattern
- `A` = adaptation rule

One generic propagation step can be represented as:

```text
P_next = T(C, E, P) + K - D - L
```

Reconstruction:

```text
P_hat = reconstruct(P_next, observations, priors)
```

Adaptation:

```text
C', E', policy' = A(feedback, P_hat, target)
```

The exact forms differ by domain, but the roles remain fixed.

---

## Domain Instantiations

## Audio

### Mapping

- carrier: air, cavity, microphone or speaker path
- excitation: strike, pluck, breath, playback impulse
- pattern: note, chord, phoneme contour, spectral envelope
- distortion: room reflections, clipping, phase smear, noise
- coupling: sympathetic vibration, harmonic reinforcement
- resonance: stable harmonic reinforcement across bands
- damping: decay, absorption, signal loss
- reconstruction: denoise, EQ, interpret timbre or speech
- adaptation: tuning, mixing, dynamic control

### Measurable signals

- spectral centroid
- flux
- phase stability
- band energy
- harmonic-to-noise ratio

### Falsifiable prediction

If UPG is valid, a banded instability model should outperform a single scalar audio gate for detecting "near-break but still usable" voice states. That is directly testable against the current spectrum experiment.

Related anchor:

- [SCBE_AUDIO_GATE_SPECTRUM_EXPERIMENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SCBE_AUDIO_GATE_SPECTRUM_EXPERIMENT.md)

## Fiber Optics

### Mapping

- carrier: optical fiber / waveguide mode
- excitation: laser launch and modulation
- pattern: encoded light pulses and channel state
- distortion: chromatic dispersion, PMD, Kerr effects, attenuation
- coupling: amplifier interactions, nonlinear cross-effects, modal interactions
- resonance: coherent recovery under channel alignment
- damping: attenuation and effective SNR loss
- reconstruction: equalization, diagnostics, compensation
- adaptation: power retuning, compensation strategy, route changes

### Measurable signals

- OTDR-like traces
- BER / Q-factor
- group delay
- polarization state
- FFT / wavelength spread

### Falsifiable prediction

If UPG is valid, multiview fiber packets with `L0-L3` should outperform prose-only SFT on impairment separation between chromatic dispersion, PMD, attenuation loss, and Kerr nonlinearity.

Related anchors:

- [2026-04-01-wave-layer-fiber-optics-training-plan.md](C:/Users/issda/SCBE-AETHERMOORE/notes/theory/2026-04-01-wave-layer-fiber-optics-training-plan.md)
- [fiber_optics_multiview_schema.json](C:/Users/issda/SCBE-AETHERMOORE/training-data/schemas/fiber_optics_multiview_schema.json)

## LLM Training

### Mapping

- carrier: token stream, latent manifold, parameter space
- excitation: data batch, prompt, optimizer step, reward signal
- pattern: desired behavior / latent task structure
- distortion: spectral bias, overfit, reward hacking, domain mismatch
- coupling: SFT enabling DPO, views reinforcing each other
- resonance: aligned multi-view gradients and reusable structure
- damping: vanishing task signal, curriculum washout, forgetting
- reconstruction: inferring task structure from examples and losses
- adaptation: fine-tuning, DPO, curriculum updates, self-play

### Measurable signals

- loss by stage
- eval deltas by view
- gradient stability
- behavior win rates
- preference agreement

### Falsifiable prediction

If UPG is valid, the strongest gains should come from aligning the same pattern across carriers or views, not from adding more unstructured volume. That predicts multiview and deliberate-practice style data should beat equivalent-token prose-only baselines.

Related anchor:

- [2026-04-01-harmonic-training-complete-synthesis.md](C:/Users/issda/SCBE-AETHERMOORE/notes/theory/2026-04-01-harmonic-training-complete-synthesis.md)

## Governance / Agent Loops

### Mapping

- carrier: repo state, task state, runtime environment, audit chain
- excitation: proposed patch or action
- pattern: intended safe system change
- distortion: architecture drift, insecure code, stale assumptions, hallucinated fixes
- coupling: tests, policy, and trust surfaces influencing the same proposal
- resonance: a proposal passes architecture, safety, and execution checks together
- damping: retries with low new information, context decay, fatigue
- reconstruction: infer the real failure from logs, denials, and diffs
- adaptation: rewrite and retry, threshold tuning, policy updates

### Measurable signals

- gate decision sequence
- retry count
- failure mode distribution
- test pass/fail
- trust state changes

### Falsifiable prediction

If UPG is valid, a long autonomous loop should only improve when rejection feedback contains usable structural information. Blind retries should show damping; informative retries should show adaptation and eventual reconstruction.

Related anchors:

- [RESONANCE_GATE_SPEC.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/RESONANCE_GATE_SPEC.md)
- [offline_mode.ts](C:/Users/issda/SCBE-AETHERMOORE/src/governance/offline_mode.ts)

---

## Cross-Domain Mapping Table

| UPG term | Audio | Fiber optics | LLM training | Governance loop |
|---|---|---|---|---|
| Carrier | air / cavity | fiber / waveguide | tokens / weights | repo / runtime |
| Excitation | pluck / breath | launch pulse | batch / reward | patch proposal |
| Pattern | note / timbre | encoded optical signal | target behavior | intended change |
| Propagation | wave travel | channel transmission | forward/backward pass | propose-evaluate-retry |
| Distortion | clipping / smear | CD / PMD / Kerr | bias / overfit / mismatch | drift / insecurity |
| Coupling | sympathetic vibration | nonlinear interaction | view or stage interaction | tests + policy + trust |
| Resonance | harmonic reinforcement | coherent recovery | aligned gradients | all gates agree |
| Damping | decay / absorption | attenuation | forgetting / weak signal | retry fatigue |
| Reconstruction | denoise / interpret | equalize / diagnose | infer latent structure | derive true fix |
| Adaptation | retune / remix | compensate / rebalance | fine-tune / DPO | rewrite / repatch |

---

## Test Program

The next useful step is not more vocabulary. It is cross-domain measurement.

### Test 1: Audio

Compare:

- scalar gate only
- banded propagation profile

Success condition:

- banded profile predicts usable-vs-broken outputs better than scalar-only gating

### Test 2: Fiber Optics

Compare:

- prose-only SFT
- multiview `L0-L3` packet training

Success condition:

- multiview route improves impairment classification and remediation quality

### Test 3: LLM Training

Compare:

- single-view corpus
- matched-token multiview corpus

Success condition:

- multiview corpus outperforms in transfer and robustness, not just in-domain memorization

### Test 4: Governance Loops

Compare:

- retry loops with generic denials
- retry loops with structured denial reasons

Success condition:

- structured feedback yields fewer retries and higher final approval rates

---

## Failure Conditions

This grammar should be rejected or revised if:

1. It cannot produce measurable variables in a target domain.
2. It does not improve prediction relative to simpler baselines.
3. Its mappings are post-hoc and do not constrain implementation choices.
4. The same term means incompatible things across domains.
5. It produces elegant explanations but no operational improvements.

That is the anti-cult rule. The grammar only survives if it predicts.

---

## Immediate Repo Integration

1. Treat the current audio spectrum work as the first concrete UPG instantiation.
2. Treat the new fiber-optics multiview schema as the second.
3. Convert the harmonic training notes into an explicit LLM propagation test matrix.
4. Add governance-loop metrics that distinguish damping from adaptation.

Near-term follow-up docs that would be worth adding:

- `docs/specs/UPG_LLM_TRAINING_MAP.md`
- `docs/specs/UPG_GOVERNANCE_LOOP_METRICS.md`
- `docs/specs/UPG_AUDIO_VALIDATION_PLAN.md`
- `docs/specs/UPG_FIBER_EVAL_PLAN.md`

---

## Bottom Line

The system should not stop at "music theory for AI" or "fiber optics for AI." The correct abstraction level is a propagation grammar for structured energy or information moving through constrained media.

If the same grammar produces useful predictions in audio, fiber optics, LLM training, and governance loops, then it is real architecture. If it cannot survive those mappings, it stays a metaphor.
