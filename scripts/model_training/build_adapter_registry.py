#!/usr/bin/env python3
"""Build the SCBE coding-adapter registry.

The registry is the source of truth for routing-before-merge decisions. It
tracks remote adapter repos, local adapter weights, base model identity,
training lanes, dispatch packets, and available evaluation reports without
performing any training or merge action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MERGE_PROFILE = REPO_ROOT / "config" / "model_training" / "coding-agent-qwen-merged-coding-model.json"
DEFAULT_HF_JOBS_ROOT = REPO_ROOT / "artifacts" / "hf_coding_agent_jobs"
DEFAULT_KAGGLE_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "kaggle_output"
DEFAULT_MODEL_EVAL_ROOT = REPO_ROOT / "artifacts" / "model_evals"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "adapter_registry" / "registry.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def latest_job_packets(root: Path) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    for packet_path in root.glob("*/20*/job_packet.json"):
        try:
            packet = read_json(packet_path)
        except Exception:
            continue
        profile_id = str(packet.get("profile_id") or packet_path.parents[1].name)
        current = packets.get(profile_id)
        if current is None or str(packet.get("prepared_at_utc", "")) > str(current.get("prepared_at_utc", "")):
            packet["_packet_path"] = safe_rel(packet_path)
            packets[profile_id] = packet
    return packets


def local_adapter_dirs(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for config_path in root.rglob("adapter_config.json"):
        adapter_dir = config_path.parent
        if adapter_dir.name.startswith("checkpoint-") and (adapter_dir.parent / "adapter_config.json").exists():
            continue
        model_path = adapter_dir / "adapter_model.safetensors"
        if not model_path.exists():
            model_path = adapter_dir / "adapter_model.bin"
        try:
            config = read_json(config_path)
        except Exception:
            config = {}
        rows.append(
            {
                "local_adapter_dir": safe_rel(adapter_dir),
                "adapter_config_path": safe_rel(config_path),
                "adapter_model_path": safe_rel(model_path) if model_path.exists() else "",
                "adapter_model_sha256": sha256_file(model_path) if model_path.exists() else "",
                "base_model": config.get("base_model_name_or_path"),
                "lora_r": config.get("r"),
                "lora_alpha": config.get("lora_alpha"),
                "target_modules": config.get("target_modules") or [],
            }
        )
    return sorted(rows, key=lambda row: row["local_adapter_dir"])


def latest_eval_reports(root: Path) -> dict[str, list[dict[str, Any]]]:
    reports: dict[str, list[dict[str, Any]]] = {}
    for report_path in root.rglob("report.json"):
        try:
            payload = read_json(report_path)
        except Exception:
            continue
        adapter = payload.get("adapter")
        if adapter is None and payload.get("results"):
            adapter = ",".join(str(row.get("adapter")) for row in payload["results"])
        if not adapter:
            continue
        summary = payload.get("summary") or {}
        reports.setdefault(str(adapter), []).append(
            {
                "report_path": safe_rel(report_path),
                "generated_at_utc": payload.get("generated_at_utc"),
                "summary": summary,
            }
        )
    for rows in reports.values():
        rows.sort(key=lambda row: str(row.get("generated_at_utc") or row.get("report_path")), reverse=True)
    return reports


def model_sha(repo_id: str, enabled: bool) -> str:
    if not enabled or not repo_id:
        return ""
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(repo_id)
        return str(getattr(info, "sha", "") or "")
    except Exception:
        return ""


def match_local(profile_id: str, adapter_repo: str, local_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tokens = {profile_id.lower(), adapter_repo.rsplit("/", 1)[-1].lower()}
    return [
        row
        for row in local_rows
        if any(token and token in row["local_adapter_dir"].lower() for token in tokens)
    ]


def build_registry(args: argparse.Namespace) -> dict[str, Any]:
    profile = read_json(args.merge_profile)
    job_packets = latest_job_packets(args.hf_jobs_root)
    local_rows = local_adapter_dirs(args.kaggle_output_root)
    eval_reports = latest_eval_reports(args.model_eval_root)

    refresh_hf = not args.no_hf_refresh
    base_model = str(profile.get("base_model") or "")
    base_sha = model_sha(base_model, refresh_hf)
    adapters = []
    for item in profile.get("adapters", []):
        profile_id = str(item.get("profile_id"))
        adapter_repo = str(item.get("adapter_repo"))
        packet = job_packets.get(profile_id, {})
        adapters.append(
            {
                "profile_id": profile_id,
                "lane": item.get("stage"),
                "adapter_repo": adapter_repo,
                "adapter_repo_sha": model_sha(adapter_repo, refresh_hf),
                "base_model": packet.get("base_model") or base_model,
                "base_model_sha": base_sha,
                "parent_shas": [sha for sha in [base_sha] if sha],
                "merge_profile_weight": item.get("weight"),
                "required": bool(item.get("required", False)),
                "status": "registered_remote",
                "dispatch": {
                    "job_id": (packet.get("dispatch") or {}).get("job_id", ""),
                    "packet_path": packet.get("_packet_path", ""),
                    "prepared_at_utc": packet.get("prepared_at_utc", ""),
                    "dispatched": bool(packet.get("dispatched", False)),
                },
                "train_datasets": packet.get("train_datasets", []),
                "eval_datasets": packet.get("eval_datasets", []),
                "local_adapters": match_local(profile_id, adapter_repo, local_rows),
                "eval_reports": eval_reports.get(adapter_repo, []),
                "promotion": {
                    "route_first": True,
                    "merge_eligible": False,
                    "reason": "Executable and drift gates must pass before merge.",
                },
            }
        )

    for row in local_rows:
        if any(row in adapter["local_adapters"] for adapter in adapters):
            continue
        adapters.append(
            {
                "profile_id": Path(row["local_adapter_dir"]).name,
                "lane": "local_unregistered",
                "adapter_repo": "",
                "adapter_repo_sha": row.get("adapter_model_sha256", ""),
                "base_model": row.get("base_model"),
                "base_model_sha": base_sha if row.get("base_model") == base_model else "",
                "parent_shas": [sha for sha in [base_sha if row.get("base_model") == base_model else ""] if sha],
                "merge_profile_weight": None,
                "required": False,
                "status": "local_unregistered",
                "dispatch": {},
                "train_datasets": [],
                "eval_datasets": [],
                "local_adapters": [row],
                "eval_reports": [],
                "promotion": {
                    "route_first": True,
                    "merge_eligible": False,
                    "reason": "Local adapter is not in the merge profile registry.",
                },
            }
        )

    return {
        "schema_version": "scbe_adapter_registry_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "merge_profile": safe_rel(args.merge_profile),
        "base_model": base_model,
        "base_model_sha": base_sha,
        "policy": {
            "default": "route_before_merge",
            "merge_requires": [
                "adapter registry entry",
                "solo executable gate",
                "stage6 regression guard",
                "drift decision not route_only",
                "lineage block in model card",
            ],
        },
        "adapters": adapters,
        "blocked_adapters": profile.get("blocked_adapters", []),
    }


def write_outputs(registry: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Adapter Registry",
        "",
        f"Generated: `{registry['generated_at_utc']}`",
        "",
        "| Profile | Lane | Repo | Local Weights | Eval Reports | Merge Eligible |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for adapter in registry["adapters"]:
        lines.append(
            f"| `{adapter['profile_id']}` | `{adapter.get('lane')}` | `{adapter.get('adapter_repo')}` | "
            f"{len(adapter.get('local_adapters') or [])} | {len(adapter.get('eval_reports') or [])} | "
            f"{adapter['promotion']['merge_eligible']} |"
        )
    blocked = registry.get("blocked_adapters") or []
    if blocked:
        lines.extend(
            [
                "",
                "## Blocked / Quarantined Adapters",
                "",
                "| Profile | Repo | Status | Reason |",
                "| --- | --- | --- | --- |",
            ]
        )
        for adapter in blocked:
            reason = str(adapter.get("reason") or "").replace("\n", " ")
            if len(reason) > 240:
                reason = reason[:237] + "..."
            lines.append(
                f"| `{adapter.get('profile_id', '')}` | `{adapter.get('adapter_repo', '')}` | "
                f"`{adapter.get('status', 'blocked')}` | {reason} |"
            )
    output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merge-profile", type=Path, default=DEFAULT_MERGE_PROFILE)
    parser.add_argument("--hf-jobs-root", type=Path, default=DEFAULT_HF_JOBS_ROOT)
    parser.add_argument("--kaggle-output-root", type=Path, default=DEFAULT_KAGGLE_OUTPUT_ROOT)
    parser.add_argument("--model-eval-root", type=Path, default=DEFAULT_MODEL_EVAL_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-hf-refresh", action="store_true", help="Skip best-effort Hugging Face SHA lookup.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = build_registry(args)
    write_outputs(registry, args.output)
    print(f"Registry JSON: {args.output}")
    print(f"Registry MD:   {args.output.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
