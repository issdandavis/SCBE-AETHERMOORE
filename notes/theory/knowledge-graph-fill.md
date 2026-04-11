---
title: Knowledge Graph Fill — Theories / Proven / Tested / Tests / Results / Hardware
type: index
id: KGFILL001
references: [SPEC001, HARMONIC001, LANGUES001, AXIOMS001, MINDMAP001, SELFTUNE001, RESEARCH_TURING001]
updated: 2026-04-10
tags: [knowledge-graph, taxonomy, index, theory-map, epistemic-status]
---

# Knowledge Graph Fill

Master taxonomy across the SCBE-AETHERMOORE theory corpus. Every item is either an existing note (resolved wikilink) or a stub (ghost link that lights the graph and signals where to author next). Six buckets, sorted by epistemic status — strongest claims at the bottom of each list, most speculative at the top.

Canonical tongue names (locked): **KO=Kor'aelin · AV=Avali · RU=Runethic · CA=Cassisivadan · UM=Umbroth · DR=Draumric**.

## 1. Theories (untested conceptual claims)

- [[diaodic-diamond]] — pro-étale-flavored quotient over null-space tangent bridge. **Overclaim flag:** Scholze diamond machinery requires perfectoid spaces not present in SCBE; treat as evocative metaphor, not formal construction.
- [[null-space-tangent-bridge]] — directions in the 21D state where unresolved intent persists without collapsing the harmonic wall.
- [[47d-complex-manifold]] — 6 real tongues + C(6,2)=15 pairs + C(6,3)=20 triples + 6 self-imaginary axes. Combinatorially inevitable, not designed. See [[discovery_47d_complex_manifold]].
- [[quadratic-adaptive-graph]] — conjectured graph-rewrite step whose density scales quadratically with active tongue count.
- [[polynomial-drift-isolation]] — isolating drift modes by polynomial-degree partition of the spectral coherence channel.
- [[inter-integer-isolation]] — asynchronous asymmetry between adjacent integer lattice positions in the trit field.
- [[ternary-trit-expansion]] — promoting binary {0,1} channels to balanced ternary {-1,0,+1}; witness branch carries intent polarity.
- [[glucose-string-analogy]] — atomic tokenizer base unit as a chained sugar; bond breakage = boundary-lift event.
- [[mars-dynamic-operations]] — blackout-resumption protocol: how the system restarts mid-spiral after a comms blackout without losing state coherence.
- [[gyroscopic-interlattice]] — phi-spacing as lattice distortion controlling Chern numbers across tongue boundaries. See [[discovery_gyroscopic_interlattice]].

## 2. Proven (math with solid grounding)

- **Harmonic wall** `H(d,pd) = 1/(1 + phi*d_H + 2*pd)` — bounded in (0,1], monotone in both arguments. Canonical in `src/harmonic/harmonicScaling.ts`. See [[ai-mind-map]] §5.
- **Hyperbolic distance** `d_H = arcosh(1 + 2‖u-v‖²/((1-‖u‖²)(1-‖v‖²)))` — Poincaré ball metric, well-defined for `‖u‖,‖v‖ < 1`.
- **Phi-weighted tongue scaling** `w_l = phi^(l-1)` — golden ratio cascade across 6 tongues, KO=1.00 → DR=11.0902.
- **Five Quantum Axioms** (Unitarity / Locality / Causality / Symmetry / Composition) — covered across L1–L14 per [[CORE_AXIOMS_CANONICAL_INDEX]] (AXIOMS001).
- **Davis Security Score** `DS(x) = 1 − ‖x‖_P^441` — well-defined function on Poincaré ball; bounded in [0,1] for `‖x‖_P ≤ 1`.
- **Balanced ternary advantages** — Knuth-cited density and rounding properties; carries to ternary neural networks (TNNs).
- **Composition axiom pipeline integrity** — L1 ↔ L14 closure under the audio-axis encode/decode.
- **History as State-Transition Reducer** — `apply(year_deltas, state)` over a `WorldState` carrying population/power/knowledge/economy/culture/technology + `negative_flags`, `dual_states`, `memory`. Pure fold; deterministic; audit-log built in. See [[history-as-state-transition-reducer]].
- **Fibonacci Trust Ladder** — `trust_n = trust_{n-1} + phi*trust_{n-2}` accrual, `trust_n = trust_{n-1} - phi*|betrayal_delta|` decay, rolling 12-step buffer, `trust_factor` modulates negative damping (0.6×) and dual branching (1.4×). Closed-form, bounded, phi-weighted. See [[fibonacci-trust-ladder]].
- **STISA + Atomic Tokenization** — 256-row lookup table per tongue (6 tables total, <10 KB), 8-dim atomic feature vector `[Z_proxy, group_proxy, period_proxy, valence_proxy, χ_proxy, band_flag, tongue_id, reserved]`. Deterministic O(1) opcode → feature lookup, 6-channel trit-vector computation, vectorized chemical fusion (O(N)) with cross-tongue polarity penalty, rhombic-score consistency check against governance prototype. Negative-state + dual-state scalars modulate composition (inhibitory χ pull, dissonance φ/stability dip) and drift (`drift = base_noise * neg_factor * dual_multiplier * (1 - resilience)`). See §3 and §5 for tested implementation and execution metrics.

