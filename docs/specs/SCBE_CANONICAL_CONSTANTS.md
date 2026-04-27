# SCBE Canonical Constants

Locked reference values used across the SCBE-AETHERMOORE codebase.
Changing any value here requires a coordinated update across TS and Python implementations.

## Core Mathematical Constants

| Constant | Value | Source |
|----------|-------|--------|
| PHI (Golden Ratio) | 1.618033988749895 | `src/index.ts`, `src/browser/evaluator.ts` |
| ARCHITECTURE_LAYERS | 14 | `src/index.ts` |
| POINCARE_RADIUS | 0.99 | `src/index.ts` DEFAULT_CONFIG |
| HARMONIC_SCALING | 1.5 | `src/index.ts` DEFAULT_CONFIG |

## Governance Thresholds (scan API)

| Decision | H_eff Threshold | Meaning |
|----------|----------------|---------|
| ALLOW | >= 0.75 | Safe operation |
| QUARANTINE | >= 0.45 | Suspicious, monitored |
| ESCALATE | >= 0.20 | High risk, needs review |
| DENY | < 0.20 | Adversarial, blocked |

Source: `src/index.ts` THRESHOLDS

## Browser Evaluator Thresholds (risk score)

| Decision | Risk Score | Meaning |
|----------|-----------|---------|
| ALLOW | < 0.30 | Green zone |
| QUARANTINE | < 0.60 | Yellow zone, monitored |
| ESCALATE | < 0.85 | Red zone, needs approval |
| DENY | >= 0.85 | Blocked |

Source: `src/browser/evaluator.ts` THRESHOLDS

## Sacred Tongues (Langues Metric)

| Tongue | ID | Phi Weight | Layer |
|--------|-----|-----------|-------|
| KO (Kor'aelin) | 0 | 1.000 | Knowledge/Oversight |
| AV (Avali) | 1 | 1.618 | Analysis/Verification |
| RU (Runethic) | 2 | 2.618 | Runtime/Ethics |
| CA (Cassisivadan) | 3 | 4.236 | Cascade/Causality |
| UM (Umbroth) | 4 | 6.854 | Uncertainty/Mystery |
| DR (Draumric) | 5 | 11.090 | Diagnosis/Dream |

Weight formula: `phi^n` where n is the tongue index.
Source: `src/tokenizer/`, `src/spiralverse/`

## Harmonic Wall Cost Function

```
H(d, pd) = 1 / (1 + d_H + 2*pd)
```

Where:
- `d_H` = hyperbolic distance in Poincaré ball
- `pd` = phase deviation (semantic injection penalty + control char penalty)

Super-exponential wall: `phi^((phi * d*)^2)`

## Hyperbolic Distance (Layer 5)

```
d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
```

## Post-Quantum Cryptography

| Algorithm | Standard | Usage |
|-----------|----------|-------|
| ML-KEM-768 | NIST FIPS 203 | Key encapsulation |
| ML-DSA-65 | NIST FIPS 204 | Digital signatures |
| AES-256-GCM | NIST SP 800-38D | Symmetric encryption |

## Domain Risk Scores (Browser Agent)

| Domain Pattern | Risk | Zone |
|---------------|------|------|
| bank, finance, pay, money | 0.95 | RED |
| health, medical | 0.80 | RED |
| .gov, government | 0.75 | RED |
| facebook, twitter, instagram | 0.60 | YELLOW |
| amazon, ebay, shop | 0.50 | YELLOW |
| google, bing, duckduckgo | 0.30 | GREEN |
| default | 0.40 | GREEN |

## Model Provider Tiers

| Tier | Provider | Cost |
|------|----------|------|
| 0 | LOCAL | Free |
| 1 | HAIKU, FLASH | Low |
| 2 | GROK | Medium |
| 3 | SONNET | High |
| 4 | OPUS | Highest |

## Version

Package: 4.0.3 (npm + PyPI)
Patent: USPTO #63/961,403
