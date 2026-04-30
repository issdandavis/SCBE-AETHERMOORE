#!/usr/bin/env python3
"""Build external poly-encoded coding task SFT records.

The input catalog points at public source families (SAM.gov, DARPA, NASA,
Kaggle, Hugging Face/BigCode) but this builder emits generated seed tasks, not
copied third-party code. Each task is encoded as one contract across language
lenses, binary/hex transport, CA operation hints, and GeoSeal tokenizer metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "config" / "training" / "poly_coding_source_catalog.json"
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"

LANGUAGE_TONGUES = {
    "python": {"tongue": "KO", "tongue_name": "Kor'aelin"},
    "typescript": {"tongue": "AV", "tongue_name": "Avali"},
    "rust": {"tongue": "RU", "tongue_name": "Runethic"},
    "c": {"tongue": "CA", "tongue_name": "Cassisivadan"},
    "haskell": {"tongue": "DR", "tongue_name": "Draumric"},
    "java": {"tongue": "AV", "tongue_name": "Avali"},
}

CA_OPCODES = {
    "add": "0x00",
    "sub": "0x01",
    "div": "0x03",
    "min": "0x27",
    "max": "0x28",
    "within": "0x2A",
    "lt": "0x22",
    "gte": "0x25",
    "eq": "0x20",
    "map": "0x39",
    "filter": "0x38",
}

SYSTEM_PROMPT = (
    "You are an SCBE-AETHERMOORE coding-data compiler. Preserve one task contract "
    "across language lenses, binary/hex transport, CA operation hints, and GeoSeal "
    "tokenizer metadata. Do not treat transport bytes as user-facing canon."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _transport(text: str) -> dict[str, Any]:
    raw = text.encode("utf-8")
    return {
        "encoding": "utf-8",
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "hex_prefix": raw.hex()[:96],
        "binary_prefix": " ".join(f"{byte:08b}" for byte in raw[:12]),
        "round_trip_ok": raw.decode("utf-8") == text,
    }


def _python_code(task_id: str) -> str:
    if task_id == "external_safe_divide":
        return "def safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n"
    if task_id == "external_parse_json_name":
        return (
            "import json\n\n"
            "def parse_json_name(payload: str):\n"
            "    try:\n"
            "        data = json.loads(payload)\n"
            "    except Exception:\n"
            "        return None\n"
            "    return data.get('name')\n"
        )
    if task_id == "external_grid_neighbors":
        return (
            "def grid_neighbors(row: int, col: int, rows: int, cols: int):\n"
            "    out = []\n"
            "    for r, c in ((row - 1, col), (row, col - 1), (row, col + 1), (row + 1, col)):\n"
            "        if 0 <= r < rows and 0 <= c < cols:\n"
            "            out.append((r, c))\n"
            "    return out\n"
        )
    if task_id == "external_patch_bounds_check":
        return "def read_at(buf, idx):\n    if idx < 0 or idx >= len(buf):\n        return None\n    return buf[idx]\n"
    if task_id == "external_normalize_scores":
        return (
            "def normalize_scores(values):\n"
            "    if not values:\n"
            "        return []\n"
            "    lo, hi = min(values), max(values)\n"
            "    if hi == lo:\n"
            "        return [0.0 for _ in values]\n"
            "    return [(value - lo) / (hi - lo) for value in values]\n"
        )
    raise KeyError(task_id)


def _typescript_code(task_id: str) -> str:
    if task_id == "external_safe_divide":
        return "export function safeDivide(a: number, b: number): number | null {\n  return b === 0 ? null : a / b;\n}\n"
    if task_id == "external_parse_json_name":
        return (
            "export function parseJsonName(payload: string): string | null {\n"
            "  try {\n"
            "    const data = JSON.parse(payload);\n"
            "    return typeof data.name === 'string' ? data.name : null;\n"
            "  } catch {\n"
            "    return null;\n"
            "  }\n"
            "}\n"
        )
    if task_id == "external_grid_neighbors":
        return (
            "export function gridNeighbors(row: number, col: number, rows: number, cols: number): [number, number][] {\n"
            "  return [[row - 1, col], [row, col - 1], [row, col + 1], [row + 1, col]]\n"
            "    .filter(([r, c]) => r >= 0 && r < rows && c >= 0 && c < cols) as [number, number][];\n"
            "}\n"
        )
    if task_id == "external_patch_bounds_check":
        return "export function readAt<T>(buf: T[], idx: number): T | null {\n  return idx < 0 || idx >= buf.length ? null : buf[idx];\n}\n"
    if task_id == "external_normalize_scores":
        return (
            "export function normalizeScores(values: number[]): number[] {\n"
            "  if (values.length === 0) return [];\n"
            "  const lo = Math.min(...values), hi = Math.max(...values);\n"
            "  return hi === lo ? values.map(() => 0) : values.map((value) => (value - lo) / (hi - lo));\n"
            "}\n"
        )
    raise KeyError(task_id)


def _rust_code(task_id: str) -> str:
    if task_id == "external_safe_divide":
        return "fn safe_divide(a: f64, b: f64) -> Option<f64> {\n    if b == 0.0 { None } else { Some(a / b) }\n}\n"
    if task_id == "external_parse_json_name":
        return (
            "fn parse_json_name(payload: &str) -> Option<String> {\n"
            "    let data: serde_json::Value = serde_json::from_str(payload).ok()?;\n"
            "    data.get(\"name\")?.as_str().map(|s| s.to_string())\n"
            "}\n"
        )
    if task_id == "external_grid_neighbors":
        return (
            "fn grid_neighbors(row: i32, col: i32, rows: i32, cols: i32) -> Vec<(i32, i32)> {\n"
            "    [(row - 1, col), (row, col - 1), (row, col + 1), (row + 1, col)]\n"
            "        .into_iter().filter(|(r, c)| *r >= 0 && *r < rows && *c >= 0 && *c < cols).collect()\n"
            "}\n"
        )
    if task_id == "external_patch_bounds_check":
        return "fn read_at<T: Copy>(buf: &[T], idx: isize) -> Option<T> {\n    if idx < 0 { None } else { buf.get(idx as usize).copied() }\n}\n"
    if task_id == "external_normalize_scores":
        return (
            "fn normalize_scores(values: &[f64]) -> Vec<f64> {\n"
            "    if values.is_empty() { return vec![]; }\n"
            "    let lo = values.iter().copied().fold(f64::INFINITY, f64::min);\n"
            "    let hi = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);\n"
            "    if hi == lo { vec![0.0; values.len()] } else { values.iter().map(|v| (v - lo) / (hi - lo)).collect() }\n"
            "}\n"
        )
    raise KeyError(task_id)


def _java_code(task_id: str) -> str:
    if task_id == "external_safe_divide":
        return "static Double safeDivide(double a, double b) {\n    return b == 0.0 ? null : a / b;\n}\n"
    if task_id == "external_patch_bounds_check":
        return "static <T> T readAt(java.util.List<T> buf, int idx) {\n    return idx < 0 || idx >= buf.size() ? null : buf.get(idx);\n}\n"
    return "// Java lens is planned for this task; preserve the canonical contract before implementation.\n"


def _c_code(task_id: str) -> str:
    if task_id == "external_safe_divide":
        return "int safe_divide(double a, double b, double *out) {\n    if (b == 0.0) return 0;\n    *out = a / b;\n    return 1;\n}\n"
    if task_id == "external_patch_bounds_check":
        return "int read_at(const int *buf, int len, int idx, int *out) {\n    if (idx < 0 || idx >= len) return 0;\n    *out = buf[idx];\n    return 1;\n}\n"
    return "/* C lens planned: preserve bounds, null/error return, and deterministic contract. */\n"


def _haskell_code(task_id: str) -> str:
    if task_id == "external_safe_divide":
        return "safeDivide :: Double -> Double -> Maybe Double\nsafeDivide _ 0 = Nothing\nsafeDivide a b = Just (a / b)\n"
    if task_id == "external_patch_bounds_check":
        return "readAt :: [a] -> Int -> Maybe a\nreadAt xs i | i < 0 = Nothing\nreadAt xs i = if i >= length xs then Nothing else Just (xs !! i)\n"
    return "-- Haskell lens planned: preserve Maybe-based guard behavior.\n"


CODE_GENERATORS = {
    "python": _python_code,
    "typescript": _typescript_code,
    "rust": _rust_code,
    "c": _c_code,
    "haskell": _haskell_code,
    "java": _java_code,
}


def _ca_plan(ops: list[str]) -> dict[str, Any]:
    return {
        "ops": ops,
        "hex_sequence": [CA_OPCODES[op] for op in ops if op in CA_OPCODES],
        "missing_ops": [op for op in ops if op not in CA_OPCODES],
        "source": "python.scbe.ca_opcode_table.OP_TABLE",
    }


def _lens(language: str, task_id: str) -> dict[str, Any]:
    code = CODE_GENERATORS[language](task_id)
    meta = LANGUAGE_TONGUES[language]
    return {
        "language": language,
        "tongue": meta["tongue"],
        "tongue_name": meta["tongue_name"],
        "code": code,
        "transport": _transport(code),
    }


def build_record(task: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    lenses = [_lens(language, task["task_id"]) for language in LANGUAGE_TONGUES]
    python_code = next(lens["code"] for lens in lenses if lens["language"] == "python")
    payload = {
        "schema_version": "scbe_external_poly_coding_answer_v1",
        "task_id": task["task_id"],
        "source": {
            "source_id": source["source_id"],
            "source_family": task["source_family"],
            "source_url": source["source_url"],
            "license_or_terms": source["license_or_terms"],
            "ingest_status": source["ingest_status"],
            "allowed_use": source["allowed_use"],
            "blocked_use": source["blocked_use"],
        },
        "contract": task["contract"],
        "instruction": task["instruction"],
        "operation_plan": task["operation_plan"],
        "ca_operation_hints": _ca_plan(task["operation_plan"]),
        "canonical_python_transport": _transport(python_code),
        "language_lenses": lenses,
        "geoseal_tokenizer": {
            "role": "cross_domain_agent_substrate",
            "transport_boundary": "semantic contract is upstream; bytes/hex are downstream transport",
            "bijective_checks": {
                "all_lens_utf8_round_trip": all(lens["transport"]["round_trip_ok"] for lens in lenses),
                "python_sha256": _sha(python_code),
            },
        },
        "training_tags": [
            "external_poly_coding",
            "multi_language_lens",
            "binary_hex_transport",
            "geoseal_tokenizer",
            task["domain"],
        ],
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task["instruction"]},
            {"role": "assistant", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
        ],
        "metadata": {
            "source": "build_external_poly_coding_sft",
            "task_id": task["task_id"],
            "source_family": task["source_family"],
            "domain": task["domain"],
            "created_at": _utc_now(),
            "content_sha256": _sha(json.dumps(payload, sort_keys=True)),
        },
    }


def build_dataset(catalog_path: Path) -> dict[str, Any]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    sources = {row["source_id"]: row for row in catalog["sources"]}
    records = []
    for task in catalog["seed_tasks"]:
        source = sources[task["source_family"]]
        records.append(build_record(task, source))
    holdout = records[-1:]
    train = records[:-1]
    return {
        "schema_version": "scbe_external_poly_coding_dataset_v1",
        "catalog": catalog,
        "train": train,
        "holdout": holdout,
    }


def write_outputs(dataset: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "external_poly_coding_v1_train.sft.jsonl"
    holdout_path = out_dir / "external_poly_coding_v1_holdout.sft.jsonl"
    manifest_path = out_dir / "external_poly_coding_v1_manifest.json"
    for path, rows in ((train_path, dataset["train"]), (holdout_path, dataset["holdout"])):
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "schema_version": "scbe_external_poly_coding_manifest_v1",
        "created_at": _utc_now(),
        "catalog_schema": dataset["catalog"]["schema_version"],
        "source_count": len(dataset["catalog"]["sources"]),
        "seed_task_count": len(dataset["catalog"]["seed_tasks"]),
        "train_count": len(dataset["train"]),
        "holdout_count": len(dataset["holdout"]),
        "outputs": {
            "train": str(train_path),
            "holdout": str(holdout_path),
        },
        "source_ids": [row["source_id"] for row in dataset["catalog"]["sources"]],
        "policy": dataset["catalog"]["policy"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return {"train": str(train_path), "holdout": str(holdout_path), "manifest": str(manifest_path), "summary": manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    dataset = build_dataset(args.catalog)
    result = write_outputs(dataset, args.out_dir)
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
