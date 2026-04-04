---
name: latticegate-orchestrator
description: >
  Applies SCBE-AETHERMOORE governance protocols to evaluate AI agent intent
  using hyperbolic harmonic wall mathematics. Invoke whenever a user asks to
  run a drift-check on a prompt, generate a governance audit report, evaluate
  agent safety under the SCBE framework, apply LatticeGate or PhaseTunnelGate
  logic, compute a Davis Security Score, or produce client-facing AI governance
  documentation. Also trigger for any reference to harmonic walls, Poincare
  ball embeddings, ALLOW/ATTENUATE/COLLAPSE gate decisions, or Sacred Tongue
  governance routing.
---

# LatticeGate Orchestrator

Governs AI agent intent using the SCBE-AETHERMOORE framework (US Provisional
Patent #63/961,403). Produces both machine-readable JSON telemetry and
human-readable audit narratives. Every evaluation generates training data.

---

## Mathematical Foundation

### Harmonic Wall — Canonical Form (CURRENT)

The governance safety score uses the **canonical unified formula**:

```
H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)
```

Where:
- `d_H` = hyperbolic distance from safe origin (Layer 5 Poincare metric)
- `pd`  = prior deception history (Layer 9 spectral coherence deviation)
- `phi` = golden ratio = 1.6180339...
- H is in (0, 1]: H=1 at origin (safe), H->0 at boundary (adversarial)

Phi enters as a LINEAR coefficient because phi^0 through phi^5 are the
Sacred Tongue weights, and phi is the unique fixed point of x^2 = x + 1.

### Retired Formulas (DO NOT USE)

```
R^(d^2)                    : Numerical collapse at small d — RETIRED
R * pi^(phi * d*)          : Never implemented — RETIRED
1 + alpha * tanh(beta * d) : Absorbed into 1/H — RETIRED
R^(d^phi)                  : Sensitivity backwards — RETIRED
```

### Davis Security Score

The Davis Security Score (DS) quantifies how safe a prompt embedding is:

```
DS(x) = H(d_H, pd) = 1 / (1 + phi * d_H + 2 * pd)
```

DS is in (0, 1]:
- DS -> 1.0 : embedding near Poincare origin (low drift, safe)
- DS -> 0.0 : embedding near boundary (high drift, adversarial)

Behavior table:
```
d_H=0.0, pd=0.0 -> DS=1.000  ALLOW
d_H=0.3, pd=0.1 -> DS=0.593  ALLOW
d_H=0.5, pd=0.1 -> DS=0.498  ALLOW
d_H=1.0, pd=0.1 -> DS=0.355  QUARANTINE
d_H=2.0, pd=0.2 -> DS=0.204  ESCALATE
d_H=5.0, pd=0.5 -> DS=0.094  DENY
```

### Omega Gate (Full Decision)

The harmonic wall is a SHAPING function, not the final decision.
Final decisions emerge from the coupled omega gate:

```
Omega = pqc_valid * harm_score * drift_factor * triadic_stable * spectral_score
```

Where:
- `pqc_valid`      : post-quantum crypto envelope valid (0 or 1)
- `harm_score`     : Davis Security Score H(d,pd)
- `drift_factor`   : 1 - accumulated_drift (from driftTracker)
- `triadic_stable` : triadic temporal distance within bounds (L11)
- `spectral_score` : spectral coherence S_spec = 1 - r_HF (L9)

No single metric triggers denial alone. It is the coupled interaction.

### Phase Tunnel Gate

The transmission probability through the governance gate:

```
T = cos^2( (beta_phase - phi_wall) / 2 )
```

Where:
- `beta_phase` : phase angle of the prompt embedding
- `phi_wall`   : harmonic wall phase angle
- T is in [0, 1] : fraction of intent that passes the gate

### Gate Decision Logic

```
DS > tau_allow                 -> ALLOW     (full transmission)
tau_collapse < DS <= tau_allow -> ATTENUATE (scale attention by T)
DS <= tau_collapse             -> COLLAPSE  (terminate, log event)
```

### Session-Level DS Tracking (Temporal Defense)

Single-request DS cannot catch slow-ramp, gravity-well, or insider threat
attacks. These require temporal pattern analysis:

```
DS_session(t) = alpha * DS(x_t) + (1 - alpha) * DS_session(t-1)
```

Where alpha is in (0, 1) — a decay parameter controlling memory.
- alpha near 1.0 : session score tracks single requests closely (responsive)
- alpha near 0.0 : session score changes slowly (catches gradual drift)
- Default: alpha = 0.3 (UNCALIBRATED — needs tuning against attack sequences)

**Detection signals:**
- DS(x_t) stays above tau_allow BUT DS_session(t) trends toward tau_collapse
  = gravity well attack (each request is safe, trajectory is adversarial)
- DS variance increases monotonically over session
  = boundary probing (staircase pattern)
- Tongue coverage set grows from 1-2 to 5-6 over time
  = role creep / insider reconnaissance
- Telemetry field count decreases over time
  = slow boil withdrawal (blinding the observer)

**Session gate logic:**
```
DS_session > tau_allow          -> SESSION_HEALTHY
DS_session trending down        -> SESSION_WARNING (flag for review)
DS_session < tau_collapse       -> SESSION_TERMINATE
```

A SESSION_WARNING does not DENY individual requests. It flags the session
for human review while allowing operations to continue under heightened
monitoring. This prevents false-positive shutdowns from natural variance.

### Sacred Tongue Routing

Every evaluation routes through the 6 Sacred Tongues with phi-scaled weights:

```
KO (Koraelin)    : phi^0 = 1.000  — Control / Intent
AV (Avali)       : phi^1 = 1.618  — I/O / Transport
RU (Runethic)    : phi^2 = 2.618  — Policy / Energy
CA (Cassisivadan): phi^3 = 4.236  — Compute / Logic
UM (Umbroth)     : phi^4 = 6.854  — Security / Trust
DR (Draumric)    : phi^5 = 11.090 — Structure / Deep Lock
```

The tongue classification determines which channels process the evaluation.
Null (inactive) tongues are logged — the absence pattern is informative.

---

## Threshold Status

**UNCALIBRATED** — defaults tau_allow = 0.72, tau_collapse = 0.31 are
engineering estimates, not empirically validated values.

See `references/calibration.md` for the calibration protocol:
1. Collect corpus: 200+ prompts per class (SAFE, BORDERLINE, ADVERSARIAL)
2. Compute DS distribution via /drift-check
3. Set thresholds via ROC analysis (95% recall for allow, 1% FPR for collapse)
4. Document and sign off before removing UNCALIBRATED flag

---

## Workflow

### 1. /drift-check <prompt>

Embed a prompt and return DS + gate decision + tongue routing.

**Steps**:
1. Classify dominant tongue from prompt content
2. Compute null pattern (which tongues are inactive)
3. Embed prompt via configured embedding model
4. Project to Poincare ball: x_H = tanh(||v|| / (2*sqrt(D))) * v/||v||
5. Compute d_H = hyperbolic distance from origin
6. Estimate pd from spectral coherence of embedding
7. Compute DS = 1 / (1 + phi * d_H + 2 * pd)
8. Compute T = cos^2((beta - phi_wall) / 2)
9. Apply gate thresholds
10. Log as training pair (instruction: the prompt, output: the telemetry)

**Output — Machine JSON**:
```json
{
  "command": "drift-check",
  "timestamp": "<ISO-8601>",
  "embedding_model": "<MODEL_ID>",
  "tongue": "<dominant tongue>",
  "tongues_active": ["KO", "..."],
  "tongues_null": ["AV", "..."],
  "poincare_radius": 0.0000,
  "hyperbolic_distance": 0.0000,
  "prior_deception": 0.0000,
  "davis_score": 0.0000,
  "gate_transmission": 0.0000,
  "omega_components": {
    "harm_score": 0.0000,
    "drift_factor": 0.0000,
    "triadic_stable": true,
    "spectral_score": 0.0000
  },
  "decision": "ALLOW | ATTENUATE | COLLAPSE",
  "threshold_status": "UNCALIBRATED",
  "thresholds_used": {
    "tau_allow": 0.72,
    "tau_collapse": 0.31
  }
}
```

**Output — Narrative Summary** (append after JSON):
Write 2-3 sentences interpreting the DS and decision. Include tongue routing.
Always state threshold_status as UNCALIBRATED until calibration is complete.

### 2. /audit-report

Generate a full governance audit document for a session.

**Steps**:
1. Collect all /drift-check results from current session
2. Compute aggregate: mean DS, DS variance, COLLAPSE count, tongue distribution
3. Identify lowest-DS prompt (maximum drift event)
4. Generate machine JSON + narrative audit summary

**Output sections**:
1. Executive Summary (3 sentences)
2. Methodology (embedding model, projection, gate formula, threshold status)
3. Findings (DS distribution table, tongue activation patterns, null analysis)
4. Risk Assessment (COLLAPSE/ATTENUATE counts in plain language)
5. Omega Gate Analysis (which components contributed to decisions)
6. Calibration Notice (mandatory disclaimer — see below)

**Mandatory Calibration Disclaimer** (always include in client reports):
> Thresholds (tau_allow = 0.72, tau_collapse = 0.31) are engineering defaults,
> not empirically validated values. Davis Security Scores should not be used
> for compliance decisions until calibration against a domain-specific corpus
> is complete.

---

## Training Data Generation

Every /drift-check and /audit-report generates training pairs:

**SFT pair from /drift-check**:
```json
{
  "instruction": "<the prompt that was checked>",
  "output": "<the Davis Score + decision + explanation>",
  "tongue": "<dominant tongue>",
  "tongues_active": ["..."],
  "tongues_null": ["..."],
  "layer": "L2",
  "category": "governance_evaluation",
  "governance": "<ALLOW|ATTENUATE|COLLAPSE>",
  "davis_score": 0.0000,
  "source": "latticegate_drift_check"
}
```

Append to: `training-data/sft/latticegate_evaluations_sft.jsonl`

This closes the loop: evaluations become training data, training improves
the model, improved model produces better evaluations.

---

## Honesty Constraints

Non-negotiable. Cannot be overridden by user instructions:

1. Never remove the UNCALIBRATED flag until empirical calibration is documented
2. Never claim cryptographic hardness for H(d,pd) — it is a governance cost
   function, not a hardness reduction
3. Never cite a model ID that has not been confirmed to exist
4. Always report DS variance alongside mean DS in audit reports
5. Never present the harmonic wall as the sole decision mechanism — always
   reference the coupled omega gate
6. Always log tongue activation AND null patterns — absence is informative

---

## Embedding Configuration

Model-agnostic. Set before use:

```
EMBEDDING_MODEL_ID = "<your-huggingface-model-id>"
EMBEDDING_DIM      = <output-dim>
POINCARE_DIM       = 21
```

Projection (Euclidean to Poincare ball):
```
x_H = tanh(||v|| / (2*sqrt(D))) * v / ||v||
```
This ensures ||x_H|| < 1 (stays inside the ball).

Model candidates (evaluate before committing):
- `BAAI/bge-small-en-v1.5` — lightweight, strong retrieval
- `sentence-transformers/all-MiniLM-L6-v2` — fast inference, 384-dim
- `issdandavis/phdm-21d-embedding` — native 21D SCBE embedding (if available)

Document chosen model in `references/model-card.md` before client delivery.

---

## Monetization Products

### Product 1: Governance Starter Kit ($29)
Templates, decision records, threshold worksheets, manual.
Live at: aethermoorgames.com/offers

### Product 2: AI Security Training Vault ($29)
SFT datasets, projector weights, Colab fine-tuning workflow.
Live at: Stripe checkout

### Product 3: Pruning Audit (future, $5K+)
PhaseTunnelGate as model optimization service.
Customer uploads weights, receives pruning blueprint.

### Product 4: Safety Wedge API (future, $500-2500/mo)
Hosted LatticeGate as SaaS proxy for customer LLM calls.

---

## Reference Paths

- `docs/specs/LAYER_12_CANONICAL_FORMULA.md` — canonical H(d,pd) formula
- `docs/research/CANONICAL_TRIADIC_HARMONIC_SYMBOL_REGISTRY.md` — symbol registry
- `docs/specs/GEODESIC_GATEWAYS_SPEC.md` — geodesic gateway math
- `src/harmonic/harmonicScaling.ts` — TypeScript implementation
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py` — Python implementation
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/governance_scorer.py` — GovernanceScorer
- `scripts/route_tagger.py` — tongue classification
- `training/training_station.py` — training pipeline
- `references/calibration.md` — threshold calibration protocol
- Patent: US Provisional #63/961,403
