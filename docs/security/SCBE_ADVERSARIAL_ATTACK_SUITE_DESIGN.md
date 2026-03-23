# SCBE Adversarial Attack Suite — Design Document

## Status: BUILT — 10 test files, 91 attacks, 15 clean baseline, 35.2% detection @ 0% FP
## Source: Gemini collaboration + Issac's system architecture, 2026-03-22

---

## Core Positioning

> SCBE converts prompt injection from a detection problem into a constrained execution problem.

> A state-space control system for AI behavior under adversarial input.

---

## What Tests Currently Prove
- ✅ Internal consistency
- ✅ Detection of state perturbation
- ✅ System invariants (35/35 pytest pass)

## What Tests Do NOT Yet Prove
- ❌ Reduction in real-world attack success rate
- ❌ Robustness under adaptive adversaries
- ❌ Superiority over existing methods

---

## Attack Taxonomy (10 Classes)

### Standard Classes (from research + OWASP)
1. **Direct Injection** — "ignore previous instructions"
2. **Indirect Injection (RAG Poisoning)** — malicious instructions in documents
3. **Encoding Attacks** — base64, homoglyphs, whitespace tricks
4. **Multilingual Attacks** — semantic attacks without English keywords
5. **Adaptive Multi-Step** — attacker iterates based on response
6. **Tool/Action Hijack** — "send data to external API"

### SCBE-Specific Classes
7. **Tongue Manipulation** — force KO dominance, suppress DR/UM validation
8. **Spin Drift** — subtle semantic drift across steps (slow poisoning)
9. **Cross-Surface Inconsistency** — data consistent in one surface, anomalous in another
10. **Boundary Exploit** — push representations toward Poincare boundary, hide in edge behavior

---

## Adaptive Attacker Engine

Fallback strategies when initial attack fails:
1. Simplify (complex → basic override)
2. Obfuscate (encoding/spacing/homoglyphs)
3. Split (multi-step instead of single)
4. Move domain (language switch / tongue domain switch)
5. Indirect (embed in retrieved content)

---

## Benchmark Metrics
- Attack Success Rate (ASR)
- False Positive Rate
- Drift magnitude
- Cross-surface disagreement
- Time-to-detection
- Allowed vs denied actions

---

## Key Insight
Testing NOT: "did the model say something bad?"
Testing: "did the system allow a dangerous state transition?"

---

## File Structure (when built)
```
tests/adversarial/
├── test_direct_injection.py
├── test_indirect_injection.py
├── test_encoding_attacks.py
├── test_multilingual_attacks.py
├── test_adaptive_sequences.py
├── test_tool_exfiltration.py
├── test_cross_surface_attacks.py
├── test_scbe_specific_attacks.py
├── test_boundary_attacks.py
└── test_combined_attacks.py
```

---

## Current Results (2026-03-23)

| Attack Class | Detection | Notes |
|---|---|---|
| combined_multi | 100% (5/5) | Multi-vector is hardest to evade |
| boundary_exploit | 80% (4/5) | Poincare boundary detection strong |
| direct_override | 50% (5/10) | Lexical patterns catch half |
| encoding_obfuscation | 40% (4/10) | |
| tool_exfiltration | 40% (4/10) | |
| tongue_manipulation | 30% (3/10) | SCBE-specific vectors |
| indirect_injection | 20% (2/10) | Hardest standard class |
| multilingual | 20% (2/10) | Cross-lingual patterns help |
| spin_drift | 20% (2/10) | Late steps detected |
| adaptive_sequence | 9% (1/11) | Gradual escalation evades |
| **False positives** | **0% (0/15)** | Zero false alarms |
| **OVERALL** | **35.2% (32/91)** | **0% FP** |

## Next Steps
1. ~~Build full attack suite (100+ attacks)~~ DONE
2. ~~Integrate with existing pytest suite~~ DONE
3. Build SCBE vs baseline benchmark comparison runner
4. Improve multilingual detection (semantic layer needed)
5. Add sequence-aware drift detection (cost trajectory analysis)
6. Generate ONE measurable metric for external claims
