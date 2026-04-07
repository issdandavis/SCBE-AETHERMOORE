# Decimal Drift Forensics

> Decimal Drift is a forensic instrument that converts IEEE 754 floating-point rounding errors into cryptographic watermarks, enabling distinction between data that has traversed the SCBE 14-layer pipeline and data that has not.

## Core Concept

Every floating-point operation in the 14-layer pipeline introduces predictable rounding artifacts due to the nature of IEEE 754 double-precision arithmetic. Rather than treating these as noise, Decimal Drift captures and analyzes them as a **Proof of Process** -- evidence that data "earned" its values by traversing mandatory governance layers.

### Two Data Classes

| Class | Description |
|-------|-------------|
| **Organic Data** | Data that has traversed the full 14-layer pipeline, accumulating characteristic drift signatures at each stage |
| **Synthetic Data** | Data generated offline or injected without passing through the pipeline; lacks the expected drift fingerprint |

## 14-Stage Computational Interferometry

Each layer of the pipeline contributes a measurable drift component. Three layers are primary drift sources:

### Layer 3 -- Weighted Transform

The langues metric weighted transform applies phi-scaled coefficients (KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09) to input vectors. Each multiplication and accumulation step introduces rounding at the least significant bits. The drift pattern is deterministic for a given input but impossible to reproduce without executing the actual transform.

### Layer 4 -- Poincare Embedding (tanh)

The hyperbolic tangent mapping into the Poincare ball model is a transcendental function evaluation. The `tanh` computation produces characteristic rounding patterns that differ measurably from naive approximations or lookup tables. The embedding step creates a drift signature that is tightly coupled to the input magnitude and the specific implementation path.

### Layer 7 -- Mobius Phase

The Mobius transformation applies a conformal map in the Poincare disk. This operation involves division by complex denominators near the unit boundary, where floating-point precision degrades predictably. The resulting drift is amplified in regions of high curvature, creating a position-dependent watermark.

### Cumulative Drift

The drift from all 14 layers compounds. Each layer's output becomes the next layer's input, so rounding errors propagate and interact in patterns that are:

- **Deterministic**: Same input through same pipeline produces same drift
- **Non-trivial to forge**: Reproducing the exact drift pattern requires executing every layer in sequence
- **Measurable**: Standard statistical tests can distinguish pipeline-processed data from synthetic data

## Detection Performance

| Detection Task | AUC Score |
|---------------|-----------|
| Synthetic / No-Pipeline | 0.9954 |
| Anomalous Scale | 1.0000 |

The near-perfect AUC scores indicate that Decimal Drift analysis can reliably distinguish organic from synthetic data, and can detect anomalous scaling (e.g., data that was multiplied or divided outside the pipeline) with zero false negatives.

## Fractional Entropy Analysis

Fractional entropy measures the randomness distribution in the least significant decimal digits of pipeline outputs.

### Detection Rule

```
IF sigma_decimal > 2x baseline THEN ALERT
```

Where `sigma_decimal` is the standard deviation of the fractional digit distribution. Organic data exhibits a characteristic entropy band; deviations beyond 2x baseline indicate tampering, injection, or bypass.

### Interpretation

- **Within baseline**: Data traversed the pipeline normally
- **1x-2x baseline**: Marginal -- possible edge-case inputs or numerical boundary conditions
- **> 2x baseline**: ALERT -- data likely did not traverse the full pipeline, or was modified post-pipeline

## Spectral Decimal Drift

The audio axis (Layer 14) applies DSP filter operations that create additional drift artifacts in the frequency domain.

### Hard Wall Property

The spectral drift creates a "Hard Wall" against spoofing because:

1. **FFT operations** introduce their own rounding patterns based on butterfly decomposition order
2. **Filter coefficients** interact with input spectra to produce drift that depends on the full signal history
3. **Inverse FFT** compounds the drift in a way that is coupled to the forward transform
4. The resulting spectral fingerprint cannot be reproduced without executing the actual DSP pipeline

An attacker attempting to forge the spectral drift signature would need to replicate the exact FFT implementation, filter topology, and coefficient precision -- effectively requiring them to run the real pipeline.

## Proof of Process

Decimal Drift transforms the 14-layer pipeline from a processing system into a **provenance system**. Each piece of data carries embedded evidence of its computational history:

- **What it traversed**: The drift pattern encodes which layers were executed
- **In what order**: Layer interactions create order-dependent drift
- **With what parameters**: Governance parameters (tongue weights, curvature settings) influence drift magnitudes
- **At what precision**: The specific floating-point implementation leaves its mark

This is not a traditional watermark (inserted data) but an **emergent watermark** -- a natural consequence of the computation itself, requiring no additional overhead to generate and no separate channel to verify.

## Relationship to Pipeline Integrity

Decimal Drift serves as a complementary verification mechanism alongside:

- **GeoSeal**: Cryptographic binding of governance state
- **HYDRA consensus**: Byzantine-tolerant agreement on processing outcomes
- **Axiom mesh**: Mathematical invariant verification across layers

Together, these systems ensure that data provenance is verifiable at multiple levels: cryptographic (GeoSeal), consensus (HYDRA), mathematical (axioms), and computational (Decimal Drift).
