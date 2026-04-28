#!/usr/bin/env python3
"""
Regenerate the SCBE AI card stack — one card per dataset / model config / run /
experiment artifact, written to ``data/cards/ai_card_stack.json``.

The script never edits the underlying data; it only indexes what already
exists on disk so a future scheduler (or a person) can "deal" cards out of a
single registry instead of crawling four surfaces by hand.

Surfaces scanned:

    sft_dataset         training-data/sft/*_manifest.json
    model_config        config/model_training/*.json
    kaggle_run          artifacts/training/kaggle_kernel_inventory_*.json
                        (most-recent inventory wins)
    experiment_artifact experiments/bijective_2tongue_build/*.exe

Card schema (all fields required, ``relations`` may be empty):

    {
      "id":            "<surface>::<short-name>",
      "type":          "<one of the surfaces above>",
      "path":          "<repo-relative path or external ref>",
      "last_modified": "<ISO-8601 UTC>",
      "status":        "live" | "staged" | "blocked" | "unknown",
      "size_hint":     "<rows / bytes / 'n/a'>",
      "summary":       "<one-line human-readable>",
      "relations":     [{"type": "...", "target": "..."}]
    }

# future: ES-style sampling over cards (Salimans et al. 2017, arxiv 1703.03864)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SFT_DIR = REPO_ROOT / "training-data" / "sft"
MODEL_CFG_DIR = REPO_ROOT / "config" / "model_training"
KAGGLE_DIR = REPO_ROOT / "scripts" / "kaggle_auto"
EXPERIMENTS_DIR = REPO_ROOT / "experiments" / "bijective_2tongue_build"
KAGGLE_INVENTORY_GLOB = REPO_ROOT / "artifacts" / "training"
OUTPUT_PATH = REPO_ROOT / "data" / "cards" / "ai_card_stack.json"

SCHEMA_VERSION = "scbe-ai-card-stack-v1"


def _iso_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def scan_sft_datasets() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    if not SFT_DIR.is_dir():
        return cards
    for manifest in sorted(SFT_DIR.glob("*_manifest.json")):
        data = _load_json(manifest) or {}
        slug = manifest.stem.replace("_manifest", "")
        output_rel = data.get("output") or ""
        output_path = (REPO_ROOT / output_rel) if output_rel else None
        rows = data.get("output_records") or data.get("source_records") or "n/a"
        status = "live" if output_path and output_path.is_file() else "staged"
        cards.append(
            {
                "id": f"sft_dataset::{slug}",
                "type": "sft_dataset",
                "path": _rel(manifest),
                "last_modified": _iso_mtime(manifest),
                "status": status,
                "size_hint": f"{rows} rows" if rows != "n/a" else "n/a",
                "summary": data.get("schema_version", slug),
                "relations": ([{"type": "produces_jsonl", "target": output_rel}] if output_rel else []),
            }
        )
    return cards


def scan_model_configs() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    if not MODEL_CFG_DIR.is_dir():
        return cards
    for cfg in sorted(MODEL_CFG_DIR.glob("*.json")):
        data = _load_json(cfg) or {}
        slug = cfg.stem
        relations: List[Dict[str, str]] = []
        base = data.get("base_model")
        if base:
            relations.append({"type": "base_model", "target": base})
        out_repo = data.get("output_model_repo")
        if out_repo:
            relations.append({"type": "output_repo", "target": out_repo})
        for adapter in data.get("adapters", []) or []:
            repo = adapter.get("adapter_repo")
            if repo:
                relations.append({"type": "uses_adapter", "target": repo})
        for blocked in data.get("blocked_adapters", []) or []:
            repo = blocked.get("adapter_repo")
            if repo:
                relations.append({"type": "blocked_adapter", "target": repo})

        if data.get("blocked_adapters"):
            status = "blocked"
        elif data.get("pre_merge_gates", {}).get("must_pass_stage6_smoke_eval"):
            status = "staged"
        else:
            status = "unknown"

        cards.append(
            {
                "id": f"model_config::{slug}",
                "type": "model_config",
                "path": _rel(cfg),
                "last_modified": _iso_mtime(cfg),
                "status": status,
                "size_hint": f"{len(data.get('adapters', []) or [])} adapters",
                "summary": data.get("title") or data.get("merge_id") or slug,
                "relations": relations,
            }
        )
    return cards


def scan_kaggle_runs() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    inventories = sorted(
        KAGGLE_INVENTORY_GLOB.glob("kaggle_kernel_inventory_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if inventories:
        latest = inventories[0]
        data = _load_json(latest) or {}
        for kernel in data.get("kernels", []) or []:
            ref = kernel.get("ref") or kernel.get("slug") or ""
            if not ref:
                continue
            slug = ref.split("/")[-1]
            lane = kernel.get("lane", "")
            recommendation = kernel.get("recommendation", "")
            status_map = {
                "active-training": "live",
                "polly-auto-archive": "staged",
                "junk-or-unnamed": "unknown",
            }
            cards.append(
                {
                    "id": f"kaggle_run::{slug}",
                    "type": "kaggle_run",
                    "path": f"kaggle://{ref}",
                    "last_modified": (kernel.get("last_run_time") or "").replace(" ", "T") + "Z",
                    "status": status_map.get(lane, "unknown"),
                    "size_hint": f"votes={kernel.get('total_votes', '0')}",
                    "summary": kernel.get("title") or slug,
                    "relations": [
                        {"type": "lane", "target": lane},
                        {"type": "recommendation", "target": recommendation},
                    ],
                }
            )
    if KAGGLE_DIR.is_dir():
        for script in sorted(KAGGLE_DIR.glob("*.py")):
            slug = script.stem
            cards.append(
                {
                    "id": f"kaggle_run::tooling::{slug}",
                    "type": "kaggle_run",
                    "path": _rel(script),
                    "last_modified": _iso_mtime(script),
                    "status": "live",
                    "size_hint": f"{script.stat().st_size} bytes",
                    "summary": f"kaggle automation: {slug}",
                    "relations": [{"type": "tooling", "target": "kaggle_auto"}],
                }
            )
    return cards


def scan_experiment_artifacts() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    if not EXPERIMENTS_DIR.is_dir():
        return cards
    for binary in sorted(EXPERIMENTS_DIR.glob("*.exe")):
        slug = binary.stem
        cards.append(
            {
                "id": f"experiment_artifact::{slug}",
                "type": "experiment_artifact",
                "path": _rel(binary),
                "last_modified": _iso_mtime(binary),
                "status": "live",
                "size_hint": f"{binary.stat().st_size} bytes",
                "summary": f"compiled bijective tongue test: {slug}",
                "relations": [{"type": "experiment", "target": "bijective_2tongue_build"}],
            }
        )
    return cards


def derive_hf_repo_cards(model_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for mc in model_cards:
        for rel in mc.get("relations", []):
            if rel["type"] not in {"base_model", "output_repo", "uses_adapter", "blocked_adapter"}:
                continue
            ref = rel["target"]
            if ref in seen:
                seen[ref]["relations"].append({"type": "referenced_by", "target": mc["id"]})
                continue
            status = "blocked" if rel["type"] == "blocked_adapter" else "live"
            seen[ref] = {
                "id": f"hf_repo::{ref}",
                "type": "hf_repo",
                "path": f"hf://{ref}",
                "last_modified": mc["last_modified"],
                "status": status,
                "size_hint": "n/a",
                "summary": f"{rel['type']} for {mc['id']}",
                "relations": [{"type": "referenced_by", "target": mc["id"]}],
            }
    return list(seen.values())


def build_stack() -> Dict[str, Any]:
    sft = scan_sft_datasets()
    models = scan_model_configs()
    kaggle = scan_kaggle_runs()
    experiments = scan_experiment_artifacts()
    hf_repos = derive_hf_repo_cards(models)
    cards = sft + models + kaggle + experiments + hf_repos
    type_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}
    for c in cards:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_cards": len(cards),
        "type_counts": type_counts,
        "status_counts": status_counts,
        "cards": cards,
    }


def main(argv: Optional[List[str]] = None) -> int:
    out = OUTPUT_PATH if not argv else Path(argv[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    stack = build_stack()
    out.write_text(json.dumps(stack, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print(f"  total={stack['total_cards']} types={stack['type_counts']}")
    print(f"  status={stack['status_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
