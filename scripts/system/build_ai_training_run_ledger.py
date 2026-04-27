#!/usr/bin/env python3
"""Build a platform-split ledger of SCBE AI training runs and next conversions.

The ledger is intentionally local-first. It gathers evidence from Kaggle,
Hugging Face Jobs reports, Colab receipts, local runs, and eval artifacts, then
classifies each item into what it should become next: promotion evidence, repair
data, ops/development-interaction data, or non-quantized merge readiness input.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "training_run_ledger" / "latest"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def first_existing_json(root: Path, names: list[str]) -> tuple[str, Any | None]:
    for name in names:
        matches = sorted(root.rglob(name), key=lambda p: p.stat().st_mtime, reverse=True)
        if matches:
            return rel(matches[0]), load_json(matches[0])
    return "", None


def infer_lane(text: str) -> str:
    lowered = text.lower()
    lane_map = [
        ("dsl_synthesis", ("dsl", "well_select", "executable")),
        ("bijective_tongue", ("bijective", "tongue", "langues", "cross_tongue")),
        ("binary_hex", ("binary", "hex")),
        ("coding_approval", ("approval", "metric", "college")),
        ("regularized_coding", ("regularized", "coding-v8")),
        ("stage6_repair", ("stage6", "atomic_workflow")),
        ("operator_agent_bus", ("operator", "agent_bus", "agentic")),
        ("aligned_foundations", ("aligned", "foundation", "chemistry")),
        ("local_sync", ("local_cloud_sync", "sync")),
    ]
    for lane, hints in lane_map:
        if any(hint in lowered for hint in hints):
            return lane
    return "general_training"


def infer_conversion(item: dict[str, Any]) -> dict[str, str]:
    text = json.dumps(item, sort_keys=True).lower()
    status = str(item.get("status") or item.get("promotion_status") or "").lower()
    lane = item.get("lane", "")

    if "dsl_failure_math" in text or "format_repair_result" in text:
        return {
            "conversion": "convert_diagnostics_to_training_controls",
            "why": "Failure math and format-repair reports should update samplers, token weights, and repair curricula.",
            "next_step": "Keep these as trainer-control evidence; verify matching kernel/config patches exist before another run.",
        }
    if "merge" in text and ("plan" in text or "readiness" in text):
        return {
            "conversion": "merge_readiness_evidence",
            "why": "Merge reports should constrain non-quantized adapter routing/merge decisions.",
            "next_step": "Use only after adapters pass gates; keep route-first when drift/sign-conflict is high.",
        }
    if "promotion-negative" in text or "quarantine" in text or "unparseable_output" in text:
        return {
            "conversion": "mine_failure_rows_to_repair_sft",
            "why": "Failed adapter output is most useful as targeted repair data, not merge input.",
            "next_step": "Run/extend scorer failure mining, add rows to contract repair corpus, retrain small repair lane.",
        }
    if "eval-pending" in text or "adapter pushed" in text or item.get("has_adapter"):
        return {
            "conversion": "run_frozen_eval_and_gate",
            "why": "Adapter exists but is not proven routable or mergeable.",
            "next_step": "Run DSL executable, Stage 6 regression, frozen perplexity, and coding benchmark gates.",
        }
    if "running" in status or "queued" in status or "pushed" in status:
        return {
            "conversion": "pull_then_eval",
            "why": "Remote run state must be reconciled before its outputs can be used.",
            "next_step": "Poll/pull output, write round report, then run eval gates.",
        }
    if item.get("platform") == "colab":
        return {
            "conversion": "ops_interaction_training_data",
            "why": "Saved Colab receipts are mostly notebook/control-plane evidence, not completed trainer output.",
            "next_step": "Convert verified/blocked handoffs into operator-agent-bus examples and Colab runbook fixes.",
        }
    if item.get("platform") == "local" and lane == "local_sync":
        return {
            "conversion": "index_as_lineage_evidence",
            "why": "Local sync artifacts prove file movement and state snapshots, not model quality.",
            "next_step": "Use manifests for lineage; do not train on indexes directly.",
        }
    if item.get("platform") == "dataset":
        return {
            "conversion": "bucket_and_balance_dataset",
            "why": "Raw SFT files need bucket assignment and imbalance checks before training.",
            "next_step": "Regularize into train/eval buckets, cap dominant classes, preserve aligned multi-representation links.",
        }
    return {
        "conversion": "needs_classification",
        "why": "No decisive metric or state found yet.",
        "next_step": "Attach report/eval evidence or classify manually before training or merge.",
    }


def run_command(args: list[str], timeout: int = 30) -> str:
    try:
        proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return (proc.stdout + "\n" + proc.stderr).strip()
    except Exception as exc:
        return f"UNAVAILABLE: {exc}"


def parse_kaggle_live() -> dict[str, str]:
    output = run_command(["kaggle", "kernels", "list", "--mine", "--csv"], timeout=30)
    refs: dict[str, str] = {}
    for line in output.splitlines():
        if not line.startswith("issacizrealdavis/"):
            continue
        ref = line.split(",", 1)[0].strip()
        slug = ref.split("/", 1)[-1]
        if "polly-auto" not in slug:
            continue
        status_out = run_command(["kaggle", "kernels", "status", ref], timeout=20).lower()
        if "complete" in status_out:
            refs[slug] = "complete"
        elif "running" in status_out:
            refs[slug] = "running"
        elif "queued" in status_out:
            refs[slug] = "queued"
        elif "error" in status_out or "failed" in status_out:
            refs[slug] = "error"
        else:
            refs[slug] = "unknown"
    return refs


def extract_kernel_config(script_path: Path) -> dict[str, Any]:
    text = script_path.read_text(encoding="utf-8", errors="replace") if script_path.exists() else ""
    match = re.search(r"KERNEL_CONFIG\s*=\s*'(\{.*?\})'", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def collect_kaggle(live: bool) -> list[dict[str, Any]]:
    live_status = parse_kaggle_live() if live else {}
    items: dict[str, dict[str, Any]] = {}
    for kernel_dir in sorted((ROOT / "artifacts" / "kaggle_kernels").glob("polly-auto-*")):
        if not kernel_dir.is_dir():
            continue
        slug = kernel_dir.name
        meta = load_json(kernel_dir / "kernel-metadata.json") or {}
        cfg = extract_kernel_config(kernel_dir / "script.py")
        items[slug] = {
            "id": slug,
            "platform": "kaggle",
            "lane": infer_lane(slug + " " + json.dumps(cfg)),
            "status": live_status.get(slug, "staged_or_unknown"),
            "kernel_dir": rel(kernel_dir),
            "kernel_ref": meta.get("id", ""),
            "hf_repo": cfg.get("hf_repo", ""),
            "base_model": cfg.get("base_model", ""),
            "dataset_files": cfg.get("files", []),
            "eval_files": cfg.get("eval_files", []),
            "non_quantized_policy": "do_not_quantize_for_merge; Kaggle training may use low-bit loading only as remote training implementation detail",
        }

    for output_dir in sorted((ROOT / "artifacts" / "kaggle_output").glob("polly-auto-*")):
        if not output_dir.is_dir():
            continue
        slug = output_dir.name
        item = items.setdefault(
            slug,
            {
                "id": slug,
                "platform": "kaggle",
                "lane": infer_lane(slug),
                "status": live_status.get(slug, "pulled_output"),
            },
        )
        done_path, done = first_existing_json(output_dir, ["DONE.json"])
        status_path, status = first_existing_json(output_dir, ["STATUS.json"])
        history_path, history = first_existing_json(output_dir, ["TRAINING_HISTORY.json", "trainer_state.json"])
        item.update(
            {
                "output_dir": rel(output_dir),
                "done_path": done_path,
                "status_path": status_path,
                "history_path": history_path,
                "has_adapter": any((p / "adapter_config.json").exists() for p in output_dir.rglob("*") if p.is_dir()),
            }
        )
        if isinstance(done, dict):
            item["done"] = done
        if isinstance(status, dict):
            item["status_payload"] = status
            item["status"] = live_status.get(slug) or status.get("phase") or item.get("status")
        if isinstance(history, dict):
            item["history_summary"] = {
                "global_step": history.get("global_step"),
                "best_metric": history.get("best_metric"),
                "best_model_checkpoint": history.get("best_model_checkpoint"),
                "train_records": history.get("train_records"),
                "eval_records": history.get("eval_records"),
            }
    return [decorate(item) for item in sorted(items.values(), key=lambda x: x["id"])]


def collect_huggingface() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((ROOT / "artifacts" / "training_reports").glob("*.json")):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        text = json.dumps(payload).lower()
        platform = str(payload.get("platform") or "").lower()
        if "huggingface" not in platform and "hf_job" not in text and "hf_repo" not in payload:
            continue
        item = {
            "id": payload.get("round") or path.stem,
            "platform": "huggingface",
            "lane": infer_lane(path.stem + " " + text),
            "status": payload.get("promotion_status") or payload.get("status") or "report_found",
            "report": rel(path),
            "hf_job_id": payload.get("hf_job_id", ""),
            "hf_repo": payload.get("hf_repo") or payload.get("adapter_path") or "",
            "base_model": payload.get("base_model", ""),
            "dataset_files": payload.get("dataset_files", []),
            "eval_files": payload.get("eval_files", []),
            "results": payload.get("results", {}),
            "promotion_status": payload.get("promotion_status", ""),
            "non_quantized_policy": "route or merge full-precision adapter deltas only; no quantized merge artifact",
            "has_adapter": bool(payload.get("adapter_path") or payload.get("hf_repo")),
        }
        items.append(decorate(item))

    jobs_ps = run_command(["hf", "jobs", "ps"], timeout=30)
    if "No jobs found" in jobs_ps or "no jobs found" in jobs_ps.lower():
        items.append(
            decorate(
                {
                    "id": "hf-jobs-live",
                    "platform": "huggingface",
                    "lane": "ops",
                    "status": "no_live_jobs_found",
                    "report": "",
                    "next_observation": "Local reports still contain completed HF Jobs evidence; live CLI currently reports no active jobs.",
                }
            )
        )
    return items


def collect_colab() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    inventory_path = ROOT / "artifacts" / "training_reports" / "colab_saved_runs_inventory_20260426.json"
    payload = load_json(inventory_path)
    if isinstance(payload, dict):
        for idx, receipt in enumerate(payload.get("records") or payload.get("receipts") or []):
            if not isinstance(receipt, dict):
                continue
            item = {
                "id": receipt.get("name") or receipt.get("id") or f"colab-receipt-{idx:03d}",
                "platform": "colab",
                "lane": infer_lane(json.dumps(receipt)),
                "status": receipt.get("classification") or receipt.get("kind") or "receipt",
                "report": rel(inventory_path),
                "receipt_path": receipt.get("path") or receipt.get("file") or "",
                "notebook": receipt.get("notebook") or receipt.get("name") or "",
            }
            items.append(decorate(item))
    else:
        items.append(
            decorate(
                {
                    "id": "colab-inventory",
                    "platform": "colab",
                    "lane": "ops",
                    "status": "inventory_missing",
                    "report": rel(inventory_path),
                }
            )
        )

    for path in sorted((ROOT / "notebooks").glob("*.ipynb")) + sorted((ROOT / "artifacts" / "colab").glob("*.ipynb")):
        items.append(
            decorate(
                {
                    "id": path.stem,
                    "platform": "colab",
                    "lane": infer_lane(path.name),
                    "status": "notebook_available",
                    "notebook": rel(path),
                }
            )
        )
    return items


def collect_local() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for report in sorted((ROOT / "artifacts" / "training_reports").glob("*.md")):
        text = report.read_text(encoding="utf-8", errors="replace")[:4000]
        if any(token in report.name.lower() for token in ("colab", "kaggle", "hf-")):
            continue
        items.append(
            decorate(
                {
                    "id": report.stem,
                    "platform": "local",
                    "lane": infer_lane(report.name + " " + text),
                    "status": "report",
                    "report": rel(report),
                }
            )
        )

    for run_summary in sorted((ROOT / "training" / "runs").rglob("run_summary.json"))[-30:]:
        payload = load_json(run_summary) or {}
        items.append(
            decorate(
                {
                    "id": run_summary.parent.name,
                    "platform": "local",
                    "lane": "local_sync",
                    "status": "snapshot",
                    "report": rel(run_summary),
                    "summary": payload if isinstance(payload, dict) else {},
                }
            )
        )
    return items


def collect_datasets() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((ROOT / "training-data" / "sft").glob("*.jsonl")):
        try:
            n = sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
        except OSError:
            n = 0
        items.append(
            decorate(
                {
                    "id": path.name,
                    "platform": "dataset",
                    "lane": infer_lane(path.name),
                    "status": "available",
                    "path": rel(path),
                    "records": n,
                }
            )
        )
    return items


def decorate(item: dict[str, Any]) -> dict[str, Any]:
    item.setdefault("lane", infer_lane(json.dumps(item)))
    item.update(infer_conversion(item))
    return item


def build_ledger(live_kaggle: bool) -> dict[str, Any]:
    platforms = {
        "kaggle": collect_kaggle(live_kaggle),
        "huggingface": collect_huggingface(),
        "colab": collect_colab(),
        "local": collect_local(),
        "dataset": collect_datasets(),
    }
    all_items = [item for rows in platforms.values() for item in rows]
    conversion_counts = Counter(item["conversion"] for item in all_items)
    platform_counts = {platform: len(rows) for platform, rows in platforms.items()}
    lane_counts = Counter(item.get("lane", "unknown") for item in all_items)
    return {
        "schema_version": "scbe_ai_training_run_ledger_v1",
        "generated_at_utc": utc_now(),
        "policy": {
            "no_quantization": True,
            "merge_rule": "Do not quantize or merge adapters until route/eval gates pass. Prefer routing first; use non-quantized PEFT merge only after gates.",
            "source_of_truth": "Repo manifests, training reports, frozen evals, and pulled remote artifacts.",
        },
        "summary": {
            "platform_counts": platform_counts,
            "conversion_counts": dict(conversion_counts),
            "lane_counts": dict(lane_counts),
        },
        "platforms": platforms,
        "work_order": build_work_order(all_items),
    }


def build_work_order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "pull_then_eval": 10,
        "run_frozen_eval_and_gate": 20,
        "mine_failure_rows_to_repair_sft": 30,
        "bucket_and_balance_dataset": 40,
        "ops_interaction_training_data": 50,
        "index_as_lineage_evidence": 60,
        "convert_diagnostics_to_training_controls": 25,
        "merge_readiness_evidence": 35,
        "needs_classification": 70,
    }
    rows = []
    for item in items:
        rows.append(
            {
                "priority": priority.get(item["conversion"], 99),
                "id": item.get("id"),
                "platform": item.get("platform"),
                "lane": item.get("lane"),
                "conversion": item.get("conversion"),
                "next_step": item.get("next_step"),
                "evidence": item.get("report") or item.get("output_dir") or item.get("kernel_dir") or item.get("path") or item.get("notebook") or "",
            }
        )
    return sorted(rows, key=lambda row: (row["priority"], str(row["platform"]), str(row["id"])))


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        "# AI Training Run Ledger",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        "",
        "## Policy",
        "",
        "- No quantization for merge or final model consolidation.",
        "- Route first. Non-quantized PEFT merge only after frozen eval, executable, Stage 6, and functional gates pass.",
        "- Failed outputs become repair data. Colab control-plane receipts become development-interaction data.",
        "",
        "## Summary",
        "",
        f"- Platform counts: `{json.dumps(payload['summary']['platform_counts'], sort_keys=True)}`",
        f"- Conversion counts: `{json.dumps(payload['summary']['conversion_counts'], sort_keys=True)}`",
        "",
        "## Work Order",
        "",
        "| Priority | Platform | Lane | ID | Conversion | Next Step | Evidence |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["work_order"][:120]:
        lines.append(
            f"| {row['priority']} | {row['platform']} | {row['lane']} | `{row['id']}` | "
            f"{row['conversion']} | {row['next_step']} | `{row['evidence']}` |"
        )

    for platform, rows in payload["platforms"].items():
        lines.extend(["", f"## {platform.title()}", "", "| ID | Lane | Status | Conversion | Evidence |", "| --- | --- | --- | --- | --- |"])
        for item in rows[:80]:
            evidence = item.get("report") or item.get("output_dir") or item.get("kernel_dir") or item.get("path") or item.get("notebook") or ""
            status = str(item.get("status", "")).replace("\n", " ")[:120]
            lines.append(
                f"| `{item.get('id')}` | {item.get('lane')} | {status} | {item.get('conversion')} | `{evidence}` |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-live-kaggle", action="store_true", help="Skip Kaggle CLI status checks.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    payload = build_ledger(live_kaggle=not args.no_live_kaggle)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "ledger.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out_dir / "ledger.md").write_text(render_md(payload), encoding="utf-8")
    print(f"Wrote {rel(args.out_dir / 'ledger.md')}")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
