# Evaluation Contract — v1.0

**Status:** Draft — proposed. Not yet conformed by any harness.
**Owner:** Issac D. Davis
**Date:** 2026-04-20
**Purpose:** A single stable JSON envelope that every SCBE benchmark / evaluation script emits, so that (a) Kaggle, CI, and local runs are interchangeable execution substrates; (b) governance artifacts have a uniform audit shape; (c) metric families (including the Phase-I Deliverable #4 `substrate_consistency` block) compose additively without breaking downstream readers.

This spec is the **contract**, not the metric catalog. Individual benchmarks own their metric semantics; this file owns the envelope and the registry of metric-family names.

---

## 1. Scope

### 1.1 In scope

- Top-level JSON envelope emitted by every benchmark script.
- Required fields, types, and semantics.
- Registered metric-family names and their shape.
- Gate-evaluation block.
- Failure-reporting block.
- Artifact-pointer block.
- The `raw` passthrough slot for pattern-specific native output.

### 1.2 Out of scope

- The internal structure of any one metric family's scoring logic.
- The specific adversary suite or prompt set.
- Substrate (Kaggle / CI / local) bootstrap mechanics.

### 1.3 Non-goals

- Forcing existing harnesses to drop their native output shape. The envelope is additive: the native report goes in `raw`.
- Mandating a specific serializer. JSON only; ordering not significant except as specified.

---

## 2. Envelope schema (v1)

```jsonc
{
  "contract_version": "v1",           // string, required, literal "v1"
  "benchmark_id":     "string",       // required, stable, kebab or snake (e.g. "tongue-challenge-harness")
  "run_id":           "string",       // required, UUID or ISO-8601 + suffix
  "timestamp":        "ISO-8601 UTC", // required, "Z" suffix
  "env": {                            // required; all fields required unless noted
    "git_sha":   "string | null",     // HEAD sha when clean, commit sha otherwise
    "git_dirty": true,                // bool; true if uncommitted changes
    "python":    "3.11.x",            // interpreter version
    "torch":     "2.x.y | null",      // null if torch not used
    "gpu":       "string | null",     // e.g. "T4", "P100", null for CPU-only
    "platform":  "linux | darwin | windows | kaggle | colab"
  },
  "pass":    true,                    // required bool; logical AND across all gates[].pass
  "metrics": { /* family blocks, see §3 */ },
  "gates":   [ /* see §4 */ ],
  "failures":[ /* see §5 */ ],
  "artifacts": {                      // required; paths relative to run working dir or absolute
    "geoseal_trace":   "string | null",
    "stdout_log":      "string | null",
    "raw_report":      "string | null"
  },
  "raw": { /* pattern-specific native output, see §6 */ }
}

```

### 2.1 Required vs optional

- Required fields must be present and non-null except where the schema explicitly allows `null`.
- `metrics`, `gates`, `failures`, and `raw` may be empty (`{}` or `[]`) but must be present.
- Unknown top-level fields MUST be preserved by readers but SHOULD NOT be introduced by writers without bumping `contract_version`.

### 2.2 Versioning

- `contract_version` is a literal. v1 readers reject any other value.
- Additive changes (new registered metric families, new optional env fields) do NOT bump the version.
- Breaking changes (renamed/removed required fields, changed semantics) bump to v2 and keep v1 readers for at least one release.

---

## 3. Metric families

Each key under `metrics` is a **family name** drawn from the registry in §3.2. The family's value is a block owned by that family's spec.

### 3.1 Registration rules

- A family is registered here before any harness emits under that name.
- Families are namespaced at the top level of `metrics` — no nested families without explicit spec.
- Family shape is the responsibility of the family's spec; this document only lists the names.

### 3.2 Registry

| Family | Status | Spec | Summary |
|--------|--------|------|---------|
| `transport_invariance` | proposed | this file §7.1 | Bijectivity of Sacred-Tongues transport (self, pairwise, multi-hop). |
| `routing_determinism` | proposed | this file §7.2 | Keyword-routing and forced-route idempotence. |
| `substrate_consistency` | proposed | this file §8 — **Phase-I Deliverable #4** extension | C₁/C₂/C₃ under tongue re-expression with four acceptance gates. |
| `kl_capacity` | proposed | future | Bootstrap KL channel capacity with CIs. |
| `permutation_separation` | proposed | future | Marginal-preserving permutation tests with one-sided upper p bound. |
| `structural_quality` | proposed | future | Pattern-B aggregate rates (by_stage, by_map, by_tongue). |
| `code_eval` | proposed | future | Pattern-C per-record eval summaries. |

A benchmark MAY emit zero or more families; the set of families it emits is part of its identity and should be stable across runs.

---

## 4. Gates block

```jsonc
"gates": [
  {
    "id":        "regime_invariance_aggregate", // stable string
    "metric":    "substrate_consistency.regime_invariance.aggregate",
    "op":        ">=",                  // one of: ">=", "<=", "==", "!=", ">", "<"
    "threshold": 0.99,                  // number, string, or null — see §4.3
    "observed":  1.0,                   // number or string, whatever the metric emits
    "pass":      true,                  // bool or null — see §4.3
    "hard_stop": false,                 // bool; see §4.1
    "informational": false              // bool; see §4.3
  }
]

```

### 4.1 Hard-stop semantics

A gate with `"hard_stop": true` that fails forces the envelope's top-level `pass` to `false` **regardless** of other gates. The canonical use case is the per-tongue floor in `substrate_consistency` (see §8).

Soft gates (`hard_stop: false`) contribute to `pass` via the AND of all gate outcomes; hard-stop gates additionally short-circuit.

### 4.2 Evaluation order

- Gates are evaluated in array order. Order is informational only — `pass` does not depend on order.
- A gate references a metric by dotted path into the `metrics` block. Dereference failure is a `gate_unresolved` failure (§5).

### 4.3 Informational gates (null threshold)

A gate with `"informational": true` is **emitted for audit but excluded from the top-level `pass` AND**. This is the canonical encoding for a metric that is tracked at v1 but whose threshold is not yet calibrated (e.g., `embedding_lipschitz_p95` pending Phase-I measurement of ε_target).

Rules:

1. **`threshold` MAY be `null`** iff `"informational": true`. A non-informational gate MUST have a non-null threshold.
2. **`pass` MUST be `null`** when `"informational": true`. The observed value is still recorded in `observed`.
3. **Informational gates do NOT contribute to top-level `pass`.** The AND in §9 clause (4) skips any gate where `informational == true`.
4. **Informational gates MUST NOT set `"hard_stop": true`.** A gate that is not enforced cannot short-circuit a run.
5. **Conformance is per-emitted-gate.** A harness MAY elect not to emit an informational gate at all; if emitted, the shape above is required.
6. **Promotion to enforced.** When Phase-I (or any subsequent milestone) fixes a threshold, the gate flips to `"informational": false` with a non-null `threshold` and a boolean `pass`. This is an additive change — no `contract_version` bump.

A required gate whose observation currently lacks a calibrated threshold is therefore encoded as informational — the "required but not enforced" ambiguity is resolved by making non-enforcement explicit in the gate object itself.

---

## 5. Failures block

```jsonc
"failures": [
  {
    "kind":    "gate_failed | gate_unresolved | axiom_violation | transport_mismatch | schema_invalid | runtime_error",
    "gate_id": "string | null",         // required for gate_*, else null
    "metric":  "string | null",         // dotted path if applicable
    "detail":  "string",                // human-readable
    "data":    { /* optional structured payload */ }
  }
]

```

Failures are additive: a run MAY report `pass: false` with zero failures (back-compat for legacy pattern-A output) but SHOULD enumerate each failed gate.

---

## 6. Raw passthrough (`raw`)

The `raw` block preserves the pattern-specific native output of the underlying harness, verbatim. This lets the envelope be additive over existing reports without rewriting them.

Three patterns are recognized:

- **Pattern A** (binary-gate, `tongue_challenge_harness`): `raw` contains `{overall_ok, checks, summary}`.
- **Pattern B** (aggregate-breakdown, `polly_structural_benchmark`): `raw` contains `{summary, by_stage, by_map, by_tongue}`.
- **Pattern C** (per-record, `scbe_code_eval`): `raw` contains an array of `EvalRecord` dataclasses.

Readers MUST NOT rely on `raw` shape. All decisions flow through `metrics`, `gates`, and `failures`.

---

## 7. Core metric families (v1 shipped)

### 7.1 `transport_invariance`

Scope: Sacred-Tongues `encode_bytes` / `decode_tokens` bijectivity.

```jsonc
"transport_invariance": {
  "self":      { "total": 18, "failures": 0, "per_tongue": { "KO": {"total": 3, "failures": 0}, ... } },
  "pairwise":  { "total": 108, "failures": 0, "pairs": { "KO->AV": {"total": 3, "failures": 0}, ... } },
  "multi_hop": { "total": 18,  "failures": 0, "chains": { "KO->AV->RU->KO": {"total": 3, "failures": 0}, ... } },
  "stress":    { "text_payloads": 10, "binary_payloads": 36, "text_total": 360, "binary_total": 1296, "failures": 0 }
}

```

Canonical gate: `transport_invariance.*.failures == 0` across all sub-blocks, hard_stop.

### 7.2 `routing_determinism`

Scope: keyword routing, forced-route idempotence, route determinism.

```jsonc
"routing_determinism": {
  "keyword_routing":        { "total": 18, "failures": 0 },
  "route_determinism":      { "total": 21, "failures": 0 },
  "forced_route_idempotence": { "total": 18, "failures": 0 }
}

```

Canonical gates: `routing_determinism.*.failures == 0`, hard_stop.

---

## 8. `substrate_consistency` — Phase-I Deliverable #4 extension

This family is the evaluation-contract realization of `docs/specs/SCBE_TECHNICAL_PACKET_v1.md` §9.4. It measures the three-part consistency criterion (C₁, C₂, C₃) for a tongue-transport map `T` drawn from the bijectively-verified harness family (§7.1).

### 8.1 Criterion recap

- **C₁** — regime invariance under re-expression: `𝟙[classify(K) = classify(T(K))]`.
- **C₂** — embedding Lipschitz perturbation (measured target, not a proved bound at v1): `d_H(embed(K), embed(T(K)))`.
- **C₃** — cross-substrate agreement: `𝟙[regime_DAVA(T(K)) = regime_SCBE(T(K))]`.

### 8.2 Block shape

```jsonc
"substrate_consistency": {
  "n_prompts":   0,                     // integer, total K in sample
  "n_transports": 0,                    // integer, total T applied (distinct tongue maps × chains)
  "observer_versions": {                // required; pins the two observers
    "scbe_embed":  "string",            // git sha or release tag
    "scbe_l8_l13": "string",
    "dava_tier":   "string"
  },
  "regime_invariance": {
    "aggregate": 0.0,                   // float in [0, 1]
    "per_tongue": {                     // required; all six tongues
      "KO": { "n": 0, "rate": 0.0 },
      "AV": { "n": 0, "rate": 0.0 },
      "RU": { "n": 0, "rate": 0.0 },
      "CA": { "n": 0, "rate": 0.0 },
      "UM": { "n": 0, "rate": 0.0 },
      "DR": { "n": 0, "rate": 0.0 }
    },
    "per_tongue_floor": 0.0             // min over per_tongue[*].rate; surfaces hard-stop condition
  },
  "embedding_lipschitz": {
    "mean":      0.0,                   // float, d_H units
    "median":    0.0,
    "p95":       0.0,                   // the measured-bound target
    "p99":       0.0,
    "max":       0.0,
    "epsilon_target":  null,            // float or null; Phase-I reports the value, v1 does not pre-fix
    "per_tongue": {                     // p95 by source tongue
      "KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0
    }
  },
  "dava_scbe_agreement": {
    "rate": 0.0,                        // float in [0, 1]
    "per_regime_confusion": {           // required; L13 tiers
      "ALLOW":      { "ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0 },
      "QUARANTINE": { "ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0 },
      "ESCALATE":   { "ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0 },
      "DENY":       { "ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0 }
    }
  }
}

```

Rows of `per_regime_confusion` are SCBE's assignment; columns are DAVA's. The diagonal sum divided by the grand total is the agreement rate.

### 8.3 Required gates

| Gate `id` | Metric path | `op` | Threshold | `hard_stop` | `informational` | Rationale |
|-----------|-------------|------|-----------|-------------|-----------------|-----------|
| `regime_invariance_aggregate` | `substrate_consistency.regime_invariance.aggregate` | `>=` | `0.99` | `false` | `false` | Aggregate floor; soft-fails without per-tongue collapse. |
| `regime_invariance_per_tongue_floor` | `substrate_consistency.regime_invariance.per_tongue_floor` | `>=` | `0.99` | **`true`** | `false` | Any one tongue below 0.99 fails the benchmark — symmetric coverage is the point. |
| `embedding_lipschitz_p95` | `substrate_consistency.embedding_lipschitz.p95` | `<=` | `null` (v1) | `false` | **`true`** (v1) | Measured bound — `epsilon_target` is reported at Phase-I, not pre-fixed at v1. Encoded per §4.3 as informational: `threshold: null`, `pass: null`, excluded from top-level AND. Flips to `informational: false` with a numeric threshold once Phase-I lands its measurement. |
| `dava_scbe_agreement_rate` | `substrate_consistency.dava_scbe_agreement.rate` | `>=` | `0.95` | `false` | `false` | Cross-substrate agreement with per-regime confusion attached. |

### 8.4 Hard-stop clause (canonical language)

> A `substrate_consistency` run **fails** if any single tongue's `regime_invariance.per_tongue[*].rate` falls below `0.99`, regardless of aggregate performance. An aggregate invariance rate held up by five healthy tongues with one collapsed tongue is the failure mode the benchmark is built to catch.

### 8.5 Evidence registers

- **Proven (2026-04-20).** The transport layer `T` drawn from the §7.1 family is bijective on the actual `geoseal_cli` command surface, including UTF-8 subprocess I/O on Windows. The harness report records `9 / 9` checks passing and the CLI regression suite records `10` passing tests. The composition `G ∘ T⁻¹ ∘ T = G` is therefore true at the transport layer under the tested harness scope; `substrate_consistency` measures whether `G ∘ T` (with no decoder) agrees with `G` — i.e., whether SCBE's governance signal is substrate-invariant, not merely transport-invariant. This does **not** by itself prove full executable semantic bijection across code languages.
- **Designed.** The three-criterion measurement, the four gates, the hard-stop clause, the envelope shape above.
- **Open (Phase-I).** Measured ε_target. Full-tongue aggregate and per-tongue invariance rates. DAVA–SCBE concurrence rate with per-regime confusion matrix. Whether C₂ admits an analytical Lipschitz bound under the φ-weighted L3 and Möbius L7 or remains empirical-only at Phase-I scope.

---

## 9. Conformance

A benchmark script conforms to `evaluation_contract_v1` iff:

1. It emits a JSON document whose top level matches §2.
2. Every metric-family key under `metrics` is registered in §3.2 at the time of emission. **Conformance is per-emitted-family, not per-registry-family** — a harness is not required to emit every registered family, only to ensure each family it does emit is registered and well-shaped.
3. Every enforced (`"informational": false`) `gates[*].metric` dereferences successfully. Informational-gate dereference failures are reported as `gate_unresolved` under `failures` but do not break conformance.
4. Top-level `pass` equals the AND of `gates[*].pass` over all gates where `"informational": false`, and no gate with `"hard_stop": true` has `pass: false`. Gates with `"informational": true` are excluded from the AND and MUST have `pass: null` per §4.3.
5. The native pattern-A/B/C output (if any) is preserved under `raw`.

### 9.1 First conforming harness

`scripts/benchmark/tongue_challenge_harness.py` — scheduled as the first conforming emitter. Known-passing baseline from `artifacts/benchmark/tongue_challenge_harness_report.json` maps to:

- `metrics.transport_invariance` — populated from existing `transport_*` checks.
- `metrics.routing_determinism` — populated from `keyword_routing`, `route_determinism`, `forced_route_idempotence`.
- `raw` — the existing `{overall_ok, checks, summary}` document, verbatim.

No `substrate_consistency` block is emitted by the harness at v1; that family ships under the Phase-I Deliverable #4 workstream via a separate harness that wires both SCBE and DAVA observers.

---

## 10. Open items

- **ε_target determination.** Phase-I reports a measured p95; v1 cannot pre-fix a value without data. Gate is informational until Phase-I lands.
- **Observer version pinning.** `observer_versions` strings are required but not yet canonicalized — need a stable tagging convention across the SCBE repo and DAVA bundle.
- **Kaggle bootstrap.** The envelope is substrate-agnostic; the Kaggle wrapper that ingests emitted envelopes and uploads to the HF dataset repo is a separate deliverable, not part of this contract.

---

## Version history

| Date | Version | Change |
|------|---------|--------|
| 2026-04-20 | v1.0 (draft) | Initial envelope. `transport_invariance` + `routing_determinism` registered for first conforming harness. `substrate_consistency` registered as Phase-I Deliverable #4 extension with C₁/C₂/C₃ criterion, four gates, hard-stop clause on per-tongue regime collapse. |
