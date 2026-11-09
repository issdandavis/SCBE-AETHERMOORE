# Layer-14A predictive sensory trits (design hypothesis)

This sidecar reuses, rather than replaces, existing SCBE structures:

- Layer 14 remains the canonical audio/telemetry composition axis.
- `L14A_AUDIO_COHERENCE_INPUT` still occurs before Layer 13; `L14B` remains
  post-decision sonification.
- `SpectralObservation.status` distinguishes observed, silent, missing, and
  too-short input, so numeric/trit zero does not have to carry missingness.
- `DualTernaryState` supplies the existing 3x3 carrier.

The sidecar maps prediction error to the primary trit and observation context
to the mirror trit:

| Primary | Meaning |
|---:|---|
| `-1` | observed below prediction |
| `0` | within the configured residual dead zone |
| `+1` | observed above prediction |

| Mirror | Meaning |
|---:|---|
| `-1` | expected signal omitted |
| `0` | measured silence without an active omission |
| `+1` | evidence physically observed |

Adaptation and precision remain bounded continuous fields; quantizing them
prematurely would discard the magnitude needed to test whether a route should
be suppressed or amplified. Missing and too-short data return neutral trits but
retain their typed status and never update the predictor.

The provisional route equation is

`precision*abs(observed-predicted) - lambda*adaptation + eta*omission`.

This is a removable `PY_FULL14`/Layer-14A research sidecar, not a change to the
canonical decision formula. It needs matched adaptation, expectation,
omission, and time-shuffle controls before any Layer-13 integration.
