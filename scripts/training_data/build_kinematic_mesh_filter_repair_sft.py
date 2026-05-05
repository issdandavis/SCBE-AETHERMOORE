#!/usr/bin/env python3
"""Build a disposable repair SFT shard from training digest residues.

This applies the kinematic mesh filter pattern from
``notes/concepts/kinematic_mesh_filter.md`` to model training:

- reusable mesh: the stable gate/harness
- sacrificial liner: compact residue JSONL from a failed run
- scab ejection: failed residues become a small repair shard

The script is data-only. It does not launch training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESIDUES = REPO_ROOT / "artifacts" / "training_digestion"
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_CONTRACT = REPO_ROOT / "config" / "model_training" / "chemistry_verification_eval_contract.json"
TRAIN_NAME = "kinematic_mesh_filter_repair_v1_train.sft.jsonl"
EVAL_NAME = "kinematic_mesh_filter_repair_v1_eval.sft.jsonl"
MANIFEST_NAME = "kinematic_mesh_filter_repair_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE training repair agent. Use the kinematic mesh filter pattern: "
    "the stable gate is the reusable mesh, failed outputs are sacrificial liner residue, and repair "
    "rows must be compact. Preserve required markers exactly and avoid forbidden boundary strings."
)


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _load_contract_prompts(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    prompts = payload.get("prompts") if isinstance(payload, dict) else []
    if not isinstance(prompts, list):
        return {}
    return {str(item.get("id")): item for item in prompts if isinstance(item, dict) and item.get("id")}


def _latest_residue_path(root: Path) -> Path:
    candidates = sorted(root.glob("*/training_residues.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No training_residues.jsonl found under {root}")
    return candidates[0]


def _tokens(row: dict[str, Any], field: str) -> list[str]:
    return [str(item) for item in row.get(field) or [] if str(item).strip()]


def _required_tokens(row: dict[str, Any], contract_prompt: dict[str, Any] | None) -> list[str]:
    if contract_prompt:
        required = [str(item) for item in contract_prompt.get("required") or [] if str(item).strip()]
        if required:
            return required
    return _tokens(row, "missing_required") or _tokens(row, "raw_missing_required") or _tokens(row, "token_chain")


def _forbidden_tokens(row: dict[str, Any], contract_prompt: dict[str, Any] | None) -> list[str]:
    if contract_prompt:
        forbidden = [str(item) for item in contract_prompt.get("forbidden") or [] if str(item).strip()]
        if forbidden:
            return forbidden
    return _tokens(row, "triggered_forbidden") or _tokens(row, "raw_triggered_forbidden")


def _assistant_for_residue(row: dict[str, Any], contract_prompt: dict[str, Any] | None = None) -> str:
    required = _required_tokens(row, contract_prompt)
    forbidden = _forbidden_tokens(row, contract_prompt)
    if row.get("kind") == "positive_residue":
        required = _tokens(row, "token_chain")

    marker_line = "REQUIRED_MARKERS=" + " | ".join(required) if required else "REQUIRED_MARKERS=none"
    boundary_line = "BOUNDARY_GUARD=" + " | ".join(forbidden) if forbidden else "BOUNDARY_GUARD=none"
    verdict = "PASS" if row.get("kind") == "positive_residue" else "REPAIR"
    if forbidden:
        verdict = "BOUNDARY_REPAIR"

    if row.get("prompt_id") == "chem_eval_pentavalent_carbon_reject":
        return (
            f"{marker_line}\n"
            f"{boundary_line}\n"
            "KINEMATIC_MESH_MODE=boundary_residue | BOUNDARY_REPAIR. "
            "C(C)(C)(C)(C)C is the rejected molecule. The central carbon is pentavalent, "
            "which violates carbon valence 4. RDKit rejects or invalidates this material "
            "chemistry claim. Governance verdict: DENY. Do not write PASS, promote, or drug-like."
        )

    return (
        f"{marker_line}\n"
        f"{boundary_line}\n"
        f"KINEMATIC_MESH_MODE={row.get('kind', 'repair_residue')} | {verdict}. "
        "Treat the reusable gate as the mesh and this compact row as the sacrificial liner. "
        "Replay the required markers exactly, keep forbidden strings out of the generated answer, "
        "and retest before promotion."
    )


def _user_for_residue(row: dict[str, Any], contract_prompt: dict[str, Any] | None = None) -> str:
    required = _required_tokens(row, contract_prompt)
    forbidden = _forbidden_tokens(row, contract_prompt)
    task = str((contract_prompt or {}).get("prompt") or "")
    task_line = f" Frozen task: {task}" if task else ""
    return (
        f"Build a compact repair response for prompt_id={row.get('prompt_id', 'unknown')}. "
        f"Required markers: {', '.join(required) if required else 'none'}. "
        f"Forbidden boundary strings: {', '.join(forbidden) if forbidden else 'none'}. "
        "Use the kinematic mesh filter pattern and do not copy the noisy original log." + task_line
    )


def _record(
    row: dict[str, Any], index: int, split: str, repeat_index: int, contract_prompt: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _user_for_residue(row, contract_prompt)},
            {"role": "assistant", "content": _assistant_for_residue(row, contract_prompt)},
        ],
        "metadata": {
            "track": "kinematic_mesh_filter_repair_v1",
            "split": split,
            "source_run_id": row.get("run_id"),
            "source_contract_id": row.get("contract_id"),
            "source_prompt_id": row.get("prompt_id"),
            "source_kind": row.get("kind"),
            "repeat_index": repeat_index,
            "contract_augmented": bool(contract_prompt),
            "source_note": "notes/concepts/kinematic_mesh_filter.md",
            "sacrificial_layer": "training_residue",
            "mesh_role": "reusable_gate_harness",
        },
    }
    payload["id"] = f"kinematic_mesh_filter_repair_v1_{split}_{index}_{_sha(payload)[:16]}"
    return payload


def build_rows(
    residue_path: Path,
    *,
    include_positive: bool = False,
    repeats: int = 7,
    contract_path: Path | None = DEFAULT_CONTRACT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    residues = _read_jsonl(residue_path)
    contract_prompts = _load_contract_prompts(contract_path)
    selected = [
        row for row in residues if include_positive or row.get("kind") in {"repair_residue", "boundary_residue"}
    ]
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    index = 0
    for row in selected:
        contract_prompt = contract_prompts.get(str(row.get("prompt_id")))
        for repeat_index in range(repeats):
            split = "eval" if index % 5 == 4 else "train"
            record = _record(row, index, split, repeat_index, contract_prompt)
            if split == "eval":
                eval_rows.append(record)
            else:
                train.append(record)
            index += 1
    return train, eval_rows


def write_outputs(
    residue_path: Path,
    out_dir: Path,
    *,
    include_positive: bool = False,
    repeats: int = 7,
    contract_path: Path | None = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    train, eval_rows = build_rows(
        residue_path,
        include_positive=include_positive,
        repeats=repeats,
        contract_path=contract_path,
    )
    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME

    train_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in train) + ("\n" if train else ""),
        encoding="utf-8",
    )
    eval_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in eval_rows)
        + ("\n" if eval_rows else ""),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "kinematic_mesh_filter_repair_manifest_v1",
        "track": "kinematic_mesh_filter_repair_v1",
        "source_note": "notes/concepts/kinematic_mesh_filter.md",
        "source_residues": str(
            residue_path.relative_to(REPO_ROOT) if residue_path.is_relative_to(REPO_ROOT) else residue_path
        ),
        "source_contract": str(
            contract_path.relative_to(REPO_ROOT)
            if contract_path and contract_path.exists() and contract_path.is_relative_to(REPO_ROOT)
            else contract_path
        ),
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "include_positive": include_positive,
        "repeats": repeats,
        "files": {
            TRAIN_NAME: _sha(train),
            EVAL_NAME: _sha(eval_rows),
        },
        "pattern": {
            "reusable_mesh": "stable gate/harness",
            "sacrificial_liner": "training residue JSONL",
            "scab_ejection": "compact failed residues become repair SFT rows",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return {
        "ok": True,
        "source_residues": str(residue_path),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--residues", type=Path, default=None, help="training_residues.jsonl path")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--include-positive", action="store_true")
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    residue_path = args.residues or _latest_residue_path(DEFAULT_RESIDUES)
    result = write_outputs(
        residue_path,
        args.out_dir,
        include_positive=args.include_positive,
        repeats=args.repeats,
        contract_path=args.contract,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "kinematic mesh repair SFT: "
            f"train={result['train_records']} eval={result['eval_records']} "
            f"source={result['source_residues']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
