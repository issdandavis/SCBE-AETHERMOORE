# Semantic Separation and Controlled Blending

Date: 2026-04-25

This note converts the continuity / expansion / contraction discussion into a concrete SCBE operations gate. It is not a replacement for Sacred Eggs, cryptographic checks, or authorization. It governs whether facts, semantic context, analogies, inferences, and experimental lanes may influence AI operation routing.

## Operating Axioms

1. Continuity: useful system state must persist or propagate through time.
2. Dual harmonic control: expansion and contraction are coupled by resonance, not treated as separate modes.
3. Controlled openness: new variables are allowed only under explicit policy.
4. Representation layering: fact, semantic, analogy, inference, and experimental sources stay distinguishable.
5. Emergent stability: viable systems use bounded oscillation instead of static equilibrium.
6. Generative expansion: novelty can arise from dimensional expansion, solving in the expanded space, then compressing back into a stable representation.

## Gate Contract

The implementation lives in `python/scbe/semantic_gate.py`.

Inputs:

- `SemanticSignal`: value plus label, source, confidence, and provenance.
- `SemanticBlendPolicy`: context, risk, allowed source classes, fact requirement, and confidence floor.

Outputs:

- `SemanticGateRecord`: deterministic decision record with `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`.
- `blended_value`: confidence-weighted numeric blend over allowed numeric signals only.
- `allowed_sources` and `blocked_sources`: explicit provenance outcome.
- `record_hash`: stable digest over policy, signals, and decision fields.

## Default Behavior

- Facts can affect all contexts when they meet confidence policy.
- Semantics and inference can affect routing/training unless the policy disables them.
- Analogy is sandboxed by default.
- Experimental sources are quarantined unless explicitly allowed.
- High-risk action contexts require fact-only influence.
- Missing required fact channels fail closed.

## Basket-Weave Integration

`scripts/experiments/basket_weave_consistency_gate.py` now includes a semantic gate check. The check intentionally presents:

- a factual rename benchmark score,
- an analogy-lane geometry closure score,
- an experimental T / EML prototype signal.

The expected result is `QUARANTINE` with only the fact channel used in the blend. This keeps layered geometry and EML useful for routing and research while preventing them from silently becoming action-critical fact channels.

