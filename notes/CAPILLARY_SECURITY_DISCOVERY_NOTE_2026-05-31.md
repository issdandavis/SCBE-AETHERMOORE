# Capillary Security: Discovery Note

**Date:** 2026-05-31  
**Status:** Internal — not a core proposal claim  
**Author:** Issac Davis / SCBE-AETHERMOORE  

---

## Summary

Existing SCBE components, when wired together, already support a coherent "capillary security" interpretation of inter-system data governance. This note maps the concept to current code, identifies what was missing (one unwired connection), and flags the MATHBAC proposal abstraction.

---

## The Concept

*Capillary security* models inter-system data movement as vascular flow: data passes between systems through narrow, high-resistance channels (capillaries), and each crossing is subject to a pressure-based gate. The gate does not stop all flow — it sets the resistance proportional to the measured risk of the payload. High-risk payloads face exponentially greater resistance; benign payloads pass with near-zero overhead.

The hyperbolic geometry makes this precise:

- **Capillary pressure** = Poincaré-ball norm of the payload's state vector → `‖ψ‖`
- **Gate resistance** = harmonic wall cost `H(d_H, pd) = 1/(1 + φ·d_H + 2·pd)` — low near origin (safe), near zero at boundary (adversarial)
- **Membrane permeability** = `tri_lattice_membrane.membrane_permeability` in `src/storage/tri_lattice_membrane.py`
- **Vascular fingerprint** = per-tongue pathway heatmap from `src/video/dye_injection.py:DyeInjector`

The "sub-dermal" layer is the L1–L14 composed operator `T`. Data flowing between systems passes through `T` before handoff authorization; the hyperbolic state update is the sub-dermal trace of that crossing.

---

## Components Already Present

| Role | File | Key member |
|---|---|---|
| Boundary scanner (computes capillary pressure) | `agents/hyperbolic_scanner.py` | `scan_boundary_state()` |
| Inter-system gate (policy decision per crossing) | `agents/kernel_antivirus_gate.py` | `evaluate_kernel_event()`, `geometry_norm` field on `KernelEvent` |
| Membrane routing (feedback on rejection) | `src/storage/tri_lattice_membrane.py` | `TriLatticeMembrane`, `membrane_permeability`, `_sphere_feedback()` |
| Vascular fingerprint tracer | `src/video/dye_injection.py` | `DyeInjector.trace_vascular_fingerprint()` |
| Inter-layer handoff packet | `src/m4mesh/canonical_bridge.py` | `run_governance_pipeline()` — 21D canonical state with `harmonic` and `radial` fields |
| Immune cell state | `agents/kernel_antivirus_gate.py` | `_cell_state()` — HEALTHY / PRIMED / INFLAMED / NECROTIC |

---

## What Was Missing (Now Fixed)

`KernelEvent.geometry_norm` defaulted to 0.0. The gate used it in the suspicion blend (`0.15 * geometry_norm`) but no code auto-populated it from the hyperbolic scanner. Callers had to supply it manually or it was silently zero — a dead weight in the formula.

**Fix committed (2026-05-31):**

- Added `geometry_norm_from_state(state_vector)` — thin adapter that returns just the Poincaré-ball norm.
- Added `evaluate_kernel_event_with_state(event, state_vector)` — auto-calls the scanner and replaces `geometry_norm` on the event before evaluation. Caller-supplied `geometry_norm` (without state_vector) still works unchanged.
- Created `hydra/turnstile.py` — the missing stub that `kernel_antivirus_gate` and `extension_gate` both import; implements antibody-load accumulation and honeypot escalation.
- Regression tests: `tests/agents/test_kernel_antivirus_gate_capillary.py` — 4 cases.

---

## What the Wired System Now Does

When a system handoff occurs with a numeric payload:

```
payload_state_vector
    → hyperbolic_scanner.scan_boundary_state()    # compute d_H and norm
    → evaluate_kernel_event_with_state()           # scanner norm → geometry_norm
    → suspicion blend: 0.50·scan_risk + 0.35·integrity_risk + 0.15·geometry_norm
    → _base_decision() → ALLOW / QUARANTINE / ESCALATE / DENY
    → resolve_turnstile() → immune cell update (antibody_load, membrane_stress)
    → KernelGateResult: decision, cell_state, kernel_action
```

The 15% weight of `geometry_norm` in the suspicion blend means:
- A completely benign payload (norm ≈ 0.05) contributes ≈ 0.0075 to suspicion — negligible
- A near-boundary payload (norm ≈ 0.95) contributes ≈ 0.14 to suspicion — sufficient to push an otherwise borderline event from ALLOW to QUARANTINE

---

## Relationship to SCBE's L12 Harmonic Wall

The `geometry_norm` in the gate is the same Poincaré-ball norm that L12's harmonic wall uses:

```
H(d_H, pd) = 1 / (1 + φ·d_H + 2·pd)
```

The gate's suspicion blend is the *kernel-layer* equivalent of L12: it scores the same geometry but at a different layer of the stack (kernel event processing rather than the 14-layer pipeline's harmonic wall). Together they implement a multi-layer geometric gating strategy:

- **L12 harmonic wall**: scores agent communication acts within the pipeline
- **Kernel gate**: scores inter-system data handoffs at the OS boundary
- **Tri-lattice membrane**: scores storage routing decisions across lattice backends

All three use the same underlying hyperbolic norm. The resistance function differs per layer but the geometric substrate is shared.

---

## MATHBAC Proposal Abstraction

For the MATHBAC proposal, the safe abstraction is:

> "The trust-weighted directed Laplacian `L_H(G_t)` with edge weights `H(d_H, pd)` applies to the inter-agent protocol graph exactly as the kernel gate applies to inter-system data handoffs — geometric resistance proportional to state drift, accumulated immune memory via antibody load, and coherence tracked via λ₂."

Do not use the vascular metaphor in the proposal. Use: "trust-weighted directed Laplacian over the inter-system handoff graph." The capillary interpretation is the conceptual bridge, not the formal claim.

---

## Next Steps (If Developing Further)

1. Wire `evaluate_kernel_event_with_state` into the M4 mesh canonical bridge's handoff path so every inter-subsystem packet is auto-scanned.
2. Expose `dye_injection.DyeInjector` as a diagnostic tool that traces which capillary paths a given payload took through the 14 layers.
3. Consider whether `tri_lattice_membrane.membrane_permeability` should be dynamically set from the gate's `geometry_norm` output (closing the full feedback loop).
