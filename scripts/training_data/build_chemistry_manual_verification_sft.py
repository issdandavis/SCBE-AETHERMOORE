"""Convert manual chemistry verification rows into SFT training pairs.

The source dataset is intentionally "by hand": every molecule carries valence,
electronegativity, functional-group, bond, and governance expectations.  This
builder turns those rows into compact instruction records that teach the model
to walk the verification path instead of only guessing a chemistry label.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "training-data" / "chemistry_manual_verification_v1.jsonl"
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN_OUT = SFT_ROOT / "chemistry_manual_verification_v1_train.sft.jsonl"
EVAL_OUT = SFT_ROOT / "chemistry_manual_verification_v1_eval.sft.jsonl"
MANIFEST_OUT = SFT_ROOT / "chemistry_manual_verification_v1_sft_manifest.json"
KAGGLE_MIRROR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-coding-agent-stage6-repair-v7"

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE chemistry verification agent. Run the chemistry path explicitly: "
    "SMILES to atoms, bonds, valence, electronegativity, functional group, RDKit validity, SCBE fusion, "
    "and governance verdict. Keep material chemistry separate from structural chemistry metaphors."
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def assistant_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "scbe_chemistry_manual_verification_answer_v1",
        "molecule": {
            "name": row["name"],
            "smiles": row["smiles"],
            "expected_elements": row["expected_elements"],
            "expected_family": row["expected_family"],
        },
        "manual_path": {
            "valence": row["manual_valence_check"],
            "electronegativity": row["manual_electronegativity"],
            "functional_group": row["manual_functional_group"],
            "bond_analysis": row["manual_bond_analysis"],
        },
        "verification_plan": row["required_checks"],
        "scbe_expectations": {
            "tau_hat_signs": row["expected_tau_hat_signs"],
            "coherence_range": row["expected_coherence_range"],
            "valence_pressure_range": row["expected_valence_pressure_range"],
        },
        "verdict": {
            "expected_valid": row["expected_valid"],
            "expected_governance": row["expected_governance"],
            "promotion_rule": (
                "PASS only when external chemistry validity, manual arithmetic, and SCBE fusion expectations "
                "agree; HOLD or DENY otherwise."
            ),
        },
    }


def make_record(row: dict[str, Any], split: str, index: int, dataset_name: str, source_path: Path) -> dict[str, Any]:
    stable_id = sha256_text(
        "|".join(
            [
                dataset_name,
                split,
                row["name"],
                row["smiles"],
                str(index),
            ]
        )
    )[:16]
    user_prompt = (
        f"Verify molecule `{row['name']}` with SMILES `{row['smiles']}`. "
        "Show the manual chemistry checks and return the SCBE governance verdict."
    )
    return {
        "id": f"{dataset_name}_{row['name']}_{stable_id}",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {
                "role": "assistant",
                "content": json.dumps(assistant_payload(row), ensure_ascii=False, sort_keys=True),
            },
        ],
        "metadata": {
            "track": dataset_name,
            "split": split,
            "source_file": str(source_path.relative_to(REPO_ROOT)),
            "source": row["source"],
            "difficulty": row["difficulty"],
            "expected_governance": row["expected_governance"],
            "expected_valid": row["expected_valid"],
            "tags": row["tags"],
            "training_pattern": "predict_verify_receipt_promote",
        },
    }


def split_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        # Keep one held-out example per source bucket when possible, with a
        # deterministic fallback every fifth row.
        if index % 5 == 4 or row["name"] in {"aspirin", "pentavalent_carbon"}:
            eval_rows.append(row)
        else:
            train.append(row)
    return train, eval_rows


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _paths_for_source(source_path: Path) -> tuple[str, Path, Path, Path]:
    dataset_name = source_path.stem
    if source_path == SOURCE_PATH:
        return dataset_name, TRAIN_OUT, EVAL_OUT, MANIFEST_OUT
    return (
        dataset_name,
        SFT_ROOT / f"{dataset_name}_train.sft.jsonl",
        SFT_ROOT / f"{dataset_name}_eval.sft.jsonl",
        SFT_ROOT / f"{dataset_name}_sft_manifest.json",
    )


def build(copy_kaggle: bool = False, source_path: Path | None = None) -> dict[str, Any]:
    source_path = (source_path or SOURCE_PATH).resolve()
    dataset_name, train_out, eval_out, manifest_out = _paths_for_source(source_path)
    rows = load_jsonl(source_path)
    train_raw, eval_raw = split_rows(rows)
    train_rows = [make_record(row, "train", index, dataset_name, source_path) for index, row in enumerate(train_raw)]
    eval_rows = [make_record(row, "eval", index, dataset_name, source_path) for index, row in enumerate(eval_raw)]

    write_jsonl(train_out, train_rows)
    write_jsonl(eval_out, eval_rows)

    manifest = {
        "schema_version": "chemistry_manual_verification_sft_manifest_v1",
        "dataset_name": dataset_name,
        "source": str(source_path.relative_to(REPO_ROOT)),
        "outputs": {
            "train": str(train_out.relative_to(REPO_ROOT)),
            "eval": str(eval_out.relative_to(REPO_ROOT)),
        },
        "row_counts": {"source": len(rows), "train": len(train_rows), "eval": len(eval_rows)},
        "training_pattern": "predict_verify_receipt_promote",
        "gates": [
            "RDKit parse or explicit invalid rejection",
            "manual valence arithmetic",
            "manual electronegativity and functional-group explanation",
            "SCBE 9D chemistry fusion expectations",
            "governance verdict agreement",
        ],
        "hashes": {
            "source_sha256": file_sha256(source_path),
            "train_sha256": file_sha256(train_out),
            "eval_sha256": file_sha256(eval_out),
        },
    }
    manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    if copy_kaggle:
        KAGGLE_MIRROR.mkdir(parents=True, exist_ok=True)
        for path in (train_out, eval_out, manifest_out):
            shutil.copy2(path, KAGGLE_MIRROR / path.name)
        manifest["kaggle_mirror"] = str(KAGGLE_MIRROR.relative_to(REPO_ROOT))

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(SOURCE_PATH), help="Source chemistry manual verification JSONL.")
    parser.add_argument(
        "--copy-kaggle", action="store_true", help="Copy outputs into the active Kaggle dataset mirror."
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable manifest summary.")
    args = parser.parse_args()

    manifest = build(copy_kaggle=args.copy_kaggle, source_path=Path(args.source))
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"[chemistry_manual_sft] dataset -> {manifest['dataset_name']}")
        print(
            f"[chemistry_manual_sft] train rows -> {manifest['row_counts']['train']} at {manifest['outputs']['train']}"
        )
        print(f"[chemistry_manual_sft] eval rows -> {manifest['row_counts']['eval']} at {manifest['outputs']['eval']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
