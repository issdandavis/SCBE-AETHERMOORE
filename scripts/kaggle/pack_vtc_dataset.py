"""Pack the frozen VTC corpus as a Kaggle dataset upload folder.

The VTC training notebook can consume this folder from `/kaggle/input/...`.
This script does not upload anything; it only creates a small, checksum-stamped
dataset directory that can be uploaded with Kaggle's UI or CLI.

Example:
    python scripts/kaggle/pack_vtc_dataset.py
    kaggle datasets create -p artifacts/kaggle/vtc-mbpp-refined
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "training-data" / "sft" / "vtc_mbpp_refined.jsonl"
DEFAULT_MANIFEST = ROOT / "training-data" / "sft" / "vtc_mbpp_refined.manifest.json"
DEFAULT_OUT = ROOT / "artifacts" / "kaggle" / "vtc-mbpp-refined"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_jsonl(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def pack(corpus: Path = DEFAULT_CORPUS, manifest: Path = DEFAULT_MANIFEST, out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    if not corpus.exists():
        raise FileNotFoundError(f"missing VTC corpus: {corpus}")
    if not manifest.exists():
        raise FileNotFoundError(f"missing VTC manifest: {manifest}")

    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_out = out_dir / corpus.name
    manifest_out = out_dir / manifest.name
    shutil.copy2(corpus, corpus_out)
    shutil.copy2(manifest, manifest_out)

    upstream_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    row_count = _count_jsonl(corpus_out)
    digest = _sha256(corpus_out)
    kaggle_metadata = {
        "title": "SCBE VTC MBPP Refined",
        "id": "issdandavis/vtc-mbpp-refined",
        "licenses": [{"name": "CC0-1.0"}],
    }
    dataset_manifest = {
        "schema": "scbe_vtc_kaggle_dataset_v1",
        "corpus_file": corpus_out.name,
        "manifest_file": manifest_out.name,
        "rows": row_count,
        "sha256": digest,
        "source_manifest": upstream_manifest,
        "kaggle_dataset_id": kaggle_metadata["id"],
        "notebook_hint": "Add this dataset to notebooks/vtc_lift_qwen15_colab.ipynb; Kaggle mounts it under /kaggle/input/vtc-mbpp-refined/.",
    }
    (out_dir / "dataset-metadata.json").write_text(json.dumps(kaggle_metadata, indent=2), encoding="utf-8")
    (out_dir / "vtc_kaggle_manifest.json").write_text(json.dumps(dataset_manifest, indent=2), encoding="utf-8")
    return {
        "out_dir": str(out_dir),
        "corpus": str(corpus_out),
        "manifest": str(manifest_out),
        "rows": row_count,
        "sha256": digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Kaggle upload folder for the frozen VTC MBPP corpus")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    result = pack(Path(args.corpus), Path(args.manifest), Path(args.out_dir))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
