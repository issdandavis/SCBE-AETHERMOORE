# The Mason's Game Board — AlphaGo-Grounded Training-Loop Design

**Date:** 2026-06-10 · **Status:** design (local, not pushed) · **Engine:** `scripts/tools/mason.py` + the flow board (`scripts/scbe-system-cli.py`)

This document maps how AlphaGo / AlphaGo Zero / KataGo were *actually trained* onto our
mason + flow-board loop, so a small free model can climb the same ladder. Sources are the
original papers (researched 2026-06-10; citations at the end). The mechanism rule carried
from everything we've null-tested before: **the verifier is the board, the delta is the
only honest score, and a learned model never gets to accept or reject — only to order.**

---

## 0. What already exists (the board is built)

| Piece | Where | State |
|---|---|---|
| Stone library + schematics | `scripts/tools/mason.py` + `scripts/tools/mason_stones/` packs | 5 schematics, 21 stones, pure-data packs auto-register |
| Real-execution verify | `mason._verify` (subprocess, exit-0 + REQUEST_OK) | every placement verified in place |
| Capture + escalate | `mason.build` (`captured`, `MODEL_LADDER`) | a failed stone is never placed |
| Stub-crack gate | `tests/test_mason.py` generic tests | every pack's hollow stub must crack, enforced forever |
| Flow board | `_build_flow_status_board`, `_execute_flow_packet`, `_run_acceptance_check` | dependency topology + executable acceptance + REWORK |

Our one structural advantage over AlphaGo, worth keeping in view the whole way down:
**AlphaGo's reward was one ±1 bit at the end of a ~200-move game; ours is an exact
verdict per placement.** They needed 4.9M games and thousands of TPUs largely *because*
their signal was sparse and their evaluators approximate. Our rollout (subprocess
execution) is exact and free. We should expect orders-of-magnitude better sample
efficiency — hundreds-to-thousands of logged builds, not millions.

---

## 1. The dictionary (AlphaGo → mason)

| AlphaGo component | What it really was | Our counterpart |
|---|---|---|
| Board state | 19×19 stones + history | partial build: stones placed, open slots, dependency frontier |
| Move | one stone placement | (stone choice, chisel fills) for the open slot; or "next packet" on the flow board |
| **SL policy net** (13-layer CNN, 29.4M expert positions, 57.0% acc, 3 ms) | imitation of experts; bootstraps everything | small free model proposing stone+fills, first SFT'd on logged *sealed* placements |
| **Fast rollout policy** (24.2% acc, 2 µs — 1500× faster) | dumb-but-cheap policy so search can afford full playouts | the mason's deterministic default path: obvious stone by shape, default fills, run acceptance — **no LLM call** |
| **RL policy** (REINFORCE vs a pool of frozen past selves; >80% vs SL) | self-play improvement | re-running schematics with the model as mason; exit-0 *is* z=±1 |
| **Value net** (30M positions, ONE per game; 15,000× cheaper than a rollout) | cheap outcome predictor | pass-probability ranker over candidate stones/packets — used to ORDER, never to decide |
| **MCTS / PUCT** (argmax Q + c·P·√ΣN/(1+N), c=5; move = max VISITS not max Q) | prior-guided explore/exploit | the slot retry loop made principled: per (slot-type, stone) keep N tries, Q pass-rate, P model prior; try argmax(Q + c·P/(1+N)) |
| λ=0.5 value/rollout mixing (each alone ≥95% worse) | blending two *approximate* evaluators | **don't copy** — our rollout is exact, so λ→1 at decision time; the learned score only pre-screens |
| Dirichlet root noise (ε=0.25) + τ=1 first 30 moves | exploration only at the root, where it's cheap | occasionally force a low-ranked stone into the try-queue; sample on cheap early slots, argmax on expensive late ones |
| **Resignation** (v_resign auto-tuned, false-abandon <5% measured via 10% control group) | stop doomed games to save compute | escalation IS our resignation; tune the give-up threshold from logs, keep a control fraction that exhausts the small model to *measure* false escalations |
| **Gated evaluation** (new net must win >55% of 400 games) — later deleted by AlphaZero | protects data quality while training is noisy | a new fine-tune becomes the default mason only after beating the incumbent on held-out schematics by a margin; drop the gate once stable |
| Self-play games (4.9M in 3 days) | the data factory | logged mason builds; the *product is the dataset*, the towns are a byproduct |

---

## 2. Five rules the research forces

1. **The verifier is the board.** DeepSeek-R1 abandoned neural process-reward models
   because the model learned to *hack* them; ORPS showed execution feedback can replace a
   trained PRM entirely. A learned ranker's only safe job is prioritization — exit-0
   stays the sole authority that places a stone. A hacked ranker costs wasted executions,
   never a false receipt.
2. **Train on the post-search choice.** AlphaGo Zero's engine of improvement is that the
   training target is what *search concluded*, not what the raw net first guessed. For
   us: the sealed stone (after captures and escalation) is the policy target; captured
   tries are pruned exploration — KataGo explicitly prunes forced exploration out of the
   policy target. Never teach the model its own reroll noise.
