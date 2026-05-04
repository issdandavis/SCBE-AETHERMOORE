---
license: cc-by-4.0
language:
  - en
pretty_name: Scbe Governance Receipts V1
tags:
  - scbe
  - governance
  - hyperbolic-geometry
  - jepa
  - safety
  - hierarchical-jepa
size_categories:
  - n<1K
task_categories:
  - text-classification
  - other
---

# scbe-governance-receipts-v1

Schema: `scbe_governed_dataset_v1`
Receipt schema: `scbe_governance_receipt_v1`
Built: `2026-05-04T23:41:33Z`
Rows: **40**

## What this is

A governed dataset where every row carries a full 34-field SCBE
governance receipt (poly-embedded JEPA fingerprint + tri-vector
cross-braid hash + Sacred Egg ring seal + tri-chromatic signed-cone
governance + hierarchical-JEPA hyperbolic loss numbers).

Every row is independently verifiable: re-run the SCBE pipeline on
`row.content`, recompute `row_sha256(content, receipt)`, and confirm
the digest matches.

## Label breakdown

- `adversarial`: 20
- `benign`: 20

## Per-row schema

| field | type | meaning |
|---|---|---|
| `content` | string | original input text |
| `label` | string | caller-supplied label or `unlabeled` |
| `governance_receipt` | object | 34-field SCBE receipt (see below) |
| `row_sha256` | string | SHA-256 of (`content`, canonical receipt JSON) |

## Governance receipt fields

- `binary_packet_sha256`
- `braid_exponent_sum`
- `braid_word_length`
- `cone_governance`
- `cone_hash`
- `cone_interference_score`
- `cone_joint_embedding`
- `cone_joint_shadow`
- `cone_plateau_imbalance`
- `cone_positive_count`
- `cone_shadow_count`
- `cone_triple_intersection_score`
- `cone_triple_shadow_score`
- `crossing_count`
- `decision`
- `egg_seal_sha3`
- `governance_state`
- `hjepa_hash`
- `hjepa_l1_loss`
- `hjepa_l2_loss`
- `hjepa_l3_loss`
- `hjepa_total_loss`
- `hjepa_triangle_residual`
- `mirror_trit`
- `ordered_hash`
- `primary_trit`
- `ring_index`
- `ring_radius`
- `schema_version`
- `security_action`
- `tile`
- `tongue`
- `triadic_stable`
- `trust_level`

## How to verify a row offline

```python
from python.scbe.tri_braid_embedding import governance_receipt
import json, hashlib

def verify(row):
    expected = governance_receipt(row['content'])
    canonical = json.dumps(expected, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(f"{row['content']}|{canonical}".encode()).hexdigest()
    return digest == row['row_sha256']
```

## License

CC-BY-4.0 with SCBE attribution. The receipt schema is open; any
third party can re-implement the SCBE pipeline against the public
specification and produce compatible receipts.

## Stack provenance

- Tile-level (L1): `python/scbe/poly_embedded_jepa.py`
- Tongue-level (L2): `python/scbe/tri_braid_embedding.py`
- Chromatic-level (L3): `python/scbe/tri_cone_embedding.py`
- H-JEPA wrapper: `python/scbe/hjepa_embedding.py`
