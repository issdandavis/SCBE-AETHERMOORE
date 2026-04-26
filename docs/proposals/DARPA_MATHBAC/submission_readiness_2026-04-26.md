# MATHBAC Submission Readiness - 2026-04-26

**Solicitation:** DARPA-PA-26-05, MATHBAC TA1  
**Current status:** Drafted, not submitted  
**Primary objective:** move from draft text to a submission-grade packet with diagrams, verified channels, and explicit claim boundaries.

## Submission State

| Item | Status | Evidence / path |
|---|---|---|
| Abstract draft | Ready for review | `artifacts/mathbac/MATHBAC_ABSTRACT_DRAFT_v1_2026-04-26.md` |
| Abstract PDF | Rendered locally | `artifacts/mathbac/MATHBAC_ABSTRACT_v1.pdf` |
| Email body | Drafted, not sent | `artifacts/mathbac/MATHBAC_ABSTRACT_EMAIL_DRAFT_2026-04-26.md` |
| Visual appendix | Drafted locally | `artifacts/mathbac/MATHBAC_VISUAL_APPENDIX_2026-04-26.md` |
| CLARA status | Submitted / pending review | `DARPA-PA-25-07-02-CLARA-FP-033`, finalized 2026-04-13 08:04 PM ET |
| BAAT account | User says account exists | Needs no new account action unless portal access fails |

## Blocking Items Before Send

- [ ] Verify official abstract channel from PA-26-05 attachments.
- [ ] Confirm whether abstract is email-only, BAAT upload, or both.
- [ ] Confirm subject line, attachment naming, and page-limit language.
- [ ] Strip internal checklist from the abstract before transmission.
- [ ] Visually inspect the final PDF after any diagram or formatting changes.
- [ ] Save send receipt or portal receipt into the private proposal packet.

## Claim Discipline

- Proven: sealed-blind recovery, KL capacity estimates, bit-identical equivariance, and two-stack convergence under the named harnesses.
- Observed: structured protocol behavior across the current SCBE/DAVA surfaces.
- Hypothesis: geometric cost scaling and broader cross-domain transfer.
- Forbidden framing: "proved universally," "general AI safety solved," or any claim that the current harness covers all agentic systems.

## Figure 1: Protocol Substrate

```mermaid
flowchart LR
    A[Agent A message] --> B[Six-tongue tokenizer]
    B --> C{Tongue boundary crossing}
    C -->|right path| D[Phi-weighted semantic carry]
    C -->|wrong path| E[Fail to noise]
    D --> F[Poincare ball state]
    F --> G[Harmonic wall metric]
    G --> H{L13 governance gate}
    H -->|stable and inside wall| I[Agent B receives governed message]
    H -->|unstable or outside wall| J[Quarantine and receipt]
    E --> J
    G --> K[MEE]
    G --> L[ACV]
    F --> M[CDPTI]
    B --> N[PIS]
```

Use this figure when the reviewer needs to see how tokenizer geometry, harmonic-wall evaluation, and governance are one system instead of three bolted-on claims.

## Figure 2: Evidence Spine

```mermaid
flowchart TB
    A[Existing harnesses] --> B[Sealed-blind boundary recovery]
    A --> C[KL channel capacity]
    A --> D["Mobius / PSU(1,1) equivariance"]
    A --> E[Two-stack convergence]
    B --> B1[24 / 24 labels, p <= 3e-4]
    C --> C1[Realm: 1.5761 b/t, 99.4% of log2 3]
    C --> C2[Regime: 2.9818 b/t, 99.4% of log2 8]
    D --> D1["Bit-identical k-means++"]
    E --> E1["DAVA/Rust x SCBE/Python on 5-of-6 surface"]
    B1 --> F[TA1 claim: protocol geometry is measurable]
    C1 --> F
    C2 --> F
    D1 --> F
    E1 --> F
    F --> G[Phase I: formalize, replicate, falsify]
```

Use this figure when the reviewer asks what evidence exists today. It keeps the packet evidence-led and prevents drift into unsupported architecture language.

## Figure 3: Phase I Workplan

```mermaid
gantt
    title MATHBAC TA1 Phase I Workplan
    dateFormat  YYYY-MM-DD
    axisFormat  %b %Y
    section Month 0-2
    Compliance lock and packet setup        :a1, 2026-09-15, 45d
    Evidence harness freeze                 :a2, 2026-09-15, 45d
    section Month 2-6
    Formal protocol substrate specification :b1, after a1, 90d
    Living Metric implementation            :b2, after a2, 90d
    section Month 6-10
    Sealed-blind replication                :c1, after b1, 90d
    Cross-stack convergence study           :c2, after b2, 90d
    section Month 10-14
    Upper-bound proof attempt and falsifiers :d1, after c1, 90d
    Program-facing evaluator package        :d2, after c2, 75d
    section Month 14-16
    Final report and Phase II bridge         :e1, after d1, 45d
    Submission-grade artifacts               :e2, after d2, 45d
```

Use this figure in the full proposal work-plan section. It is probably too large for the two-page abstract unless the abstract is reformatted around a single figure.

## Next Operator Steps

1. Pull or open the PA-26-05 attachments and verify the abstract channel.
2. Decide whether the two-page abstract includes Figure 1 or stays text-only.
3. Produce a one-page technical appendix from Figures 1 and 2 if the channel allows attachments beyond the abstract.
4. Run a final overclaim pass against the claim-discipline section above.
5. Stage the final email or portal package, then wait for explicit user authorization before sending.
