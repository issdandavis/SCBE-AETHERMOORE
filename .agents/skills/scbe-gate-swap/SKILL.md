---
name: scbe-gate-swap
description: Analyze and swap between 2-gate (binary/negabinary) and 3-gate (balanced ternary) encoding for stability optimization. Use when evaluating gate efficiency, comparing encoding strategies for governance decisions, or optimizing bit-level representation in SCBE subsystems.
---

# SCBE Gate Swap Analysis

Determine where in the SCBE-AETHERMOORE system to use 2-gate (binary) vs 3-gate (ternary) encoding for maximum stability and efficiency.

## Gate Types

### 3-Gate (Balanced Ternary)
- Digits: {-1, 0, +1} (T, 0, 1)
- No sign bit needed
- Maps directly to ALLOW/QUARANTINE/DENY
- Best for: governance decisions, small mixed-sign values, consensus voting

### 2-Gate (Binary / Negabinary)
- Standard binary: digits {0, 1}, needs sign bit for negatives
- Negabinary (base -2): digits {0, 1}, no sign bit, polarity from position
- Best for: large positive ranges, bit-level operations, hardware compatibility

## When to Use Which

| Subsystem | Recommended Gate | Why |
|-----------|-----------------|-----|
| Governance decisions | 3-gate (ternary) | Natural ALLOW/QUARANTINE/DENY mapping |
| BFT voting | 3-gate (ternary) | YES/ABSTAIN/NO maps to +1/0/-1 |
| Trust scores | 3-gate (ternary) | Trust/neutral/distrust is triadic |
| Entropy values | 2-gate (binary) | Always positive, wide range |
| Bit lengths | 2-gate (binary) | Always positive integers |
| Polarity analysis | 2-gate (negabinary) | Natural positive/negative encoding |
| Sacred Tongue mapping | 2-gate (negabinary) | KO/AV polarity from bit position |
| Hamiltonian routing | 3-gate (ternary) | Direction: forward/stay/backward |
| Safety scores | 3-gate (ternary) | Safe/uncertain/unsafe |
| Cryptographic keys | 2-gate (binary) | Hardware/algorithm compatibility |
| Spectral coefficients | 3-gate (ternary) | Positive/zero/negative frequency |

## Analysis Workflow

### 1. Profile the Value Range
```python
from src.symphonic_cipher.scbe_aethermoore.negabinary import analyze_gate_stability

# Collect values from the subsystem
values = [...]  # the data to encode

report = analyze_gate_stability(values)
print(report.stability_recommendation)
print(f"Binary:     {report.binary_total_bits} bits")
print(f"Ternary:    {report.ternary_total_trits} trits")
print(f"Negabinary: {report.negabinary_total_bits} bits")
```

### 2. Interpret the Recommendation
The analyzer uses these heuristics:
- **Small mixed-sign (|max| <= 40, has negatives)**: TERNARY
- **Mixed polarity, negabinary more compact**: NEGABINARY
- **Ternary fewer trits than negabinary bits**: TERNARY
- **Large positive range**: BINARY

### 3. Cross-Convert if Needed
```python
from src.symphonic_cipher.scbe_aethermoore.negabinary import (
    negabinary_to_balanced_ternary,
    balanced_ternary_to_negabinary,
)
from src.symphonic_cipher.scbe_aethermoore.trinary import BalancedTernary
from src.symphonic_cipher.scbe_aethermoore.negabinary import NegaBinary

# Ternary -> Negabinary
bt = BalancedTernary.from_int(42)
nb = balanced_ternary_to_negabinary(bt)

# Negabinary -> Ternary
nb = NegaBinary.from_int(-7)
bt = negabinary_to_balanced_ternary(nb)
```

### 4. Governance Decision Packing
```python
from src.symphonic_cipher.scbe_aethermoore.trinary import BalancedTernary

decisions = ["ALLOW", "DENY", "QUARANTINE", "ALLOW", "ALLOW"]
packed = BalancedTernary.pack_decisions(decisions)
summary = packed.governance_summary()
# {consensus: "ALLOW", net_score: 2, allow: 3, deny: 1, quarantine: 1}
```

### 5. Tongue Polarity from Negabinary
```python
from src.symphonic_cipher.scbe_aethermoore.negabinary import NegaBinary

nb = NegaBinary.from_int(42)
print(nb.tongue_polarity())   # "KO" or "AV" or "RU"
print(nb.tongue_encoding())   # ["KO", "UM", "AV", "KO", ...]

# Even bit positions = positive weight = KO (assertive)
# Odd bit positions  = negative weight = AV (receptive)
# Zero bits          = UM (silence)
```

## Integration with Existing Systems

### Dual Ternary (ai_brain/dual_ternary.py)
The existing 9-state dual ternary system uses {-1,0,+1} x {-1,0,+1} for spectral analysis. The new balanced ternary module provides arithmetic operations that complement it.

### CPSE z-vector
The CPSE deviation channels (chaosdev, fractaldev, energydev) produce values in [-1, +1]. These map naturally to ternary encoding when discretized.

### Layer 11 Triadic Distance
The triadic temporal distance already uses a 3-valued system. Balanced ternary provides the formal arithmetic foundation.

## Key Files

| File | Purpose |
|------|---------|
| `src/symphonic_cipher/scbe_aethermoore/trinary.py` | Balanced ternary encoding + governance |
| `src/symphonic_cipher/scbe_aethermoore/negabinary.py` | Negabinary + gate stability analysis |
| `src/symphonic_cipher/scbe_aethermoore/ai_brain/dual_ternary.py` | 9-state dual ternary spectral |
| `tests/test_trinary_negabinary.py` | 45 tests covering both systems |

## Entropy Comparison

```python
# Ternary: max entropy = log2(3) = 1.585 bits per trit
# Binary:  max entropy = log2(2) = 1.000 bits per bit
# Ternary packs more information per digit

bt = BalancedTernary.from_int(n)
density = bt.information_density()  # 0.0 to 1.0

nb = NegaBinary.from_int(n)
entropy = nb.bit_entropy()  # Shannon entropy of bit distribution
```
