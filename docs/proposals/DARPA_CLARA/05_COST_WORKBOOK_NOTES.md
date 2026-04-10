# DARPA CLARA TA1 — Cost Workbook Notes (Do Not Invent Numbers)

**Purpose**: A fill guide for the DARPA CLARA TA1 cost workbook(s) that keeps the proposal consistent with the technical volume and avoids unforced audit issues. This file is intentionally a *mapping + checklist*; it should not contain sensitive banking info or personal identifiers.

**Solicitation**: DARPA-PA-25-07-02 (CLARA)  
**Deadline**: April 17, 2026, 4:00 PM ET  
**Total cap**: $2,000,000 (Phase 1 + Phase 2 combined)  

---

## 1) Cost posture targets (high-level)

- Keep a clear narrative link between **each major cost line** and a **Phase milestone deliverable** from `docs/proposals/DARPA_CLARA/04_TECHNICAL_VOLUME_DRAFT.md`.
- If the solicitation reserves **~$60K hackathon incentive/attendance**, ensure:
  - the workbook totals remain under cap, and
  - non-hackathon costs stay within any stated solicitation constraint.

---

## 2) Phase mapping (what each bucket “buys”)

### Phase 1 — Feasibility (inferencing only)
Primary cost drivers should map to:
- M1: standardized benchmark integration + reproducible runner scripts
- M2: invariant artifact export (trace schema + expanded tests)
- M3: defeasible rule export and bounded-unfolding explanation traces
- M4: hackathon readiness kit (container + deterministic logs)

### Phase 2 — Proof of Concept (inferencing + training)
Primary cost drivers should map to:
- M5: training-time adaptation with artifact preservation + rollback
- M6: multi-domain adaptation with sample-complexity reporting
- M7: hackathon iteration + threshold tuning + trace interpretability

---

## 3) Budget line items (template)

Use the workbook’s categories, but keep the internal decomposition consistent:

- Personnel / Labor
  - PI (core pipeline + proposal deliverables + integration)
  - Optional: 1 supporting researcher/engineer (evaluation + artifact export + automation)
- Compute
  - cloud GPU/CPU time for evaluation and (Phase 2) adaptation runs
  - storage + egress only if required for reproducibility deliverables
- Travel
  - CLARA performer meetings / hackathons (if required)
- Materials / Software
  - minimal tools needed for reproducibility and secure packaging
- Subcontractor(s) (if used)
  - keep statement of work tight: e.g., external IV&V support, formal methods consultation, or evaluation harness support
- Indirect / Overhead
  - if using de minimis, document the basis consistently across volumes

---

## 4) Consistency checks (common audit traps)

- Do not budget “research staff” if deliverables are primarily software artifacts; name roles to match deliverables (evaluation, engineering, artifact export, IV&V).
- Ensure claimed runtime/complexity in the tech volume matches compute budget reality (don’t claim microsecond latencies while budgeting massive compute unless you explain training vs inference).
- If you list an open-source deliverable expectation, keep licensing statements consistent (avoid mixing license claims across documents).

---

## 5) What to paste into the cost narrative (short boilerplate)

Use language that ties directly to CLARA:
- “Budget supports compositional ML+AR deliverables: standardized evaluation, verifiable invariant artifacts, and defeasible rule exports with bounded unfolding depth.”
- “Phase 1 focuses on inference-time composition and IV&V-ready evidence; Phase 2 adds limited training-time adaptation with artifact preservation and rollback.”

