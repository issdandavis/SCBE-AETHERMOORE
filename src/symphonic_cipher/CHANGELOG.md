# Encoder compatibility notes

## 2026-09-17

- PROBE now terminates with its single available harmonic. The minimum count
  is capped to the modality's pool; other modalities keep their existing
  deterministic selection order.
- Fingerprint commitments now bind domain, modality and token using the same
  derivation context as the synthesized fingerprint. Persisted token-only
  commitments must be regenerated with their original keys; the encoder does
  not silently accept the old commitments.
- A subprocess regression test loads this `src` implementation by file path,
  independently of the other `symphonic_cipher` package, and enforces a timeout.
  It is included in the core Python CI lane. The focused suite passed 39 tests.

These are termination and context-binding repairs. A shared fundamental
frequency does not imply identical spectra, unique masks, or confidentiality.
Harmonic synthesis is not a substitute for vetted authenticated encryption.
