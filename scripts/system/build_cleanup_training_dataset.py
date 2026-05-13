#!/usr/bin/env python3
"""Build and publish metadata-only cleanup training data.

This turns local storage cleanup decisions into SFT-ready records without
uploading raw caches, logs, model blobs, credentials, or private file content.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "training" / "system_hygiene_cleanup"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-system-hygiene-training"
DEFAULT_HF_REPO = "issdandavis/scbe-system-hygiene-training-data"
DEFAULT_KAGGLE_OWNER = os.environ.get("KAGGLE_USERNAME", "issacizrealdavis")
DEFAULT_KAGGLE_SLUG = "scbe-system-hygiene-training"
SCHEMA_VERSION = "scbe_system_hygiene_training_v1"

SECRET_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9_=-]{12,}"),
    re.compile(r"KG[A-Za-z0-9_=-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_=-]{12,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
]

MODEL_DECISIONS = {
    "qwen2.5-coder:1.5b": {
        "decision": "keep",
        "risk": "low",
        "reason": "Default local coding model and benchmark fallback for agent/harness runs.",
        "harness_role": "coding_default",
    },
    "openclaw:latest": {
        "decision": "keep",
        "risk": "low",
        "reason": "Used by Kaggle roundtrip and OpenClaw swarm benchmark paths.",
        "harness_role": "roundtrip_swarm",
    },
    "gemma3:1b": {
        "decision": "keep",
        "risk": "low",
        "reason": "Small governance/gate comparison model.",
        "harness_role": "governance_baseline",
    },
    "scbe-geoseal-coder:q8": {
        "decision": "keep",
        "risk": "low",
        "reason": "SCBE GeoSeal coder baseline for gate and classifier smoke paths.",
        "harness_role": "geoseal_baseline",
    },
    "qwen2.5:3b-instruct": {
        "decision": "keep",
        "risk": "medium",
        "reason": "General instruction fallback and stronger small-model comparison lane.",
        "harness_role": "instruction_fallback",
    },
    "qwen2.5-coder:0.5b": {
        "decision": "keep",
        "risk": "low",
        "reason": "Cheap tiny coder for route and budget comparisons.",
        "harness_role": "tiny_coder",
    },
    "qwen2.5:7b-instruct": {
        "decision": "review",
        "risk": "medium",
        "reason": "Useful as a stronger reference model, but it is the largest local Ollama entry.",
        "harness_role": "strong_reference",
    },
    "llama-guard3:1b": {
        "decision": "review",
        "risk": "medium",
        "reason": "Possible safety baseline, but no direct repo harness reference was found in the current scan.",
        "harness_role": "safety_candidate",
    },
}

CACHE_DECISIONS = [
    {
        "label": "SCBE cache temp",
        "path": r"C:\SCBE_CACHE\temp",
        "decision": "cleanup_candidate",
        "risk": "low",
        "reason": "Regenerable temporary workspace; preserve only metadata and manifests.",
    },
    {
        "label": "SCBE npm cache",
        "path": r"C:\SCBE_CACHE\npm",
        "decision": "cleanup_candidate",
        "risk": "low",
        "reason": "Package cache can be rebuilt from lockfiles.",
    },
    {
        "label": "SCBE uv cache",
        "path": r"C:\SCBE_CACHE\uv",
        "decision": "cleanup_candidate",
        "risk": "low",
        "reason": "Python package cache can be recreated from dependency specs.",
    },
    {
        "label": "SCBE Playwright cache",
        "path": r"C:\SCBE_CACHE\playwright",
        "decision": "review",
        "risk": "medium",
        "reason": "Regenerable browser binaries, but removing them may break local e2e runs until reinstalled.",
    },
    {
        "label": "SCBE virtualenv cache",
        "path": r"C:\SCBE_CACHE\venvs",
        "decision": "review",
        "risk": "medium",
        "reason": "Often rebuildable, but some envs may encode local test state; verify before deletion.",
    },
    {
        "label": "SCBE Hugging Face cache",
        "path": r"C:\SCBE_CACHE\hf",
        "decision": "review",
        "risk": "medium",
        "reason": "Can be re-downloaded, but large datasets/models may be slow or rate-limited.",
    },
    {
        "label": "GGUF work cache",
        "path": r"C:\SCBE_CACHE\gguf-work",
        "decision": "review",
        "risk": "medium",
        "reason": "Intermediate model work may be expensive to regenerate; keep manifests before pruning.",
    },
]


@dataclass(frozen=True)
class InventoryRow:
    label: str
    path: str
    size_bytes: int
    source_kind: str
    decision: str
    risk: str
    reason: str
    harness_role: str = ""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_text(value: str) -> str:
    out = value
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def public_path(path: str | Path) -> str:
    raw = str(path)
    home = str(Path.home())
    replacements = {
        str(REPO_ROOT): "%REPO%",
        home: "%USERPROFILE%",
        r"C:\SCBE_CACHE": "%SCBE_CACHE%",
    }
    normalized = raw
    for src, dst in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(src, dst)
    return redact_text(normalized)


def safe_dir_size(path: Path, max_files: int = 25000) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    seen = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {".git", ".roots", "node_modules", "__pycache__"}]
        for name in files:
            seen += 1
            if seen > max_files:
                return total
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return total


def run_ollama_list() -> list[dict[str, Any]]:
    if not shutil.which("ollama"):
        return []
    try:
        proc = subprocess.run(
            ["ollama", "list"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []

    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[0]
        size_text = " ".join(parts[2:4])
        rows.append({"name": name, "size_text": size_text})
    return rows


def parse_size_text(size_text: str) -> int:
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([KMGT]B)\s*$", size_text, flags=re.IGNORECASE)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2).upper()
    multiplier = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}[unit]
    return int(value * multiplier)


def collect_inventory() -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    for item in CACHE_DECISIONS:
        path = Path(item["path"])
        rows.append(
            InventoryRow(
                label=item["label"],
                path=public_path(path),
                size_bytes=safe_dir_size(path),
                source_kind="cleanup_candidate",
                decision=item["decision"],
                risk=item["risk"],
                reason=item["reason"],
            )
        )

    for model in run_ollama_list():
        name = str(model["name"])
        decision = MODEL_DECISIONS.get(
            name,
            {
                "decision": "review",
                "risk": "medium",
                "reason": "Model was present locally but has not been classified by the harness retention map.",
                "harness_role": "unclassified_model",
            },
        )
        rows.append(
            InventoryRow(
                label=name,
                path="%USERPROFILE%\\.ollama\\models",
                size_bytes=parse_size_text(str(model.get("size_text", ""))),
                source_kind="local_model",
                decision=decision["decision"],
                risk=decision["risk"],
                reason=decision["reason"],
                harness_role=decision["harness_role"],
            )
        )

    return rows


def record_id(row: InventoryRow) -> str:
    digest = hashlib.sha256(f"{row.source_kind}|{row.label}|{row.path}".encode("utf-8")).hexdigest()[:16]
    return f"system-hygiene-{digest}"


def build_record(row: InventoryRow, created_at: str) -> dict[str, Any]:
    size_gb = round(row.size_bytes / (1024**3), 3)
    user_prompt = (
        "Given this Windows SCBE cleanup inventory item, decide whether it should be kept, reviewed, "
        "turned into metadata-only training data, or deleted.\n\n"
        f"Item: {row.label}\n"
        f"Path: {row.path}\n"
        f"Kind: {row.source_kind}\n"
        f"Approx size GB: {size_gb}"
    )
    assistant = (
        f"Decision: {row.decision}. Risk: {row.risk}. Convert the cleanup lesson into metadata-only "
        f"training data for Hugging Face and Kaggle, but do not upload raw files, caches, model weights, "
        f"logs, local database contents, or secrets. Rationale: {row.reason}"
    )
    if row.harness_role:
        assistant += f" Harness role: {row.harness_role}."

    payload = {
        "schema": SCHEMA_VERSION,
        "id": record_id(row),
        "created_at_utc": created_at,
        "source_kind": row.source_kind,
        "label": redact_text(row.label),
        "path": row.path,
        "size_bytes": row.size_bytes,
        "size_gb": size_gb,
        "decision": row.decision,
        "risk": row.risk,
        "reason": redact_text(row.reason),
        "harness_role": row.harness_role,
        "platform_targets": ["huggingface", "kaggle"],
        "privacy": "metadata_only",
        "messages": [
            {"role": "system", "content": "You are an SCBE local-first system hygiene and training-data curator."},
            {"role": "user", "content": redact_text(user_prompt)},
            {"role": "assistant", "content": redact_text(assistant)},
        ],
    }
    payload["source_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return payload


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "source_kind", "label", "path", "size_gb", "decision", "risk", "harness_role", "privacy"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fields})


def write_readme(path: Path, records: list[dict[str, Any]], created_at: str, title: str) -> None:
    keep = sum(1 for record in records if record["decision"] == "keep")
    review = sum(1 for record in records if record["decision"] == "review")
    cleanup = sum(1 for record in records if record["decision"] == "cleanup_candidate")
    text = f"""---
