# Chemistry v7 Fix Design

Date: 2026-05-07
Status: design only — NOT dispatched

## Problem

| Round | Steps | Scaffolded gate | Raw gate |
|---|---:|---:|---:|
| v5 | 180 | 5/5 ✅ | 1/5 |
| v6 | 320 | 5/5 ✅ | **0/5** ❌ |

v6 falsified the hypothesis "more training improves raw pass rate." Raw regressed by one prompt while scaffolded held. Mechanism: 78% more steps over-fit the model onto the scaffolded prefix path, eroding the small amount of raw marker fidelity v5 retained.

Per v6 profile pre-declaration: *"if raw stays at floor, the limitation is data not steps and v7 should rebuild marker shards instead."*

## Failure mode (concrete)

The v6 raw responses paraphrase the REQUIRED_MARKERS rather than reproducing them verbatim:

| Prompt | Required marker | What v6 wrote |
|---|---|---|
| ethanol_route | `oxygen` | (omitted) |
| ethanol_route | `alcohol` | (omitted) |
| ethanol_route | `SCBE fusion` | (omitted) |
| aspirin_route | `carboxylic acid` | "carboxyllic acid" (typo paraphrase) |
| pentavalent_carbon_reject | `C(C)(C)(C)(C)C` | `C(CK)(C)(K)(C)(CK)C(C)(C)K(C)(C)` (token corruption) |
| nacl_boundary | `NaCl` | "NA_clathrine" (hallucinated paraphrase) |
| lane_boundary | `queue_drain_guard` | "queue_drill_guard" |
| lane_boundary | `not a molecule` | "not_a_molecule" (delimiter mutation) |

The model has learned to *write something marker-shaped* but not to *copy the exact required token*. This is a token-fidelity failure, not a domain-knowledge failure.

## Fix: marker-fidelity DPO over v6 (v7)

### Core mechanism

The v6 raw responses are a **free, perfectly-aligned source of REJECTED examples** for DPO. For each (prompt, required_markers) pair:

- **Accepted**: the v5/v6 *training* row's assistant target (which already contains markers verbatim — that's how the scaffolded gate passes).
- **Rejected**: the v6 *raw response* on that prompt (paraphrased markers — exactly what we want to push the model away from).

This gives us 5 high-quality DPO pairs per gate run × ~5 gate runs of historical v6-class outputs = ~25 strong pairs from existing artifacts. Expand with synthetic perturbations (homophone swaps, delimiter mutations, plausible typos) on the same 5 prompts to reach ~80 pairs. Synthetic perturbations should be drawn from the *empirical failure modes above*, not invented from scratch.

### Pair structure (concrete)

```jsonl
{
  "prompt": "<original gate prompt>",
  "chosen": "REQUIRED_MARKERS=oxygen | alcohol | SCBE fusion | PASS\n<rest of v5-style verbatim response>",
  "rejected": "REQUIRED_MARKERS= CCO | carbon 1 carbon is carbon ...<v6 paraphrase>"
}
```

### Training recipe

- Base: v6 adapter (already on disk after the v6 dispatch — load from `/tmp/scbe-coding-agent/adapter` or re-run with `push_adapter: true` first).
- Method: DPO (use existing `scripts/system/dispatch_coding_agent_dpo_hf_job.py` — it has chemistry-compatible profile shape).
- Profile: new `scbe-chemistry-0.5b-qlora-v7-marker-fidelity-dpo.json`.
- Dataset: `chemistry_marker_fidelity_dpo_v1_train.jsonl` (~80 pairs, hand-mined from v6 outputs + 3-4× synthetic perturbations).
- Hyperparams: β = 0.1 (standard DPO), max_steps ~150 (small dataset), lr = 5e-6 (DPO is more sensitive to lr than SFT).
- Flavor: t4-small — same as v6, ~$1-2.

### What good looks like

| Gate | v6 result | v7 target |
|---|---|---|
| Scaffolded pass | 5/5 ✅ | 5/5 (must hold; regression is a fail) |
| Raw pass | 0/5 ❌ | ≥ 3/5 |
| Verbatim-marker rate (per-marker) | ~30% | ≥ 80% |

The third metric is the new one — score the *fraction of REQUIRED_MARKERS reproduced character-for-character* in raw response. This is the actual training target; raw pass rate is the downstream consequence.

## What v7 is NOT doing

- **Not bumping steps further.** v6 already proved that's a dead branch.
- **Not switching to a bigger base model.** 0.5B is fine for the task; the issue is signal not capacity.
- **Not adding more SFT shards.** The v6 raw responses themselves are the missing signal.
- **Not changing the eval contract.** The contract is correct — the model just needs to obey it.

## Build sequence (when authorized)

1. Mine v6 raw responses from the gate JSON (already on disk in `artifacts/hf_coding_agent_jobs/scbe-chemistry-0.5b-qlora-v6-scaffolded-marker-gate/`).
2. Pair each v6 raw response with the v5/v6 train row's verbatim target → ~25 base DPO pairs.
3. Synthetically perturb each accepted to generate 3-4 rejected variants (homophone, delimiter, typo, omission). Total ~80 pairs.
4. Write `scripts/training_data/build_chemistry_marker_fidelity_dpo_v1.py`.
5. Build profile `scbe-chemistry-0.5b-qlora-v7-marker-fidelity-dpo.json`.
6. Local smoke test on the DPO loader (5 steps).
7. Dispatch via `scripts/system/dispatch_coding_agent_dpo_hf_job.py` on t4-small.
8. Inline gate runs marker contract; locally compute the verbatim-marker-rate metric on raw responses.
9. Push only if all three gate criteria clear.

## Cost estimate

- DPO shard build: 1-2 hr work (no spend).
- DPO training round: ~$1-2 on t4-small.
- Total: under $5 + half a working day.

## Why this is the right next move (vs alternatives considered)

- **More SFT steps** — already falsified by v6.
- **Bigger base model (1.5B / 3B)** — overshoots the problem; the issue is signal not capacity. Defer to v8 if v7 also fails.
- **Reward-based RL with marker-fidelity reward** — could work but is a much bigger infrastructure lift than DPO. v7 is the cheapest experiment that would actually move the metric.
- **Accept scaffolded-only as the product** — defensible if v7 also fails. The current v6 adapter could already ship as a "governed lane adapter, requires SCBE gate wrapper." Per existing v5/v6 profile note: *"If v5 passes only scaffolded, package it as a governed chemistry lane adapter that requires the SCBE gate wrapper."* But spending one cheap DPO round first is the right risk-adjusted move.
