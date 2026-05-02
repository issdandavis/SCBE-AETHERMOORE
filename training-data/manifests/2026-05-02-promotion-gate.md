# 2026-05-02 Executable Promotion Gate

Pairs with `2026-05-02-pretrain-manifest.json`. Nothing from that manifest is
allowed into a Hugging Face push (or any external publish surface) until every
gate below passes against the manifest's hashes on a frozen holdout.

This gate exists because prior cycles (v1 bijective overfit, v7-v12 stage6 SFT
plateau) all looked healthy on training metrics but failed on executable
holdouts. Training metrics are not evidence; executable pass/fail is.

## Gate G1 — Code: lanes still compile and tests still pass

Required before any retraining or merge action:

```bash
# TS canonical
npm run build && npx vitest run tests/L2-unit/tileLang.unit.test.ts

# Python parity + control plane
python -m pytest tests/test_tile_lang.py tests/coding_spine/test_deterministic_tongue_router.py -v
```

Pass criteria:

- `npm run build` exits 0.
- vitest reports 4/4 in `tileLang.unit.test.ts`.
- pytest reports 7/7 across the two files.

If any test changed, also re-hash the file and update the manifest before
proceeding.

## Gate G2 — Routing: deterministic router stays at 6/6 vs canonical map

```bash
python scripts/system/bench_geoseal_coder_pair.py \
    --bridge http://127.0.0.1:8766 \
    --champ scbe-geoseal-coder:q8 \
    --challenger qwen2.5-coder:0.5b \
    --tracks routing
```

Pass criteria (read from new bench JSON, not v2 baseline):

- `summary.routing.deterministic_route_acc == 1.0` on the 6-prompt canonical
  set.
- `summary.routing.deterministic_route_pass == summary.routing.n`.

This guards against accidental regressions in
`src/coding_spine/deterministic_tongue_router.py` keyword tables. Adversarial
expansion (ambiguous prompts, multi-language prompts) is required before
declaring the router robust, but is **not** part of this gate — that lives in
a separate router-hardening lane.

## Gate G3 — Coding: pair bench coding track stays at >=5/6 both sides

```bash
python scripts/system/bench_geoseal_coder_pair.py \
    --bridge http://127.0.0.1:8766 \
    --tracks coding
```

Pass criteria:

- `summary.coding.champ_acc >= 0.83` (5/6 floor, 6/6 baseline).
- `summary.coding.challenger_acc >= 0.83`.
- No new empty-output failures on the existing 6 prompts.

Smoke-tier intentionally — promotion to a real benchmark needs ~30 coding
prompts, tracked separately.

## Gate G4 — Packet integrity: deterministic_route field round-trips

```bash
python -c "
import requests, json
r = requests.post('http://127.0.0.1:8766/harness/pair', json={
    'prompt': 'write a Rust ring buffer with zero-cost abstractions'
}, timeout=30)
r.raise_for_status()
body = r.json()
route = body.get('deterministic_route')
assert route is not None, 'missing deterministic_route'
assert route['tongue'] == 'RU', route
assert route['language'] == 'Rust', route
assert route['source'] in ('keyword', 'force', 'atomic-token-router'), route
print('packet OK:', route)
"
```

Pass criteria:

- Bridge returns 200.
- `deterministic_route.tongue == "RU"` for the rust prompt.
- `deterministic_route.language == "Rust"`.
- `source` is one of the three documented values.

This guards the wrap-not-retrain contract: every pair response must carry the
deterministic verdict, and the verdict must be authority for downstream routing.

## Gate G5 — Chemistry / aligned-foundations: deferred

Aligned-foundations + chemistry corpora are not yet rebuilt for this cycle
(step 3 of the night plan). When they are, this gate adds:

- Element/equation tokenizer round-trip on a held-out chemistry prompt set.
- Structure-preservation check: chemistry prompts route to the configured
  tongue (currently UM / Julia under the coding-routing face) without
  contaminating the routing keyword table.

Until that work lands, treat G5 as **not yet required** for code-only
promotions, and **required** for any push that claims chemistry coverage.

## Promotion record

When all required gates pass, append a promotion entry to
`training-data/manifests/promotion_log.jsonl` with: timestamp, manifest_id,
gates passed, command outputs, and the artifact being promoted (HF repo,
ollama tag, etc.). Do not push if any gate is skipped without an explicit
"deferred — see G5" note.

## Honest scope

- This gate is small. It catches lane breakage and routing regressions.
- It does **not** catch generalization failure on prompts the bench doesn't
  cover. The v2 bench routing track is 6 canonical prompts; treat 6/6 as a
  sanity floor, not a robustness claim.
- The constrained-decoding shim from the prior bijective cycle is the
  precedent for this kind of gate: keep the executable pass cheap to run and
  refuse to ship without it.
