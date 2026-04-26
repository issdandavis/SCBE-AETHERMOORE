"""Phase 1 — LoRA fine-tune Qwen on the tongue truth table.

Structure-first training: the model only needs to memorize ~13 bijective
cells. LoRA on a 0.5B-param base that already knows python/rust/lisp is
orders of magnitude more efficient than blank-slate CLM.

Run after current GPU job finishes:
    python scripts/train/lora_tongue_table.py \
        --base_model Qwen/Qwen2.5-0.5B \
        --data data/tongue_drill/drill_v1.jsonl \
        --output artifacts/tongue-table-lora-v1 \
        --max_steps 500 \
        --eval_every 25
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _iso_utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _checkpoint_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("checkpoint-"):
            continue
        try:
            step = int(entry.name.replace("checkpoint-", "", 1))
        except ValueError:
            continue
        size_bytes = sum(p.stat().st_size for p in entry.rglob("*") if p.is_file())
        rows.append({
            "name": entry.name,
            "step": step,
            "path": str(entry.resolve()),
            "size_bytes": size_bytes,
        })
    return sorted(rows, key=lambda row: row["step"])


def _write_run_manifest(
    output_dir: Path,
    *,
    base_model: str,
    data_path: str,
    run_config: dict[str, Any],
    mirror_dir: Path | None = None,
) -> Path:
    manifest = {
        "schema_version": "tongue_table_run_manifest_v1",
        "created_at_utc": _iso_utc_now(),
        "output_dir": str(output_dir.resolve()),
        "base_model": base_model,
        "data_path": data_path,
        "run_config": run_config,
        "mirror_dir": str(mirror_dir.resolve()) if mirror_dir else None,
        "checkpoints": _checkpoint_rows(output_dir),
    }
    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip())
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned or "run"


def _looks_like_hf_network_error(exc: Exception) -> bool:
    text = str(exc)
    return any(
        marker in text
        for marker in (
            "ConnectError",
            "access a socket",
            "ConnectionError",
            "ReadTimeout",
            "Temporary failure in name resolution",
        )
    )


def _hf_from_pretrained_cached(loader, model_id: str, **kwargs):
    try:
        return loader.from_pretrained(model_id, **kwargs)
    except Exception as exc:
        if not _looks_like_hf_network_error(exc):
            raise
        print(f"[HF] network blocked for {model_id}; retrying from local cache")
        try:
            from huggingface_hub import snapshot_download
        except Exception:
            cached_kwargs = dict(kwargs)
            cached_kwargs["local_files_only"] = True
            return loader.from_pretrained(model_id, **cached_kwargs)

        local_snapshot = snapshot_download(repo_id=model_id, local_files_only=True)
        cached_kwargs = dict(kwargs)
        cached_kwargs.pop("local_files_only", None)
        return loader.from_pretrained(local_snapshot, **cached_kwargs)


def _mirror_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _mirror_run_state(
    output_dir: Path,
    mirror_root: Path,
    *,
    run_name: str,
    include_final_only: bool = False,
) -> Path:
    target = mirror_root / _safe_slug(run_name)
    target.mkdir(parents=True, exist_ok=True)

    names = {"run_manifest.json", "baseline_table_lock.json", "baseline_drill_map_eval.json",
             "final_table_lock.json", "final_drill_map_eval.json",
             "table_lock_trajectory.jsonl", "drill_map_trajectory.jsonl"}
    for item in output_dir.iterdir():
        if item.name in names and item.is_file():
            shutil.copy2(item, target / item.name)

    if not include_final_only:
        for cp in output_dir.iterdir():
            if cp.is_dir() and cp.name.startswith("checkpoint-"):
                _mirror_tree(cp, target / cp.name)

    final_dir = output_dir / "lora_final"
    if final_dir.exists():
        _mirror_tree(final_dir, target / "lora_final")
    return target


def _save_final_adapter(output_dir: Path, model, tokenizer) -> Path:
    final_dir = output_dir / "lora_final"
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    return final_dir


def _maybe_upload_hf_folder(folder_path: Path, *, repo_id: str, repo_path: str, commit_message: str) -> None:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is required for checkpoint upload.")
    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"huggingface_hub unavailable: {exc}") from exc

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    api.upload_folder(
        folder_path=str(folder_path),
        repo_id=repo_id,
        repo_type="model",
        path_in_repo=repo_path,
        commit_message=commit_message,
    )


def load_drill_dataset(
    path: Path,
    tokenizer,
    block_size: int = 256,
    *,
    map_weights: dict[str, float] | None = None,
    default_weight: float = 1.0,
):
    """Load drill rows, tokenize, and attach per-sample loss weights by map."""
    from datasets import Dataset

    map_weights = map_weights or {}
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            map_name = rec.get("map", "") or ""
            weight = float(map_weights.get(map_name, default_weight))
            rows.append({
                "text": rec["text"],
                "prefix": rec.get("prefix", "") or "",
                "map": map_name,
                "loss_weight": weight,
            })
    ds = Dataset.from_list(rows)

    def tok_fn(batch):
        out = tokenizer(
            batch["text"],
            truncation=True,
            max_length=block_size,
            padding="max_length",
        )
        labels: list[list[int]] = []
        for ids, prefix in zip(out["input_ids"], batch["prefix"]):
            row_labels = list(ids)
            if prefix:
                # Cloze row: score only the post-prefix span.
                prefix_ids = tokenizer(
                    prefix,
                    truncation=True,
                    max_length=block_size,
                    add_special_tokens=False,
                )["input_ids"]
                prefix_len = min(len(prefix_ids), block_size)
                for i in range(prefix_len):
                    row_labels[i] = -100
            labels.append(row_labels)
        out["labels"] = labels
        out["loss_weight"] = list(batch["loss_weight"])
        return out

    ds = ds.map(tok_fn, batched=True, remove_columns=["text", "map", "prefix"])
    return ds


def run_table_lock_eval(model, tokenizer, device: str):
    from scripts.eval.table_lock_eval import evaluate

    model.eval()
    results = evaluate(tokenizer, model)
    return results


def summarize_drill_eval(summary: dict[str, Any], focus_maps: list[str] | None = None) -> str:
    focus_maps = focus_maps or [
        "transport_atomic",
        "atomic_semantic",
        "convergence_action",
        "cartography_state",
        "runtime_emission",
    ]
    bits: list[str] = []
    by_map = summary.get("by_map", {})
    for map_name in focus_maps:
        stats = by_map.get(map_name)
        if not stats:
            continue
        bits.append(f"{map_name}={stats['avg_loss']:.3f}")
    if not bits and by_map:
        for map_name, stats in sorted(by_map.items())[:4]:
            bits.append(f"{map_name}={stats['avg_loss']:.3f}")
    return " ".join(bits)


def run_drill_map_eval(
    model,
    tokenizer,
    *,
    data_path: str,
    split: str,
    holdout_mod: int,
    holdout_bucket: int,
    max_per_cell: int,
    max_length: int,
):
    from scripts.eval.drill_map_eval import (
        limit_rows_per_cell,
        load_drill_rows,
        score_rows,
        split_rows,
        summarize_structural_rows,
        summarize_losses,
    )

    rows = load_drill_rows(data_path)
    rows = split_rows(
        rows,
        split=split,
        holdout_mod=holdout_mod,
        holdout_bucket=holdout_bucket,
    )
    rows = limit_rows_per_cell(rows, max_per_cell)
    scored = score_rows(rows, tokenizer, model, max_length=max_length)
    summary = summarize_losses(scored)
    summary["_structural"] = summarize_structural_rows(rows)
    summary["_config"] = {
        "data": data_path,
        "split": split,
        "holdout_mod": holdout_mod,
        "holdout_bucket": holdout_bucket,
        "max_per_cell": max_per_cell,
        "max_length": max_length,
    }
    return summary


def run_drill_structure_preflight(
    data_path: str,
) -> dict[str, Any]:
    from scripts.eval.drill_map_eval import load_drill_rows
    from scripts.eval.drill_structure_preflight import validate_rows

    rows = load_drill_rows(data_path)
    return validate_rows(rows)


def summarize_structural_benchmark(summary: dict[str, Any]) -> str:
    bits: list[str] = []
    by_stage = summary.get("by_stage", {})
    for stage in ("atom_seed", "braid_helix", "causal_transform", "route_governance"):
        stats = by_stage.get(stage)
        if not stats:
            continue
        bits.append(f"{stage}={stats['pass_rate']:.1%}")
    trajectory = summary.get("trajectory_bundles", {})
    if trajectory:
        bits.append(f"trajectory={trajectory.get('pass_rate', 0.0):.1%}")
    return " ".join(bits)


def run_structural_benchmark_eval(
    model,
    tokenizer,
    *,
    data_path: str,
    split: str,
    holdout_mod: int,
    holdout_bucket: int,
    max_per_stage: int,
):
    from scripts.benchmark.polly_structural_benchmark import (
        _default_generator,
        run_structural_benchmark,
    )

    return run_structural_benchmark(
        data_path=data_path,
        split=split,
        holdout_mod=holdout_mod,
        holdout_bucket=holdout_bucket,
        max_per_stage=max_per_stage,
        generator=_default_generator(tokenizer, model),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max_steps", type=int, default=500)
    ap.add_argument("--eval_every", type=int, default=25)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch_size", type=int, default=4)
    ap.add_argument("--grad_accum", type=int, default=4)
    ap.add_argument("--lora_r", type=int, default=16)
    ap.add_argument("--lora_alpha", type=int, default=32)
    ap.add_argument("--block_size", type=int, default=256)
    ap.add_argument("--early_stop_score", type=float, default=0.99,
                    help="Stop if table-lock >= this fraction")
    ap.add_argument("--drill_eval_split", default="holdout",
                    choices=["all", "train", "holdout"])
    ap.add_argument("--drill_holdout_mod", type=int, default=10)
    ap.add_argument("--drill_holdout_bucket", type=int, default=0)
    ap.add_argument("--drill_max_per_cell", type=int, default=10)
    ap.add_argument("--drill_eval_max_length", type=int, default=256)
    ap.add_argument("--benchmark_split", default="holdout", choices=["all", "train", "holdout"])
    ap.add_argument("--benchmark_holdout_mod", type=int, default=10)
    ap.add_argument("--benchmark_holdout_bucket", type=int, default=0)
    ap.add_argument("--benchmark_max_per_stage", type=int, default=12)
    ap.add_argument(
        "--skip_structural_benchmark",
        action="store_true",
        help="Skip generation-side structural benchmark runs.",
    )
    ap.add_argument(
        "--map_weights",
        type=str,
        default="",
        help=(
            "JSON object mapping drill `map` name -> loss weight, e.g. "
            '\'{"transport_atomic":2.5,"atomic_semantic":2.0}\'. '
            "Samples with no entry get --default_map_weight."
        ),
    )
    ap.add_argument("--default_map_weight", type=float, default=1.0)
    ap.add_argument(
        "--checkpoint_mirror_root",
        type=str,
        default="",
        help="Optional local/offload root to mirror manifests, evals, and checkpoints into during training.",
    )
    ap.add_argument(
        "--checkpoint_hf_repo",
        type=str,
        default="",
        help="Optional Hugging Face model repo to upload mirrored checkpoints/final adapter into.",
    )
    ap.add_argument(
        "--checkpoint_hf_every",
        type=int,
        default=0,
        help="Optional upload cadence in steps. 0 disables checkpoint uploads; final adapter still uploads if repo is set.",
    )
    ap.add_argument(
        "--skip_structure_preflight",
        action="store_true",
        help="Skip the numeric structural validation pass on the drill before training.",
    )
    ap.add_argument(
        "--resume_adapter",
        type=str,
        default="",
        help="Optional path to an existing LoRA adapter to warm-start from (continual learning).",
    )
    ap.add_argument(
        "--lr_scheduler_type",
        type=str,
        default="cosine",
        help="Learning rate scheduler type passed through to TrainingArguments.",
    )
    ap.add_argument(
        "--warmup_steps",
        type=int,
        default=20,
        help="Number of warmup steps for the LR scheduler.",
    )
    args = ap.parse_args()

    map_weights: dict[str, float] = {}
    if args.map_weights.strip():
        try:
            raw = json.loads(args.map_weights)
            if not isinstance(raw, dict):
                raise ValueError("--map_weights must be a JSON object")
            map_weights = {str(k): float(v) for k, v in raw.items()}
        except (json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(f"Invalid --map_weights: {exc}")
    if map_weights:
        print(f"Per-map loss weights: {map_weights} (default={args.default_map_weight})")

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainerCallback,
        TrainingArguments,
    )

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    mirror_root = Path(args.checkpoint_mirror_root).expanduser() if args.checkpoint_mirror_root.strip() else None
    run_config = {
        "max_steps": args.max_steps,
        "eval_every": args.eval_every,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "block_size": args.block_size,
        "early_stop_score": args.early_stop_score,
        "drill_eval_split": args.drill_eval_split,
        "drill_holdout_mod": args.drill_holdout_mod,
        "drill_holdout_bucket": args.drill_holdout_bucket,
        "drill_max_per_cell": args.drill_max_per_cell,
        "drill_eval_max_length": args.drill_eval_max_length,
        "benchmark_split": args.benchmark_split,
        "benchmark_holdout_mod": args.benchmark_holdout_mod,
        "benchmark_holdout_bucket": args.benchmark_holdout_bucket,
        "benchmark_max_per_stage": args.benchmark_max_per_stage,
        "map_weights": map_weights,
        "default_map_weight": args.default_map_weight,
    }
    _write_run_manifest(
        out_dir,
        base_model=args.base_model,
        data_path=args.data,
        run_config=run_config,
        mirror_dir=mirror_root,
    )

    if args.skip_structure_preflight:
        print("Skipping structural drill preflight (--skip_structure_preflight).")
    else:
        print("\n=== DRILL STRUCTURE PREFLIGHT ===")
        preflight = run_drill_structure_preflight(args.data)
        preflight_path = out_dir / "drill_structure_preflight.json"
        preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")
        structural = preflight["structural"]["_summary"]
        print(
            f"Preflight structural coverage: "
            f"{structural['structural_count']}/{structural['count']} = "
            f"{structural['structural_ratio']:.1%}"
        )
        if preflight["missing_maps"]:
            print(f"Missing maps: {', '.join(preflight['missing_maps'])}")
        if preflight["failures"]:
            print(f"Preflight failures: {len(preflight['failures'])}")
        if not preflight["ok"]:
            raise SystemExit(
                "Structural drill preflight failed; fix the drill or pass "
                "--skip_structure_preflight to override."
            )

    print(f"Loading base model: {args.base_model}")
    tokenizer = _hf_from_pretrained_cached(AutoTokenizer, args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = _hf_from_pretrained_cached(
        AutoModelForCausalLM,
        args.base_model,
        torch_dtype=torch.float16,
    )
    if torch.cuda.is_available():
        model = model.to("cuda")
        print(f"Model on CUDA: {torch.cuda.get_device_name(0)}")

    if args.resume_adapter.strip():
        from peft import PeftModel
        resume_path = args.resume_adapter.strip()
        print(f"[CONTINUAL] Warm-starting LoRA from: {resume_path}")
        model = PeftModel.from_pretrained(model, resume_path, is_trainable=True)
        model.print_trainable_parameters()
    else:
        lora_cfg = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_cfg)
        model.print_trainable_parameters()

    print(f"Loading drill dataset: {args.data}")
    ds = load_drill_dataset(
        Path(args.data),
        tokenizer,
        block_size=args.block_size,
        map_weights=map_weights,
        default_weight=args.default_map_weight,
    )
    print(f"Dataset: {len(ds)} samples")
    if map_weights:
        weights_tensor = ds["loss_weight"]
        from collections import Counter
        wc = Counter(round(w, 3) for w in weights_tensor)
        print(f"Loss-weight distribution: {dict(sorted(wc.items()))}")

    # Baseline table-lock before training
    print("\n=== BASELINE TABLE-LOCK (before training) ===")
    baseline = run_table_lock_eval(model, tokenizer, "cuda")
    print(f"Baseline: {baseline['_summary']['correct']}/{baseline['_summary']['total_cells']} "
          f"= {baseline['_summary']['score']:.1%}")
    (out_dir / "baseline_table_lock.json").write_text(json.dumps(baseline, indent=2))

    print("\n=== BASELINE DRILL MAP EVAL ===")
    baseline_drill = run_drill_map_eval(
        model,
        tokenizer,
        data_path=args.data,
        split=args.drill_eval_split,
        holdout_mod=args.drill_holdout_mod,
        holdout_bucket=args.drill_holdout_bucket,
        max_per_cell=args.drill_max_per_cell,
        max_length=args.drill_eval_max_length,
    )
    print(
        f"Baseline drill: loss={baseline_drill['_summary']['avg_loss']:.4f} "
        f"ppl={baseline_drill['_summary']['perplexity']:.1f} "
        f"{summarize_drill_eval(baseline_drill)}"
    )
    print(
        f"Baseline structural coverage: "
        f"{baseline_drill['_structural']['_summary']['structural_count']}/"
        f"{baseline_drill['_structural']['_summary']['count']} = "
        f"{baseline_drill['_structural']['_summary']['structural_ratio']:.1%}"
    )
    (out_dir / "baseline_drill_map_eval.json").write_text(json.dumps(baseline_drill, indent=2))

    if args.skip_structural_benchmark:
        print("\nSkipping structural benchmark (--skip_structural_benchmark).")
    else:
        print("\n=== BASELINE STRUCTURAL BENCHMARK ===")
        baseline_benchmark = run_structural_benchmark_eval(
            model,
            tokenizer,
            data_path=args.data,
            split=args.benchmark_split,
            holdout_mod=args.benchmark_holdout_mod,
            holdout_bucket=args.benchmark_holdout_bucket,
            max_per_stage=args.benchmark_max_per_stage,
        )
        print(
            f"Baseline benchmark: pass={baseline_benchmark['summary']['pass_rate']:.1%} "
            f"exact={baseline_benchmark['summary']['exact_match_rate']:.1%} "
            f"{summarize_structural_benchmark(baseline_benchmark)}"
        )
        (out_dir / "baseline_structural_benchmark.json").write_text(
            json.dumps(baseline_benchmark, indent=2),
            encoding="utf-8",
        )

    # Table-lock callback — runs eval at fixed checkpoints
    trajectory_path = out_dir / "table_lock_trajectory.jsonl"
    drill_trajectory_path = out_dir / "drill_map_trajectory.jsonl"

    class TableLockCallback(TrainerCallback):
        def __init__(self):
            self.best_score = 0.0
            self.should_stop = False

        def _sync_state(self, *, step: int, final_only: bool = False) -> None:
            manifest_path = _write_run_manifest(
                out_dir,
                base_model=args.base_model,
                data_path=args.data,
                run_config=run_config,
                mirror_dir=mirror_root,
            )
            if mirror_root:
                mirrored = _mirror_run_state(
                    out_dir,
                    mirror_root,
                    run_name=out_dir.name,
                    include_final_only=final_only,
                )
                print(f"[DURABILITY] mirrored run state -> {mirrored}")
            if args.checkpoint_hf_repo.strip():
                should_upload = final_only or (
                    args.checkpoint_hf_every > 0 and step > 0 and step % args.checkpoint_hf_every == 0
                )
                if should_upload:
                    source_dir = out_dir / "lora_final" if final_only else out_dir
                    repo_subdir = f"{_safe_slug(out_dir.name)}/final" if final_only else f"{_safe_slug(out_dir.name)}/step-{step}"
                    try:
                        _maybe_upload_hf_folder(
                            source_dir,
                            repo_id=args.checkpoint_hf_repo.strip(),
                            repo_path=repo_subdir,
                            commit_message=f"{out_dir.name}: {'final' if final_only else f'checkpoint step {step}'}",
                        )
                        print(f"[DURABILITY] uploaded {source_dir.name} -> hf://{args.checkpoint_hf_repo.strip()}/{repo_subdir}")
                    except Exception as exc:
                        print(f"[DURABILITY] checkpoint upload skipped: {exc}")
            if manifest_path.exists():
                print(f"[DURABILITY] manifest -> {manifest_path}")

        def on_step_end(self, args_inner, state, control, **kwargs):
            if state.global_step == 0 or state.global_step % args.eval_every != 0:
                return control
            model_local = kwargs.get("model")
            if model_local is None:
                return control
            results = run_table_lock_eval(model_local, tokenizer, "cuda")
            score = results["_summary"]["score"]
            entry = {
                "step": state.global_step,
                "score": score,
                "correct": results["_summary"]["correct"],
                "total": results["_summary"]["total_cells"],
            }
            with trajectory_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            print(f"[TABLE-LOCK] step={state.global_step:>4} "
                  f"score={score:.1%} ({entry['correct']}/{entry['total']})")

            drill_summary = run_drill_map_eval(
                model_local,
                tokenizer,
                data_path=args.data,
                split=args.drill_eval_split,
                holdout_mod=args.drill_holdout_mod,
                holdout_bucket=args.drill_holdout_bucket,
                max_per_cell=args.drill_max_per_cell,
                max_length=args.drill_eval_max_length,
            )
            drill_entry = {
                "step": state.global_step,
                "loss": drill_summary["_summary"]["avg_loss"],
                "perplexity": drill_summary["_summary"]["perplexity"],
                "by_map": {
                    name: stats["avg_loss"]
                    for name, stats in drill_summary.get("by_map", {}).items()
                },
            }
            with drill_trajectory_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(drill_entry) + "\n")
            print(
                f"[DRILL-MAP] step={state.global_step:>4} "
                f"loss={drill_entry['loss']:.4f} "
                f"{summarize_drill_eval(drill_summary)}"
            )
            print(
                f"[DRILL-STRUCTURAL] step={state.global_step:>4} "
                f"coverage={drill_summary['_structural']['_summary']['structural_ratio']:.1%}"
            )

            if not args.skip_structural_benchmark:
                benchmark_summary = run_structural_benchmark_eval(
                    model_local,
                    tokenizer,
                    data_path=args.data,
                    split=args.benchmark_split,
                    holdout_mod=args.benchmark_holdout_mod,
                    holdout_bucket=args.benchmark_holdout_bucket,
                    max_per_stage=args.benchmark_max_per_stage,
                )
                benchmark_entry = {
                    "step": state.global_step,
                    "pass_rate": benchmark_summary["summary"]["pass_rate"],
                    "exact_match_rate": benchmark_summary["summary"]["exact_match_rate"],
                    "validator_pass_rate": benchmark_summary["summary"]["validator_pass_rate"],
                    "trajectory_pass_rate": benchmark_summary["trajectory_bundles"]["pass_rate"],
                    "by_stage": {
                        name: stats["pass_rate"]
                        for name, stats in benchmark_summary.get("by_stage", {}).items()
                    },
                }
                benchmark_trajectory_path = out_dir / "structural_benchmark_trajectory.jsonl"
                with benchmark_trajectory_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(benchmark_entry) + "\n")
                print(
                    f"[STRUCT-BENCH] step={state.global_step:>4} "
                    f"pass={benchmark_entry['pass_rate']:.1%} "
                    f"{summarize_structural_benchmark(benchmark_summary)}"
                )
                (out_dir / f"structural_benchmark_step_{state.global_step}.json").write_text(
                    json.dumps(benchmark_summary, indent=2),
                    encoding="utf-8",
                )

            if score > self.best_score:
                self.best_score = score
            if score >= args.early_stop_score:
                print(f"[EARLY-STOP] table-lock {score:.1%} >= {args.early_stop_score:.1%}")
                control.should_training_stop = True
                self.should_stop = True
            self._sync_state(step=state.global_step)
            model_local.train()
            return control

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        logging_steps=10,
        save_strategy="steps",
        save_steps=args.eval_every,
        save_total_limit=3,
        fp16=True,
        warmup_steps=args.warmup_steps,
        lr_scheduler_type=args.lr_scheduler_type,
        report_to=["none"],
    )

    class MapWeightedLossTrainer(Trainer):
        """Trainer that scales token-CE loss per-sample by `loss_weight`.

        Uses the causal-LM shift (labels[:, 1:] predicted from logits[:, :-1]),
        computes token-level CE, averages across non-pad tokens per sample,
        then weights each sample's scalar loss by its map's weight.
        """

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            loss_weight = inputs.pop("loss_weight", None)
            labels = inputs.get("labels")
            outputs = model(**inputs)
            if loss_weight is None or labels is None:
                loss = outputs.loss
                return (loss, outputs) if return_outputs else loss

            logits = outputs.logits  # (B, T, V)
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = labels[:, 1:].contiguous()

            loss_fct = torch.nn.CrossEntropyLoss(
                ignore_index=-100, reduction="none"
            )
            flat_loss = loss_fct(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
            ).view(shift_labels.size())  # (B, T-1)

            mask = (shift_labels != -100).float()
            # Also treat pad tokens as zero-contribution (pad_token_id == eos for Qwen)
            pad_id = tokenizer.pad_token_id
            if pad_id is not None:
                mask = mask * (shift_labels != pad_id).float()

            per_sample_sum = (flat_loss * mask).sum(dim=1)
            per_sample_tok = mask.sum(dim=1).clamp(min=1.0)
            per_sample_loss = per_sample_sum / per_sample_tok  # (B,)

            w = loss_weight.to(per_sample_loss.device).float()
            loss = (per_sample_loss * w).sum() / w.sum().clamp(min=1e-6)

            return (loss, outputs) if return_outputs else loss

    def weighted_collate(features):
        """Collate tokenized examples and stack `loss_weight` as a float tensor."""
        weights = torch.tensor(
            [float(f.pop("loss_weight", 1.0)) for f in features], dtype=torch.float32
        )
        batch = {
            "input_ids": torch.tensor([f["input_ids"] for f in features], dtype=torch.long),
            "attention_mask": torch.tensor(
                [f["attention_mask"] for f in features], dtype=torch.long
            ),
            "labels": torch.tensor([f["labels"] for f in features], dtype=torch.long),
            "loss_weight": weights,
        }
        return batch

    trainer_cls = MapWeightedLossTrainer if map_weights else Trainer
    trainer_kwargs = dict(
        model=model,
        args=training_args,
        train_dataset=ds,
        processing_class=tokenizer,
    )
    if map_weights:
        trainer_kwargs["data_collator"] = weighted_collate
    callback = TableLockCallback()
    trainer_kwargs["callbacks"] = [callback]
    trainer = trainer_cls(**trainer_kwargs)

    trainer.train()

    # Final eval
    print("\n=== FINAL TABLE-LOCK ===")
    final = run_table_lock_eval(model, tokenizer, "cuda")
    print(f"Final: {final['_summary']['correct']}/{final['_summary']['total_cells']} "
          f"= {final['_summary']['score']:.1%}")
    (out_dir / "final_table_lock.json").write_text(json.dumps(final, indent=2))

    print("\n=== FINAL DRILL MAP EVAL ===")
    final_drill = run_drill_map_eval(
        model,
        tokenizer,
        data_path=args.data,
        split=args.drill_eval_split,
        holdout_mod=args.drill_holdout_mod,
        holdout_bucket=args.drill_holdout_bucket,
        max_per_cell=args.drill_max_per_cell,
        max_length=args.drill_eval_max_length,
    )
    print(
        f"Final drill: loss={final_drill['_summary']['avg_loss']:.4f} "
        f"ppl={final_drill['_summary']['perplexity']:.1f} "
        f"{summarize_drill_eval(final_drill)}"
    )
    print(
        f"Final structural coverage: "
        f"{final_drill['_structural']['_summary']['structural_count']}/"
        f"{final_drill['_structural']['_summary']['count']} = "
        f"{final_drill['_structural']['_summary']['structural_ratio']:.1%}"
    )
    (out_dir / "final_drill_map_eval.json").write_text(json.dumps(final_drill, indent=2))

    final_dir = _save_final_adapter(out_dir, model, tokenizer)
    print(f"\nSaved LoRA to: {final_dir}")

    if not args.skip_structural_benchmark:
        print("\n=== FINAL STRUCTURAL BENCHMARK ===")
        final_benchmark = run_structural_benchmark_eval(
            model,
            tokenizer,
            data_path=args.data,
            split=args.benchmark_split,
            holdout_mod=args.benchmark_holdout_mod,
            holdout_bucket=args.benchmark_holdout_bucket,
            max_per_stage=args.benchmark_max_per_stage,
        )
        print(
            f"Final benchmark: pass={final_benchmark['summary']['pass_rate']:.1%} "
            f"exact={final_benchmark['summary']['exact_match_rate']:.1%} "
            f"{summarize_structural_benchmark(final_benchmark)}"
        )
        (out_dir / "final_structural_benchmark.json").write_text(
            json.dumps(final_benchmark, indent=2),
            encoding="utf-8",
        )
    callback._sync_state(step=args.max_steps, final_only=True)


if __name__ == "__main__":
    main()
