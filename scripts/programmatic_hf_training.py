#!/usr/bin/env python3
"""Repo-native Hugging Face training orchestrator for SCBE.

This script consolidates the current training surfaces into one governed lane:

1. Refresh local SFT staging inputs from offload runs and merged repo sources.
2. Rebuild the ledgered clean dataset.
3. Audit the clean dataset before promotion.
4. Emit a deterministic Hugging Face dataset package.
5. Optionally publish the dataset package to the Hub.
6. Optionally train the local lightweight PHDM placeholder model on the curated file.

The default mode is safe: local build + audit + package only. Remote Hub writes require
explicit flags and are blocked if the dataset audit returns QUARANTINE unless
--allow-quarantine is set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import build_offload_sft_records as offload_builder
from scripts import build_training_ingestion_pool as ingestion_pool_builder
from scripts import merge_and_upload as merge_builder
from scripts import train_hf_longrun_placeholder as hf_trainer
from scripts import training_auditor as dataset_auditor
from src.training import auto_ledger

try:
    from huggingface_hub import HfApi, get_token
except Exception:  # noqa: BLE001
    HfApi = None  # type: ignore[assignment]
    get_token = None  # type: ignore[assignment]


DEFAULT_DATASET_REPO = "issdandavis/scbe-aethermoore-knowledge-base"
DEFAULT_BACKUP_DATASET_REPO = "issdandavis/scbe-aethermoore-datasets"
DEFAULT_MODEL_REPO = "issdandavis/phdm-21d-embedding-next"
DEFAULT_RUN_ROOT = REPO_ROOT / "training" / "runs" / "programmatic_hf_training"
DEFAULT_SFT_DIR = REPO_ROOT / "training" / "sft_records"
DEFAULT_LEDGERED_CLEAN = REPO_ROOT / "training" / "ledgered" / "sft_ledgered_clean.jsonl"
DEFAULT_REPO_MERGED_SFT = DEFAULT_SFT_DIR / "sft_repo_merged.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def path_for_manifest(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def stage_repo_merged_sft(output_path: Path, legacy_max_ratio: float) -> dict[str, Any]:
    records = merge_builder.merge_all(legacy_max_ratio=legacy_max_ratio)
    merge_builder.write_jsonl(records, output_path)
    track_split = merge_builder.split_by_track(records)
    return {
        "status": "ok",
        "output_path": path_for_manifest(output_path),
        "record_count": len(records),
        "track_counts": {track: len(items) for track, items in track_split.items()},
        "legacy_max_ratio": legacy_max_ratio,
    }


def audit_jsonl(path: Path, threshold: float) -> dict[str, Any]:
    rows = dataset_auditor._read_jsonl(path)
    report = dataset_auditor.audit_dataset_records(rows, threshold=threshold)
    return report


def split_records(
    rows: list[dict[str, Any]],
    *,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    if not rows:
        return {"train": [], "validation": [], "test": []}
    if train_ratio <= 0 or val_ratio < 0 or train_ratio + val_ratio >= 1:
        raise ValueError("Expected 0 < train_ratio and train_ratio + val_ratio < 1.")

    shuffled = list(rows)
    rng = random.Random(seed)
    rng.shuffle(shuffled)

    total = len(shuffled)
    train_cut = max(1, int(total * train_ratio))
    val_cut = max(1, int(total * val_ratio)) if total >= 3 else 0
    if train_cut + val_cut >= total:
        val_cut = max(0, total - train_cut - 1)
    test_cut = total - train_cut - val_cut
    if test_cut <= 0 and total >= 2:
        test_cut = 1
        if train_cut > 1:
            train_cut -= 1
        elif val_cut > 0:
            val_cut -= 1

    train_rows = shuffled[:train_cut]
    validation_rows = shuffled[train_cut : train_cut + val_cut]
    test_rows = shuffled[train_cut + val_cut :]
    return {
        "train": train_rows,
        "validation": validation_rows,
        "test": test_rows,
    }


def build_embedding_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        instruction = str(row.get("instruction", "")).strip()
        output = str(row.get("output", row.get("response", ""))).strip()
        if not instruction or not output:
            continue
        pair_id = hashlib.sha256(f"{instruction}::{output}".encode("utf-8")).hexdigest()[:16]
        pairs.append(
            {
                "pair_id": pair_id,
                "pair_index": index,
                "text_a": instruction,
                "text_b": output,
                "label": 1,
                "pair_type": "instruction_response_positive",
                "metadata": {
                    "source": str(row.get("source", "programmatic_hf_training")),
                    "tongue": row.get("tongue", ""),
                    "curriculum": row.get("curriculum", ""),
                    "content_hash": row.get("content_hash", ""),
                },
            }
        )
    return pairs


def render_dataset_readme(
    *,
    dataset_repo: str,
    total_rows: int,
    split_counts: dict[str, int],
    pair_count: int,
    source_path: Path,
    audit_status: str,
) -> str:
    return (
        f"# {dataset_repo}\n\n"
        "Programmatic SCBE training package built from the local ledgered corpus.\n\n"
        f"- Generated at: {utc_now()}\n"
        f"- Source file: `{path_for_manifest(source_path)}`\n"
        f"- Audit status: `{audit_status}`\n"
        f"- Rows total: `{total_rows}`\n"
        f"- Train rows: `{split_counts['train']}`\n"
        f"- Validation rows: `{split_counts['validation']}`\n"
        f"- Test rows: `{split_counts['test']}`\n"
        f"- Positive pairs: `{pair_count}`\n\n"
        "## Files\n"
        "- `data/all.jsonl` — full curated dataset\n"
        "- `data/train.jsonl` — train split\n"
        "- `data/validation.jsonl` — validation split\n"
        "- `data/test.jsonl` — test split\n"
        "- `data/embedding_pairs.jsonl` — weak positive pairs for bootstrap embedding work\n"
        "- `manifest.json` — build metadata and counts\n"
    )


def build_dataset_package(
    *,
    source_path: Path,
    output_dir: Path,
    dataset_repo: str,
    audit_report: dict[str, Any],
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> dict[str, Any]:
    rows = read_jsonl(source_path)
    splits = split_records(rows, train_ratio=train_ratio, val_ratio=val_ratio, seed=seed)
    pairs = build_embedding_pairs(rows)

    data_dir = output_dir / "data"
    write_jsonl(data_dir / "all.jsonl", rows)
    for split_name, split_rows in splits.items():
        write_jsonl(data_dir / f"{split_name}.jsonl", split_rows)
    write_jsonl(data_dir / "embedding_pairs.jsonl", pairs)

    split_counts = {name: len(items) for name, items in splits.items()}
    manifest = {
        "generated_at": utc_now(),
        "dataset_repo": dataset_repo,
        "source_path": path_for_manifest(source_path),
        "audit_status": audit_report.get("status", "UNKNOWN"),
        "audit_hashchain_root": audit_report.get("hashchain_root", ""),
        "total_rows": len(rows),
        "split_counts": split_counts,
        "embedding_pair_count": len(pairs),
        "seed": seed,
        "train_ratio": train_ratio,
        "val_ratio": val_ratio,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(
        render_dataset_readme(
            dataset_repo=dataset_repo,
            total_rows=len(rows),
            split_counts=split_counts,
            pair_count=len(pairs),
            source_path=source_path,
            audit_status=audit_report.get("status", "UNKNOWN"),
        ),
        encoding="utf-8",
    )
    return manifest


def resolve_hf_token(explicit_token: str | None = None) -> str:
    token = (explicit_token or os.getenv("HF_TOKEN", "")).strip()
    if token:
        return token
    if get_token is not None:
        try:
            return (get_token() or "").strip()
        except Exception:  # noqa: BLE001
            return ""
    return ""


def publish_dataset_package(
    *,
    package_dir: Path,
    repo_id: str,
    token: str,
    private: bool,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "repo_id": repo_id,
            "package_dir": path_for_manifest(package_dir),
            "private": private,
        }
    if HfApi is None:
        return {"status": "skipped", "reason": "huggingface_hub not installed"}
    if not token:
        return {"status": "skipped", "reason": "HF token missing"}

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=str(package_dir),
        commit_message=f"Update programmatic dataset package from {package_dir.name}",
    )
    return {
        "status": "ok",
        "repo_id": repo_id,
        "url": f"https://huggingface.co/datasets/{repo_id}",
    }


def load_samples_from_jsonl(path: Path, max_samples: int) -> list[tuple[str, str, str]]:
    rows = read_jsonl(path)
    items: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for row in rows:
        normalized = dict(row)
        if "response" not in normalized and normalized.get("output") is not None:
            normalized["response"] = normalized.get("output")
        if "category" not in normalized and normalized.get("label") is not None:
            normalized["category"] = normalized.get("label")
        text = hf_trainer._text_from_record(normalized)
        label = hf_trainer._label_from_record(normalized)
        if not text:
            continue
        key = hashlib.sha256(f"{label}::{text}".encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        items.append((text, label, str(path)))
        if len(items) >= max_samples:
            break
    return items


def run_local_placeholder_training(
    *,
    source_path: Path,
    run_dir: Path,
    dataset_repo: str,
    model_repo: str,
    epochs: int,
    embedding_dim: int,
    learning_rate: float,
    val_ratio: float,
    seed: int,
    max_samples: int,
    push_to_hub: bool,
    token: str,
) -> dict[str, Any]:
    samples = load_samples_from_jsonl(source_path, max_samples=max_samples)
    if len(samples) < 8:
        raise RuntimeError(f"Not enough curated samples for training (found {len(samples)}).")
    if len(samples) < 24:
        samples = hf_trainer.augment_samples(samples, min_count=24)

    random.seed(seed)
    np.random.seed(seed)
    random.shuffle(samples)

    texts = [sample[0] for sample in samples]
    labels = [sample[1] for sample in samples]
    label_names = sorted(set(labels))
    label_to_id = {label: index for index, label in enumerate(label_names)}
    y = np.array([label_to_id[label] for label in labels], dtype=np.int64)

    x = hf_trainer.vectorize(texts, embedding_dim)
    split = max(1, int((1.0 - val_ratio) * len(samples)))
    split = min(split, len(samples) - 1)
    x_train, x_val = x[:split], x[split:]
    y_train, y_val = y[:split], y[split:]

    w, b, history = hf_trainer.train_model(
        x_train=x_train,
        y_train=y_train,
        x_val=x_val,
        y_val=y_val,
        epochs=epochs,
        learning_rate=learning_rate,
        seed=seed,
    )

    first = history[0]
    best = max(history, key=lambda metric: metric["val_accuracy"])
    last = history[-1]
    growth = {
        "val_accuracy_gain": round(last["val_accuracy"] - first["val_accuracy"], 6),
        "val_loss_drop": round(first["val_loss"] - last["val_loss"], 6),
        "best_val_accuracy": round(best["val_accuracy"], 6),
        "best_epoch": int(best["epoch"]),
    }
    growth_confirmed = bool((growth["val_accuracy_gain"] > 0.01) or (growth["val_loss_drop"] > 0.02))

    run_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "provider": "huggingface",
        "status": "completed",
        "generated_at": utc_now(),
        "run_id": run_dir.name,
        "dataset_repo": dataset_repo,
        "model_repo": model_repo,
        "source_path": path_for_manifest(source_path),
        "run_dir": path_for_manifest(run_dir),
        "data": {
            "sample_count": len(samples),
            "train_count": int(x_train.shape[0]),
            "val_count": int(x_val.shape[0]),
            "label_count": len(label_names),
            "labels": label_names,
        },
        "training": {
            "epochs": epochs,
            "embedding_dim": embedding_dim,
            "learning_rate": learning_rate,
            "seed": seed,
            "history": history,
        },
        "growth": {"confirmed": growth_confirmed, **growth},
    }

    (run_dir / "label_map.json").write_text(json.dumps(label_to_id, indent=2), encoding="utf-8")
    np.savez(run_dir / "model_weights.npz", w=w, b=b)
    (run_dir / "hf_training_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (run_dir / "training_growth_summary.md").write_text(
        "\n".join(
            [
                "# Programmatic HF Training Growth Summary",
                "",
                f"- run_id: `{run_dir.name}`",
                f"- source_path: `{path_for_manifest(source_path)}`",
                f"- samples: `{len(samples)}` (train `{x_train.shape[0]}`, val `{x_val.shape[0]}`)",
                f"- labels: `{len(label_names)}`",
                f"- first val_accuracy: `{first['val_accuracy']:.4f}`",
                f"- last val_accuracy: `{last['val_accuracy']:.4f}`",
                f"- best val_accuracy: `{best['val_accuracy']:.4f}` (epoch {int(best['epoch'])})",
                f"- val_loss drop: `{growth['val_loss_drop']:.4f}`",
                f"- growth_confirmed: `{growth_confirmed}`",
            ]
        ),
        encoding="utf-8",
    )

    upload_result = {"status": "skipped", "reason": "push disabled or HF token missing"}
    if push_to_hub and token:
        upload_result = hf_trainer.upload_to_hf(model_repo, run_dir, token, report)
    report["huggingface_upload"] = upload_result
    (run_dir / "hf_training_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SCBE programmatic Hugging Face training orchestrator")
    parser.add_argument("--dataset-repo", default=DEFAULT_DATASET_REPO)
    parser.add_argument("--backup-dataset-repo", default=DEFAULT_BACKUP_DATASET_REPO)
    parser.add_argument("--model-repo", default=DEFAULT_MODEL_REPO)
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.9)
    parser.add_argument("--val-ratio", type=float, default=0.05)
    parser.add_argument("--audit-threshold", type=float, default=0.78)
    parser.add_argument("--legacy-max-ratio", type=float, default=merge_builder.DEFAULT_LEGACY_MAX_RATIO)
    parser.add_argument("--min-output-chars", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--embedding-dim", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.15)
    parser.add_argument("--max-samples", type=int, default=40000)
    parser.add_argument("--hf-token", default="")
    parser.add_argument("--skip-ingestion-pool-refresh", action="store_true")
    parser.add_argument("--skip-offload", action="store_true")
    parser.add_argument("--skip-merge-stage", action="store_true")
    parser.add_argument("--skip-ledger-refresh", action="store_true")
    parser.add_argument("--publish-dataset", action="store_true")
    parser.add_argument("--mirror-backup", action="store_true")
    parser.add_argument("--train-model", action="store_true")
    parser.add_argument("--push-model", action="store_true")
    parser.add_argument("--private-dataset", action="store_true")
    parser.add_argument("--allow-quarantine", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write to remote Hugging Face repos. Local staging and training still run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = make_run_id()
    run_root = Path(args.run_root)
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    offline_mode = bool(args.dry_run and not args.publish_dataset and not args.push_model)
    if offline_mode:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("SCBE_DISABLE_HF_CLASSIFIER", "1")

    summaries: dict[str, Any] = {
        "generated_at": utc_now(),
        "run_id": run_id,
        "dataset_repo": args.dataset_repo,
        "backup_dataset_repo": args.backup_dataset_repo,
        "model_repo": args.model_repo,
        "dry_run": args.dry_run,
        "offline_mode": offline_mode,
    }

    if not args.skip_ingestion_pool_refresh:
        summaries["ingestion_pool_refresh"] = ingestion_pool_builder.build_ingestion_pool(
            output_path=ingestion_pool_builder.DEFAULT_OUTPUT,
            doc_output_path=ingestion_pool_builder.DEFAULT_DOC_OUTPUT,
            run_root=ingestion_pool_builder.DEFAULT_RUN_ROOT,
        )
    else:
        summaries["ingestion_pool_refresh"] = {"status": "skipped"}

    if not args.skip_offload:
        summaries["offload_refresh"] = offload_builder.build_sft_records(
            run_root=offload_builder.DEFAULT_RUN_ROOT,
            output_path=offload_builder.DEFAULT_OUTPUT,
            min_output_chars=args.min_output_chars,
        )
    else:
        summaries["offload_refresh"] = {"status": "skipped"}

    if not args.skip_merge_stage:
        summaries["repo_merge_stage"] = stage_repo_merged_sft(
            output_path=DEFAULT_REPO_MERGED_SFT,
            legacy_max_ratio=args.legacy_max_ratio,
        )
    else:
        summaries["repo_merge_stage"] = {"status": "skipped"}

    if not args.skip_ledger_refresh:
        summaries["ledger_refresh"] = auto_ledger.run_pipeline(sft_dir=DEFAULT_SFT_DIR, push_to_hf=False)
    else:
        summaries["ledger_refresh"] = {"status": "skipped"}

    clean_path = DEFAULT_LEDGERED_CLEAN
    if not clean_path.exists():
        raise FileNotFoundError(f"Expected ledgered dataset at {clean_path}")

    audit_report = audit_jsonl(clean_path, threshold=args.audit_threshold)
    (run_dir / "audit_report.json").write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
    summaries["audit_report"] = audit_report

    package_dir = run_dir / "dataset_package"
    package_manifest = build_dataset_package(
        source_path=clean_path,
        output_dir=package_dir,
        dataset_repo=args.dataset_repo,
        audit_report=audit_report,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
    )
    summaries["dataset_package"] = package_manifest

    token = resolve_hf_token(args.hf_token)
    audit_allows_promotion = audit_report.get("status") == "ALLOW" or args.allow_quarantine
    if not audit_allows_promotion:
        summaries["promotion_gate"] = {
            "status": "blocked",
            "reason": f"audit returned {audit_report.get('status', 'UNKNOWN')}",
        }
    else:
        summaries["promotion_gate"] = {"status": "open"}

    if args.publish_dataset:
        if audit_allows_promotion:
            summaries["dataset_publish"] = publish_dataset_package(
                package_dir=package_dir,
                repo_id=args.dataset_repo,
                token=token,
                private=args.private_dataset,
                dry_run=args.dry_run,
            )
            if args.mirror_backup:
                summaries["dataset_backup_publish"] = publish_dataset_package(
                    package_dir=package_dir,
                    repo_id=args.backup_dataset_repo,
                    token=token,
                    private=args.private_dataset,
                    dry_run=args.dry_run,
                )
            else:
                summaries["dataset_backup_publish"] = {"status": "skipped"}
        else:
            summaries["dataset_publish"] = {"status": "blocked", "reason": "audit gate closed"}
            summaries["dataset_backup_publish"] = {"status": "blocked", "reason": "audit gate closed"}
    else:
        summaries["dataset_publish"] = {"status": "skipped"}
        summaries["dataset_backup_publish"] = {"status": "skipped"}

    if args.train_model:
        if audit_allows_promotion:
            model_run_dir = run_dir / "model_run"
            summaries["model_training"] = run_local_placeholder_training(
                source_path=clean_path,
                run_dir=model_run_dir,
                dataset_repo=args.dataset_repo,
                model_repo=args.model_repo,
                epochs=args.epochs,
                embedding_dim=args.embedding_dim,
                learning_rate=args.learning_rate,
                val_ratio=args.val_ratio,
                seed=args.seed,
                max_samples=args.max_samples,
                push_to_hub=args.push_model and not args.dry_run,
                token=token,
            )
        else:
            summaries["model_training"] = {"status": "blocked", "reason": "audit gate closed"}
    else:
        summaries["model_training"] = {"status": "skipped"}

    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