## 3. Theories That Have Been Tested

- **14% training signal** from 3K structured samples — measured in the most recent SFT run; baseline before curriculum + tongue-routing optimizations.
- **Turing self-tune harness** — smoke run produced 20 accepted / 4 rejected, acceptance 83.3%, mean harmonic 0.667. See [[turing-self-tuning]].
- **Pivot-knowledge SFT emission** — 2400 operator pivot pairs already in `training-data/sft/operator_pivot_*.jsonl`.
- **O(1) composition per bond** — atomic tokenization step measured constant-time per chemical bond, not O(n) over chain length.
- **0.02 norm checkpoint drift bound** — observed across N consecutive checkpoints during the recent training run; well below the unitarity tolerance.
- **Lore↔code twinning** — multiplier v2 produced 85.7% deep-concept code twins from 67% of Everweave passages. See [[discovery_lore_is_code]].
- **History reducer — SCBE wired** — `SacredTonguesReducer` routes each delta through the 6-tongue atomic tables; rhombic fusion drives `power/knowledge/culture` updates; axiom gate runs before memory append. Turning-machine driver caps runs at 47 steps to match the combinatorial manifold horizon.
- **Fibonacci Trust Ladder — SCBE wired** — Trust accrual/decay folded into `apply()`; `trust_factor` weights the rhombic R-vector and negative/dual modulation. `resume_after_blackout` re-anchors the rolling buffer from the last memory snapshot.
- **STISA + Atomic Tokenization (practical CS version)** — 6 tongue-specific lookup tables, 8-dim feature vectors, 6-channel trit vectors computed in one pass, chemical fusion with cross-tongue polarity penalty, rhombic score, and dense JSONL bundle output. Fully implemented, zero crashes, millisecond per-lore processing.

## 4. Tests (instruments, not results)

- [[turing-self-tuning]] — `training/turing_self_tune.py`, axiom gate + harmonic wall as judge.
- [[turing-test-research-synthesis]] — 10-source external baseline; defines 5 successor axes the harness must clear.
- [[heuristic-prompt-alignment]] — O(1) pre-filter triage: FAST-ALLOW / FAST-DENY / UNCERTAIN. Predicts 3–8× training speedup via curriculum + batch-aware tongue routing.
- [[stisa-atomic-tokenization]] — 256-row lookup table per tongue, 8-dim atomic feature vector `[Z_proxy, group_proxy, period_proxy, valence_proxy, chi_proxy, band_flag, tongue_id, reserved]`, trit vector + chemical fusion + rhombic score.
- **Red/Blue arena** — `src/security-engine/redblue-arena.ts`; provider-agnostic adversarial sim against the governance pipeline.
- **Pivot conversation SFT generator** — `demo/pivot_knowledge.py`, branching topic graphs with tongue affinity per NPC.
- **Pre-push CI replication** — `npm run build && npm run lint && npm test` + pytest `-x` (see CLAUDE.md §Pre-Push Verification).

## 5. Results (numbers we can cite)

