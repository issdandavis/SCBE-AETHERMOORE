# Token-Prime Bridge Probe v0

Date: 2026-06-05

## Question

Can token lookups and prime lookups be connected by a learned bridge if both
sides carry truthful sidecar coordinates?

This is a controlled-scale probe, not a language-model capability result.

## Setup

The probe creates a synthetic inventory of 384 token instances and paired prime
addresses.

- `token_id` is randomized and treated as a dictionary address only.
- `token_sidecar` carries meaningful occurrence coordinates: sector, role, ring,
  and modular phase.
- `prime_address` carries prime index/log-scale coordinates and index-phase
  buckets.
- A one-layer ridge bridge is trained on 249 pairs and tested on 135 held-out
  pairs.
- The null preserves both inventories but shuffles the training pairings.

Command:

```bash
python scripts/eval/token_prime_bridge_probe.py
```

## Result

```text
CONTROLLED_BRIDGE_RECOVERS_SIDECAR_RELATION
samples=384 train=249 test=135 nulls=200
token->prime sidecar: top1=0.319 top5=0.837 mrr=0.538
token->prime id_only: top1=0.007 top5=0.052 mrr=0.041
token->prime null: mean=0.008 p95=0.022 p=0.0050
prime->token sidecar: top1=0.289 top5=0.770 mrr=0.489
prime->token null: mean=0.008 p95=0.022 p=0.0050
```

Artifact:

```text
artifacts/eval/token_prime_bridge_probe_v0.json
```

## Interpretation

The bridge works when the relation is real and represented in the sidecar:
token-to-prime and prime-to-token retrieval both beat the shuffled-pair null.

The raw token ID alone does not work. That is the important boundary: BPE/token
IDs are lookup addresses, not semantic values. The meaningful layer is the
sidecar coordinate attached to a token occurrence.

## Caveat

This only proves the membrane architecture is mechanically viable at controlled
scale. It does not prove that a real tokenizer, attention layer, or LLM improves
without a downstream ablation.

The next real test would be:

```text
baseline model/router
vs
baseline + token sidecar prime-address bridge
```

measured on retrieval, long-context tracking, tool routing, or audit stability.

## Next Gate

The immediate non-tautological follow-up is specified in
`docs/eval/token_prime_bridge_probe_v1_gate_spec.md` and implemented in
`scripts/eval/token_prime_bridge_probe_v1.py`.

That v1 gate fixes the main v0 limitation: v0's `prime_index` / `log(prime)`
target is a monotone view of the injected synthetic latent. v1 must operate on
real consecutive primes, use equal-width prime-structure and monotone-index
sidecars, predict `gap_next_bucket`, and score with balanced accuracy. The
headline metric is:

```text
delta_prime_minus_monotone
```

not merely `delta_prime_minus_null`. If prime structure does not beat the
monotone-index control, the correct verdict remains:

```text
positive-control only; prime label is decorative
```

Current v1 result: `PRIME_STRUCTURE_ADDS_SIGNAL` on the real-prime
`gap_next_bucket` gate, with prime balanced accuracy `0.4151` versus monotone
`0.3463` and null95 `0.3747`. This is a narrow arithmetic result, not an LLM
improvement claim.
