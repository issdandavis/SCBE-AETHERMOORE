# SCBE Adversarial Attack Suite — Design Document

## Status: DESIGNED, NOT YET BUILT
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

## Next Steps
1. Build full attack suite (100+ attacks)
2. Integrate with existing pytest suite
3. Build SCBE vs baseline benchmark comparison runner
4. Generate ONE measurable metric for external claims