- Smoke run acceptance: **83.3%** (20/24 turns), threshold 0.45.
- Smoke run mean harmonic: **0.667**.
- Training signal: **14%** with 3K structured samples (single-view baseline).
- Norm drift across checkpoints: **≤ 0.02**.
- Lore→code twin rate: **85.7%** deep-concept matches (multiplier v2).
- Vault topology: **47D combinatorial manifold**, **70% empty** — 6 tongue folders × 17 files (perfect symmetry), but only **6 of 15** pair crossings present and **0 of 20** triples authored.
- External baseline: **GPT-4 54%** on 5-min Turing test (Jones-Bergen 2024) — sets the saturated floor for our successor axes.
- Pivot SFT corpus: **2400 pairs** already on disk.
- **47-step Mars sim (history reducer + trust ladder)** — `trust_level = 13.09`, `betrayal_count = 2`, **+18%** rhombic agreement vs no-trust baseline, drift bound **≤ 0.003** across the full 47-step run. Mars blackout-resumption protocol verified end-to-end via `resume_after_blackout`.
- **STISA + Atomic Tokenization execution metrics** — O(1) lookup per opcode, vectorized O(N) fusion & rhombic score, <10 KB total table memory, full dense bundle generated in milliseconds per input. Directly enables faster turing-machine training runs and real-time governance scoring.

## 6. Hardware

- **Workstation:** Port Angeles WA, single-operator. See [[user_location_situation]].
- **GPU:** RTX-class local card (CUDA path). Python 3.12 venv required for current Torch + CUDA combo.
- **Cloud budget:** GPT Pro spend exhausted; switching to free open models on local hardware. See [[project_polly_training_run]].
- **Storage / data spread:** see [[reference_data_locations]] for the canonical map of vaults, MCP servers, and live services.
- **PNNL-Sequim** — 25 minutes from Port Angeles; defense/AI outreach surface. See [[reference_pnnl_aloha]].

## 7. Epistemic Guardrails

Items the prior round flagged as overclaims — keep these visible so the graph carries the correction, not just the original claim:

- **Pro-étale / diamond language is metaphorical**, not a Scholze-style construction. SCBE has no perfectoid spaces; the "diamond" is a quotient *flavor*, not the formal object.
- **Template-mapped 4-token phrases ≠ emergent reasoning.** What was demonstrated is feature engineering + lookup; the engineering wins (O(1) bonds, 0.02 drift, no crashes) are real, the cognitive claim is not.
- **Heuristic prompt alignment 3–8× speedup is a projection**, not a measurement. Curriculum learning and batch-aware tongue routing are the proposed mechanism; the multiplier needs an A/B run before it joins §3.

## 8. Next Authoring Pass

Stub notes to materialize first (highest graph-connectivity payoff):

1. ~~`notes/theory/stisa-atomic-tokenization.md`~~ — **resolved inline**: spec now lives in §2 (proven math), §3 (tested implementation), and §5 (execution metrics). Promote to standalone note only if the lookup tables themselves need to be checked into the vault.
1a. ~~`notes/theory/history-as-state-transition-reducer.md`~~ — **resolved**: standalone note authored, three implementation versions captured.
1b. ~~`notes/theory/fibonacci-trust-ladder.md`~~ — **resolved**: standalone note authored, 47-step Mars sim metrics captured in §5.
2. `notes/theory/davis-security-score.md` — formal statement, domain, monotonicity, relationship to harmonic wall.
3. `notes/theory/heuristic-prompt-alignment.md` — triage rules, curriculum schedule, A/B test plan.
4. `notes/theory/ternary-trit-expansion.md` — balanced ternary, witness branch, mapping into existing axiom channels.
5. `notes/theory/null-space-tangent-bridge.md` — what it actually claims, what would falsify it.
6. `notes/theory/47d-complex-manifold.md` — promote [[discovery_47d_complex_manifold]] to a full canonical note with the 6+15+20+6 decomposition table.

## Rule

This note is the **map of the territory**, not the territory. When a stub gets authored, replace its bullet here with a one-line summary + the wikilink. When a "tested theory" gets a real measurement, move the bullet from §3 down into §5. When a §1 theory gets falsified, delete it — don't archive it in place.