3. **Dense receipts beat sparse outcomes.** KataGo's single biggest win (~1.65×) was
   auxiliary targets — ownership maps and score, not just win/lose. Our receipts already
   carry per-stone set/captured, crack reason, stones-set fraction, ladder rung. Log all
   of it; one build is worth dozens of labels, not one bit.
4. **Diversity in proposals, sharpness in evaluation.** AlphaGo's *imitation* policy made
   a better search prior than the stronger RL policy (humans propose a diverse beam; RL
   collapses to one move) — while the RL-derived value net won. And rStar-Math found the
   preference model becomes the ceiling once the policy is decent. So: keep the chooser
   diverse, pour improvement into the ranker.
5. **Spend search only where it mints data.** KataGo ran ~75% of games cheap (few
   playouts, value-data volume) and ~25% full (policy-quality targets). AlphaCode killed
   ~95% of 1M samples with execution filters before any model ranked anything. Cheap
   builds for volume, full builds for policy targets.

---

## 3. The loop, staged (each stage is usable on its own)

**A — Bootstrap (now; zero training).** Scripted mason + big-model escalation is exactly
rStar-Math's round-1 bootstrap (they used a 236B teacher; ours is the ladder). Every
build — scripted or escalated — logs `(slot digest, candidates tried, pass/fail, crack
reason, sealed stone, rung)` to a replay buffer (JSONL under `training-data/`).

