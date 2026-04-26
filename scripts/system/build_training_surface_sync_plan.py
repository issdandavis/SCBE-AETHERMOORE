#!/usr/bin/env python3
"""Build executable sync instructions for SCBE training surfaces.

The consolidation step decides which specialist buckets should train. This
script turns that decision into a no-launch command plan for Hugging Face,
Kaggle, and local verification. It is intentionally dry-run only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSOLIDATION_PLAN = (
    REPO_ROOT / "artifacts" / "ai_training_consolidation" / "latest" / "consolidation_plan.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "ai_training_consolidation" / "latest"
KAGGLE_LAUNCHER = REPO_ROOT / "scripts" / "kaggle_auto" / "launch.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON payload must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _repo_rel(path: Path | str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate).replace("\\", "/")
    try:
        return str(candidate.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(candidate).replace("\\", "/")


def _ps_quote(value: str) -> str:
    """Quote a command argument for copy-safe PowerShell display."""
    if not value:
        return "''"
    if all(ch.isalnum() or ch in "-_./:\\\\" for ch in value):
        return value
    return shlex.quote(value)


def _load_kaggle_rounds() -> dict[str, Any]:
    if not KAGGLE_LAUNCHER.exists():
        return {}
    spec = importlib.util.spec_from_file_location("scbe_kaggle_launch_config", KAGGLE_LAUNCHER)
    if spec is None or spec.loader is None:
        return {}
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    rounds = getattr(module, "ROUNDS", {})
    return rounds if isinstance(rounds, dict) else {}


def _dataset_files(profile: dict[str, Any]) -> list[dict[str, Any]]:
    dataset = profile.get("dataset") or {}
    hub = profile.get("hub") or {}
    dataset_repo = str(hub.get("dataset_repo", "")).strip()
    root_rel = str(dataset.get("root", "training-data/sft")).replace("\\", "/")
    root = REPO_ROOT / root_rel
    rows: list[dict[str, Any]] = []
    for split_key, split in (("train_files", "train"), ("eval_files", "eval")):
        for name in dataset.get(split_key, []) or []:
            rel = f"{root_rel}/{name}".replace("\\", "/")
            path = root / str(name)
            rows.append(
                {
                    "split": split,
                    "name": str(name),
                    "repo_path": rel,
                    "exists": path.exists(),
                    "upload_command": (
                        "BLOCKED: profile hub.dataset_repo is missing"
                        if not dataset_repo
                        else (
                            "hf upload "
                            f"{_ps_quote(dataset_repo)} "
                            f"{_ps_quote(rel)} {_ps_quote(str(name))} --repo-type dataset"
                        )
                    ),
                }
            )
    return rows


def build_profile_plan(profile_path: Path) -> dict[str, Any]:
    profile = _load_json(profile_path)
    hub = profile.get("hub") or {}
    execution = profile.get("execution") or {}
    profile_rel = _repo_rel(profile_path)
    dataset_repo = str(hub.get("dataset_repo", ""))
    adapter_repo = str(hub.get("adapter_repo", ""))
    files = _dataset_files(profile)
    missing_files = [item["repo_path"] for item in files if not item["exists"]]
    missing_config = []
    if not dataset_repo:
        missing_config.append("hub.dataset_repo")
    if not adapter_repo:
        missing_config.append("hub.adapter_repo")

    return {
        "profile_id": profile.get("profile_id", profile_path.stem),
        "profile_path": profile_rel,
        "base_model": profile.get("base_model", ""),
        "dataset_repo": dataset_repo,
        "adapter_repo": adapter_repo,
        "recommended_target": execution.get("recommended_target", "hf-jobs"),
        "hf_flavor": execution.get("hf_flavor", ""),
        "timeout": execution.get("timeout", ""),
        "dataset_files": files,
        "missing_files": missing_files,
        "missing_config": missing_config,
        "preflight_command": (
            "python scripts\\system\\dispatch_coding_agent_hf_job.py plan "
            f"--profile-path {_ps_quote(profile_rel)} --json"
        ),
        "dispatch_command": (
            "python scripts\\system\\dispatch_coding_agent_hf_job.py dispatch "
            f"--profile-path {_ps_quote(profile_rel)}"
        ),
        "safe_to_dispatch": not missing_files and not missing_config,
    }


def _unique_profile_paths(consolidation_plan: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for specialist in consolidation_plan.get("specialists", []) or []:
        if specialist.get("status") not in {"ready_for_training", "promote_candidate"}:
            continue
        for raw in specialist.get("profile_candidates", []) or []:
            rel = str(raw).replace("\\", "/")
            if rel in seen:
                continue
            seen.add(rel)
            path = REPO_ROOT / rel
            if path.exists():
                paths.append(path)
    return paths


def _kaggle_plan(rounds: dict[str, Any]) -> list[dict[str, Any]]:
    selected = []
    for name, config in rounds.items():
        files = config.get("files")
        if not isinstance(files, list):
            continue
        if any("geoseal" in str(item).lower() or "bijective" in str(item).lower() for item in files):
            selected.append(
                {
                    "round": name,
                    "description": config.get("desc", ""),
                    "base_model": config.get("base_model", ""),
                    "hf_repo": config.get("hf_repo", ""),
                    "hf_dataset_repo": config.get("hf_dataset_repo", ""),
                    "kaggle_dataset": config.get("kaggle_dataset", ""),
                    "launch_command": f"python scripts\\kaggle_auto\\launch.py --round {name} --gpu t4x2 --poll",
                    "status_command": "python scripts\\kaggle_auto\\launch.py --status",
                    "pull_command": f"python scripts\\kaggle_auto\\launch.py --pull --round {name}",
                }
            )
    return selected


def build_sync_plan(consolidation_plan_path: Path = DEFAULT_CONSOLIDATION_PLAN) -> dict[str, Any]:
    consolidation_plan = _load_json(consolidation_plan_path)
    profile_plans = [build_profile_plan(path) for path in _unique_profile_paths(consolidation_plan)]
    kaggle_rounds = _kaggle_plan(_load_kaggle_rounds())
    missing_profiles = [
        raw
        for specialist in consolidation_plan.get("specialists", []) or []
        for raw in specialist.get("profile_candidates", []) or []
        if not (REPO_ROOT / str(raw)).exists()
    ]

    return {
        "schema_version": "scbe_training_surface_sync_plan_v1",
        "generated_at_utc": _utc_now(),
        "source_plan": _repo_rel(consolidation_plan_path),
        "rule": "Do not dispatch remote jobs until dataset uploads, local preflight, and bucket readiness pass.",
        "local_preflight_commands": [
            "python scripts\\system\\consolidate_ai_training.py --include-kaggle --include-hf --include-cloud",
            "python scripts\\benchmark\\specialist_bucket_readiness.py",
            "python scripts\\system\\review_training_runs.py",
        ],
        "profile_jobs": profile_plans,
        "missing_profile_candidates": sorted(set(str(item).replace("\\", "/") for item in missing_profiles)),
        "kaggle_rounds": kaggle_rounds,
        "post_run_commands": [
            "python scripts\\system\\review_training_runs.py",
            "python scripts\\benchmark\\specialist_bucket_readiness.py",
            "python scripts\\check_secrets.py",
        ],
    }


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# SCBE Training Surface Sync Plan",
        "",
        f"Generated: {plan['generated_at_utc']}",
        "",
        plan["rule"],
        "",
        "## Local Preflight",
        "",
    ]
    for command in plan["local_preflight_commands"]:
        lines.append(f"- `{command}`")

    lines.extend(["", "## Hugging Face Dataset Uploads and Jobs", ""])
    for job in plan["profile_jobs"]:
        state = "READY" if job["safe_to_dispatch"] else "BLOCKED"
        lines.append(f"### {job['profile_id']} ({state})")
        lines.append("")
        lines.append(f"- Profile: `{job['profile_path']}`")
        lines.append(f"- Base model: `{job['base_model']}`")
        lines.append(f"- Dataset repo: `{job['dataset_repo']}`")
        lines.append(f"- Adapter repo: `{job['adapter_repo']}`")
        if job["missing_files"]:
            lines.append(f"- Missing local files: `{', '.join(job['missing_files'])}`")
        if job.get("missing_config"):
            lines.append(f"- Missing profile config: `{', '.join(job['missing_config'])}`")
        lines.append("- Upload commands:")
        for item in job["dataset_files"]:
            marker = (
                "CONFIG-BLOCKED"
                if str(item["upload_command"]).startswith("BLOCKED:")
                else ("OK" if item["exists"] else "MISSING")
            )
            lines.append(f"- `{item['upload_command']}`  # {item['split']} {marker}")
        lines.append(f"- Preflight: `{job['preflight_command']}`")
        lines.append(f"- Dispatch when ready: `{job['dispatch_command']}`")
        lines.append("")

    if plan["missing_profile_candidates"]:
        lines.extend(["## Missing Profile Candidates", ""])
        for item in plan["missing_profile_candidates"]:
            lines.append(f"- `{item}`")
        lines.append("")

    lines.extend(["## Kaggle Rounds", ""])
    if not plan["kaggle_rounds"]:
        lines.append("- No matching Kaggle training rounds found.")
    for round_plan in plan["kaggle_rounds"]:
        lines.append(f"### {round_plan['round']}")
        lines.append("")
        lines.append(f"- Description: {round_plan['description']}")
        lines.append(f"- Base model: `{round_plan['base_model']}`")
        lines.append(f"- Output repo: `{round_plan['hf_repo']}`")
        lines.append(f"- Launch: `{round_plan['launch_command']}`")
        lines.append(f"- Status: `{round_plan['status_command']}`")
        lines.append(f"- Pull: `{round_plan['pull_command']}`")
        lines.append("")

    lines.extend(["## Post-Run Verification", ""])
    for command in plan["post_run_commands"]:
        lines.append(f"- `{command}`")
    lines.append("")
    return "\n".join(lines)


def run(
    consolidation_plan_path: Path = DEFAULT_CONSOLIDATION_PLAN,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    plan = build_sync_plan(consolidation_plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "training_surface_sync_plan.json"
    md_path = output_dir / "TRAINING_SURFACE_SYNC_PLAN.md"
    _write_json(json_path, plan)
    md_path.write_text(render_markdown(plan), encoding="utf-8")
    return {
        "schema_version": "scbe_training_surface_sync_plan_result_v1",
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "profile_job_count": len(plan["profile_jobs"]),
        "kaggle_round_count": len(plan["kaggle_rounds"]),
        "blocked_profile_jobs": [
            item["profile_id"] for item in plan["profile_jobs"] if not item["safe_to_dispatch"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCBE HF/Kaggle/local training sync plan")
    parser.add_argument("--consolidation-plan", default=str(DEFAULT_CONSOLIDATION_PLAN))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run(Path(args.consolidation_plan), Path(args.output_dir))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