license: cc-by-4.0
task_categories:
- text-generation
- question-answering
language:
- en
tags:
- scbe
- system-hygiene
- training-data
- metadata-only
---

# {title}

Metadata-only SCBE cleanup training records generated at `{created_at}`.

This dataset teaches local-first cleanup decisions: keep harness-wired models,
review ambiguous model/cache state, and turn deletion candidates into scrubbed
training examples before pruning local storage.

It does **not** include raw cache files, model weights, local logs, database
contents, credentials, or private source documents.

## Files

- `records.jsonl`: full metadata and ChatML-style messages.
- `records.chat.jsonl`: message-only records for SFT ingestion.
- `records.csv`: compact tabular decisions.
- `manifest.json`: generation and count metadata.

## Counts

- total records: {len(records)}
- keep: {keep}
- review: {review}
- cleanup_candidate: {cleanup}
"""
    path.write_text(text, encoding="utf-8")


def build_dataset(out_dir: Path, kaggle_dir: Path, kaggle_ref: str) -> dict[str, Any]:
    created_at = now_utc()
    inventory = collect_inventory()
    records = [build_record(row, created_at) for row in inventory]
    chat_records = [
        {
            "id": record["id"],
            "schema": record["schema"],
            "messages": record["messages"],
            "decision": record["decision"],
            "source_kind": record["source_kind"],
            "privacy": record["privacy"],
        }
        for record in records
    ]
    manifest = {
        "schema": SCHEMA_VERSION,
        "created_at_utc": created_at,
        "record_count": len(records),
        "privacy": "metadata_only",
        "source": "local_cleanup_inventory",
        "hf_repo_default": DEFAULT_HF_REPO,
        "kaggle_ref": kaggle_ref,
        "outputs": ["records.jsonl", "records.chat.jsonl", "records.csv", "README.md", "dataset-metadata.json"],
    }

    for target in (out_dir, kaggle_dir):
        target.mkdir(parents=True, exist_ok=True)
        write_jsonl(target / "records.jsonl", records)
        write_jsonl(target / "records.chat.jsonl", chat_records)
        write_csv(target / "records.csv", records)
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_readme(target / "README.md", records, created_at, "SCBE System Hygiene Training")
        metadata = {
            "id": kaggle_ref,
            "title": "SCBE System Hygiene Training",
            "subtitle": "Metadata-only cleanup decisions for AI system harnesses",
            "licenses": [{"name": "cc"}],
            "keywords": ["ai", "systems", "storage", "benchmark", "metadata"],
        }
        (target / "dataset-metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    return {"manifest": manifest, "records": records}


def upload_hf(folder: Path, repo_id: str, token: str | None) -> None:
    if not token:
        raise RuntimeError("HF_TOKEN is required for --upload-hf")
    try:
        from huggingface_hub import HfApi  # type: ignore
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is required for --upload-hf") from exc

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(folder),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="publish system hygiene cleanup training data",
    )


def push_kaggle(folder: Path, create_new: bool, public: bool, message: str) -> None:
    from scripts.kaggle.scbe_kaggle import KaggleBridge

    bridge = KaggleBridge()
    if create_new:
        bridge.push_create(folder, is_public=public)
    else:
        bridge.push_version(folder, message=message)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--hf-repo", default=DEFAULT_HF_REPO)
    parser.add_argument("--kaggle-ref", default=f"{DEFAULT_KAGGLE_OWNER}/{DEFAULT_KAGGLE_SLUG}")
    parser.add_argument("--upload-hf", action="store_true")
    parser.add_argument("--push-kaggle", action="store_true")
    parser.add_argument("--kaggle-new", action="store_true")
    parser.add_argument("--kaggle-public", action="store_true")
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_dataset(args.output_dir, args.kaggle_dir, args.kaggle_ref)
    manifest = result["manifest"]
    print(
        f"[cleanup-training] wrote {manifest['record_count']} metadata-only records "
        f"to {public_path(args.output_dir)} and {public_path(args.kaggle_dir)}"
    )

    if args.upload_hf:
        upload_hf(args.output_dir, args.hf_repo, args.hf_token)
        print(f"[cleanup-training] uploaded Hugging Face dataset: https://huggingface.co/datasets/{args.hf_repo}")

    if args.push_kaggle:
        push_kaggle(
            args.kaggle_dir,
            create_new=args.kaggle_new,
            public=args.kaggle_public,
            message="publish metadata-only SCBE system hygiene cleanup training data",
        )
        print(f"[cleanup-training] pushed Kaggle dataset: https://www.kaggle.com/datasets/{args.kaggle_ref}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