**B — SFT on verified traces.** Fine-tune (or few-shot prompt-pack) the small model on
*sealed placements only*, weighted toward builds with high stones-set fractions.
rStar-Coder: verified-trace SFT alone took Qwen2.5-7B from 17.4% → 57.3% on
LiveCodeBench. This is the cheapest competence in the whole pipeline (AlphaGo's SL stage).

**C — Ranker from pairs, free.** Every escalation already records (sealed stone,
captured stone, crack reason) for the same slot — that's a Bradley-Terry training pair
(rStar-Math's PPM recipe: rank pairs, never regress noisy scores; CodePRM: feed the
crack reason *into* the ranker as input). One position per build for any
outcome-predictor (AlphaGo's one-per-game decorrelation trick — slot states within one
build share an outcome and would be memorized).

**D — Self-evolution rounds.** Re-run the same schematic packs with the newer model;
spend extra candidate budget *only* on slots that still escalate (rStar-Math went
60% → 90% coverage in 4 rounds this way). Gate each new fine-tune AlphaGo-Zero-style
(beat the incumbent on held-out schematics by a clear margin), and delete the gate once
training is stable, as AlphaZero did.

**E — Proposer (later).** Absolute-Zero-style: the model *proposes* new schematics +
acceptance requests; a proposal is admissible only if the acceptance actually runs and at
least one known stone assembly passes it. Calibrate proposals so the current policy
passes ~50% — a self-generated curriculum with zero human authoring.

---

## 4. Board-state digest (KataGo's global pooling, our size)

KataGo injected a tiny global summary (mean/max pools) into every local decision. Our
equivalent: prepend a fixed **5–10 field digest** to every slot/packet decision — stones
placed/captured so far, open slots, dependency frontier, current rung, budget left.
`mason.build` already computes all of it. Small and structured; the win came from cheap
global signal, not from dumping the whole state.

---

## 5. Verifier strength — the adversarial audit

The generic tests prove a *hollow* stone cracks. The sharper attack is a *cheating*
stone: hardcode the exact trace the scripted requests expect. We ran one attacker per
pack (results below). The structural fix, from three independent sources, is the same:
**grow the tests beyond the scripted trace** — AlphaCodium (grow tests before trusting
them: 19% → 44% pass@5), AlphaCode (cluster candidates by behavior on *generated probe
inputs*), rStar-Coder (mutual verification: label expected outputs by agreement of
independent solutions).

*Audit results (2026-06-10):* **4/4 cheats passed** against the original requests — every
pack, including the hand-written snake, was gamed by a lookup-table stone that replayed
the exact scripted trace (full verdicts: `artifacts/mason/_adversarial_audit.json`).
The harness was sound; the acceptance corpus was a closed, author-known input set.

*Fix applied same day:* every load-bearing slot request now carries an **unseeded-random
property probe** — operands/configs drawn at request-run time with the expectation
computed *from the input* (calc: random RPN arithmetic; rocket: random stage config,
altitude must equal the burn math; snake: random injected food position, head coordinate
asserted; breakout: random brick off the ball's path must NOT score). No finite lookup
table can pass, by construction — randomness in the *request* is the anti-cheat weapon,
while stones themselves stay deterministic.

*Re-verified:* the documented cheats were replayed against the hardened requests and all
were **captured** (calc cheat: `ValueError: off-script` at the evaluator slot; snake and
breakout cheat fingerprints captured at the engine slot). Real stones still build 3/3
randomized runs; all stubs still crack; 7/7 suite green. Lesson for the loop: cheap
verification invites trace-memorizing policies — exactly why AlphaCodium grows tests and
AlphaCode probes with generated inputs before trusting any candidate.

*Corroborating case, same day, different subsystem:* `src/crypto/sacred_eggs.py`
ring-descent auth computed an HMAC and never checked it — any 32 bytes escalated
OUTER→CORE — and the existing test **handed it a random secret and asserted success**.
AI wrote the hole; AI wrote the test that blessed it. Fixed fail-closed
(`hmac.compare_digest` against the shell commitment, deny burns the shell, 64+85 tests
green, independently re-verified). The pattern is identical to the stone-pack audit: a
verifier that encodes the implementation's behavior — instead of the *spec's* behavior —
will seal anything, including the bug it grew up with. This is why the board's training
data must only ever come from requests that derive expectations from inputs (properties),
never from recorded outputs.

---

## 6. What NOT to copy (and why)

- **Their scale.** 4.9M games / 64 GPU workers existed because Go's reward is one bit per
  200 moves. Ours is dense; copying the scale would be cargo cult.
- **MCTS over tokens.** DeepSeek-R1 tried and abandoned it — token-level branching
  explodes. It works here precisely because our action space is a *finite stone library*,
  like Go's legal moves. Search over stones, never over tokens.
- **λ-blending the verifier with a learned value.** They blended because both evaluators
  were approximate. Ours is exact; blending would *dilute ground truth with a guess*.
- **Human-curated "good stone" examples.** AlphaGo Zero's SL twin predicted human moves
  *better* and still lost — imitation of curated labels caps you at the curator. Train
  only on what execution certified.

---

## 7. Smallest next slices (in order)

1. **Receipts → replay buffer.** `mason build --log-receipts`: append the full build log
   (digest, tries, crack reasons, seals, rung) as one JSONL row. The dataset is the product.
2. **Fast/full build modes.** KataGo's playout-cap randomization: ~75% of training builds
   take the first candidate only; ~25% run k-candidate expansion + ladder. Tag every row
   with its mode; policy targets come only from full mode.
3. **k-sibling expansion before escalation.** On a crack, try k=4–8 alternate stones
   (PUCT-lite from a logged crack-rate table — no model needed yet) before climbing the
   ladder. AlphaCode's lesson: cheap sampling + execution filtering recovers most of what
   a bigger model buys.
4. **Probe inputs per slot.** Kill trace-hardcoding (§5); cluster candidates by probe
   behavior.
5. **Plug the small model in as the prior.** Ollama model ranks candidate stones (the SL
   policy enters the PUCT formula as P). Everything before this step works without any
   model — which is the proof the board, not the model, is load-bearing.

---

## Sources

- Silver et al., *Mastering the game of Go with deep neural networks and tree search*, Nature 2016 — SL policy (29.4M positions, 57.0%), rollout policy (2 µs), RL pool self-play, value net one-position-per-game, PUCT c=5, λ=0.5, max-visits move choice.
- Silver et al., *Mastering the game of Go without human knowledge* (AlphaGo Zero), Nature 2017 — dual-head net (+~600 Elo), MCTS as policy-improvement operator, π targets, 55% gate, Dirichlet root noise, auto-tuned resignation (<5% false positives via 10% control), 4.9M games/3 days.
- Silver et al., *AlphaZero*, Science 2018 — gate removed, no augmentation, 800 sims/move, chess 44M games/9h.
- Wu, *Accelerating Self-Play Learning in Go* (KataGo) — ~50× compute cut: auxiliary targets (~1.65×), playout cap randomization, forced playouts + policy target pruning, global pooling, board-size curriculum; <30 V100s for 19 days vs ELF's ~74 GPU-years.
- rStar-Math (arXiv 2501.04519) — 7B+MCTS+PPM: MATH 58.8→90.0; terminal-guided Q backprop; PPM pairwise (never regress Q); 4 self-evolution rounds 60→90% coverage; PPM is the ceiling.
- AlphaCode (2203.07814) / AlphaCode 2 tech report — 1M samples → ~95% execution-filtered → behavior clustering → 10 submissions.
- AlphaCodium (2401.08500) — grow the test set before trusting it (19→44% pass@5).
- RLEF (2410.02089) — execution feedback in-context + RL: 8B@3 samples beats AlphaCode-9B@1000; train the model to *consume* crack reasons.
- DeepSeek-R1 (2501.12948) — neural PRMs reward-hacked; token-MCTS abandoned; verifiable outcome rewards won.
- ORPS (2412.15118) / CodePRM (ACL Findings 2025) — execution feedback eliminates/feeds the PRM.
- rStar-Coder (2505.21297) — verified data quality dominates for small models (7B: 17.4→57.3 LCB).
- Absolute Zero (2505.03335) — proposer/solver self-play with an executor as the only judge.
- LATS (2310.04406) — MCTS for agents: HumanEval 92.7 pass@1 (GPT-4).

Full structured research notes: `artifacts/mason/_research_alphago.json`.
