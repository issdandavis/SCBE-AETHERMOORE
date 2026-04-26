#!/usr/bin/env python3
"""Inventory and regularize SCBE training dataset surfaces.

This is intentionally a catalog/plan builder, not a flat merger.  It counts
local datasets, remote notebook surfaces, and training profiles, then emits a
purpose-bucketed merge plan so coding, governance, operator, lore, and
experimental lanes stay separable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "training_inventory" / "latest"
DATA_EXTENSIONS = {".jsonl", ".json", ".csv", ".parquet", ".arrow", ".txt"}
NOTEBOOK_EXTENSION = ".ipynb"

PURPOSE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "coding_model",
        (
            "coding",
            "coder",
            "codeflow",
            "code_lanes",
            "code-lanes",
            "bijective",
            "command_lattice",
            "command-lattice",
            "geoseal_command",
            "command_harmony",
            "binary_interpretation_matrix",
            "eml_operator",
            "atomic_workflow",
            "stage6",
            "qwen",
            "polyglot",
        ),
    ),
    (
        "operator_agent_bus",
        (
            "apollo",
            "browser",
            "aetherbrowser",
            "operator",
            "sidekick",
            "cash",
            "workflow",
            "email",
            "youtube",
            "field_trips",
            "context_sft",
        ),
    ),
    (
        "governance_security",
        (
            "governance",
            "security",
            "null_space",
            "compliance",
            "adversarial",
            "crypto",
            "geoseal_crypto",
            "attacks",
            "l13",
            "risk",
            "tor_sweeps",
        ),
    ),
    (
        "aligned_foundations",
        (
            "aligned_foundations",
            "chemistry_primary",
            "tongue",
            "tongues",
            "langues",
            "semantic",
            "layer_index",
            "phi_poincare",
            "architecture_explainer",
            "curriculum",
        ),
    ),
    (
        "story_lore",
        (
            "spiralverse",
            "lore",
            "story",
            "aethermoor",
            "iseki",
            "npc",
            "everweave",
            "thalorion",
            "book",
            "music",
            "webtoon",
            "art-style",
            "gacha",
            "game_sessions",
        ),
    ),
    (
        "commerce_product",
        (
            "commerce",
            "stripe",
            "gumroad",
            "funnel",
            "tax",
            "photographer_tax",
            "checkout",
            "product",
        ),
    ),
    (
        "research_bridge",
        (
            "research",
            "arxiv",
            "source_manifest",
            "page_evidence",
            "cutting_edge",
            "photonic",
            "quantum",
            "math_patterns",
        ),
    ),
)

MODEL_SET_POLICIES: dict[str, dict[str, Any]] = {
    "coding_model": {
        "destination": "training-data/regularized/coding_model/",
        "merge_strategy": "weighted_sft_with_holdout_kept_separate",
        "weight": 1.0,
        "must_have": ["instruction", "response", "metadata"],
        "eval_gate": "coding lane benchmark plus frozen stage6 eval",
    },
    "operator_agent_bus": {
        "destination": "training-data/regularized/operator_agent_bus/",
        "merge_strategy": "tool_trace_sft_plus_command_recall",
        "weight": 0.7,
        "must_have": ["instruction", "response", "metadata"],
        "eval_gate": "CLI command recall and governed route smoke tests",
    },
    "governance_security": {
        "destination": "training-data/regularized/governance_security/",
        "merge_strategy": "security_sft_with_quarantine_audit",
        "weight": 0.8,
        "must_have": ["instruction", "response", "metadata"],
        "eval_gate": "governance decision and invalid-input regression tests",
    },
    "aligned_foundations": {
        "destination": "training-data/regularized/aligned_foundations/",
        "merge_strategy": "paired_multirepresentation_records",
        "weight": 0.9,
        "must_have": ["instruction", "response", "metadata"],
        "eval_gate": "cross-lane concept preservation and packet compliance",
    },
    "story_lore": {
        "destination": "training-data/regularized/story_lore/",
        "merge_strategy": "keep_out_of_coder_unless_explicit_lore_code_pair",
        "weight": 0.35,
        "must_have": ["instruction", "response", "metadata"],
        "eval_gate": "style/canon eval, not coding eval",
    },
    "commerce_product": {
        "destination": "training-data/regularized/commerce_product/",
        "merge_strategy": "offer_ops_sft_with_secret_sweep",
        "weight": 0.55,
        "must_have": ["instruction", "response", "metadata"],
        "eval_gate": "checkout/fulfillment workflow smoke tests",
    },
    "research_bridge": {
        "destination": "training-data/regularized/research_bridge/",
        "merge_strategy": "source_grounded_records_only",
        "weight": 0.5,
        "must_have": ["instruction", "response", "metadata.source"],
        "eval_gate": "source citation and claim verification",
    },
    "uncategorized": {
        "destination": "training-data/regularized/quarantine/",
        "merge_strategy": "inspect_before_training",
        "weight": 0.0,
        "must_have": ["instruction", "response"],
        "eval_gate": "manual classification required",
    },
}


@dataclass(frozen=True)
class InventoryOptions:
    output_dir: Path
    include_kaggle: bool
    include_hf: bool
    include_cloud: bool
    max_cloud_files: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_purpose(path_text: str) -> str:
    lowered = path_text.lower().replace("\\", "/")
    for purpose, needles in PURPOSE_RULES:
        if any(needle in lowered for needle in needles):
            return purpose
    return "uncategorized"


def _split_hint(path_text: str) -> str:
    lowered = path_text.lower()
    if "holdout" in lowered or "eval" in lowered or "test" in lowered:
        return "eval"
    if "train" in lowered:
        return "train"
    if "manifest" in lowered or "summary" in lowered or "audit" in lowered:
        return "manifest"
    return "unknown"


def _jsonl_stats(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as probe:
            first_line = probe.readline().strip()
            second_line = probe.readline().strip()
            if first_line == "version https://git-lfs.github.com/spec/v1" and second_line.startswith("oid sha256:"):
                return {
                    "record_count": 0,
                    "malformed_count": 0,
                    "empty_line_count": 0,
                    "first_keys": [],
                    "schema_shape_count": 0,
                    "top_schema_shapes": [],
                    "prompt_response_records": 0,
                    "messages_records": 0,
                    "lfs_pointer": True,
                }
    except OSError:
        pass
    records = 0
    malformed = 0
    empty = 0
    schema_shapes: Counter[str] = Counter()
    first_keys: list[str] = []
    prompt_response = 0
    messages = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                empty += 1
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(payload, dict):
                malformed += 1
                continue
            records += 1
            keys = sorted(str(key) for key in payload.keys())
            if not first_keys:
                first_keys = keys
            schema_shapes["|".join(keys)] += 1
            if payload.get("instruction") is not None and payload.get("response") is not None:
                prompt_response += 1
            if isinstance(payload.get("messages"), list):
                messages += 1
    return {
        "record_count": records,
        "malformed_count": malformed,
        "empty_line_count": empty,
        "first_keys": first_keys,
        "schema_shape_count": len(schema_shapes),
        "top_schema_shapes": schema_shapes.most_common(5),
        "prompt_response_records": prompt_response,
        "messages_records": messages,
    }


def _json_stats(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"json_valid": False}
    stats: dict[str, Any] = {"json_valid": True}
    if isinstance(payload, dict):
        stats["top_keys"] = sorted(str(key) for key in payload.keys())[:40]
        if "record_count" in payload:
            stats["declared_record_count"] = payload["record_count"]
        if isinstance(payload.get("counts"), dict):
            stats["declared_counts"] = payload["counts"]
        if "profiles" in payload and isinstance(payload["profiles"], list):
            stats["profile_count"] = len(payload["profiles"])
        if "train_files" in payload:
            stats["declared_train_files"] = len(payload.get("train_files") or [])
    elif isinstance(payload, list):
        stats["list_count"] = len(payload)
    return stats


def _csv_stats(path: Path) -> dict[str, Any]:
    rows = 0
    columns: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for idx, row in enumerate(reader):
            if idx == 0:
                columns = [str(item) for item in row]
            else:
                rows += 1
    return {"record_count": rows, "columns": columns[:40]}


def inspect_file(path: Path, source: str) -> dict[str, Any]:
    rel = _rel(path)
    suffix = path.suffix.lower()
    row: dict[str, Any] = {
        "path": rel,
        "source": source,
        "extension": suffix,
        "bytes": path.stat().st_size,
        "last_modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "sha256": _sha256(path),
        "purpose": classify_purpose(rel),
        "split_hint": _split_hint(rel),
    }
    if suffix == ".jsonl":
        row.update(_jsonl_stats(path))
    elif suffix == ".json":
        row.update(_json_stats(path))
    elif suffix == ".csv":
        row.update(_csv_stats(path))
    elif suffix == NOTEBOOK_EXTENSION:
        row.update(_json_stats(path))
        row["purpose"] = classify_purpose(rel)
        row["split_hint"] = "notebook"
    else:
        row["record_count"] = None
    row["regularization_status"] = regularization_status(row)
    return row


def regularization_status(row: dict[str, Any]) -> str:
    if row.get("bytes", 0) < 80:
        return "quarantine_tiny"
    if row.get("extension") == ".jsonl":
        if row.get("lfs_pointer"):
            return "lfs_pointer_needs_pull"
        if row.get("malformed_count", 0):
            return "quarantine_malformed"
        if row.get("record_count", 0) == 0:
            return "quarantine_empty"
        if row.get("prompt_response_records", 0) == row.get("record_count", 0):
            return "ready_prompt_response"
        if row.get("messages_records", 0) == row.get("record_count", 0):
            return "ready_messages"
        return "needs_schema_adapter"
    if row.get("extension") == ".json":
        return "manifest_or_metadata" if row.get("json_valid") else "quarantine_malformed"
    if row.get("extension") == NOTEBOOK_EXTENSION:
        return "notebook_surface"
    if row.get("extension") in {".parquet", ".arrow"}:
        return "binary_dataset_needs_loader"
    if row.get("extension") == ".csv":
        return "tabular_needs_adapter"
    return "inspect"


def collect_local_files() -> list[dict[str, Any]]:
    roots = [
        (REPO_ROOT / "training-data", "local_training_data"),
        (REPO_ROOT / "training", "local_training_runs"),
        (REPO_ROOT / "config" / "model_training", "local_training_profile"),
    ]
    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for root, source in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path in seen:
                continue
            if path.suffix.lower() in DATA_EXTENSIONS:
                rows.append(inspect_file(path, source))
                seen.add(path)
    notebook_root = REPO_ROOT / "notebooks"
    if notebook_root.exists():
        for path in sorted(notebook_root.rglob(f"*{NOTEBOOK_EXTENSION}")):
            rows.append(inspect_file(path, "local_notebook"))
    return rows


def _run_command(args: list[str], timeout: int = 45) -> dict[str, Any]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError:
        return {"status": "not_found", "command": args[0], "items": []}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": args[0], "items": []}
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "items": [],
    }


def collect_kaggle_kernels() -> dict[str, Any]:
    result = _run_command(["kaggle", "kernels", "list", "--mine", "--page-size", "100"], timeout=45)
    if result["status"] != "ok":
        return result
    items: list[dict[str, Any]] = []
    for line in result["stdout"].splitlines():
        raw = line.rstrip()
        if not raw or raw.startswith("ref ") or raw.startswith("-") or raw.lower().startswith("warning:"):
            continue
        parts = raw.split()
        if not parts or "/" not in parts[0]:
            continue
        ref = parts[0]
        title = raw[len(ref) :].strip()
        items.append({"ref": ref, "title_line": title, "purpose": classify_purpose(raw), "source": "kaggle_kernel"})
    return {"status": "ok", "items": items, "count": len(items)}


def collect_hf_datasets(author: str = "issdandavis") -> dict[str, Any]:
    code = (
        "import json\n"
        "from huggingface_hub import HfApi\n"
        f"items=[]\nfor ds in HfApi().list_datasets(author={author!r}, limit=200):\n"
        "    items.append({'id': ds.id, 'last_modified': str(getattr(ds, 'last_modified', '') or ''), 'tags': list(getattr(ds, 'tags', []) or [])[:20]})\n"
        "print(json.dumps(items))\n"
    )
    result = _run_command([sys.executable, "-c", code], timeout=60)
    if result["status"] != "ok":
        return result
    try:
        items = json.loads(result["stdout"] or "[]")
    except json.JSONDecodeError:
        return {"status": "parse_error", "items": [], "stdout_preview": result["stdout"][:500]}
    for item in items:
        item["purpose"] = classify_purpose(str(item.get("id", "")))
        item["source"] = "huggingface_dataset"
    return {"status": "ok", "items": items, "count": len(items)}


def collect_cloud_surfaces(limit: int) -> dict[str, Any]:
    candidates = [
        Path(os.environ.get("USERPROFILE", "")) / "Drive",
        Path(os.environ.get("USERPROFILE", "")) / "Google Drive",
        Path(os.environ.get("USERPROFILE", "")) / "My Drive",
        Path(os.environ.get("USERPROFILE", "")) / "OneDrive",
        Path(os.environ.get("USERPROFILE", "")) / "Dropbox",
    ]
    items: list[dict[str, Any]] = []
    for root in candidates:
        if not root.exists():
            continue
        try:
            iterator = root.rglob("*")
            for path in iterator:
                if len(items) >= limit:
                    break
                if not path.is_file():
                    continue
                suffix = path.suffix.lower()
                if suffix not in DATA_EXTENSIONS and suffix != NOTEBOOK_EXTENSION:
                    continue
                text = str(path)
                if not any(token in text.lower() for token in ("scbe", "aether", "colab", "kaggle", "qwen", "polly", "training")):
                    continue
                items.append(
                    {
                        "path": str(path),
                        "source": "cloud_sync_surface",
                        "extension": suffix,
                        "bytes": path.stat().st_size,
                        "last_modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                        "purpose": classify_purpose(text),
                    }
                )
        except OSError:
            continue
    return {"status": "ok", "items": items, "count": len(items)}


def build_merge_plan(local_rows: list[dict[str, Any]], remotes: dict[str, Any]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in local_rows:
        buckets[row["purpose"]].append(row)
    model_sets: dict[str, Any] = {}
    for purpose, policy in MODEL_SET_POLICIES.items():
        rows = buckets.get(purpose, [])
        ready_rows = [
            row
            for row in rows
            if str(row.get("regularization_status", "")).startswith("ready")
            and row.get("split_hint") != "eval"
        ]
        eval_rows = [row for row in rows if row.get("split_hint") == "eval"]
        model_sets[purpose] = {
            **policy,
            "local_file_count": len(rows),
            "ready_train_file_count": len(ready_rows),
            "eval_file_count": len(eval_rows),
            "known_records": sum(int(row.get("record_count") or 0) for row in rows),
            "train_candidates": [row["path"] for row in ready_rows],
            "eval_candidates": [row["path"] for row in eval_rows],
        }
    return {
        "schema_version": "scbe_dataset_merge_plan_v1",
        "generated_at_utc": _utc_now(),
        "rule": "Do not flat-merge all corpora. Keep purpose buckets separate, dedupe inside each bucket, and promote only through that bucket's eval gate.",
        "external_pattern": {
            "deepseek_v3": "large diverse high-quality pretraining followed by SFT/RL; architecture matters but data quality and stable staged training are explicit",
            "deepseek_r1": "verifiable reward tasks allow reasoning improvement without relying only on human demonstrations",
            "kimi_k2": "agentic data synthesis plus joint RL against real/synthetic environments is the relevant coding-agent pattern",
        },
        "remote_surfaces": {
            key: {"status": value.get("status"), "count": value.get("count", len(value.get("items", [])))}
            for key, value in remotes.items()
        },
        "model_sets": model_sets,
        "regularization_steps": [
            "Validate JSONL parse and schema shape before merge.",
            "Normalize to instruction/response/metadata or messages/metadata, preserving source_path and sha256.",
            "Dedupe exact prompt-response hashes inside each purpose bucket.",
            "Near-dedupe after exact dedupe using source_path plus normalized prompt text; do not cross-dedupe train and eval blindly.",
            "Keep holdout/eval files frozen by concept/source, not random line split.",
            "Run secret/anomaly audit before any upload or public dataset push.",
            "Emit weighted mixture configs; never train story/lore into coder unless records are explicit lore-code pairs.",
        ],
    }


def write_outputs(local_rows: list[dict[str, Any]], remotes: dict[str, Any], plan: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(local_rows, remotes)
    inventory = {
        "schema_version": "scbe_training_dataset_inventory_v1",
        "generated_at_utc": _utc_now(),
        "summary": summary,
        "local_datasets": local_rows,
        "remote_surfaces": remotes,
    }
    paths = {
        "inventory": output_dir / "inventory.json",
        "regularized_index": output_dir / "regularized_index.jsonl",
        "merge_plan": output_dir / "merge_plan.json",
        "report": output_dir / "report.md",
    }
    paths["inventory"].write_text(json.dumps(inventory, indent=2, ensure_ascii=True), encoding="utf-8")
    with paths["regularized_index"].open("w", encoding="utf-8") as handle:
        for row in local_rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    paths["merge_plan"].write_text(json.dumps(plan, indent=2, ensure_ascii=True), encoding="utf-8")
    paths["report"].write_text(render_report(summary, plan), encoding="utf-8")
    return paths


def summarize(local_rows: list[dict[str, Any]], remotes: dict[str, Any]) -> dict[str, Any]:
    by_source = Counter(row["source"] for row in local_rows)
    by_purpose = Counter(row["purpose"] for row in local_rows)
    by_status = Counter(row.get("regularization_status", "unknown") for row in local_rows)
    jsonl_rows = [row for row in local_rows if row.get("extension") == ".jsonl"]
    total_known_records = sum(int(row.get("record_count") or 0) for row in jsonl_rows)
    return {
        "local_file_count": len(local_rows),
        "local_jsonl_file_count": len(jsonl_rows),
        "local_notebook_count": by_source.get("local_notebook", 0),
        "local_known_jsonl_records": total_known_records,
        "by_source": dict(sorted(by_source.items())),
        "by_purpose": dict(sorted(by_purpose.items())),
        "by_regularization_status": dict(sorted(by_status.items())),
        "remote_counts": {
            key: value.get("count", len(value.get("items", []))) for key, value in remotes.items()
        },
    }


def render_report(summary: dict[str, Any], plan: dict[str, Any]) -> str:
    lines = [
        "# SCBE Training Dataset Inventory",
        "",
        f"Generated: {plan['generated_at_utc']}",
        "",
        "## Counts",
        "",
        f"- Local dataset/config/notebook files: {summary['local_file_count']}",
        f"- Local JSONL files: {summary['local_jsonl_file_count']}",
        f"- Known local JSONL records: {summary['local_known_jsonl_records']}",
        f"- Local repo notebooks: {summary['local_notebook_count']}",
    ]
    for key, count in sorted(summary["remote_counts"].items()):
        lines.append(f"- Remote {key}: {count}")
    lines.extend(["", "## Purpose Buckets", ""])
    for purpose, count in sorted(summary["by_purpose"].items()):
        model_set = plan["model_sets"].get(purpose, {})
        known = model_set.get("known_records", 0)
        lines.append(f"- {purpose}: {count} files, {known} known records")
    lines.extend(["", "## Regularization Status", ""])
    for status, count in sorted(summary["by_regularization_status"].items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Merge Rule",
            "",
            plan["rule"],
            "",
            "## Model Sets",
            "",
        ]
    )
    for purpose, model_set in plan["model_sets"].items():
        lines.append(
            f"- {purpose}: train candidates {model_set['ready_train_file_count']}, eval candidates {model_set['eval_file_count']}, strategy {model_set['merge_strategy']}"
        )
    lines.extend(["", "## Regularization Steps", ""])
    for step in plan["regularization_steps"]:
        lines.append(f"- {step}")
    lines.append("")
    return "\n".join(lines)


def build_inventory(options: InventoryOptions) -> dict[str, Any]:
    local_rows = collect_local_files()
    remotes: dict[str, Any] = {}
    if options.include_kaggle:
        remotes["kaggle_kernels"] = collect_kaggle_kernels()
    if options.include_hf:
        remotes["huggingface_datasets"] = collect_hf_datasets()
    if options.include_cloud:
        remotes["cloud_surfaces"] = collect_cloud_surfaces(options.max_cloud_files)
    plan = build_merge_plan(local_rows, remotes)
    paths = write_outputs(local_rows, remotes, plan, options.output_dir)
    summary = summarize(local_rows, remotes)
    return {
        "summary": summary,
        "paths": {key: _rel(path) for key, path in paths.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory and regularize SCBE training datasets")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--include-kaggle", action="store_true")
    parser.add_argument("--include-hf", action="store_true")
    parser.add_argument("--include-cloud", action="store_true")
    parser.add_argument("--max-cloud-files", type=int, default=250)
    args = parser.parse_args()

    result = build_inventory(
        InventoryOptions(
            output_dir=Path(args.output_dir),
            include_kaggle=bool(args.include_kaggle),
            include_hf=bool(args.include_hf),
            include_cloud=bool(args.include_cloud),
            max_cloud_files=int(args.max_cloud_files),
        )
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
