---
name: scbe-audio-intent
description: Encode and decode intent values as phase-modulated audio waveforms using FFT-based demodulation. Use when working with the audio intent layer, phase encoding/recovery, or the symphonic cipher carrier signal.
---

# SCBE Audio Intent

Use this skill for phase-modulated intent encoding and decoding in the SCBE-AETHERMOORE audio layer.

## Core Mechanism

Intent values ∈ [0, 1] are encoded as phase offsets on a carrier frequency, then recovered via FFT peak analysis.

### Encoding (Phase Modulation)
```
wave(t) = cos(2π · f_carrier · t + 2π · intent) + noise
```
- f_carrier = 440 Hz (A4)
- Sample rate = 44100 Hz
- Duration = 0.5 seconds
- Gaussian noise σ = 0.1 added for transmission simulation

### Decoding (FFT Demodulation)
1. Compute FFT of received waveform.
2. Find peak index in positive-frequency half.
3. Extract phase angle at peak: `angle(FFT[peak_idx])`.
4. Normalize: `intent_recovered = (phase mod 2π) / 2π`.

## Audio Constants

| Name          | Value  | Purpose                |
|---------------|--------|------------------------|
| CARRIER_FREQ  | 440.0  | Base carrier (Hz)      |
| SAMPLE_RATE   | 44100  | Samples per second     |
| DURATION      | 0.5    | Waveform length (sec)  |

## Workflow

1. Accept intent value ∈ [0, 1].
2. Generate time vector: `linspace(0, DURATION, SAMPLE_RATE * DURATION)`.
3. Produce carrier with phase offset: `cos(2π·440·t + 2π·intent)`.
4. Add Gaussian noise.
5. To recover: FFT → peak detection → phase extraction → normalize.

## Accuracy Considerations

- Phase recovery is approximate due to noise and FFT bin resolution.
- For governance decisions, the recovered intent is compared against known target (e.g., 0.75) with tolerance ±0.1.
- Higher sample rates or longer durations improve phase resolution.

## Integration Points

- The recovered intent feeds into the coherence check in `governance_9d`.
- Coherence is HIGH (0.95) when `|intent - 0.75| < 0.1`, LOW (0.4) otherwise.
- The audio layer provides a physical-channel encoding for the v2 (Intent Phase) component.

## Guardrails

1. Intent must be clamped to [0, 1] before encoding.
2. Only use positive-frequency half of FFT for peak detection.
3. Phase normalization must use modulo 2π before dividing.
4. Noise level (σ=0.1) is fixed for reproducibility; do not increase without testing recovery accuracy.
