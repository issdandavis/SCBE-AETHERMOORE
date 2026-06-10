#!/usr/bin/env python3
"""Build a model portfolio board for SCBE Hugging Face + local training profiles.

This is a consolidation planning tool. It does not delete, hide, move, or merge
remote models. It inventories live Hugging Face models, reconciles them with
local training and merge profiles, then writes bucketed recommendations.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "model_portfolio" / "latest"
DEFAULT_AUTHORS = ("issdandavis", "SCBE-AETHER")

ACTIVE_BUCKETS = {
    "promoted_full_model",
    "merge_candidate",
    "active_specialist_adapter",
    "active_training_profile",
    "foundational_reference",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _norm_repo(repo_id: str) -> str:
    return str(repo_id or "").strip()


def fetch_hf_models(authors: tuple[str, ...] = DEFAULT_AUTHORS) -> list[dict[str, Any]]:
    from huggingface_hub import HfApi

    api = HfApi()
    rows: list[dict[str, Any]] = []
    for author in authors:
        for model in api.list_models(author=author, full=True, limit=500):
            rows.append(
                {
                    "repo_id": model.modelId,
                    "author": author,
                    "downloads": int(getattr(model, "downloads", 0) or 0),
                    "likes": int(getattr(model, "likes", 0) or 0),
                    "pipeline_tag": getattr(model, "pipeline_tag", None) or "",
                    "tags": list(getattr(model, "tags", None) or []),
                    "last_modified": str(getattr(model, "last_modified", "") or ""),
                }
            )
    return rows


def local_training_profiles() -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / "config" / "model_training").glob("*.json")):
        payload = load_json(path)
        if not payload:
            continue
        schema = str(payload.get("schema_version", ""))
        hub = payload.get("hub") or {}
        if schema == "scbe_model_training_profile_v1" or hub:
            profiles.append(
                {
                    "profile_id": str(payload.get("profile_id", path.stem)),
                    "profile_path": repo_rel(path),
                    "schema_version": schema,
                    "base_model": str(payload.get("base_model", "")),
                    "adapter_repo": str(hub.get("adapter_repo", "")),
                    "dataset_repo": str(hub.get("dataset_repo", "")),
                    "stage": str(payload.get("stage", "")),
                    "title": str(payload.get("title", "")),
                    "description": str(payload.get("description", "")),
                    "dataset": payload.get("dataset") or {},
                    "evaluation": payload.get("evaluation") or {},
                }
            )
    return profiles


def local_merge_profiles() -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for path in sorted((REPO_ROOT / "config" / "model_training").glob("*.json")):
        payload = load_json(path)
        if not payload or payload.get("schema_version") != "scbe_coding_model_merge_profile_v1":
            continue
        profiles.append(
            {
                "merge_id": str(payload.get("merge_id", path.stem)),
                "profile_path": repo_rel(path),
                "base_model": str(payload.get("base_model", "")),
                "output_model_repo": str(payload.get("output_model_repo", "")),
                "merge_mode": str(payload.get("merge_mode", "")),
                "adapters": payload.get("adapters") or [],
                "blocked_adapters": payload.get("blocked_adapters") or [],
                "post_merge_gates": payload.get("post_merge_gates") or {},
            }
        )
    return profiles


def collect_local_runtime_models() -> dict[str, Any]:
    result: dict[str, Any] = {
        "ollama": {"available": False, "models": [], "error": ""},
        "hf_cache": {"available": False, "rows": [], "error": ""},
    }
    try:
        proc = subprocess.run(
            ["ollama", "list"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if proc.returncode == 0:
            models = []
            for line in proc.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    models.append(
                        {
                            "name": parts[0],
                            "id": parts[1],
                            "size": " ".join(parts[2:4]),
                            "modified": " ".join(parts[4:]),
                        }
                    )
            result["ollama"] = {"available": True, "models": models, "error": ""}
        else:
            result["ollama"]["error"] = (proc.stderr or proc.stdout).strip()[-1000:]
    except Exception as exc:
        result["ollama"]["error"] = f"{type(exc).__name__}: {exc}"

    try:
        proc = subprocess.run(
            ["hf", "cache", "ls"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if proc.returncode == 0:
            result["hf_cache"] = {
                "available": True,
                "rows": [line for line in proc.stdout.splitlines() if line.strip()][:100],
                "error": "",
            }
        else:
            result["hf_cache"]["error"] = (proc.stderr or proc.stdout).strip()[-1000:]
    except Exception as exc:
        result["hf_cache"]["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _profile_by_adapter(profiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        repo = _norm_repo(profile.get("adapter_repo", ""))
        if repo:
            out[repo] = profile
    return out


def _merge_inputs(merge_profiles: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for merge in merge_profiles:
        merge_id = str(merge.get("merge_id", ""))
        for adapter in merge.get("adapters") or []:
            if isinstance(adapter, dict) and adapter.get("adapter_repo"):
                out[_norm_repo(adapter["adapter_repo"])].append(merge_id)
    return dict(out)


def _merge_outputs(merge_profiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        _norm_repo(merge.get("output_model_repo", "")): merge
        for merge in merge_profiles
        if _norm_repo(merge.get("output_model_repo", ""))
    }


def _family(repo_id: str) -> str:
    name = repo_id.split("/", 1)[-1].lower()
    if "coding-agent" in name or "coder" in name or "coding" in name:
        return "coding_agent"
    if "polly" in name or "spiralverse" in name:
        return "polly_spiralverse"
    if "tongue" in name or "bijective" in name or "langue" in name:
        return "sacred_tongues"
    if "governance" in name or "phdm" in name or "geoseed" in name:
        return "governance_foundation"
    if "ops" in name:
        return "ops_assets"
    return "uncategorized"


def classify_model(
    row: dict[str, Any],
    *,
    profile_by_adapter: dict[str, dict[str, Any]],
    merge_inputs: dict[str, list[str]],
    merge_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    repo_id = _norm_repo(row["repo_id"])
    name = repo_id.split("/", 1)[-1].lower()
    downloads = int(row.get("downloads", 0) or 0)
    profile = profile_by_adapter.get(repo_id)
    merge_ids = merge_inputs.get(repo_id, [])
    merge_output = merge_outputs.get(repo_id)

    reasons: list[str] = []
    bucket = "archive_candidate"
    action = "keep_remote_public_but_remove_from_active_training_plan"

    if merge_output:
        bucket = "merge_candidate"
        action = "gate_with_smoke_eval_then_promote_or_archive"
        reasons.append(f"output of merge profile {merge_output['merge_id']}")
    elif "merged" in name:
        bucket = "merge_candidate"
        action = "gate_with_smoke_eval_then_promote_or_archive"
        reasons.append("name indicates merged full-model candidate")
    elif merge_ids:
        bucket = "active_specialist_adapter"
        action = "keep_as_merge_input_until_next gated merge"
        reasons.append("referenced by merge profile(s): " + ", ".join(sorted(merge_ids)))
    elif profile:
        bucket = "active_training_profile"
        action = "keep_if_profile_is_still_in_manifest_or_recent_plan"
        reasons.append(f"local profile exists: {profile['profile_id']}")
    elif any(token in name for token in ("smoke", "ckpt", "brick", "r8", "v7-hfjobs")):
        bucket = "archive_candidate"
        action = "tag_archive_after_confirming_no_profile_references"
        reasons.append("checkpoint/smoke/experimental naming")
    elif any(token in name for token in ("phdm", "geoseed", "ops-assets", "spiralverse-ai-federated")):
        bucket = "foundational_reference"
        action = "keep_as_reference_or_asset_repo_not_training_merge_input"
        reasons.append("foundation/reference/asset model family")
    elif downloads > 0:
        bucket = "public_interest_archive"
        action = "keep_public_card_but exclude from active merge unless eval evidence exists"
        reasons.append(f"has public downloads={downloads}")
    else:
        reasons.append("no local profile, no merge reference, no clear live role")

    if repo_id.startswith("SCBE-AETHER/"):
        action = "mirror_check_keep_one_canonical_owner_or_mark_as_org_mirror"
        reasons.append("organization mirror namespace")

    return {
        **row,
        "family": _family(repo_id),
        "bucket": bucket,
        "recommended_action": action,
        "active": bucket in ACTIVE_BUCKETS,
        "local_profile": profile or None,
        "merge_input_for": merge_ids,
        "merge_output_profile": merge_output,
        "reasons": reasons,
    }


def build_portfolio(hf_models: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = local_training_profiles()
    merges = local_merge_profiles()
    classified = [
        classify_model(
            row,
            profile_by_adapter=_profile_by_adapter(profiles),
            merge_inputs=_merge_inputs(merges),
            merge_outputs=_merge_outputs(merges),
        )
        for row in sorted(hf_models, key=lambda item: item["repo_id"].lower())
    ]
    buckets = Counter(row["bucket"] for row in classified)
    families = Counter(row["family"] for row in classified)
    active = [row for row in classified if row["active"]]
    archive = [row for row in classified if not row["active"]]
    return {
        "schema_version": "scbe_model_portfolio_board_v1",
        "created_at": utc_now(),
        "summary": {
            "hf_model_count": len(classified),
            "active_count": len(active),
            "archive_or_reference_count": len(archive),
            "bucket_counts": dict(sorted(buckets.items())),
            "family_counts": dict(sorted(families.items())),
        },
        "policy": {
            "do_not_merge_all": True,
            "merge_rule": "Only merge adapters that share the same base model and pass their frozen eval gates.",
            "canonical_target": "one promoted coding model plus specialist adapters retained only as gated merge inputs",
            "archive_rule": "Tag or document old experiments first; do not delete remote repos in this script.",
        },
        "local_training_profiles": profiles,
        "local_merge_profiles": merges,
        "local_runtime_models": collect_local_runtime_models(),
        "models": classified,
    }


def _write_markdown(board: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE Model Portfolio Board",
        "",
        f"- created_at: `{board['created_at']}`",
        f"- hf_model_count: `{board['summary']['hf_model_count']}`",
        f"- active_count: `{board['summary']['active_count']}`",
        f"- archive_or_reference_count: `{board['summary']['archive_or_reference_count']}`",
        "",
        "## Bucket Counts",
        "",
    ]
    for bucket, count in board["summary"]["bucket_counts"].items():
        lines.append(f"- `{bucket}`: {count}")
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- Do not merge all models together.",
            "- Merge only adapters with compatible base model, purpose, and eval evidence.",
            "- Keep one promoted coding model target; specialist adapters feed gated merges.",
            "- Archive means remove from active plan or tag/document, not delete.",
            "",
            "## Local Runtime Models",
            "",
        ]
    )
    ollama = board.get("local_runtime_models", {}).get("ollama", {})
    if ollama.get("available"):
        lines.append("| Runtime | Model | Size |")
        lines.append("| --- | --- | ---: |")
        for row in ollama.get("models", []):
            lines.append(f"| Ollama | `{row['name']}` | {row['size']} |")
    else:
        lines.append(f"- Ollama inventory unavailable: `{ollama.get('error', '')}`")
    hf_cache = board.get("local_runtime_models", {}).get("hf_cache", {})
    if hf_cache.get("available"):
        lines.append(f"- Hugging Face cache entries found: `{len(hf_cache.get('rows', []))}`")
    else:
        lines.append(f"- Hugging Face cache unavailable/empty: `{hf_cache.get('error', '')}`")
    lines.extend(
        [
            "",
            "## Models",
            "",
            "| Repo | Bucket | Family | Downloads | Action |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in board["models"]:
        lines.append(
            "| `{repo}` | `{bucket}` | `{family}` | {downloads} | {action} |".format(
                repo=row["repo_id"],
                bucket=row["bucket"],
                family=row["family"],
                downloads=row.get("downloads", 0),
                action=row["recommended_action"],
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(board: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "model_portfolio.json"
    md_path = output_dir / "MODEL_PORTFOLIO.md"
    json_path.write_text(json.dumps(board, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(board, md_path)
    return {"json": str(json_path), "markdown": str(md_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--authors", default=",".join(DEFAULT_AUTHORS))
    parser.add_argument("--offline-hf-json", type=Path, default=None, help="Use pre-fetched HF model rows JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.offline_hf_json:
        hf_models = json.loads(args.offline_hf_json.read_text(encoding="utf-8"))
    else:
        authors = tuple(author.strip() for author in args.authors.split(",") if author.strip())
        hf_models = fetch_hf_models(authors)
    board = build_portfolio(hf_models)
    paths = write_outputs(board, args.output_dir)
    print(json.dumps({"ok": True, "summary": board["summary"], "paths": paths}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
