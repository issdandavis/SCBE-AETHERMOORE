# CLARA Program Manager Research — Benjamin Grosof (Public Sources)

**Purpose**: Provide proposal-writing guidance aligned with CLARA’s public framing and the PM’s stated interests, without inventing requirements or overfitting to rumor. Use this as a “messaging lint” during final edits of the Technical Volume.

**Last updated**: 2026-04-07

---

## 1) Canonical public sources (primary)

- DARPA CLARA program page (program framing + goals): https://www.darpa.mil/research/programs/clara
- DARPA opportunity page (DARPA-PA-25-07-02 listing): https://www.darpa.mil/work-with-us/opportunities/darpa-pa-25-07-02
- DARPA PM bio (Benjamin Grosof): https://www.darpa.mil/about/people/benjamin-grosof
- DARPA CLARA FAQ PDF (milestones / hackathon cap constraints, etc.): https://www.darpa.mil/sites/default/files/attachment/2026-02/program-clara-faq.pdf
- DARPA Disruptioneering listing (deadline confirmation for DOs): https://www.darpa.mil/work-with-us/disruptioneering
- Coherent Knowledge team bio (Grosof background in rule systems + standards): https://coherentknowledge.com/team/

---

## 2) What CLARA says it wants (use their words)

From DARPA’s public CLARA framing:
- CLARA is explicitly positioned against “tack-on AR” approaches: AR and ML should be **tightly integrated** and aimed at **high assurance**.
- CLARA calls out **logic programs** (alongside Bayesian and neural nets) as in-scope building blocks for compositional ML+AR.
- Key expected properties emphasized publicly: **verifiability**, **logical explainability**, and **computational tractability**.

Implication for SCBE narrative:
- Keep “AR-in-the-guts” as the spine: invariants + rule export + trace artifacts that are *produced during inference*, not post-hoc.

---

## 3) Benjamin Grosof’s stated interests (what to lean into)

From DARPA bio + Coherent Knowledge bio:
- Deep combination of **logical knowledge representation/reasoning with ML and NLP** (neuro-symbolic).
- **Scalability** and tractability of reasoning (his wording includes scalability and trustworthiness / critical thinking).
- **Explainability / interpretability** (highly explainable decision support).
- Applications spanning defense operations/planning, policy/legal, supply chain, healthcare, etc.

Implication for SCBE narrative:
- Emphasize **exportable reasoning artifacts** (defeasible rule traces) and **hierarchical explainability** (bounded unfolding).
- Emphasize **tractability** (fixed-dimensional bottleneck + bounded checks) and avoid claiming “general formal proof of safety.”

---

## 4) Proposal vocabulary: “use” vs “avoid” (practical guidance)

### Use (aligned with CLARA framing)
- compositional / composability
- tightly integrated ML+AR
- verifiable artifacts / machine-checkable invariants
- tractable / scalable
- logic programs (as an export format for governance decisions)
- explainable / interpretable / hierarchical explainability
- concept bottleneck (if used, define it plainly and show it bounds explanation depth)
- evidence, traceability, replayable decision logs (IV&V-friendly)

### Avoid (unless the solicitation explicitly asks for it)
- “mathematically proves AI is safe” (too absolute)
- buzzwords that read off-mission (e.g., blockchain)
- “quantum” as a primary pitch axis (unless clearly bounded to implementation security needs, and only if solicitation language supports it)

---

## 5) One-paragraph “Grosof-aligned” framing (drop-in helper)

Use this as a style template (not verbatim copy):

> “SCBE-AETHERMOORE is a compositional ML+AR governance layer designed to provide high-assurance agent behavior through tightly integrated inference-time constraints. ML components project raw interaction signals into a small, interpretable concept bottleneck; AR components evaluate machine-checkable invariants and export tiering decisions as defeasible logic-style traces. This yields scalable, tractable enforcement with replayable evidence artifacts suitable for IV&V and hackathon evaluation.”

---

## 6) Deadline sanity (don’t let the website mismatch trip you)

DARPA web pages may show different deadlines across:
- the CLARA program page,
- the Disruptioneering listing,
- and the SAM.gov opportunity record (including amendments).

**Rule**: treat the SAM.gov opportunity record (including amendments) as source-of-truth for the submission deadline and keep all internal documents consistent with that. If DARPA pages disagree, capture a screenshot/PDF of the opportunity record you are submitting against for your own records.

Practical note (public): DARPA’s Disruptioneering listing shows **DARPA-PA-25-07-02** with a **Deadline: April 17, 2026**. Treat that as a strong corroborating signal, but still reconcile against the SAM.gov opportunity record + amendments before final submission.
