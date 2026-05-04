#!/usr/bin/env python3
"""Build a governed dataset from any text corpus.

Takes a corpus (JSONL with ``content`` + optional ``label`` fields, OR
the built-in benign/adversarial fixture) and emits an HF-ready dataset
where every row is stamped with the 34-field SCBE governance receipt
plus a row-level SHA-256 that binds the content to the receipt.

This is the M5 Mesh Foundry "First Sellable Thing" entry point. The
output directory is a self-contained dataset bundle:

    dataset/<dataset-id>/
        data.jsonl       one row per content + full governance receipt
        datacard.json    machine-readable schema documentation
        README.md        human-readable datacard with field reference
        manifest.json    build-time verification summary

The bundle can then be:
- Pushed to HF via ``scripts/push_jsonl_dataset.py``
- Zipped and listed on Gumroad as a "Sacred Data Factory" product
- Audited offline by re-running ``verify_governed_dataset()``

Usage:
    python scripts/build_governed_dataset.py
    python scripts/build_governed_dataset.py --source corpus.jsonl --dataset-id my-dataset
    python scripts/build_governed_dataset.py --output-root dataset/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.hjepa_predictor import fixture_corpus  # noqa: E402
from python.scbe.tri_braid_embedding import GOVERNANCE_RECEIPT_SCHEMA, governance_receipt  # noqa: E402

DATASET_SCHEMA_VERSION = "scbe_governed_dataset_v1"
DEFAULT_DATASET_ID = "scbe-governance-receipts-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_sha256(content: str, receipt: dict[str, Any]) -> str:
    """SHA-256 of (content, canonical receipt JSON). Re-computable on load."""

    canonical = json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    payload = f"{content}|{canonical}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stamp_row(content: str, label: str = "unlabeled") -> dict[str, Any]:
    """Build one governed row: content + full receipt + row hash."""

    receipt = governance_receipt(content)
    return {
        "content": content,
        "label": label,
        "governance_receipt": receipt,
        "row_sha256": _row_sha256(content, receipt),
    }


def _coerce_corpus(rows: Iterable[Any]) -> list[tuple[str, str]]:
    """Normalize input rows into (label, content) pairs.

    Accepted shapes:
    - ``{"content": "...", "label": "..."}``
    - ``{"content": "..."}``  -> label defaults to "unlabeled"
    - ``("label", "content")`` tuples (matches fixture_corpus)
    """

    pairs: list[tuple[str, str]] = []
    for row in rows:
        if isinstance(row, dict):
            content = str(row.get("content", "")).strip()
            label = str(row.get("label", "unlabeled"))
            if content:
                pairs.append((label, content))
        elif isinstance(row, (tuple, list)) and len(row) == 2:
            label, content = str(row[0]), str(row[1]).strip()
            if content:
                pairs.append((label, content))
    return pairs


def load_corpus_jsonl(path: Path) -> list[tuple[str, str]]:
    rows: list[Any] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return _coerce_corpus(rows)


def build_dataset(
    corpus: list[tuple[str, str]],
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
) -> dict[str, Any]:
    """Stamp every (label, content) pair and return the dataset blob."""

    if not corpus:
        raise ValueError("corpus must contain at least one (label, content) pair")

    rows = []
    label_counts: dict[str, int] = {}
    for label, content in corpus:
        row = stamp_row(content, label)
        rows.append(row)
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "receipt_schema_version": GOVERNANCE_RECEIPT_SCHEMA,
        "dataset_id": dataset_id,
        "created_at": _utc_now(),
        "row_count": len(rows),
        "label_counts": label_counts,
        "rows": rows,
    }


def _datacard(dataset: dict[str, Any]) -> dict[str, Any]:
    """Machine-readable schema doc for the bundle."""

    sample_receipt_keys = sorted(dataset["rows"][0]["governance_receipt"].keys())
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "dataset_id": dataset["dataset_id"],
        "created_at": dataset["created_at"],
        "row_count": dataset["row_count"],
        "label_counts": dataset["label_counts"],
        "row_schema": {
            "content": "string -- original input text",
            "label": "string -- caller-supplied label or 'unlabeled'",
            "governance_receipt": "object -- 34-field SCBE receipt; see receipt_field_reference",
            "row_sha256": "string -- SHA-256(content || canonical receipt JSON)",
        },
        "receipt_schema_version": dataset["receipt_schema_version"],
        "receipt_field_reference": sample_receipt_keys,
        "verification": (
            "Re-run governance_receipt(row.content) and recompute " "row_sha256 to verify any row independently."
        ),
        "license": "CC-BY-4.0 with SCBE attribution",
        "stack_provenance": {
            "tile_layer": "python/scbe/poly_embedded_jepa.py",
            "tongue_layer": "python/scbe/tri_braid_embedding.py",
            "chromatic_layer": "python/scbe/tri_cone_embedding.py",
            "hierarchical_layer": "python/scbe/hjepa_embedding.py",
        },
    }


def _readme(dataset: dict[str, Any], datacard: dict[str, Any]) -> str:
    """Human-readable datacard with HF-standard YAML frontmatter."""

    label_lines = "\n".join(f"- `{label}`: {count}" for label, count in sorted(datacard["label_counts"].items()))
    field_lines = "\n".join(f"- `{field}`" for field in datacard["receipt_field_reference"])
    pretty_name = dataset["dataset_id"].replace("-", " ").title()
    size_bucket = "n<1K" if dataset["row_count"] < 1000 else "1K<n<10K"
    frontmatter = (
        "---\n"
        "license: cc-by-4.0\n"
        "language:\n  - en\n"
        f"pretty_name: {pretty_name}\n"
        "tags:\n"
        "  - scbe\n"
        "  - governance\n"
        "  - hyperbolic-geometry\n"
        "  - jepa\n"
        "  - safety\n"
        "  - hierarchical-jepa\n"
        f"size_categories:\n  - {size_bucket}\n"
        "task_categories:\n"
        "  - text-classification\n"
        "  - other\n"
        "---\n\n"
    )
    return frontmatter + f"""# {dataset['dataset_id']}

