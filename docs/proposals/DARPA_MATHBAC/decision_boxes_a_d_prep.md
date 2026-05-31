# Decision Boxes A–D — Prep Memo for User Sign-Off

**Status:** Draft 2026-04-29 · **Audience:** Issac (decision owner) · **Purpose:** Unblock Vol I §4 drafting (punch-list #8) and Cost workbook scoping (punch-list #9). All four boxes block downstream compliance work — see `pa_26_05_compliance_checklist.md` Section VI.

**How to use this memo:** Reply with letters (e.g. "A=NMR, B=ChemBERTa+Qwen, C=Mixtral, D=as recommended"). One sentence of pushback per box if you want to deviate. If silence by 2026-05-06 (T-41 days), the recommended option ships in Vol I draft.

---

## Box A — Science subdomain (cascades to §2.4, §2.5, §2.7, §2.10, §3.1, §3.3, Vol I §6)

**Options:** (i) Cheminformatics / reaction prediction (USPTO baseline), (ii) **NMR spectroscopy / structure elucidation**, (iii) Materials discovery (perovskite/MOF subset), (iv) Mathematical theorem-proving (Lean/Mathlib).

**Recommendation: NMR spectroscopy.**

**Why this not that:** NMR is the only candidate explicitly named in PA-26-05 (line 305, Karplus equation), and SCBE's L9–L10 spectral/spin coherence layers map to NMR signal structure without requiring a new geometric primitive — the other three force us to invent domain glue we don't have shipped code for.

**Cost of deferring past 2026-05-06:** Vol I §4 cannot reference any concrete dataset, baseline, or evaluation harness; §6 milestones become hand-wavy; reviewer reads it as "didn't pick a problem."

---

## Box B — Small Science Model selection (blocks TA1-(3) latent-space access claims)

**Options:** (i) **ChemBERTa-77M** as primary SSM, (ii) Qwen2.5-Coder-0.5B-Instruct (already running locally), (iii) MolT5 (mol↔NL translation), (iv) Mistral-Small + chemistry SFT.

**Recommendation: ChemBERTa-77M as primary SSM + Qwen2.5-Coder-0.5B-Instruct as orchestrator.**

**Why this not that:** ChemBERTa is the only option with a published latent space accessible at HF Pro tier *and* a track record on chemical reasoning benchmarks; MolT5 is heavier and translation-specialized; Mistral-Small + SFT shifts months of training cost onto Phase I; Qwen alone has no chemistry pretraining. Pairing them lets us claim "small science model + general-purpose orchestrator" without needing a new training run.

**Cost of deferring:** TA1 mathematical challenge MC-1 ("Agents as Operators") cannot name a concrete operator domain in Vol I §4; cost workbook can't size GPU hours for SSM probing.

---

## Box C — TA1 baseline protocol model (blocks §2.10 baseline comparison)

**Options:** (i) **Mixtral-8x7B** (open MoE, latent-space accessible), (ii) DBRX-Instruct, (iii) Switch-Transformer-base.

**Recommendation: Mixtral-8x7B.**

**Why this not that:** Mixtral has the most active third-party benchmark coverage and runs on a single A10G or L4x1 (within HF Pro plan limits); DBRX needs more VRAM than HF Pro Jobs allow; Switch-Transformer-base is too small to be a credible "MoE protocol" baseline reviewers will accept.

**Cost of deferring:** §2.10 baseline-comparison table is empty; no quantitative claim possible against PA's "Mixture of Experts" framing.

---

## Box D — Two task families in chosen subdomain (blocks §2.5 task-family enumeration)

**Options (assuming Box A = NMR):** (i) **1H NMR → structure prediction**, (ii) **mixture-spectrum deconvolution**, (iii) (alternate) NMR → reaction-mechanism inference, (iv) (alternate) heteronuclear (13C/1H) coupled inversion.

**Recommendation: (i) 1H NMR → structure prediction + (ii) mixture-spectrum deconvolution.**

**Why this not that:** These two families share an evaluation harness (signal-vs-prediction loss) but exercise *different* operator regimes — single-source inversion (i) tests MC-1's operator framing on isolated agents, mixture deconvolution (ii) tests MC-2's protocol-graph framing on coupled agents. The alternates either fold into (i)/(ii) or require new ground-truth corpora we don't have.

**Cost of deferring:** §2.5 task families are unnamed; IV&V cannot construct evaluation cases; M3 metric calibration (per `proposer_added_metrics_v1.md`) loses its anchor.

---

## Cross-cutting note — what *isn't* on this memo

- **Decision Box A is the keystone.** B/C/D are easier to revise after A is fixed; A is the one that sets the cost-vs-evidence tradeoff for the whole proposal. If you want to change only one thing on this memo, change A.
- **None of these decisions touches the 14-layer pipeline, axioms, or operator-theoretic mapping** in `ta1_mathematical_challenges_v1.md`. That doc is subdomain-agnostic and stays valid under any A choice.
- **No HF publishes, no GH comments, no Kaggle pushes** are gated on this memo. This is purely Vol I §4–§6 + Vol II cost-workbook unblocker.

---

## Author trail

- 2026-04-29 — v1 draft, audience = user; option sets pulled verbatim from `pa_26_05_compliance_checklist.md` §VI; recommendations carry forward from that file's "Recommendation" lines with explicit "why this not that" + deferral-cost rationale added per advisor pushback (2026-04-29 session).
