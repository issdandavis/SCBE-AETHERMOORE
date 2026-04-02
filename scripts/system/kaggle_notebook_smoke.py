#!/usr/bin/env python3
"""Hard-fail Kaggle preflight for SCBE training notebooks."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "kaggle_smoke"
DEFAULT_DATASET_REPO = "issdandavis/scbe-aethermoore-training-data"
DEFAULT_DATA_FILE = "cleaned/consolidated_labels.jsonl"
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_DEPENDENCIES = (
    "torch",
    "datasets",
    "transformers",
    "peft",
    "trl",
    "accelerate",
    "huggingface_hub",
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sanitize(value: Any, *, max_text: int = 160) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(val, max_text=max_text) for key, val in list(value.items())[:12]}
    if isinstance(value, list):
        return [_sanitize(item, max_text=max_text) for item in value[:8]]
    if isinstance(value, str):
        compact = " ".join(value.split())
        return compact[:max_text]
    return value


def detect_runtime(*, environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ or os.environ
    return {
        "is_kaggle": bool(env.get("KAGGLE_KERNEL_RUN_TYPE") or env.get("KAGGLE_URL_BASE")),
        "run_type": env.get("KAGGLE_KERNEL_RUN_TYPE", ""),
        "url_base": env.get("KAGGLE_URL_BASE", ""),
        "working_dir_exists": Path("/kaggle/working").exists(),
        "input_dir_exists": Path("/kaggle/input").exists(),
    }


def probe_dependencies(
    module_names: tuple[str, ...] = DEFAULT_DEPENDENCIES,
    *,
    importer: Callable[[str], Any] = importlib.import_module,
) -> dict[str, Any]:
    loaded: list[str] = []
    missing: list[dict[str, str]] = []
    for module_name in module_names:
        try:
            importer(module_name)
            loaded.append(module_name)
        except Exception as exc:  # pragma: no cover - defensive path
            missing.append({"module": module_name, "error": str(exc)})
    return {
        "required": list(module_names),
        "loaded": loaded,
        "missing": missing,
        "ok": not missing,
    }


def probe_gpu(*, torch_module: Any) -> dict[str, Any]:
    cuda = getattr(torch_module, "cuda", None)
    if cuda is None:
        return {
            "available": False,
            "device_count": 0,
            "device_name": "",
            "reason": "torch_cuda_missing",
        }

    try:
        available = bool(cuda.is_available())
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "available": False,
            "device_count": 0,
            "device_name": "",
            "reason": str(exc),
        }

    device_count = int(cuda.device_count()) if available else 0
    device_name = ""
    if available and device_count > 0:
        try:
            device_name = str(cuda.get_device_name(0))
        except Exception:  # pragma: no cover - defensive path
            device_name = "unknown"

    return {
        "available": available,
        "device_count": device_count,
        "device_name": device_name,
        "cuda_version": getattr(torch_module, "version", None) and getattr(torch_module.version, "cuda", None),
    }


def _dataset_preview_rows(dataset: Any, sample_size: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if hasattr(dataset, "select"):
        selected = dataset.select(range(min(sample_size, len(dataset))))
        iterable = selected
    else:
        iterable = dataset
    for index, row in enumerate(iterable):
        if index >= sample_size:
            break
        rows.append(_sanitize(row))
    return rows


def probe_dataset_access(
    *,
    dataset_repo: str,
    data_file: str | None,
    split: str,
    sample_size: int,
    load_dataset_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    loader = load_dataset_fn
    if loader is None:
        from datasets import load_dataset as datasets_loader

        loader = datasets_loader

    try:
        if data_file:
            dataset = loader(dataset_repo, data_files=data_file, split=split)
        else:
            dataset = loader(dataset_repo, split=split)
        row_count = len(dataset)
        preview_rows = _dataset_preview_rows(dataset, sample_size)
        return {
            "ok": True,
            "dataset_repo": dataset_repo,
            "data_file": data_file,
            "split": split,
            "row_count": row_count,
            "sample_rows": preview_rows,
        }
    except Exception as exc:
        return {
            "ok": False,
            "dataset_repo": dataset_repo,
            "data_file": data_file,
            "split": split,
            "error": str(exc),
            "row_count": 0,
            "sample_rows": [],
        }


def probe_artifact_write(*, output_dir: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "preflight_probe.json"
        body = payload or {"status": "ok", "created_at": datetime.now(timezone.utc).isoformat()}
        target.write_text(json.dumps(body, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return {"ok": True, "path": str(target)}
    except Exception as exc:
        return {"ok": False, "path": str(output_dir / "preflight_probe.json"), "error": str(exc)}


def _first_training_text(rows: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for row in rows:
        if isinstance(row.get("text"), str) and row["text"].strip():
            texts.append(row["text"].strip())
        else:
            instruction = str(row.get("instruction") or row.get("prompt") or "").strip()
            response = str(row.get("response") or row.get("output") or "").strip()
            if instruction and response:
                texts.append(f"User: {instruction}\nAssistant: {response}")
        if len(texts) >= 2:
            break
    return texts


def probe_micro_train(
    *,
    rows: list[dict[str, Any]],
    model_id: str,
    torch_module: Any | None = None,
    tokenizer_loader: Callable[[str], Any] | None = None,
    model_loader: Callable[[str], Any] | None = None,
    optimizer_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    texts = _first_training_text(rows)
    if not texts:
        return {"ok": False, "error": "no_text_rows_available", "loss": None}

    torch_mod = torch_module
    if torch_mod is None:
        import torch as imported_torch

        torch_mod = imported_torch

    if tokenizer_loader is None or model_loader is None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer_loader = tokenizer_loader or (lambda model_name: AutoTokenizer.from_pretrained(model_name, trust_remote_code=True))
        model_loader = model_loader or (
            lambda model_name: AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
        )

    optimizer_ctor = optimizer_factory or (lambda params: torch_mod.optim.AdamW(params, lr=1e-4))
    device = "cuda" if probe_gpu(torch_module=torch_mod).get("available") else "cpu"

    try:
        tokenizer = tokenizer_loader(model_id)
        model = model_loader(model_id)
        if getattr(tokenizer, "pad_token", None) is None and getattr(tokenizer, "eos_token", None) is not None:
            tokenizer.pad_token = tokenizer.eos_token

        if hasattr(model, "to"):
            model = model.to(device)
        if hasattr(model, "train"):
            model.train()

        encoded = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=128)
        if hasattr(encoded, "items"):
            encoded = dict(encoded.items())
        encoded = {key: value.to(device) if hasattr(value, "to") else value for key, value in encoded.items()}
        input_ids = encoded.get("input_ids")
        outputs = model(**encoded, labels=input_ids)
        loss = getattr(outputs, "loss", None)
        if loss is None:
            return {"ok": False, "error": "loss_missing", "loss": None}
        loss.backward()
        optimizer = optimizer_ctor(model.parameters())
        optimizer.step()
        optimizer.zero_grad()
        loss_value = float(loss.detach().cpu().item()) if hasattr(loss, "detach") else float(loss)
        return {
            "ok": True,
            "loss": round(loss_value, 6),
            "model_id": model_id,
            "device": device,
            "sample_count": len(texts),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "loss": None,
            "model_id": model_id,
            "device": device,
            "sample_count": len(texts),
        }


def summarize_failures(report: dict[str, Any], *, require_kaggle: bool, require_gpu: bool, require_micro_train: bool) -> list[str]:
    failures: list[str] = []
    runtime = report["runtime"]
    dependencies = report["dependencies"]
    dataset = report["dataset"]
    artifact = report["artifact"]
    micro_train = report["micro_train"]
    gpu = report["gpu"]

    if require_kaggle and not runtime.get("is_kaggle"):
        failures.append("runtime:not_kaggle")
    if not dependencies.get("ok"):
        failures.append("dependencies:missing")
    if require_gpu and not gpu.get("available"):
        failures.append("runtime:no_gpu")
    if not dataset.get("ok"):
        failures.append("dataset:unavailable")
    if not artifact.get("ok"):
        failures.append("artifact:write_failed")
    if require_micro_train and not micro_train.get("ok"):
        failures.append("micro_train:failed")
    return failures


def run_kaggle_preflight(
    *,
    dataset_repo: str = DEFAULT_DATASET_REPO,
    data_file: str | None = DEFAULT_DATA_FILE,
    split: str = "train",
    sample_size: int = 8,
    output_dir: Path | None = None,
    model_id: str = DEFAULT_MODEL_ID,
    require_kaggle: bool = False,
    require_gpu: bool = True,
    require_micro_train: bool = False,
    environ: dict[str, str] | None = None,
    importer: Callable[[str], Any] = importlib.import_module,
    load_dataset_fn: Callable[..., Any] | None = None,
    torch_module: Any | None = None,
    tokenizer_loader: Callable[[str], Any] | None = None,
    model_loader: Callable[[str], Any] | None = None,
    optimizer_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    env = environ or os.environ
    artifact_dir = output_dir or ARTIFACT_ROOT / f"preflight-{_utc_stamp()}"
    runtime = detect_runtime(environ=env)
    dependencies = probe_dependencies(importer=importer)

    torch_mod = torch_module
    if torch_mod is None and dependencies.get("ok"):
        try:
            torch_mod = importer("torch")
        except Exception:
            torch_mod = None

    gpu = probe_gpu(torch_module=torch_mod) if torch_mod is not None else {
        "available": False,
        "device_count": 0,
        "device_name": "",
        "reason": "torch_missing",
    }

    dataset = probe_dataset_access(
        dataset_repo=dataset_repo,
        data_file=data_file,
        split=split,
        sample_size=max(1, sample_size),
        load_dataset_fn=load_dataset_fn,
    )

    artifact = probe_artifact_write(
        output_dir=artifact_dir,
        payload={
            "dataset_repo": dataset_repo,
            "data_file": data_file,
            "split": split,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    micro_train = {
        "ok": False,
        "skipped": not require_micro_train,
        "loss": None,
        "model_id": model_id,
    }
    if require_micro_train and dataset.get("ok") and torch_mod is not None:
        micro_train = probe_micro_train(
            rows=dataset.get("sample_rows", []),
            model_id=model_id,
            torch_module=torch_mod,
            tokenizer_loader=tokenizer_loader,
            model_loader=model_loader,
            optimizer_factory=optimizer_factory,
        )
        micro_train["skipped"] = False

    report = {
        "schema_version": "scbe_kaggle_preflight_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime": runtime,
        "dependencies": dependencies,
        "gpu": gpu,
        "dataset": dataset,
        "artifact": artifact,
        "micro_train": micro_train,
        "config": {
            "dataset_repo": dataset_repo,
            "data_file": data_file,
            "split": split,
            "sample_size": sample_size,
            "model_id": model_id,
            "require_kaggle": require_kaggle,
            "require_gpu": require_gpu,
            "require_micro_train": require_micro_train,
            "artifact_dir": str(artifact_dir),
        },
    }
    failures = summarize_failures(
        report,
        require_kaggle=require_kaggle,
        require_gpu=require_gpu,
        require_micro_train=require_micro_train,
    )
    report["status"] = "passed" if not failures else "failed"
    report["failures"] = failures

    report_path = artifact_dir / "preflight_report.json"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a hard-fail Kaggle preflight for SCBE training notebooks.")
    parser.add_argument("--dataset-repo", default=DEFAULT_DATASET_REPO)
    parser.add_argument("--data-file", default=DEFAULT_DATA_FILE)
    parser.add_argument("--split", default="train")
    parser.add_argument("--sample-size", type=int, default=8)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--require-kaggle", action="store_true")
    parser.add_argument("--allow-cpu", dest="require_gpu", action="store_false")
    parser.add_argument("--micro-train", action="store_true")
    parser.set_defaults(require_gpu=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_dir = Path(args.output_dir) if args.output_dir else None
    report = run_kaggle_preflight(
        dataset_repo=args.dataset_repo,
        data_file=args.data_file,
        split=args.split,
        sample_size=max(1, int(args.sample_size)),
        output_dir=output_dir,
        model_id=args.model_id,
        require_kaggle=bool(args.require_kaggle),
        require_gpu=bool(args.require_gpu),
        require_micro_train=bool(args.micro_train),
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