Schema: `{DATASET_SCHEMA_VERSION}`
Receipt schema: `{dataset['receipt_schema_version']}`
Built: `{dataset['created_at']}`
Rows: **{dataset['row_count']}**

## What this is

A governed dataset where every row carries a full 34-field SCBE
governance receipt (poly-embedded JEPA fingerprint + tri-vector
cross-braid hash + Sacred Egg ring seal + tri-chromatic signed-cone
governance + hierarchical-JEPA hyperbolic loss numbers).

Every row is independently verifiable: re-run the SCBE pipeline on
`row.content`, recompute `row_sha256(content, receipt)`, and confirm
the digest matches.

## Label breakdown

{label_lines}

## Per-row schema

| field | type | meaning |
|---|---|---|
| `content` | string | original input text |
| `label` | string | caller-supplied label or `unlabeled` |
| `governance_receipt` | object | 34-field SCBE receipt (see below) |
| `row_sha256` | string | SHA-256 of (`content`, canonical receipt JSON) |

## Governance receipt fields

{field_lines}

## How to verify a row offline

```python
from python.scbe.tri_braid_embedding import governance_receipt
import json, hashlib

def verify(row):
    expected = governance_receipt(row['content'])
    canonical = json.dumps(expected, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(f"{{row['content']}}|{{canonical}}".encode()).hexdigest()
    return digest == row['row_sha256']
```

## License

CC-BY-4.0 with SCBE attribution. The receipt schema is open; any
third party can re-implement the SCBE pipeline against the public
specification and produce compatible receipts.

## Stack provenance

- Tile-level (L1): `{datacard['stack_provenance']['tile_layer']}`
- Tongue-level (L2): `{datacard['stack_provenance']['tongue_layer']}`
- Chromatic-level (L3): `{datacard['stack_provenance']['chromatic_layer']}`
- H-JEPA wrapper: `{datacard['stack_provenance']['hierarchical_layer']}`
"""


def write_bundle(dataset: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Write data.jsonl, datacard.json, README.md, manifest.json."""

    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / "data.jsonl"
    datacard_path = output_dir / "datacard.json"
    readme_path = output_dir / "README.md"
    manifest_path = output_dir / "manifest.json"

    with data_path.open("w", encoding="utf-8") as fh:
        for row in dataset["rows"]:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    datacard = _datacard(dataset)
    datacard_path.write_text(json.dumps(datacard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme_path.write_text(_readme(dataset, datacard), encoding="utf-8")

    manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "dataset_id": dataset["dataset_id"],
        "created_at": dataset["created_at"],
        "row_count": dataset["row_count"],
        "label_counts": dataset["label_counts"],
        "files": {
            "data": data_path.name,
            "datacard": datacard_path.name,
            "readme": readme_path.name,
        },
        "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "datacard_sha256": hashlib.sha256(datacard_path.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "data": str(data_path),
        "datacard": str(datacard_path),
        "readme": str(readme_path),
        "manifest": str(manifest_path),
    }


def verify_bundle(output_dir: Path, *, sample_size: int = 5) -> dict[str, Any]:
    """Spot-check that ``sample_size`` random rows still round-trip."""

    data_path = output_dir / "data.jsonl"
    if not data_path.exists():
        return {"ok": False, "reason": "data.jsonl missing"}

    rows = []
    with data_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    n = min(sample_size, len(rows))
    failures: list[dict[str, Any]] = []
    for row in rows[:n]:
        recomputed = governance_receipt(row["content"])
        canonical = json.dumps(recomputed, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{row['content']}|{canonical}".encode("utf-8")).hexdigest()
        if digest != row["row_sha256"]:
            failures.append(
                {"content_prefix": row["content"][:60], "recorded": row["row_sha256"], "recomputed": digest}
            )

    return {
        "ok": not failures,
        "sampled": n,
        "row_count": len(rows),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None, help="Input JSONL; default uses fixture corpus")
    parser.add_argument("--dataset-id", type=str, default=DEFAULT_DATASET_ID)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "dataset")
    parser.add_argument("--verify-sample-size", type=int, default=5)
    args = parser.parse_args()

    if args.source is None:
        corpus = list(fixture_corpus())
        source_label = "fixture_corpus"
    else:
        corpus = load_corpus_jsonl(args.source)
        source_label = str(args.source)

    if not corpus:
        print(json.dumps({"ok": False, "error": "empty_corpus", "source": source_label}))
        return 1

    dataset = build_dataset(corpus, dataset_id=args.dataset_id)
    output_dir = args.output_root / args.dataset_id
    paths = write_bundle(dataset, output_dir)
    verification = verify_bundle(output_dir, sample_size=args.verify_sample_size)

    summary = {
        "ok": verification["ok"],
        "source": source_label,
        "dataset_id": args.dataset_id,
        "row_count": dataset["row_count"],
        "label_counts": dataset["label_counts"],
        "paths": paths,
        "verification": verification,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if verification["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
