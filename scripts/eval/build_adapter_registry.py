"""Build the canonical adapter registry / lineage manifest.

Walks known sources of adapter metadata and writes
`artifacts/adapter_registry/registry.json` indexing every published or
pending SCBE adapter with its lane, base model, training config snapshot,
dataset linkage, eval results (perplexity + executable accuracy), and
merge lineage (parents and children).

The registry is the foundation for:
  * `analyze_lora_drift.py` (which adapters to compare).
  * Multi-adapter routing (which adapters can be loaded for a request).
  * Merge acceptance gate (parent SHAs and per-lane eval anchors).

Sources walked:
  1. `config/model_training/*.json` with schema_version
     `scbe_model_training_profile_v1` — yields adapter_repo + lane label
     + training config + dataset linkage.
  2. `config/model_training/*.json` with schema_version
     `scbe_coding_model_merge_profile_v1` — yields merge children + parents
     + blocked adapters.
  3. `artifacts/model_evals/frozen/*/report.json` — yields perplexity per
     adapter slug.
  4. `artifacts/dsl_eval_reports/*.json` — yields executable accuracy and
     decision for L_dsl_synthesis-style lanes.
  5. `artifacts/kaggle_output/*/DONE.json` — yields recent Kaggle-trained
     adapters that may not yet have a config profile committed.

Output schema: `scbe_adapter_registry_v1`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", slug).strip("-.") or "adapter"


def _adapter_slug(adapter_repo: str) -> str:
    """Match `score_adapter_frozen.py` slugging: `org-repo`."""
    return _safe_slug(adapter_repo.replace("/", "-"))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _scan_training_profiles(root: Path) -> Dict[str, Dict[str, Any]]:
    """Index by adapter_repo for `scbe_model_training_profile_v1` files."""
    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.glob("config/model_training/*.json")):
        data = _read_json(path)
        if not data or data.get("schema_version") != "scbe_model_training_profile_v1":
            continue
        hub = data.get("hub") or {}
        adapter_repo = hub.get("adapter_repo")
        if not adapter_repo:
            continue
        training = data.get("training") or {}
        dataset = data.get("dataset") or {}
        out[adapter_repo] = {
            "adapter_repo": adapter_repo,
            "profile_id": data.get("profile_id"),
            "title": data.get("title"),
            "lane": data.get("profile_id"),
            "base_model": data.get("base_model"),
            "config_path": str(path.relative_to(root)).replace("\\", "/"),
            "dataset_repo": hub.get("dataset_repo"),
            "training_config": {
                "lora_rank": training.get("lora_rank"),
                "lora_alpha": training.get("lora_alpha"),
                "lora_dropout": training.get("lora_dropout"),
                "learning_rate": training.get("learning_rate"),
                "num_train_epochs": training.get("num_train_epochs"),
                "max_steps": training.get("max_steps"),
                "batch_size": training.get("batch_size"),
                "gradient_accumulation_steps": training.get("gradient_accumulation_steps"),
                "max_seq_length": training.get("max_seq_length"),
                "target_modules": training.get("target_modules"),
                "seed": training.get("seed"),
            },
            "train_files": list(dataset.get("train_files") or []),
            "eval_files": list(dataset.get("eval_files") or []),
            "evaluation": data.get("evaluation"),
        }
    return out


def _scan_merge_profiles(root: Path) -> List[Dict[str, Any]]:
    """Return all `scbe_coding_model_merge_profile_v1` records."""
    out: List[Dict[str, Any]] = []
    for path in sorted(root.glob("config/model_training/*.json")):
        data = _read_json(path)
        if not data or data.get("schema_version") != "scbe_coding_model_merge_profile_v1":
            continue
        out.append({
            "merge_id": data.get("merge_id"),
            "output_model_repo": data.get("output_model_repo"),
            "base_model": data.get("base_model"),
            "merge_mode": data.get("merge_mode"),
            "adapters": data.get("adapters") or [],
            "blocked_adapters": data.get("blocked_adapters") or [],
            "pre_merge_gates": data.get("pre_merge_gates"),
            "config_path": str(path.relative_to(root)).replace("\\", "/"),
        })
    return out


def _scan_frozen_evals(root: Path) -> Dict[str, Dict[str, Any]]:
    """Latest perplexity report per adapter slug."""
    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.glob("artifacts/model_evals/frozen/*/report.json")):
        data = _read_json(path)
        if not data:
            continue
        adapter_label = str(data.get("adapter") or "")
        if adapter_label == "BASE":
            slug = "BASE"
        else:
            slug = _adapter_slug(adapter_label)
        ts = str(data.get("generated_at_utc") or "")
        existing = out.get(slug)
        if existing and existing.get("generated_at_utc", "") >= ts:
            continue
        summary = data.get("summary") or {}
        out[slug] = {
            "report_path": str(path.relative_to(root)).replace("\\", "/"),
            "generated_at_utc": ts,
            "adapter_label": adapter_label,
            "mean_nll": summary.get("mean_nll"),
            "perplexity": summary.get("perplexity"),
            "files_evaluated": summary.get("files_evaluated"),
            "total_records": summary.get("total_records"),
        }
    return out


def _scan_executable_evals(root: Path) -> Dict[str, Dict[str, Any]]:
    """Latest executable-accuracy report per adapter slug."""
    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.glob("artifacts/dsl_eval_reports/*_executable_accuracy.json")):
        data = _read_json(path)
        if not data:
            continue
        adapter_label = str(data.get("adapter") or "")
        slug = _adapter_slug(adapter_label.split("/")[-1] if adapter_label else path.stem)
        ts = str(data.get("generated_utc") or "")
        existing = out.get(slug)
        if existing and existing.get("generated_at_utc", "") >= ts:
            continue
        out[slug] = {
            "report_path": str(path.relative_to(root)).replace("\\", "/"),
            "generated_at_utc": ts,
            "adapter_label": adapter_label,
            "executable_accuracy": data.get("executable_accuracy"),
            "gate": data.get("gate"),
            "decision": data.get("decision"),
            "category_accuracy": data.get("category_accuracy"),
            "floor_violations": data.get("floor_violations"),
        }
    return out


def _scan_stage6_evals(root: Path) -> Dict[str, Dict[str, Any]]:
    """Latest Stage 6 regression report per adapter slug."""
    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.glob("artifacts/dsl_eval_reports/*_stage6_regression.json")):
        data = _read_json(path)
        if not data:
            continue
        adapter_label = str(data.get("adapter") or "")
        slug = _adapter_slug(adapter_label.split("/")[-1] if adapter_label else path.stem)
        ts = str(data.get("generated_utc") or "")
        existing = out.get(slug)
        if existing and existing.get("generated_at_utc", "") >= ts:
            continue
        out[slug] = {
            "report_path": str(path.relative_to(root)).replace("\\", "/"),
            "generated_at_utc": ts,
            "adapter_label": adapter_label,
            "pass_rate": data.get("pass_rate"),
            "minimum_pass_rate": data.get("minimum_pass_rate"),
            "must_pass_all_ok": data.get("must_pass_all_ok"),
            "overall_pass": data.get("overall_pass"),
        }
    return out


def _scan_kaggle_outputs(root: Path) -> List[Dict[str, Any]]:
    """Kaggle DONE.json beacons for recently trained adapters."""
    out: List[Dict[str, Any]] = []
    for path in sorted(root.glob("artifacts/kaggle_output/*/DONE.json")):
        data = _read_json(path)
        if not data:
            continue
        out.append({
            "round": data.get("round"),
            "kernel": path.parent.name,
            "hf_pushed": data.get("push") or data.get("pushed"),
            "adapter_repo": data.get("adapter_repo") or data.get("hf_repo"),
            "done_path": str(path.relative_to(root)).replace("\\", "/"),
        })
    return out


def _build_lineage(merges: List[Dict[str, Any]], adapter_repo: str) -> Dict[str, Any]:
    merged_into: List[str] = []
    for merge in merges:
        for entry in merge.get("adapters", []) or []:
            if entry.get("adapter_repo") == adapter_repo:
                output_repo = merge.get("output_model_repo")
                if output_repo and output_repo not in merged_into:
                    merged_into.append(output_repo)
    return {"merged_into": merged_into, "parents": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default="artifacts/adapter_registry/registry.json",
        help="Output path (default: artifacts/adapter_registry/registry.json)",
    )
    ap.add_argument(
        "--root",
        default=str(PROJECT_ROOT),
        help="Project root (default: repo root)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    profiles = _scan_training_profiles(root)
    merges = _scan_merge_profiles(root)
    frozen_evals = _scan_frozen_evals(root)
    executable_evals = _scan_executable_evals(root)
    stage6_evals = _scan_stage6_evals(root)
    kaggle_outputs = _scan_kaggle_outputs(root)

    blocked_repos: Dict[str, Dict[str, Any]] = {}
    merge_child_repos: List[Dict[str, Any]] = []
    for merge in merges:
        for entry in merge.get("blocked_adapters", []) or []:
            repo = entry.get("adapter_repo")
            if repo and repo not in blocked_repos:
                blocked_repos[repo] = {
                    "adapter_repo": repo,
                    "profile_id": entry.get("profile_id"),
                    "blocked_reason": entry.get("reason"),
                    "merge_id": merge.get("merge_id"),
                }
        merge_child_repos.append({
            "adapter_repo": merge.get("output_model_repo"),
            "profile_id": merge.get("merge_id"),
            "lane": "merge_output",
            "base_model": merge.get("base_model"),
            "config_path": merge.get("config_path"),
            "merge_mode": merge.get("merge_mode"),
            "parents": [
                e.get("adapter_repo")
                for e in (merge.get("adapters") or [])
                if e.get("adapter_repo")
            ],
            "pre_merge_gates": merge.get("pre_merge_gates"),
        })

    adapters: List[Dict[str, Any]] = []
    seen: set = set()

    for repo, profile in profiles.items():
        slug = _adapter_slug(repo)
        record: Dict[str, Any] = dict(profile)
        record["slug"] = slug
        record["status"] = "trained" if slug in frozen_evals else "registered"
        record["frozen_eval"] = frozen_evals.get(slug)
        record["executable_eval"] = executable_evals.get(slug)
        record["stage6_regression"] = stage6_evals.get(slug)
        record["lineage"] = _build_lineage(merges, repo)
        adapters.append(record)
        seen.add(repo)

    for child in merge_child_repos:
        repo = child.get("adapter_repo")
        if not repo or repo in seen:
            continue
        slug = _adapter_slug(repo)
        adapters.append({
            **child,
            "slug": slug,
            "status": "merged" if slug in frozen_evals else "planned",
            "frozen_eval": frozen_evals.get(slug),
            "executable_eval": executable_evals.get(slug),
            "stage6_regression": stage6_evals.get(slug),
            "lineage": {"merged_into": [], "parents": child.get("parents") or []},
        })
        seen.add(repo)

    for repo, blocked in blocked_repos.items():
        if repo in seen:
            continue
        slug = _adapter_slug(repo)
        adapters.append({
            **blocked,
            "slug": slug,
            "status": "blocked",
            "frozen_eval": None,
            "executable_eval": None,
            "stage6_regression": None,
            "lineage": {"merged_into": [], "parents": []},
        })
        seen.add(repo)

    seen_slugs = {a.get("slug") for a in adapters}
    for slug, eval_data in frozen_evals.items():
        if slug == "BASE" or slug in seen_slugs:
            continue
        adapter_label = eval_data.get("adapter_label") or slug
        adapters.append({
            "adapter_repo": adapter_label,
            "slug": slug,
            "lane": "unregistered",
            "status": "evaluated_only",
            "config_path": None,
            "frozen_eval": eval_data,
            "executable_eval": executable_evals.get(slug),
            "stage6_regression": stage6_evals.get(slug),
            "lineage": {"merged_into": [], "parents": []},
            "note": "Eval report exists but no scbe_model_training_profile_v1 references this adapter_repo.",
        })
        seen_slugs.add(slug)

    base_metrics = frozen_evals.get("BASE")
    registry = {
        "schema": "scbe_adapter_registry_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root).replace("\\", "/"),
        "n_adapters": len(adapters),
        "base_eval": base_metrics,
        "adapters": adapters,
        "merge_profiles": merges,
        "kaggle_outputs": kaggle_outputs,
    }

    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    counts = {
        "trained": 0,
        "registered": 0,
        "merged": 0,
        "planned": 0,
        "blocked": 0,
        "evaluated_only": 0,
    }
    for a in adapters:
        s = a.get("status")
        if s in counts:
            counts[s] += 1
    print(f"[adapter-registry] wrote {out_path}", flush=True)
    print(
        f"[adapter-registry] adapters={len(adapters)} " +
        " ".join(f"{k}={v}" for k, v in counts.items()),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
