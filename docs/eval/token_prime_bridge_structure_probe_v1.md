# Token-Prime Bridge Structure Probe v1

Date: 2026-06-05

## Question

Does the token-prime bridge carry **prime-specific structure**, or does it only
recover a smooth index relation?

This is the missing control for `token_prime_bridge_probe_v0`.

## Setup

The v0 bridge target included prime index and log-scale coordinates. That proved
the bridge wiring worked, but it did not prove the word "prime" was doing any
work. A monotone sequence with the same index relation would behave similarly.

v1 separates three targets:

- `monotone_index`: smooth powers/logs of the paired index, with no prime lookup.
- `prime_residual`: residues, normalized gaps, and factor counts around the
  prime, with index/log coordinates removed.
- `monotone_plus_prime`: both together.

Pass condition:

```text
prime_residual clears its shuffled-pair null
AND
monotone_plus_prime beats monotone_index
```

Command:

```bash
python scripts/eval/token_prime_bridge_structure_probe.py
```

## Result

```text
PRIME_STRUCTURE_NOT_SUPPORTED_OVER_MONOTONE_INDEX
samples=384 train=249 test=135 nulls=200
monotone_index: top1=0.067 top5=0.385 null95=0.022
prime_residual: top1=0.015 top5=0.067 null95=0.022 p=0.2338
monotone_plus_prime: top1=0.037 top5=0.156 null95=0.022
delta combined-monotone: -0.02962962963
```

Artifact:

```text
artifacts/eval/token_prime_bridge_structure_probe_v1.json
```

## Interpretation

The advisor critique is confirmed.

The monotone index address clears null. The prime-only residual address does not.
Adding prime residual fields to the monotone address makes held-out retrieval
worse, not better.

So the prime label is decorative at this controlled scale. The membrane can
carry an injected relation, but the prime-specific residue/gap/factor structure
does not add useful bridge information over a smooth index control.

## What Remains True

`token_prime_bridge_probe_v0` is still useful as a positive control: the bridge
and retrieval wiring work, and raw token IDs sit at chance.

But v1 closes the stronger claim:

```text
token-prime bridge works mechanically
prime-specific bridge advantage not shown
```

The next test should not add more prime fields. It should move to a real
downstream task:

```text
baseline router/retriever
vs
baseline + sidecar coordinates
```

and only keep the sidecar if it improves retrieval, routing, attention
stability, or audit quality.
